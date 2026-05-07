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
import string
import sys
import threading
from typing import Any

from . import _config
from . import _kinds
from . import _logging
from . import _task

log = _logging.get_logger(__name__)

REPO_ROOT = _config.repo_root()


def find_runs(task: str, entrypoint: str) -> list[dict[str, Any]]:
    """Find latest implementation run per model for `task`.

    Identity (task, model, date_stamp, slug) is read from each run's
    meta.json — written by start_run.py and extended by capture_run.py.
    Run dirs without a parseable meta are skipped with a warning.
    """
    by_model: dict[str, dict[str, Any]] = {}
    builds_root = REPO_ROOT / "builds"
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
                            meta_path.relative_to(REPO_ROOT))
                continue
            if meta.get("task") != task:
                continue

            impl = run_entry / entrypoint
            if not impl.exists():
                log.warning("%s has no %s — skipping",
                            run_entry.relative_to(REPO_ROOT), entrypoint)
                continue

            date_stamp = meta.get("date_stamp")
            if not date_stamp:
                log.warning("%s missing 'date_stamp' — skipping",
                            meta_path.relative_to(REPO_ROOT))
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


def randomize_labels(n: int, rng: random.Random) -> list[str]:
    """Return n distinct uppercase labels in random order: A, B, C, ..."""
    if n > 26:
        raise ValueError("more than 26 implementations not supported")
    labels = list(string.ascii_uppercase[:n])
    rng.shuffle(labels)
    return labels


