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
    runner = shutil.which("podman") or shutil.which("docker")
    if runner is None:
        raise RuntimeError("Neither podman nor docker is available on PATH")

    argv = [
        runner,
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
        argv.extend(["-v", f"{workspace}:/workspace:rw", "-w", "/workspace"])

    argv.extend([image, "sh", "-c", command])

    try:
        result = subprocess.run(
            argv,
            shell=False,
            capture_output=True,
            timeout=timeout,
        )
        code = result.returncode
    except subprocess.TimeoutExpired:
        code = 124
        stdout = ""
        stderr = ""
    else:
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")

    combined = stdout + stderr
    if len(combined.encode("utf-8", errors="replace")) > 50000:
        # Truncate combined output to 50000 bytes while keeping valid UTF-8
        encoded = combined.encode("utf-8", errors="replace")
        truncated = encoded[:50000].decode("utf-8", errors="replace")
        # Split truncated text back into stdout/stderr proportionally
        stdout_ratio = len(stdout) / max(len(combined), 1)
        split_point = int(len(truncated) * stdout_ratio)
        stdout = truncated[:split_point]
        stderr = truncated[split_point:] + "\n... [truncated]"

    return f"exit={code}\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"


def _main() -> None:
    parser = argparse.ArgumentParser(description="Run a command in an ephemeral sandbox container.")
    parser.add_argument("--image", default="debian:stable-slim")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--network", default="none", choices=["none", "bridge"])
    parser.add_argument("--memory", default="2g")
    parser.add_argument("--pids", type=int, default=512)
    parser.add_argument("--cpus", type=float, default=2.0)
    parser.add_argument("--workspace", default=os.getcwd())
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to run after --")

    args = parser.parse_args()

    if args.command and args.command[0] == "--":
        args.command = args.command[1:]

    if not args.command:
        parser.error("No command provided after --")

    command = " ".join(args.command)
    workspace = args.workspace if os.path.isdir(args.workspace) else None

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
    _main()
