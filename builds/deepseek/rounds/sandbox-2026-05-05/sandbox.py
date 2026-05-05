#!/usr/bin/env python3

import argparse
import os
import shutil
import subprocess
import sys


def _find_runtime():
    for runtime in ("podman", "docker"):
        if shutil.which(runtime):
            return runtime
    raise RuntimeError("Neither podman nor docker found on PATH")


def _truncate(s, max_bytes=50000):
    marker = "... [truncated]"
    if len(s.encode("utf-8")) <= max_bytes:
        return s
    marker_b = len(marker.encode("utf-8"))
    lo, hi = 0, len(s)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if len(s[:mid].encode("utf-8")) + marker_b <= max_bytes:
            lo = mid
        else:
            hi = mid - 1
    return s[:lo] + marker


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
        argv.extend(["-v", f"{os.path.abspath(workspace)}:/workspace:rw", "-w", "/workspace"])

    argv.extend([image, "sh", "-c", command])

    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            timeout=timeout,
            shell=False,
        )
        exit_code = proc.returncode
        stdout = proc.stdout.decode("utf-8", errors="replace")
        stderr = proc.stderr.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        exit_code = 124
        stdout = ""
        stderr = ""

    parts = [f"exit={exit_code}"]
    parts.append("--- stdout ---")
    if stdout:
        parts.append(stdout.rstrip("\n"))
    parts.append("--- stderr ---")
    if stderr:
        parts.append(stderr)

    result = "\n".join(parts) + "\n"

    return _truncate(result)


def main():
    parser = argparse.ArgumentParser(
        description="Run a command inside an ephemeral, resource-capped container."
    )
    parser.add_argument("--image", default="debian:stable-slim")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--network", choices=["none", "bridge"], default="none")
    parser.add_argument("--memory", default="2g")
    parser.add_argument("--pids", type=int, default=512)
    parser.add_argument("--cpus", type=float, default=2.0)
    parser.add_argument("--workspace", default=None)

    args, remainder = parser.parse_known_args()

    if remainder and remainder[0] == "--":
        remainder = remainder[1:]

    if not remainder:
        parser.error("no command provided; use -- COMMAND [ARG ...]")

    command = " ".join(remainder)
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

    first_line = output.split("\n")[0]
    if first_line.startswith("exit="):
        sys.exit(int(first_line[5:]))
    sys.exit(1)


if __name__ == "__main__":
    main()
