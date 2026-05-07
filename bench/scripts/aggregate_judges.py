#!/usr/bin/env python3
"""aggregate_judges.py <task>

Reads the latest judgment phase under results/judgments/<task>-<date>/ and
delegates rendering to the task kind's `aggregate(...)` method, which
writes the report at results/reviews/<task>-<date>.md.

Inputs (orchestrator-level, kind-agnostic):
- pairings.json
- runs_index.json
- judgment_meta.json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from . import _config
from . import _kinds
from . import _logging
from . import _task

log = _logging.get_logger(__name__)

REPO_ROOT = _config.repo_root()


def latest_judgment_dir(task: str) -> pathlib.Path | None:
    base = REPO_ROOT / "results" / "judgments"
    if not base.is_dir():
        return None
    candidates = sorted(
        d for d in base.iterdir() if d.is_dir() and d.name.startswith(f"{task}-")
    )
    return candidates[-1] if candidates else None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("task", help="task name under bench/tasks/")
    p.add_argument("--judgment-dir",
                   help="explicit judgment dir under results/judgments/ "
                        "(default: latest matching task)")
    p.add_argument("--quiet", "-q", action="store_true",
                   help="warnings + errors only")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="debug output")
    args = p.parse_args()
    _logging.setup_logging(quiet=args.quiet, verbose=args.verbose)

    if args.judgment_dir:
        judgment_dir = pathlib.Path(args.judgment_dir)
        if not judgment_dir.is_absolute():
            judgment_dir = REPO_ROOT / args.judgment_dir
    else:
        judgment_dir = latest_judgment_dir(args.task)
    if judgment_dir is None or not judgment_dir.is_dir():
        log.error("no judgment dir found for task '%s'", args.task)
        return 1

    pairings_file = judgment_dir / "pairings.json"
    if not pairings_file.exists():
        log.error("%s missing", pairings_file)
        return 1
    pairings = json.loads(pairings_file.read_text())

    runs_index_file = judgment_dir / "runs_index.json"
    if not runs_index_file.exists():
        log.error("%s missing", runs_index_file)
        return 1
    runs_index = json.loads(runs_index_file.read_text())

    judgment_meta_file = judgment_dir / "judgment_meta.json"
    if not judgment_meta_file.exists():
        log.error("%s missing", judgment_meta_file)
        return 1
    judgment_meta = json.loads(judgment_meta_file.read_text())
    date_stamp = judgment_meta.get("date_stamp")
    if not date_stamp:
        log.error("%s missing 'date_stamp' field", judgment_meta_file)
        return 1

    log.info("aggregating from %s", judgment_dir.relative_to(REPO_ROOT))
    log.info("  judges: %s", ", ".join(pairings.keys()))
    log.info("  impls:  %s", ", ".join(runs_index.keys()))

    try:
        task_cfg = _task.load(args.task)
    except FileNotFoundError:
        # task.json may be missing in test fixtures; default to code kind.
        task_cfg = {}
    kind = _kinds.get(task_cfg.get("task_kind", "code"))

    review_md = kind.aggregate(
        judgment_dir=judgment_dir,
        judgment_meta=judgment_meta,
        pairings=pairings,
        runs_index=runs_index,
        repo_root=REPO_ROOT,
    )

    review_path = REPO_ROOT / "results" / "reviews" / f"{args.task}-{date_stamp}.md"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(review_md)
    log.info("wrote %s (%d lines)",
             review_path.relative_to(REPO_ROOT),
             sum(1 for _ in review_md.splitlines()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