# Prototype for the same parallelization pattern (ThreadPoolExecutor +
# per-target log file + as_completed summary) that the implementer phase
# in run_all.py will eventually adopt. Keep it as a local helper for now —
# one call site, premature to hoist into a shared module.
def auto_drive_judges(out_root: pathlib.Path,
                      judges: list[str],
                      cfg,
                      kind,
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
        log.warning("--auto skipped: %s", e)
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
            log.info("--auto: skipping '%s' (no slug in config — drive "
                     "manually)", judge)
            continue
        drivable.append(judge)

    if not drivable:
        return 0

    if concurrency <= 1:
        overall_rc = 0
        for judge in drivable:
            judge_dir = out_root / judge
            slug = cfg.slug_for(judge)
            log.info("--auto: driving %s (%s) against %s",
                     judge, slug, judge_dir.relative_to(REPO_ROOT))
            rc, _elapsed = kind.score(
                judge=judge,
                judge_dir=judge_dir,
                slug=slug,
                message=message,
                log_path=None,
                out_root_name=out_root.name,
            )
            if rc != 0:
                log.error("%s exited %d", judge, rc)
                overall_rc = overall_rc or rc
        return overall_rc

    import concurrent.futures as _cf

    log.info("--auto: dispatching %d judge(s) (concurrency=%d)",
             len(drivable), concurrency)

    results: list[tuple[str, int, float]] = []
    results_lock = threading.Lock()
    log_paths: dict[str, pathlib.Path] = {
        j: out_root / j / "judge.log" for j in drivable
    }

    def _drive(j: str) -> tuple[str, int, float]:
        rc, elapsed = kind.score(
            judge=j,
            judge_dir=out_root / j,
            slug=cfg.slug_for(j),
            message=message,
            log_path=log_paths[j],
            out_root_name=out_root.name,
        )
        return j, rc, elapsed

    with _cf.ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(_drive, j): j for j in drivable}
        for fut in _cf.as_completed(futures):
            judge, rc, elapsed = fut.result()
            log_rel = log_paths[judge].relative_to(REPO_ROOT)
            if rc == 0:
                log.info("ok: %s (%.0fs) — %s", judge, elapsed, log_rel)
            else:
                log.error("fail: %s (%.0fs) exit %d — %s",
                          judge, elapsed, rc, log_rel)
            with results_lock:
                results.append((judge, rc, elapsed))

    failed = [(j, rc) for j, rc, _ in results if rc != 0]
    passed = len(results) - len(failed)
    log.info("%d pass, %d fail", passed, len(failed))

    for judge, rc in failed:
        log_path = log_paths[judge]
        log.error("--- tail %s (exit %d) ---",
                  log_path.relative_to(REPO_ROOT), rc)
        try:
            lines = log_path.read_text(errors="replace").splitlines()
            for ln in lines[-40:]:
                print(ln, file=sys.stderr)
        except OSError as e:
            log.error("could not read log: %s", e)

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
    p.add_argument("--quiet", "-q", action="store_true",
                   help="warnings + errors only")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="debug output")
    args = p.parse_args()
    _logging.setup_logging(quiet=args.quiet, verbose=args.verbose)

    if args.concurrency is not None:
        concurrency = args.concurrency
    else:
        env = os.environ.get("JUDGE_CONCURRENCY")
        concurrency = int(env) if env else 3
    if concurrency < 1:
        log.error("--concurrency must be >= 1, got %d", concurrency)
        return 2

    try:
        task_dir = _task.require(
            args.task,
            ["JUDGE_PROMPT.md", "JUDGE_RUBRIC.md", "SPEC.md", "PROMPT.md"],
        )
    except FileNotFoundError as e:
        log.error("%s", e)
        return 1

    cfg = _config.load()
    task_cfg = _task.load(args.task)
    entrypoint = task_cfg["entrypoint"]
    kind = _kinds.get(task_cfg.get("task_kind", "code"))

    impls = find_runs(args.task, entrypoint)
    if not impls:
        log.error("no completed runs for task '%s' under "
                  "<model>/%s-*/ at repo root", args.task, args.task)
        return 1
    if len(impls) < 2:
        log.error("need at least 2 implementations to judge, found %d",
                  len(impls))
        return 1

    # Soft-validate against config: warn if an on-disk model is missing
    # from config.implementers (probably a stale dir) but do not block.
    on_disk = {impl["model"] for impl in impls}
    unconfigured = on_disk - set(cfg.implementers)
    if unconfigured:
        log.warning("%s not in bench/config.json implementers — including "
                    "anyway", sorted(unconfigured))

    log.info("found %d implementation(s):", len(impls))
    for impl in impls:
        log.info("  %-12s %s", impl['model'], impl['run_dir'].name)

    rng = random.Random(args.seed)
    date_stamp = dt.datetime.now(dt.timezone.utc).date().isoformat()
    out_root = REPO_ROOT / "results" / "judgments" / f"{args.task}-{date_stamp}"
    if out_root.exists():
        log.error("%s already exists — remove it or pick a fresh date",
                  out_root)
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
        kind.assemble_packet(
            task_dir=task_dir,
            judge_dir=judge_dir,
            impls=impls,
            mapping=mapping,
            entrypoint=entrypoint,
        )
        log.info("packet ready: %s (%d impl%s)",
                 judge_dir.relative_to(REPO_ROOT),
                 len(targets), 's' if len(targets) != 1 else '')

    (out_root / "pairings.json").write_text(
        json.dumps(pairings, indent=2, sort_keys=True) + "\n"
    )

    # Record context for aggregator: which run dir each model came from,
    # plus the run identity stamped at start_run time. Aggregator reads
    # `path` and other fields directly instead of slicing dir names.
    runs_index = {
        impl["model"]: {
            "path": str(impl["run_dir"].relative_to(REPO_ROOT)),
            "slug": impl["meta"].get("slug"),
            "date_stamp": impl["date_stamp"],
            "started_at": impl["meta"].get("started_at"),
        }
        for impl in impls
    }
    (out_root / "runs_index.json").write_text(
        json.dumps(runs_index, indent=2, sort_keys=True) + "\n"
    )

    judgment_meta = {
        "task": args.task,
        "date_stamp": date_stamp,
        "judges": judges,
        "impl_models": impl_models,
    }
    (out_root / "judgment_meta.json").write_text(
        json.dumps(judgment_meta, indent=2, sort_keys=True) + "\n"
    )

    log.info("judgment phase set up at %s", out_root.relative_to(REPO_ROOT))

    if args.auto:
        rc = auto_drive_judges(out_root, judges, cfg, kind,
                               concurrency=concurrency)
        manual = [j for j in judges if j not in cfg.slugs]
        if manual:
            print()
            print("manual judges remaining (no slug in config):")
            for j in manual:
                print(f"  - {j}: {out_root.relative_to(REPO_ROOT)}/{j}/packet/")
        print()
        print(f"aggregate when done:  python3 -m bench.scripts.aggregate_judges {args.task}")
        return rc

    # Multi-line operator instructions — kept as print so it renders as
    # a UX block regardless of log level.
    print()
    print("next steps:")
    print(f"  1. for each judge in {judges}, open its harness and read")
    print(f"     {out_root.relative_to(REPO_ROOT)}/<judge>/packet/JUDGE_PROMPT.md")
    print(f"     then write filled rubrics + scores.json to <judge>/output/")
    print(f"  2. for any judge with a slug in bench/config.json, you can rerun")
    print(f"     this script with --auto to drive it through opencode")
    print(f"  3. aggregate:  python3 -m bench.scripts.aggregate_judges {args.task}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
