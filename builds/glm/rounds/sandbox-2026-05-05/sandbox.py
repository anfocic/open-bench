#!/usr/bin/env python3
"""Ephemeral sandboxed command runner using Podman or Docker."""

import argparse
import os
import shutil
import subprocess
import sys

MAX_OUTPUT = 50_000


def _find_runtime() -> str:
    for candidate in ("podman", "docker"):
        if shutil.which(candidate):
            return candidate
    raise RuntimeError(
        "Neither podman nor docker found on PATH. Install one to use sandbox.py."
    )


def sandbox_run(
    command: str,
    workspace: str | None = None,
    image: str = "debian:stable-slim",
    timeout: int = 60,
    network: str = "none",
    memory: str = "2g",
    pids: int = 512,
    cpus: float = 2.0,
) -> str:
    runtime = _find_runtime()

    argv = [
        runtime,
        "run",
        "--rm",
        "--pull=missing",
        f"--network={network}",
        f"--memory={memory}",
        f"--pids-limit={pids}",
        f"--cpus={cpus}",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
    ]

    if workspace is not None:
        argv += ["-v", f"{workspace}:/workspace:rw", "-w", "/workspace"]

    argv += [image, "sh", "-c", command]

    timed_out = False
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout_bytes = exc.stdout or b""
        stderr_bytes = exc.stderr or b""

    if not timed_out:
        stdout_bytes = proc.stdout
        stderr_bytes = proc.stderr
        exit_code = proc.returncode
    else:
        exit_code = 124

    stdout_str = stdout_bytes.decode("utf-8", errors="replace")
    stderr_str = stderr_bytes.decode("utf-8", errors="replace")

    combined = stdout_str + stderr_str
    if len(combined) > MAX_OUTPUT:
        combined = combined[:MAX_OUTPUT]
        if len(stdout_str) >= MAX_OUTPUT:
            stdout_str = combined
            stderr_str = ""
        else:
            stderr_str = combined[len(stdout_str):]

    return (
        f"exit={exit_code}\n"
        f"--- stdout ---\n"
        f"{stdout_str}"
        f"--- stderr ---\n"
        f"{stderr_str}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a command inside an ephemeral sandboxed container.",
    )
    parser.add_argument("--image", default="debian:stable-slim")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--network", choices=("none", "bridge"), default="none")
    parser.add_argument("--memory", default="2g")
    parser.add_argument("--pids", type=int, default=512)
    parser.add_argument("--cpus", type=float, default=2.0)
    parser.add_argument("--workspace", default=os.getcwd())

    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to run (preceded by --)",
    )

    args = parser.parse_args()

    cmd_parts = args.command
    if cmd_parts and cmd_parts[0] == "--":
        cmd_parts = cmd_parts[1:]

    if not cmd_parts:
        parser.error("No command provided. Usage: sandbox.py [options] -- COMMAND [ARG ...]")

    command_str = " ".join(cmd_parts)

    workspace = args.workspace if args.workspace else None

    result = sandbox_run(
        command=command_str,
        workspace=workspace,
        image=args.image,
        timeout=args.timeout,
        network=args.network,
        memory=args.memory,
        pids=args.pids,
        cpus=args.cpus,
    )

    print(result, end="")

    exit_line = result.split("\n", 1)[0]
    code = int(exit_line.split("=", 1)[1])
    sys.exit(code)


if __name__ == "__main__":
    main()