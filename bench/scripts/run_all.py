#!/usr/bin/env python3
"""run_all.py <task>

End-to-end driver: runs every implementer in bench/config.json with --auto,
then auto-drives all judges, then aggregates. Single command per task.

Implementers run in parallel by default (concurrency=3, override via
--concurrency or IMPL_CONCURRENCY). git worktree creation is serialized
through a shared lock — only the slow opencode + capture phases overlap.

Failures in one model do not abort the rest; a summary is printed at the
end.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import os
import pathlib
import subprocess
import sys
import threading
import time

from . import _config
from . import _logging
from .start_run import start_run

log = _logging.get_logger(__name__)

REPO_ROOT = _config.repo_root()


def _drive_one_implementer(task: str,
                            model: str,
                            lock: threading.Lock,
                            log_path: pathlib.Path) -> tuple[str, int, float]:
    started = time.monotonic()
    rc = start_run(task, model, auto=True, worktree_lock=lock, log_path=log_path)
    return model, rc, time.monotonic() - started


def main() -> int:
    p = argparse.ArgumentParser(description="End-to-end: implementers -> judges -> aggregate.")
    p.add_argument("task", help="task name under bench/tasks/")
    p.add_argument("--concurrency", type=int, default=None,
                   help="parallel implementers (default: $IMPL_CONCURRENCY or 3)")
    p.add_argument("--quiet", "-q", action="store_true",
                   help="warnings + errors only")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="debug output")
    args = p.parse_args()
    _logging.setup_logging(quiet=args.quiet, verbose=args.verbose)

    if args.concurrency is not None:
        concurrency = args.concurrency
    else:
        env = os.environ.get("IMPL_CONCURRENCY")
        concurrency = int(env) if env else 3
    if concurrency < 1:
        log.error("--concurrency must be >= 1, got %d", concurrency)
        return 2

    cfg = _config.load()
    implementers = list(cfg.implementers)
    if not implementers:
        log.error("no implementers in bench/config.json")
        return 1

    ok_models: list[str] = []
    fail_models: list[str] = []
    results_lock = threading.Lock()

    log.info("==> implementer phase: %d model(s), concurrency=%d",
             len(implementers), concurrency)

    if concurrency <= 1:
        for model in implementers:
            log.info("--- %s ---", model)
            rc = start_run(args.task, model, auto=True)
            if rc == 0:
                ok_models.append(model)
            else:
                log.warning("%s failed, continuing", model)
                fail_models.append(model)
    else:
        lock = threading.Lock()
        log_paths: dict[str, pathlib.Path] = {}
        for model in implementers:
            lp = REPO_ROOT / "builds" / model / "last-impl.log"
            lp.parent.mkdir(parents=True, exist_ok=True)
            log_paths[model] = lp

        log.info("logs: builds/<model>/last-impl.log")
        with cf.ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {
                pool.submit(_drive_one_implementer, args.task, m, lock, log_paths[m]): m
                for m in implementers
            }
            for fut in cf.as_completed(futures):
                model, rc, elapsed = fut.result()
                log_rel = log_paths[model].relative_to(REPO_ROOT)
                if rc == 0:
                    log.info("ok: %s (%.0fs) — %s", model, elapsed, log_rel)
                else:
                    log.error("fail: %s (%.0fs) exit %d — %s",
                              model, elapsed, rc, log_rel)
                with results_lock:
                    if rc == 0:
                        ok_models.append(model)
                    else:
                        fail_models.append(model)

        for model in fail_models:
            log_path = log_paths[model]
            log.error("--- tail %s ---", log_path.relative_to(REPO_ROOT))
            try:
                lines = log_path.read_text(errors="replace").splitlines()
                for ln in lines[-40:]:
                    print(ln, file=sys.stderr)
            except OSError as e:
                log.error("could not read log: %s", e)

    # Propagate verbosity to subprocess children so the format is consistent.
    child_flags: list[str] = []
    if args.quiet:
        child_flags.append("--quiet")
    if args.verbose:
        child_flags.append("--verbose")

    log.info("==> judgment phase")
    rc_judge = subprocess.run(
        [sys.executable, "-m", "bench.scripts.start_judgments", "--auto",
         *child_flags, args.task],
        cwd=REPO_ROOT,
    ).returncode

    log.info("==> aggregate phase")
    rc_agg = subprocess.run(
        [sys.executable, "-m", "bench.scripts.aggregate_judges",
         *child_flags, args.task],
        cwd=REPO_ROOT,
    ).returncode

    # Summary table — kept as print so it lands on stdout for piping.
    print()
    print("==> done")
    print(f"ok:     {' '.join(ok_models) if ok_models else 'none'}")
    print(f"failed: {' '.join(fail_models) if fail_models else 'none'}")
    if rc_judge:
        log.error("judge phase exited %d", rc_judge)
    if rc_agg:
        log.error("aggregate phase exited %d", rc_agg)
    return 1 if (fail_models or rc_judge or rc_agg) else 0


if __name__ == "__main__":
    sys.exit(main())
