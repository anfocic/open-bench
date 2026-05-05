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
    runtime = "podman" if shutil.which("podman") else ("docker" if shutil.which("docker") else None)
    if runtime is None:
        raise RuntimeError("Neither podman nor docker is available on PATH")

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

    try:
        result = subprocess.run(
            argv,
            shell=False,
            capture_output=True,
            timeout=timeout,
        )
        exit_code = result.returncode
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = (exc.stdout or b"").decode("utf-8", errors="replace")
        stderr = (exc.stderr or b"").decode("utf-8", errors="replace")
        combined = stdout + stderr
        if len(combined) > 50000:
            combined = combined[:50000] + "\n... [truncated]"
        # Reconstruct stdout/stderr proportionally for truncation on timeout
        # Since we don't know the exact split after truncation, just split by halves
        # for simplicity, but the spec doesn't require exact split after truncation.
        half = len(stdout)
        if len(combined) > 50000:
            total = len(stdout) + len(stderr)
            if total > 0:
                split = int(50000 * len(stdout) / total)
            else:
                split = 0
            stdout = stdout[:split] + ("\n... [truncated]" if split < len(stdout) else "")
            stderr = stderr[:50000 - split] + ("\n... [truncated]" if (50000 - split) < len(stderr) else "")
        return f"exit={exit_code}\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"

    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")
    combined = stdout + stderr
    if len(combined) > 50000:
        total = len(stdout) + len(stderr)
        if total > 0:
            split = int(50000 * len(stdout) / total)
        else:
            split = 0
        stdout = stdout[:split] + ("\n... [truncated]" if split < len(stdout) else "")
        stderr = stderr[:50000 - split] + ("\n... [truncated]" if (50000 - split) < len(stderr) else "")

    return f"exit={exit_code}\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a command in an ephemeral sandbox container.")
    parser.add_argument("--image", default="debian:stable-slim")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--network", default="none", choices=["none", "bridge"])
    parser.add_argument("--memory", default="2g")
    parser.add_argument("--pids", type=int, default=512)
    parser.add_argument("--cpus", type=float, default=2.0)
    parser.add_argument("--workspace", default=os.getcwd())
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command after --")

    args = parser.parse_args()

    if args.command and args.command[0] == "--":
        args.command = args.command[1:]

    if not args.command:
        parser.error("No command provided. Use -- before the command.")

    command = " ".join(args.command)
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

    # Extract exit code from output
    first_line = output.splitlines()[0]
    exit_code = int(first_line.split("=", 1)[1])
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
