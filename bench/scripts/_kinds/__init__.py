"""Task-kind plugin registry.

Each task declares `task_kind` in its task.json (default: "code").
The registry maps that string to a class; `get(name)` returns a fresh
instance. Methods on the kind classes grow incrementally as logic is
carved out of capture_run / start_judgments / aggregate_judges.
"""

from __future__ import annotations

from .code import CodeTask

KINDS: dict[str, type] = {
    "code": CodeTask,
}


def get(name: str):
    if name not in KINDS:
        raise ValueError(
            f"unknown task_kind {name!r}; known kinds: {sorted(KINDS)}"
        )
    return KINDS[name]()
