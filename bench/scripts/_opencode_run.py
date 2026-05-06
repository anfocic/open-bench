"""Non-interactive `opencode run` wrapper.

Used by --auto flows in start_run.py and start_judgments.py. Builds an
argv list for `opencode run` and inherits stdout/stderr so the user
sees the session live.

Pre-flight: confirms `opencode` is on PATH and responds to --version
before any side-effects, so a missing binary fails before we create
worktrees or packets.

Set OPENCODE_RUN_DRYRUN=1 to print the argv that would run and exit 0
without invoking opencode — useful for tests and for inspecting the
command before burning credits.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import _logging

log = _logging.get_logger(__name__)


class OpencodeNotAvailable(Exception):
    pass


def preflight() -> None:
    """Confirm opencode is callable. Raises OpencodeNotAvailable on miss."""
    if shutil.which("opencode") is None:
        raise OpencodeNotAvailable(
            "opencode binary not found on PATH. Install from https://opencode.ai "
            "or pass without --auto to fall back to the manual flow."
        )
    try:
        subprocess.run(
            ["opencode", "--version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        raise OpencodeNotAvailable(f"opencode --version failed: {e}") from e


def run(
    directory: str | Path,
    model: str,
    message: str,
    attachments: list[str | Path] | None = None,
    title: str | None = None,
    log_path: str | Path | None = None,
) -> int:
    """Invoke `opencode run` non-interactively.

    Returns the subprocess return code. With log_path=None (default),
    streams stdout/stderr live to the inherited tty. With log_path set,
    redirects both streams to that file — required when running multiple
    sessions concurrently so output doesn't interleave into mush.
    """
    preflight()

    argv: list[str] = [
        "opencode", "run",
        "--dir", str(directory),
        "--model", model,
        "--dangerously-skip-permissions",
    ]
    if title:
        argv += ["--title", title]
    for att in attachments or []:
        argv += ["--file", str(att)]
    argv.append(message)

    if os.environ.get("OPENCODE_RUN_DRYRUN") == "1":
        log.debug("DRYRUN argv: %s", argv)
        return 0

    if log_path is None:
        return subprocess.run(argv, check=False).returncode

    with open(log_path, "wb") as fh:
        return subprocess.run(
            argv, check=False, stdout=fh, stderr=subprocess.STDOUT
        ).returncode
