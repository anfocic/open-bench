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
from .start_run import start_run

REPO_ROOT = _config.repo_root()


def _drive_one_implementer(task: str,
                            model: str,
                            lock: threading.Lock,
                            log_path: pathlib.Path) -> tuple[str, int, float]:
    started = time.monotonic()
    rc = start_run(task, model, auto=True, worktree_lock=lock, log_path=log_path)
    return model, rc, time.monotonic() - started


def main() -> int:
    p = argparse.ArgumentParser(description="End-to-end: implementers → judges → aggregate.")
    p.add_argument("task", help="task name under bench/tasks/")
    p.add_argument("--concurrency", type=int, default=None,
                   help="parallel implementers (default: $IMPL_CONCURRENCY or 3)")
    args = p.parse_args()

    if args.concurrency is not None:
        concurrency = args.concurrency
    else:
        env = os.environ.get("IMPL_CONCURRENCY")
        concurrency = int(env) if env else 3
    if concurrency < 1:
        print(f"error: --concurrency must be >= 1, got {concurrency}", file=sys.stderr)
        return 2

    cfg = _config.load()
    implementers = list(cfg.implementers)
    if not implementers:
        print("error: no implementers in bench/config.json", file=sys.stderr)
        return 1

    ok_models: list[str] = []
    fail_models: list[str] = []
    results_lock = threading.Lock()

    print(f"==> implementer phase: {len(implementers)} model(s), concurrency={concurrency}")

    if concurrency <= 1:
        for model in implementers:
            print()
            print(f"--- {model} ---")
            rc = start_run(args.task, model, auto=True)
            if rc == 0:
                ok_models.append(model)
            else:
                print(f"WARN: {model} failed, continuing", file=sys.stderr)
                fail_models.append(model)
    else:
        lock = threading.Lock()
        log_paths: dict[str, pathlib.Path] = {}
        for model in implementers:
            lp = REPO_ROOT / "builds" / model / "last-impl.log"
            lp.parent.mkdir(parents=True, exist_ok=True)
            log_paths[model] = lp

        print(f"  logs: builds/<model>/last-impl.log")
        with cf.ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {
                pool.submit(_drive_one_implementer, args.task, m, lock, log_paths[m]): m
                for m in implementers
            }
            for fut in cf.as_completed(futures):
                model, rc, elapsed = fut.result()
                log_rel = log_paths[model].relative_to(REPO_ROOT)
                mark = "✓" if rc == 0 else "✗"
                extra = "" if rc == 0 else f" exit {rc}"
                print(f"  {mark} {model} ({elapsed:.0f}s){extra} — {log_rel}")
                with results_lock:
                    if rc == 0:
                        ok_models.append(model)
                    else:
                        fail_models.append(model)

        for model in fail_models:
            log = log_paths[model]
            print(f"\n--- tail {log.relative_to(REPO_ROOT)} ---", file=sys.stderr)
            try:
                lines = log.read_text(errors="replace").splitlines()
                for ln in lines[-40:]:
                    print(ln, file=sys.stderr)
            except OSError as e:
                print(f"  (could not read log: {e})", file=sys.stderr)

    print()
    print("==> judgment phase")
    rc_judge = subprocess.run(
        [sys.executable, "-m", "bench.scripts.start_judgments", "--auto", args.task],
        cwd=REPO_ROOT,
    ).returncode

    print()
    print("==> aggregate phase")
    rc_agg = subprocess.run(
        [sys.executable, "-m", "bench.scripts.aggregate_judges", args.task],
        cwd=REPO_ROOT,
    ).returncode

    print()
    print("==> done")
    print(f"ok:     {' '.join(ok_models) if ok_models else 'none'}")
    print(f"failed: {' '.join(fail_models) if fail_models else 'none'}")
    if rc_judge:
        print(f"judge phase exited {rc_judge}", file=sys.stderr)
    if rc_agg:
        print(f"aggregate phase exited {rc_agg}", file=sys.stderr)
    return 1 if (fail_models or rc_judge or rc_agg) else 0


if __name__ == "__main__":
    sys.exit(main())
