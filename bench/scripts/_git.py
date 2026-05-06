"""Shared git wrapper for bench/ scripts.

Both capture_run.py and start_run.py used to carry an identical private
copy of this; both now import from here.
"""

from __future__ import annotations

import pathlib
import subprocess


def run_git(
    *args: str,
    cwd: pathlib.Path | str | None = None,
    check: bool = True,
) -> str:
    """Run `git <args>` and return stdout.

    With `check=True` (default), a non-zero return code raises
    `RuntimeError` with the failing argv and the captured stderr. With
    `check=False`, stdout is returned regardless of return code so the
    caller can branch on partial output.
    """
    result = subprocess.run(
        ["git"] + list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed: {result.stderr.strip()}"
        )
    return result.stdout
