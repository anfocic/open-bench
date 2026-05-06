"""Task configuration loader.

Single source of truth for task shape: entrypoint filename, language,
test invocation, LOC counting method. Reads from
bench/tasks/<task>/task.json; returns round-1 defaults when absent so
existing tasks continue working without any changes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import _config

REPO_ROOT = _config.repo_root()

DEFAULTS: dict[str, Any] = {
    "entrypoint": "sandbox.py",
    "language": "python",
    "test_runner": "pytest",
    "test_invocation": ["python3", "-m", "pytest", "_eval_tests/", "-v", "--tb=short"],
    "loc_method": "non_blank_non_comment_lines",
}


def load(task: str) -> dict[str, Any]:
    """Read bench/tasks/<task>/task.json and merge with defaults.

    Missing keys fall back to DEFAULTS so that omitting the file entirely
    reproduces current round-1 behaviour.
    """
    path = REPO_ROOT / "bench" / "tasks" / task / "task.json"
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