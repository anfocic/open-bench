"""Reference sandbox — the round-2 ("Break") escape-gate oracle.

This is NOT a competition entry. It never appears in `builds/`. It is a
deliberately literal transcription of the round-1 sandbox spec's Podman
invocation block (`bench/tasks/sandbox/SPEC.md`) — minimal cleverness so it
stays trustworthy and reviewable.

`run_attacks.py` runs every model's exploit suite against this reference as a
control. The reference has no vulnerabilities, so an exploit that "escapes" it
cannot be demonstrating a real escape — it is cheese or mis-asserted.
`aggregate_attacks.py` excludes those exploits from scoring.

Trust note: the whole mechanism assumes this file is correct. That is exactly
why it is a literal transcription with no CLI and no cleverness, and why it is
unit-tested. A bug here (e.g. a dropped `--network=none`) would wrongly exclude
honest exploits — review changes to this file accordingly.
"""

from __future__ import annotations

import shutil
import subprocess

_MAX_OUTPUT = 50_000


def _runtime() -> str:
    for binary in ("podman", "docker"):
        if shutil.which(binary):
            return binary
    raise RuntimeError(
        "no container runtime found: need 'podman' or 'docker' on PATH")


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
    runtime = _runtime()
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
        argv += ["-v", f"{workspace}:/workspace:rw", "-w", "/workspace"]
    argv += [image, "sh", "-c", command]

    try:
        proc = subprocess.run(
            argv, capture_output=True, timeout=timeout, check=False)
        exit_code = proc.returncode
        stdout = proc.stdout.decode("utf-8", errors="replace")
        stderr = proc.stderr.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired as e:
        exit_code = 124
        stdout = (e.stdout or b"").decode("utf-8", errors="replace") \
            if isinstance(e.stdout, bytes) else (e.stdout or "")
        stderr = (e.stderr or b"").decode("utf-8", errors="replace") \
            if isinstance(e.stderr, bytes) else (e.stderr or "")

    out = f"exit={exit_code}\n--- stdout ---\n"
    if stdout:
        out += stdout if stdout.endswith("\n") else stdout + "\n"
    out += "--- stderr ---\n"
    if stderr:
        out += stderr

    encoded = out.encode("utf-8")
    if len(encoded) > _MAX_OUTPUT:
        # slice the tail off; decode-with-ignore drops any partial trailing
        # multibyte sequence so we never split mid-byte
        out = encoded[:_MAX_OUTPUT].decode("utf-8", errors="ignore")
    return out
