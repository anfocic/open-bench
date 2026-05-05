"""sandbox.py — ephemeral, network-isolated, resource-capped container runner."""

import argparse
import os
import shutil
import subprocess
import sys

_MAX_OUTPUT_BYTES = 50_000
_TRUNCATION_MARKER = "... [truncated]"


def _find_runtime() -> str:
    """Return 'podman' or 'docker', or raise RuntimeError."""
    for exe in ("podman", "docker"):
        if shutil.which(exe):
            return exe
    raise RuntimeError("Neither podman nor docker found on PATH")


def _format_output(exit_code: int, stdout: str, stderr: str) -> str:
    """Build the formatted output string, truncated to _MAX_OUTPUT_BYTES."""
    parts = [
        f"exit={exit_code}\n",
        "--- stdout ---\n",
        stdout,
        "--- stderr ---\n",
        stderr,
    ]
    result = "".join(parts)
    encoded = result.encode("utf-8")
    if len(encoded) <= _MAX_OUTPUT_BYTES:
        return result
    cap = _MAX_OUTPUT_BYTES - len(_TRUNCATION_MARKER.encode("utf-8"))
    truncated = encoded[:cap].decode("utf-8", errors="ignore")
    return truncated + _TRUNCATION_MARKER


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
        abs_ws = os.path.abspath(workspace)
        argv.extend(["-v", f"{abs_ws}:/workspace:rw", "-w", "/workspace"])

    argv.extend([image, "sh", "-c", command])

    exit_code = 124
    stdout = ""
    stderr = ""

    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            timeout=timeout,
        )
        exit_code = result.returncode
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"").decode("utf-8", errors="replace")
        stderr = (exc.stderr or b"").decode("utf-8", errors="replace")

    return _format_output(exit_code, stdout, stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a command in an ephemeral sandbox")
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
        parser.error("no command given (use -- to separate flags from command)")

    cmd_args = list(args.command)
    if cmd_args and cmd_args[0] == "--":
        cmd_args = cmd_args[1:]
    if not cmd_args:
        parser.error("no command given (use -- to separate flags from command)")

    command = " ".join(cmd_args)

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

    try:
        exit_code = int(output.split("\n")[0].split("=")[1])
    except (ValueError, IndexError):
        exit_code = 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
