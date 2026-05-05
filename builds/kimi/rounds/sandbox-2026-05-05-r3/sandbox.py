"""sandbox.py — ephemeral, network-isolated, resource-capped containers."""

import argparse
import os
import shutil
import subprocess
import sys


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
    engine = shutil.which("podman") or shutil.which("docker")
    if engine is None:
        raise RuntimeError("Neither podman nor docker found on PATH")

    cmd = [
        engine,
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
        cmd += ["-v", f"{workspace}:/workspace:rw", "-w", "/workspace"]

    cmd += [image, "sh", "-c", command]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            shell=False,
            timeout=timeout,
        )
        exit_code = result.returncode
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
    else:
        stdout = result.stdout
        stderr = result.stderr

    stdout_text = stdout.decode("utf-8", errors="replace")
    stderr_text = stderr.decode("utf-8", errors="replace")

    combined = f"--- stdout ---\n{stdout_text}--- stderr ---\n{stderr_text}"
    header = f"exit={exit_code}\n"
    total = header + combined

    max_bytes = 50_000
    if len(total.encode("utf-8", errors="replace")) > max_bytes:
        # Truncate combined output, keeping header intact.
        header_bytes = header.encode("utf-8", errors="replace")
        remaining = max_bytes - len(header_bytes) - len("\n... [truncated]")
        combined_bytes = combined.encode("utf-8", errors="replace")
        truncated = combined_bytes[:remaining].decode("utf-8", errors="replace")
        total = header + truncated + "\n... [truncated]"

    return total


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Run a command in an ephemeral sandbox container."
    )
    parser.add_argument("--image", default="debian:stable-slim")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--network", default="none", choices=["none", "bridge"])
    parser.add_argument("--memory", default="2g")
    parser.add_argument("--pids", type=int, default=512)
    parser.add_argument("--cpus", type=float, default=2.0)
    parser.add_argument("--workspace", default=os.getcwd())
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if args.command and args.command[0] == "--":
        args.command = args.command[1:]

    if not args.command:
        parser.error("No command provided after --")

    command = " ".join(args.command)
    workspace = args.workspace if args.workspace else None

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
    sys.exit(int(output.splitlines()[0].split("=")[1]))


if __name__ == "__main__":
    _cli()
