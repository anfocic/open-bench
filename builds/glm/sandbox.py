#!/usr/bin/env python3
"""sandbox.py - run commands inside ephemeral containers."""

import argparse
import os
import shutil
import subprocess
import sys


def _find_runtime() -> str:
    for runtime in ("podman", "docker"):
        if shutil.which(runtime):
            return runtime
    raise RuntimeError(
        "Neither podman nor docker found on PATH. "
        "Install one to use sandbox.py."
    )


def _truncate_output(s: str, max_bytes: int = 50000) -> str:
    encoded = s.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return s
    marker = "\n... [truncated]"
    target = max_bytes - len(marker.encode("utf-8"))
    byte_count = 0
    cut = 0
    for i, char in enumerate(s):
        char_bytes = len(char.encode("utf-8"))
        if byte_count + char_bytes > target:
            break
        byte_count += char_bytes
        cut = i + 1
    return s[:cut] + marker


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
        argv += [
            "-v", f"{os.path.abspath(workspace)}:/workspace:rw",
            "-w", "/workspace",
        ]
    argv += [image, "sh", "-c", command]

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
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = (exc.stdout or b"").decode("utf-8", errors="replace")
        stderr = (exc.stderr or b"").decode("utf-8", errors="replace")

    parts = [f"exit={exit_code}\n--- stdout ---\n"]
    if stdout:
        parts.append(stdout)
        if not stdout.endswith("\n"):
            parts.append("\n")
    parts.append("--- stderr ---\n")
    if stderr:
        parts.append(stderr)

    return _truncate_output("".join(parts))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a command inside an ephemeral container"
    )
    parser.add_argument("--image", default="debian:stable-slim")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--network", choices=["none", "bridge"], default="none")
    parser.add_argument("--memory", default="2g")
    parser.add_argument("--pids", type=int, default=512)
    parser.add_argument("--cpus", type=float, default=2.0)
    parser.add_argument("--workspace", default=os.getcwd())
    parser.add_argument("command", nargs="+")

    args = parser.parse_args()
    command = " ".join(args.command)
    workspace = args.workspace if args.workspace else None

    result = sandbox_run(
        command=command,
        workspace=workspace,
        image=args.image,
        timeout=args.timeout,
        network=args.network,
        memory=args.memory,
        pids=args.pids,
        cpus=args.cpus,
    )
    sys.stdout.write(result)
    sys.stdout.flush()
    exit_code = int(result.split("\n")[0].split("=")[1])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()