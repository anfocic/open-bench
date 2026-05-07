"""Task configuration loader.

Single source of truth for task shape (entrypoint filename, language,
test invocation, LOC counting method) and for resolving the on-disk
location of a task. Reads from <tasks_dir>/<task>/task.json; returns
defaults when absent so existing tasks continue working without any
changes.

`tasks_dir()` honours OPENBENCH_TASKS_DIR when set so a downstream
consumer can run the harness against its own task tree without forking.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from . import _config

DEFAULTS: dict[str, Any] = {
    "entrypoint": "sandbox.py",
    "language": "python",
    "test_runner": "pytest",
    "test_invocation": ["python3", "-m", "pytest", "_eval_tests/", "-v", "--tb=short"],
    "loc_method": "non_blank_non_comment_lines",
}


def tasks_dir() -> Path:
    """Resolve the directory that holds task definitions. Defaults to
    <repo_root>/bench/tasks; OPENBENCH_TASKS_DIR overrides."""
    override = os.environ.get("OPENBENCH_TASKS_DIR")
    if override:
        return Path(override).expanduser()
    return _config.repo_root() / "bench" / "tasks"


def task_dir(name: str) -> Path:
    """Path to a single task under the active tasks directory."""
    return tasks_dir() / name


def require(name: str, files: Iterable[str] = ()) -> Path:
    """Resolve task_dir(name) and verify it (plus any required files)
    exists. Returns the resolved task_dir. Raises FileNotFoundError
    naming the specific missing path so callers can surface it as-is.
    """
    d = task_dir(name)
    if not d.is_dir():
        raise FileNotFoundError(f"no task at {d}")
    for fname in files:
        if not (d / fname).exists():
            raise FileNotFoundError(f"task missing {fname}: {d / fname}")
    return d


def load(task: str) -> dict[str, Any]:
    """Read <tasks_dir>/<task>/task.json and merge with defaults.

    Missing keys fall back to DEFAULTS so that omitting the file entirely
    reproduces current round-1 behaviour.
    """
    path = task_dir(task) / "task.json"
    if path.exists():
        with open(path) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise SystemExit(f"malformed JSON in {path}: {e}")
    else:
        data = {}
    merged = dict(DEFAULTS)
    merged.update(data)
    return merged


def loc_count(path: Path, method: str) -> int:
    """Count implementation lines per loc_method.

    Methods:
      - non_blank_non_comment_lines: exclude blank lines and full-line
        comments (Python).  Matches the old ``grep -cvE '^\\s*(#|$)'``.
      - wc_l: raw line count.
    """
    text = path.read_text(errors="replace")
    if method == "non_blank_non_comment_lines":
        return sum(
            1 for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        )
    return sum(1 for _ in text.splitlines())