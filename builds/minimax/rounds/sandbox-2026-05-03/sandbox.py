import argparse
import os
import shutil
import subprocess
import sys


def _container_cmd():
    for candidate in ("podman", "docker"):
        if shutil.which(candidate) is not None:
            return candidate
    raise RuntimeError("neither podman nor docker is on PATH")


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
    container = _container_cmd()

    argv = [
        container, "run", "--rm", "--pull=missing",
        "--network=" + network,
        "--memory=" + memory,
        "--pids-limit=" + str(pids),
        "--cpus=" + str(cpus),
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
    ]

    if workspace is not None:
        argv += ["-v", workspace + ":/workspace:rw", "-w", "/workspace"]

    argv += [image, "sh", "-c", command]

    try:
        result = subprocess.run(argv, capture_output=True, timeout=timeout, shell=False)
        exit_code = result.returncode
    except subprocess.TimeoutExpired:
        exit_code = 124

    stdout = result.stdout if exit_code != 124 else b""
    stderr = result.stderr if exit_code != 124 else b""

    combined = stdout + stderr
    if len(combined) > 50000:
        marker = b"... [truncated]"
        if len(stdout) > 50000 - len(marker):
            stdout = stdout[: 50000 - len(marker)] + marker
            stderr = b""
        elif len(stderr) > 0:
            stderr = stderr[: 50000 - len(marker)] + marker

    return (
        "exit=" + str(exit_code) + "\n"
        "--- stdout ---\n"
        + stdout.decode("utf-8", errors="replace")
        + "--- stderr ---\n"
        + stderr.decode("utf-8", errors="replace")
    )


def _cli():
    parser = argparse.ArgumentParser(prog="sandbox.py", add_help=False)
    parser.add_argument("--image", default="debian:stable-slim")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--network", default="none")
    parser.add_argument("--memory", default="2g")
    parser.add_argument("--pids", type=int, default=512)
    parser.add_argument("--cpus", type=float, default=2.0)
    parser.add_argument("--workspace", default=os.getcwd())
    parser.add_argument("--", dest="separator", action="store_true")
    parser.add_argument("command", nargs="+")
    args = parser.parse_args()

    cmd = " ".join(args.command)

    output = sandbox_run(
        command=cmd,
        workspace=args.workspace,
        image=args.image,
        timeout=args.timeout,
        network=args.network,
        memory=args.memory,
        pids=args.pids,
        cpus=args.cpus,
    )
    print(output)
    exit_line = output.split("\n")[0]
    exit_code = int(exit_line.split("=")[1])
    sys.exit(exit_code)


if __name__ == "__main__":
    _cli()