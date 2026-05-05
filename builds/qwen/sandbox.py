#!/usr/bin/env python3
"""sandbox.py — ephemeral, network-isolated, resource-capped container runner."""

import argparse
import os
import shutil
import subprocess
import sys


def _find_runtime():
    """Return 'podman' or 'docker', or raise RuntimeError."""
    for name in ("podman", "docker"):
        if shutil.which(name):
            return name
    raise RuntimeError("Neither podman nor docker is available on PATH.")


def _format_output(exit_code: int, stdout: str, stderr: str) -> str:
    """Build the output string and truncate to 50,000 bytes."""
    stdout_body = stdout.rstrip("\n")
    lines = [
        f"exit={exit_code}",
        "--- stdout ---",
    ]
    if stdout_body:
        lines.append(stdout_body)
    lines.append("--- stderr ---")
    if stderr:
        lines.append(stderr.rstrip("\n"))
    result = "\n".join(lines) + "\n"
    cap = 50_000
    encoded = result.encode("utf-8")
    if len(encoded) > cap:
        truncated = encoded[:cap].decode("utf-8", errors="ignore")
        result = truncated + "... [truncated]"
    return result


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
    """Run *command* inside an ephemeral container and return formatted output."""
    runtime = _find_runtime()

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
        abs_workspace = os.path.abspath(workspace)
        argv.extend(["-v", f"{abs_workspace}:/workspace:rw", "-w", "/workspace"])

    argv.extend([image, "sh", "-c", command])

    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            timeout=timeout,
        )
        exit_code = result.returncode
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        exit_code = 124
        stdout = ""
        stderr = ""

    return _format_output(exit_code, stdout, stderr)


def main():
    parser = argparse.ArgumentParser(description="Run a command in an ephemeral sandbox.")
    parser.add_argument("--image", default="debian:stable-slim")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--network", default="none", choices=("none", "bridge"))
    parser.add_argument("--memory", default="2g")
    parser.add_argument("--pids", type=int, default=512)
    parser.add_argument("--cpus", type=float, default=2.0)
    parser.add_argument("--workspace", default=os.getcwd())
    parser.add_argument("command", nargs=argparse.REMAINDER)

    args = parser.parse_args()

    if not args.command:
        parser.error("COMMAND is required after --")

    cmd_parts = args.command
    if cmd_parts[0] == "--":
        cmd_parts = cmd_parts[1:]
    if not cmd_parts:
        parser.error("COMMAND is required after --")

    command = " ".join(cmd_parts)

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
    sys.exit(int(output.split("\n")[0].split("=")[1]))


if __name__ == "__main__":
    main()
