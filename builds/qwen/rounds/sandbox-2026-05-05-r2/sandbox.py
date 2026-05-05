"""sandbox.py — ephemeral container command runner (v0.1)."""

import argparse
import os
import shutil
import subprocess
import sys

_MAX_OUTPUT = 50_000


def _find_runtime() -> str:
    for exe in ("podman", "docker"):
        if shutil.which(exe):
            return exe
    raise RuntimeError("Neither podman nor docker found on PATH")


def _format_output(exit_code: int, stdout: str, stderr: str) -> str:
    lines = [f"exit={exit_code}\n", "--- stdout ---\n"]
    if stdout:
        lines.append(stdout)
        if not stdout.endswith("\n"):
            lines.append("\n")
    lines.append("--- stderr ---\n")
    if stderr:
        lines.append(stderr)
    result = "".join(lines)
    encoded = result.encode("utf-8")
    if len(encoded) > _MAX_OUTPUT:
        truncated = encoded[:_MAX_OUTPUT].decode("utf-8", errors="ignore")
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
        parser.error("no command provided")

    parts = [p for p in args.command if p != "--"]
    if not parts:
        parser.error("no command provided")
    command = " ".join(parts)

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
