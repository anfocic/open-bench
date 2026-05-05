#!/usr/bin/env python3
"""Ephemeral, network-isolated, resource-capped container runner."""

import argparse
import os
import shutil
import subprocess
import sys


def _get_container_runtime():
    if shutil.which("podman"):
        return "podman"
    if shutil.which("docker"):
        return "docker"
    raise RuntimeError("Neither podman nor docker is available on PATH")


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
    runtime = _get_container_runtime()

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
        argv.extend(["-v", f"{workspace}:/workspace:rw", "-w", "/workspace"])

    argv.extend([image, "sh", "-c", command])

    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            timeout=timeout,
            shell=False,
        )
        exit_code = result.returncode
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        exit_code = 124
        stdout = ""
        stderr = ""

    output = f"exit={exit_code}\n--- stdout ---\n{stdout}--- stderr ---\n{stderr}"

    if len(output) > 50000:
        decoded = output.encode("utf-8")[:50000].decode("utf-8", errors="replace")
        output = decoded + "\n... [truncated]"

    return output


def _cli():
    parser = argparse.ArgumentParser(prog="sandbox.py")
    parser.add_argument("--image", default="debian:stable-slim")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--network", default="none", choices=["none", "bridge"])
    parser.add_argument("--memory", default="2g")
    parser.add_argument("--pids", type=int, default=512)
    parser.add_argument("--cpus", type=float, default=2.0)
    parser.add_argument("--workspace", default=None)
    parser.add_argument("command", nargs="*")

    args = parser.parse_args()

    if "--" in args.command:
        idx = args.command.index("--")
        command_parts = args.command[idx + 1:]
    else:
        command_parts = args.command

    if not command_parts:
        parser.error("No command provided")

    workspace = args.workspace if args.workspace is not None else os.getcwd()

    output = sandbox_run(
        command=" ".join(command_parts),
        workspace=workspace,
        image=args.image,
        timeout=args.timeout,
        network=args.network,
        memory=args.memory,
        pids=args.pids,
        cpus=args.cpus,
    )

    print(output, end="")

    exit_match = output.split("\n")[0]
    exit_code = int(exit_match.split("=")[1])
    sys.exit(exit_code)


if __name__ == "__main__":
    _cli()