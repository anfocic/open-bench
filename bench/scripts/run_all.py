#!/usr/bin/env python3
"""run_all.py <task>

End-to-end driver: runs every implementer in bench/config.json with --auto,
then auto-drives all judges, then aggregates. Single command per task.

Each implementer runs sequentially (implementer parallelization is deferred;
see bench/plans/improvements.md). Failures in one model do not abort the
rest; a summary is printed at the end.
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _config  # noqa: E402

from start_run import start_run

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent


def main() -> int:
    p = argparse.ArgumentParser(description="End-to-end: implementers → judges → aggregate.")
    p.add_argument("task", help="task name under bench/tasks/")
    args = p.parse_args()

    cfg = _config.load()
    implementers = list(cfg.implementers)
    if not implementers:
        print("error: no implementers in bench/config.json", file=sys.stderr)
        return 1

    ok_models: list[str] = []
    fail_models: list[str] = []

    print(f"==> implementer phase: {len(implementers)} model(s)")
    for model in implementers:
        print()
        print(f"--- {model} ---")
        rc = start_run(args.task, model, auto=True)
        if rc == 0:
            ok_models.append(model)
        else:
            print(f"WARN: {model} failed, continuing", file=sys.stderr)
            fail_models.append(model)

    print()
    print("==> judgment phase")
    rc_judge = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "start_judgments.py"), "--auto", args.task],
    ).returncode

    print()
    print("==> aggregate phase")
    rc_agg = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "aggregate_judges.py"), args.task],
    ).returncode

    print()
    print("==> done")
    print(f"ok:     {' '.join(ok_models) if ok_models else 'none'}")
    print(f"failed: {' '.join(fail_models) if fail_models else 'none'}")
    return 1 if fail_models else 0


if __name__ == "__main__":
    sys.exit(main())