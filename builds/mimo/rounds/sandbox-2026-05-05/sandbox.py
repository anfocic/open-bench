#!/usr/bin/env python3
"""sandbox.py — wraps Podman/Docker to run commands in ephemeral containers."""

import argparse
import os
import shutil
import subprocess
import sys

MAX_OUTPUT_BYTES = 50_000


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
    runtime = shutil.which("podman") or shutil.which("docker")
    if not runtime:
        raise RuntimeError("Neither 'podman' nor 'docker' found on PATH.")

    argv = [
        runtime, "run", "--rm", "--pull=missing",
        f"--network={network}",
        f"--memory={memory}",
        f"--pids-limit={pids}",
        f"--cpus={cpus}",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
    ]

    if workspace is not None:
        argv += ["-v", f"{os.path.abspath(workspace)}:/workspace:rw", "-w", "/workspace"]

    argv += [image, "sh", "-c", command]

    try:
        result = subprocess.run(argv, capture_output=True, timeout=timeout)
        exit_code = result.returncode
        stdout = result.stdout.decode(errors="replace")
        stderr = result.stderr.decode(errors="replace")
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = (exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout, bytes) else ""
        stderr = (exc.stderr or b"").decode(errors="replace") if isinstance(exc.stderr, bytes) else ""

    combined = f"exit={exit_code}\n--- stdout ---\n{stdout.rstrip(chr(10))}\n--- stderr ---\n{stderr.rstrip(chr(10))}"
    if len(combined) > MAX_OUTPUT_BYTES:
        combined = combined[:MAX_OUTPUT_BYTES] + "\n... [truncated]"
    return combined


def main():
    parser = argparse.ArgumentParser(description="Run a command in an ephemeral container.")
    parser.add_argument("--image", default="debian:stable-slim")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--network", default="none", choices=["none", "bridge"])
    parser.add_argument("--memory", default="2g")
    parser.add_argument("--pids", type=int, default=512)
    parser.add_argument("--cpus", type=float, default=2.0)
    parser.add_argument("--workspace", default=os.getcwd())
    args, remaining = parser.parse_known_args()
    command_parts = remaining
    if command_parts and command_parts[0] == "--":
        command_parts = command_parts[1:]
    if not command_parts:
        parser.error("Missing command after --")

    command = " ".join(command_parts)
    output = sandbox_run(
        command=command,
        workspace=args.workspace,
        image=args.image,
        timeout=args.timeout,
        network=args.network,
        memory=args.memory,
        pids=args.pids,
        cpus=args.cpus,
    )
    print(output, end="")

    # Extract exit code from output for process exit
    exit_line = output.split("\n", 1)[0]
    exit_code = int(exit_line.split("=", 1)[1])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
