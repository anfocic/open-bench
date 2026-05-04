import argparse
import os
import shutil
import subprocess
import sys
import uuid


_BYTE_LIMIT = 50000


def _resolve_runtime() -> str:
    if shutil.which("podman"):
        return "podman"
    if shutil.which("docker"):
        return "docker"
    raise RuntimeError("neither podman nor docker found on PATH")


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
    runtime = _resolve_runtime()

    container_name = f"sandbox-{uuid.uuid4().hex[:12]}"

    argv = [
        runtime,
        "run",
        "--rm",
        f"--name={container_name}",
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
        proc = subprocess.run(argv, capture_output=True, timeout=timeout, shell=False)
        exit_code = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired as exc:
        subprocess.run(
            [runtime, "kill", container_name],
            capture_output=True,
            timeout=5,
        )
        exit_code = 124
        stdout = exc.stdout if exc.stdout is not None else b""
        stderr = exc.stderr if exc.stderr is not None else b""

    stdout_str = stdout.decode("utf-8", errors="replace")
    stderr_str = stderr.decode("utf-8", errors="replace")

    result = f"exit={exit_code}\n--- stdout ---\n{stdout_str}--- stderr ---\n{stderr_str}"

    if len(result.encode("utf-8")) > _BYTE_LIMIT:
        result = result.encode("utf-8")[:_BYTE_LIMIT].decode("utf-8", errors="replace")
        result += "... [truncated]\n"

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a command in an ephemeral container.")
    parser.add_argument("--image", default="debian:stable-slim")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--network", choices=["none", "bridge"], default="none")
    parser.add_argument("--memory", default="2g")
    parser.add_argument("--pids", type=int, default=512)
    parser.add_argument("--cpus", type=float, default=2.0)
    parser.add_argument("--workspace", default=None)
    parser.add_argument("command", nargs=argparse.REMAINDER)

    args = parser.parse_args()

    if not args.command or args.command[0] != "--":
        parser.error("separate flags from command with --")
    command_str = " ".join(args.command[1:])

    ws = args.workspace if args.workspace is not None else os.getcwd()

    output = sandbox_run(
        command=command_str,
        workspace=ws,
        image=args.image,
        timeout=args.timeout,
        network=args.network,
        memory=args.memory,
        pids=args.pids,
        cpus=args.cpus,
    )

    sys.stdout.write(output)

    # Extract exit code from the output to propagate it.
    first_line = output.splitlines()[0] if output else ""
    if first_line.startswith("exit="):
        sys.exit(int(first_line[5:]))


if __name__ == "__main__":
    main()
