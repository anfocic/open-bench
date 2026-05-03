#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys

MAX_OUTPUT_BYTES = 50_000


def _find_runtime():
    if shutil.which("podman"):
        return "podman"
    if shutil.which("docker"):
        return "docker"
    raise RuntimeError("Neither podman nor docker found on PATH")


def _truncate(stdout: str, stderr: str) -> tuple[str, str]:
    marker = "\n... [truncated]"
    marker_bytes = len(marker.encode())

    stdout_bytes = stdout.encode(errors="replace")
    stderr_bytes = stderr.encode(errors="replace")
    total = len(stdout_bytes) + len(stderr_bytes)

    if total <= MAX_OUTPUT_BYTES:
        return stdout, stderr

    limit = MAX_OUTPUT_BYTES - marker_bytes
    if limit < 0:
        limit = 0

    if len(stdout_bytes) <= limit:
        stderr_limit = limit - len(stdout_bytes)
        stderr_truncated = stderr_bytes[:stderr_limit].decode(errors="replace") + marker
        return stdout, stderr_truncated
    else:
        stdout_truncated = stdout_bytes[:limit].decode(errors="replace") + marker
        return stdout_truncated, ""


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
        argv.extend([
            "-v", f"{os.path.abspath(workspace)}:/workspace:rw",
            "-w", "/workspace",
        ])

    argv.extend([image, "sh", "-c", command])

    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            timeout=timeout,
        )
        exit_code = proc.returncode
        stdout = proc.stdout.decode(errors="replace")
        stderr = proc.stderr.decode(errors="replace")
    except subprocess.TimeoutExpired:
        exit_code = 124
        stdout = ""
        stderr = ""

    stdout, stderr = _truncate(stdout, stderr)
    return (
        f"exit={exit_code}\n"
        f"--- stdout ---\n"
        f"{stdout}\n"
        f"--- stderr ---\n"
        f"{stderr}"
    )


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Run commands inside ephemeral, network-isolated containers.",
    )
    parser.add_argument("--image", default="debian:stable-slim")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--network", choices=["none", "bridge"], default="none")
    parser.add_argument("--memory", default="2g")
    parser.add_argument("--pids", type=int, default=512)
    parser.add_argument("--cpus", type=float, default=2.0)
    parser.add_argument("--workspace", default=None)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser.parse_args()


def main():
    args = _parse_args()
    cmd_parts = args.command
    if cmd_parts and cmd_parts[0] == "--":
        cmd_parts = cmd_parts[1:]
    if not cmd_parts:
        print("Error: no command provided", file=sys.stderr)
        sys.exit(1)
    command = " ".join(cmd_parts)

    workspace = args.workspace if args.workspace is not None else os.getcwd()

    output = sandbox_run(
        command=command,
        workspace=workspace,
        image=args.image,
        timeout=args.timeout,
        network=args.network,
        memory=args.memory,
        pids=args.pids,
        cpus=args.cpus,
    )
    print(output, end="")

    for line in output.split("\n"):
        if line.startswith("exit="):
            try:
                sys.exit(int(line.split("=", 1)[1]))
            except (ValueError, IndexError):
                pass
    sys.exit(1)


if __name__ == "__main__":
    main()
