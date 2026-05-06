#!/usr/bin/env python3
"""start_judgments.py <task>

Set up the judgment phase for a task. Reads all completed implementation
runs under <model>/<task>-<date>/ at the repo root, then builds per-judge
packets at results/judgments/<task>-<date>/<judge>/.

Each packet contains:
- PROMPT.md, SPEC.md, JUDGE_PROMPT.md, JUDGE_RUBRIC.md
- implementations/<label>.py (sandbox.py from each impl run, blinded)
- output/ (empty — judge writes filled rubrics + scores here)

Per-judge label assignments are random and stored in pairings.json so the
aggregator can demap.

Judges:
- claude, codex: judge all implementations
- each model judge: judges every implementation INCLUDING its own. Self-
  judgments are surfaced separately in the aggregator as a self-bias
  check and are excluded from the peer-median scoreboard.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import random
import re
import shutil
import string
import sys
import threading
from typing import Any

from . import _config
from . import _task

REPO_ROOT = _config.repo_root()


def find_runs(task: str, entrypoint: str) -> list[dict[str, Any]]:
    """Find latest implementation run per model for `task`.

    Layout: builds/<model>/rounds/<task>-<YYYY-MM-DD>/<entrypoint>.
    """
    by_model: dict[str, dict[str, Any]] = {}
    builds_root = REPO_ROOT / "builds"
    if not builds_root.is_dir():
        return []

    date_re = re.compile(r"^\d{4}-\d{2}-\d{2}(?:-r\d+)?$")
    prefix = f"{task}-"

    for model_entry in sorted(builds_root.iterdir()):
        if not model_entry.is_dir() or model_entry.name.startswith("."):
            continue
        run_model = model_entry.name
        rounds_dir = model_entry / "rounds"
        if not rounds_dir.is_dir():
            continue

        dated = [
            d for d in sorted(rounds_dir.iterdir())
            if d.is_dir()
            and d.name.startswith(prefix)
            and date_re.match(d.name[len(prefix):])
        ]
        if not dated:
            continue

        for run_entry in dated:
            run_date = run_entry.name[len(prefix):]
            impl = run_entry / entrypoint
            if not impl.exists():
                print(f"  warn: {run_entry.relative_to(REPO_ROOT)} has no "
                      f"{entrypoint} — skipping", file=sys.stderr)
                continue

            existing = by_model.get(run_model)
            if existing is None or run_date > existing["date"]:
                by_model[run_model] = {
                    "model": run_model,
                    "date": run_date,
                    "run_dir": run_entry,
                    "impl_path": impl,
                }

    return list(by_model.values())


def randomize_labels(n: int, rng: random.Random) -> list[str]:
    """Return n distinct uppercase labels in random order: A, B, C, ..."""
    if n > 26:
        raise ValueError("more than 26 implementations not supported")
    labels = list(string.ascii_uppercase[:n])
    rng.shuffle(labels)
    return labels


def write_packet(
    task_dir: pathlib.Path,
    judge_dir: pathlib.Path,
    impls: list[dict],
    mapping: dict[str, str],
    entrypoint: str,
) -> None:
    """Write one judge's packet at judge_dir."""
    packet = judge_dir / "packet"
    impl_dir = packet / "implementations"
    output = judge_dir / "output"
    impl_dir.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)

    for fname in ["PROMPT.md", "SPEC.md", "JUDGE_PROMPT.md", "JUDGE_RUBRIC.md"]:
        src = task_dir / fname
        if src.exists():
            shutil.copy2(src, packet / fname)

    label_to_model = {label: model for model, label in mapping.items()}
    suffix = pathlib.Path(entrypoint).suffix
    for impl in impls:
        if impl["model"] not in mapping:
            continue
        label = mapping[impl["model"]]
        shutil.copy2(impl["impl_path"], impl_dir / f"{label}{suffix}")

    # Per-judge cover note: which labels exist, no model→label leak.
    labels = sorted(label_to_model.keys())
    cover = packet / "README.md"
    cover.write_text(
        f"# Judgment packet\n\n"
        f"Implementations to review (blinded labels): {', '.join(labels)}\n\n"
        f"Read PROMPT.md and SPEC.md first to understand what was asked.\n"
        f"Then read JUDGE_PROMPT.md for your task and the output format.\n"
        f"Score each implementation independently. Write outputs to ../output/.\n"
    )


