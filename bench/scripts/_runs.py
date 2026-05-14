"""Shared run discovery.

Walks ``builds/<model>/rounds/<task>-<date>/`` and returns the latest
implementation run per model for a task, with identity read from each
run's ``meta.json`` (written by start_run.py, extended by capture_run.py).

Used by the judgment phase (``start_judgments.find_runs``) and the round-2
attack phase, which discovers both attackers (``exploit.py`` artifacts) and
targets (round-1 ``sandbox.py`` artifacts) through the same helper.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

from . import _config
from . import _logging

log = _logging.get_logger(__name__)


def find_latest_runs(
    task: str,
    entrypoint: str,
    repo_root: pathlib.Path | None = None,
) -> list[dict[str, Any]]:
    """Find the latest implementation run per model for ``task``.

    Identity (task, model, date_stamp, slug) is read from each run's
    meta.json. Run dirs without a parseable meta, without ``entrypoint``,
    or without a ``date_stamp`` are skipped with a warning.

    ``repo_root`` defaults to ``_config.repo_root()``; callers pass it
    explicitly to scope discovery to a fixture tree under test.
    """
    root = repo_root if repo_root is not None else _config.repo_root()
    by_model: dict[str, dict[str, Any]] = {}
    builds_root = root / "builds"
    if not builds_root.is_dir():
        return []

    for model_entry in sorted(builds_root.iterdir()):
        if not model_entry.is_dir() or model_entry.name.startswith("."):
            continue
        run_model = model_entry.name
        rounds_dir = model_entry / "rounds"
        if not rounds_dir.is_dir():
            continue

        for run_entry in sorted(rounds_dir.iterdir()):
            if not run_entry.is_dir():
                continue
            meta_path = run_entry / "meta.json"
            if not meta_path.exists():
                continue
            try:
                meta = json.loads(meta_path.read_text())
            except json.JSONDecodeError:
                log.warning("%s not valid JSON — skipping",
                            meta_path.relative_to(root))
                continue
            if meta.get("task") != task:
                continue

            impl = run_entry / entrypoint
            if not impl.exists():
                log.warning("%s has no %s — skipping",
                            run_entry.relative_to(root), entrypoint)
                continue

            date_stamp = meta.get("date_stamp")
            if not date_stamp:
                log.warning("%s missing 'date_stamp' — skipping",
                            meta_path.relative_to(root))
                continue

            existing = by_model.get(run_model)
            if existing is None or date_stamp > existing["date_stamp"]:
                by_model[run_model] = {
                    "model": run_model,
                    "date_stamp": date_stamp,
                    "run_dir": run_entry,
                    "impl_path": impl,
                    "meta": meta,
                }

    return list(by_model.values())