# Prototype for the same parallelization pattern (ThreadPoolExecutor +
# per-target log file + as_completed summary) that the implementer phase
# in run-all.sh will eventually adopt. Keep it as a local helper for now —
# one call site, premature to hoist into a shared module.
def _drive_one_judge(judge: str,
                     out_root: pathlib.Path,
                     cfg,
                     message: str,
                     log_path: pathlib.Path | None) -> tuple[str, int, float]:
    """Drive a single judge through `opencode run`.

    Returns (judge, rc, elapsed_seconds). Caller is responsible for
    skipping judges whose slug isn't in config — this helper assumes
    the slug exists.
    """
    import time as _time
    from . import _opencode_run

    judge_dir = out_root / judge
    slug = cfg.slug_for(judge)
    title = f"{out_root.name}-{judge}"

    started = _time.monotonic()
    rc = _opencode_run.run(
        directory=judge_dir,
        model=slug,
        message=message,
        title=title,
        log_path=log_path,
    )
    return judge, rc, _time.monotonic() - started


def auto_drive_judges(out_root: pathlib.Path,
                      judges: list[str],
                      cfg,
                      concurrency: int = 1) -> int:
    """For each judge with a slug in config, drive `opencode run` against
    its packet directory. Judges without a slug (e.g. configured to run
    through a non-opencode harness) are skipped here and listed for
    manual driving by the caller.

    With concurrency=1, runs sequentially with inherited stdout (legacy
    behavior — byte-identical to before parallelization existed). With
    concurrency>1, fans out via ThreadPoolExecutor and redirects each
    judge's stdout/stderr to <judge_dir>/judge.log so streams don't
    interleave.

    Returns 0 if every attempted judge exited cleanly, else the first
    non-zero return code so the caller can surface failure."""
    from . import _opencode_run  # local import: only loaded on --auto

    try:
        _opencode_run.preflight()
    except _opencode_run.OpencodeNotAvailable as e:
        print(f"  --auto skipped: {e}", file=sys.stderr)
        return 1

    message = (
        "Read packet/JUDGE_PROMPT.md. Score every implementation under "
        "packet/implementations/ per the rubric. Write outputs to "
        "output/ in the JSON schema specified by JUDGE_PROMPT.md. "
        "Done when every label has both <label>_rubric.md and "
        "<label>_scores.json under output/."
    )

    drivable: list[str] = []
    for judge in judges:
        if judge not in cfg.slugs:
            print(f"  --auto: skipping '{judge}' (no slug in config — "
                  f"drive manually)", file=sys.stderr)
            continue
        drivable.append(judge)

    if not drivable:
        return 0

    if concurrency <= 1:
        overall_rc = 0
        for judge in drivable:
            judge_dir = out_root / judge
            slug = cfg.slug_for(judge)
            print(f"\n▶ --auto: driving {judge} ({slug}) against "
                  f"{judge_dir.relative_to(REPO_ROOT)}")
            _, rc, _elapsed = _drive_one_judge(
                judge, out_root, cfg, message, log_path=None
            )
            if rc != 0:
                print(f"✗ {judge} exited {rc}", file=sys.stderr)
                overall_rc = overall_rc or rc
        return overall_rc

    import concurrent.futures as _cf

    print(f"\n▶ --auto: dispatching {len(drivable)} judge(s) "
          f"(concurrency={concurrency})")

    results: list[tuple[str, int, float]] = []
    results_lock = threading.Lock()
    log_paths: dict[str, pathlib.Path] = {
        j: out_root / j / "judge.log" for j in drivable
    }
    with _cf.ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {
            pool.submit(
                _drive_one_judge, j, out_root, cfg, message, log_paths[j]
            ): j
            for j in drivable
        }
        for fut in _cf.as_completed(futures):
            judge, rc, elapsed = fut.result()
            log_rel = log_paths[judge].relative_to(REPO_ROOT)
            mark = "✓" if rc == 0 else "✗"
            extra = "" if rc == 0 else f" exit {rc}"
            print(f"  {mark} {judge} ({elapsed:.0f}s){extra} — {log_rel}")
            with results_lock:
                results.append((judge, rc, elapsed))

    failed = [(j, rc) for j, rc, _ in results if rc != 0]
    passed = len(results) - len(failed)
    print(f"\n  {passed} pass, {len(failed)} fail")

    for judge, rc in failed:
        log = log_paths[judge]
        print(f"\n--- tail {log.relative_to(REPO_ROOT)} (exit {rc}) ---",
              file=sys.stderr)
        try:
            lines = log.read_text(errors="replace").splitlines()
            for ln in lines[-40:]:
                print(ln, file=sys.stderr)
        except OSError as e:
            print(f"  (could not read log: {e})", file=sys.stderr)

    return failed[0][1] if failed else 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("task", help="task name under bench/tasks/")
    p.add_argument("--seed", type=int, default=None,
                   help="RNG seed for label assignment (default: time-based)")
    p.add_argument("--auto", action="store_true",
                   help="drive each judge with a slug through opencode run")
    p.add_argument("--concurrency", type=int, default=None,
                   help="parallel judges under --auto "
                        "(default: $JUDGE_CONCURRENCY or 3)")
    args = p.parse_args()

    if args.concurrency is not None:
        concurrency = args.concurrency
    else:
        env = os.environ.get("JUDGE_CONCURRENCY")
        concurrency = int(env) if env else 3
    if concurrency < 1:
        print(f"error: --concurrency must be >= 1, got {concurrency}",
              file=sys.stderr)
        return 2

    task_dir = REPO_ROOT / "bench" / "tasks" / args.task
    if not task_dir.is_dir():
        print(f"error: no task at {task_dir}", file=sys.stderr)
        return 1
    for required in ("JUDGE_PROMPT.md", "JUDGE_RUBRIC.md", "SPEC.md", "PROMPT.md"):
        if not (task_dir / required).exists():
            print(f"error: task missing {required}", file=sys.stderr)
            return 1

    cfg = _config.load()
    task_cfg = _task.load(args.task)
    entrypoint = task_cfg["entrypoint"]

    impls = find_runs(args.task, entrypoint)
    if not impls:
        print(f"error: no completed runs for task '{args.task}' under "
              f"<model>/{args.task}-*/ at repo root", file=sys.stderr)
        return 1
    if len(impls) < 2:
        print(f"error: need at least 2 implementations to judge, found {len(impls)}",
              file=sys.stderr)
        return 1

    # Soft-validate against config: warn if an on-disk model is missing
    # from config.implementers (probably a stale dir) but do not block.
    on_disk = {impl["model"] for impl in impls}
    unconfigured = on_disk - set(cfg.implementers)
    if unconfigured:
        print(f"  warn: {sorted(unconfigured)} not in bench/config.json "
              f"implementers — including anyway", file=sys.stderr)

    print(f"found {len(impls)} implementation(s):")
    for impl in impls:
        print(f"  {impl['model']:12s}  {impl['run_dir'].name}")

    rng = random.Random(args.seed)
    date_stamp = dt.date.today().isoformat()
    out_root = REPO_ROOT / "results" / "judgments" / f"{args.task}-{date_stamp}"
    if out_root.exists():
        print(f"error: {out_root} already exists — remove it or pick a fresh date",
              file=sys.stderr)
        return 1
    out_root.mkdir(parents=True)

    impl_models = [impl["model"] for impl in impls]
    judges: list[str] = list(cfg.expert_judges) + impl_models
    pairings: dict[str, dict[str, str]] = {}

    for judge in judges:
        # Every judge — peer or expert — scores every implementation
        # including its own. Self-judgments feed the self-bias check in
        # the aggregator and are excluded from the peer-median scoreboard
        # there, so the headline numbers stay un-self-inflated.
        targets = list(impl_models)

        # randomize_labels already shuffles the label assignment; one
        # random pairing of (target -> label) is sufficient.
        labels = randomize_labels(len(targets), rng)
        mapping = dict(zip(targets, labels))
        pairings[judge] = mapping

        judge_dir = out_root / judge
        write_packet(task_dir, judge_dir, impls, mapping, entrypoint)
        print(f"  packet ready: {judge_dir.relative_to(REPO_ROOT)}  "
              f"({len(targets)} impl{'s' if len(targets) != 1 else ''})")

    (out_root / "pairings.json").write_text(
        json.dumps(pairings, indent=2, sort_keys=True) + "\n"
    )

    # Record context for aggregator: which run dir each model came from.
    runs_index = {
        impl["model"]: str(impl["run_dir"].relative_to(REPO_ROOT))
        for impl in impls
    }
    (out_root / "runs_index.json").write_text(
        json.dumps(runs_index, indent=2, sort_keys=True) + "\n"
    )

    print()
    print(f"✓ judgment phase set up at {out_root.relative_to(REPO_ROOT)}")

    if args.auto:
        rc = auto_drive_judges(out_root, judges, cfg, concurrency=concurrency)
        manual = [j for j in judges if j not in cfg.slugs]
        if manual:
            print()
            print("manual judges remaining (no slug in config):")
            for j in manual:
                print(f"  • {j}: {out_root.relative_to(REPO_ROOT)}/{j}/packet/")
        print()
        print(f"aggregate when done:  bench/scripts/aggregate_judges.py {args.task}")
        return rc

    print()
    print("next steps:")
    print(f"  1. for each judge in {judges}, open its harness and read")
    print(f"     {out_root.relative_to(REPO_ROOT)}/<judge>/packet/JUDGE_PROMPT.md")
    print(f"     then write filled rubrics + scores.json to <judge>/output/")
    print(f"  2. for any judge with a slug in bench/config.json, you can rerun")
    print(f"     this script with --auto to drive it through opencode")
    print(f"  3. aggregate:  bench/scripts/aggregate_judges.py {args.task}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
