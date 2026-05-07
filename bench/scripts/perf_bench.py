#!/usr/bin/env python3
"""perf_bench.py <task> <model> <n>

Runs the same task N times against one model, captures only timing /
cost / hidden-test signal per run, and writes an aggregate JSON +
markdown summary. Skips the judgment phase entirely — code quality is
already covered by the canonical round under results/reviews/.

Per run:
  - fresh tmp dir under /tmp/perf-bench-<model>-<uuid>/
  - PROMPT.md + SPEC.md dropped in
  - opencode run --dangerously-skip-permissions
  - session located via opencode session list (directory match)
  - cost / tokens / model_wall_clock_seconds parsed from session export
  - hidden tests copied in and run
  - tmp dir removed

Output:
  results/perf/<task>-<model>-<date>/run-<i>.json
  results/perf/<task>-<model>-<date>/summary.json
  results/perf/<task>-<model>-<date>/summary.md
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from . import _opencode
from . import _opencode_run
from . import _config
from . import _logging
from . import _pytest_parse
from . import _stats
from . import _task

log = _logging.get_logger(__name__)


def median_or_none(xs: list[float]) -> float | None:
    return _stats.median_rounded(xs, 3)


def stdev_or_none(xs: list[float]) -> float | None:
    return _stats.stdev_rounded(xs, 3)


def run_once(
    task_dir: Path,
    task_cfg: dict[str, Any],
    model_slug: str,
    repo_root: Path,
) -> dict[str, Any]:
    """Single run: fresh tmp dir, opencode, capture meta + tests.

    The work dir is removed in `finally` so timeouts and exceptions can't
    leak it into /tmp.
    """
    entrypoint = task_cfg["entrypoint"]
    run_id = uuid.uuid4().hex[:8]
    work = Path(tempfile.mkdtemp(prefix=f"perf-bench-{run_id}-"))

    try:
        prompt = task_dir / "PROMPT.md"
        spec = task_dir / "SPEC.md"
        shutil.copy2(prompt, work / "PROMPT.md")
        shutil.copy2(spec, work / "SPEC.md")
        subprocess.run(["git", "init", "-q"], cwd=work, check=True)
        subprocess.run(["git", "add", "PROMPT.md", "SPEC.md"], cwd=work, check=True)
        subprocess.run(
            ["git", "-c", "user.email=perf@bench", "-c", "user.name=perf", "commit", "-q", "-m", "init"],
            cwd=work, check=True,
        )

        started = time.time()
        started_iso = dt.datetime.fromtimestamp(started, dt.timezone.utc).isoformat(timespec="seconds")

        rc = _opencode_run.run(
            directory=work,
            model=model_slug,
            message=(
                f"Read PROMPT.md and SPEC.md at the worktree root, then implement "
                f"{entrypoint} per the spec. Stop when {entrypoint} exists at the worktree "
                f"root and your own quick smoke check passes."
            ),
        )

        ended = time.time()
        ended_iso = dt.datetime.fromtimestamp(ended, dt.timezone.utc).isoformat(timespec="seconds")
        envelope_seconds = round(ended - started, 1)

        impl = work / entrypoint
        if not impl.exists():
            return {
                "ok": False,
                "reason": f"{entrypoint} missing",
                "opencode_rc": rc,
                "envelope_seconds": envelope_seconds,
                "started": started_iso,
                "ended": ended_iso,
            }

        # session lookup + meta — opencode session list is project-scoped to
        # cwd, so we shell out from the work dir to see sessions for this run.
        session_id = None
        summary: dict[str, Any] = {}
        try:
            out = subprocess.check_output(
                ["opencode", "session", "list", "--format", "json"],
                cwd=work, text=True, stderr=subprocess.DEVNULL,
            )
            sessions = json.loads(out)
            target = str(work.resolve())
            candidates = [
                s for s in sessions
                if s.get("directory") and str(Path(s["directory"]).resolve()) == target
            ]
            if candidates:
                candidates.sort(key=lambda s: s.get("updated", 0), reverse=True)
                session_id = candidates[0]["id"]
                export = _opencode.export_session(session_id)
                if export:
                    summary = _opencode.summarize(export)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            pass

        # hidden tests
        tests_src = task_dir / "tests"
        test_dst = work / "_eval_tests"
        shutil.copytree(tests_src, test_dst)
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_dst), "-q"],
            cwd=work,
            capture_output=True,
            text=True,
            timeout=300,
        )
        test_exit = proc.returncode
        test_stdout = proc.stdout

        parsed = _pytest_parse.parse_pytest_output(test_stdout)
        passed = parsed["passed"]
        failed = parsed["failed"]

        impl_loc = _task.loc_count(impl, task_cfg["loc_method"])
        impl_content = impl.read_text(errors="replace")

        return {
            "ok": True,
            "started": started_iso,
            "ended": ended_iso,
            "envelope_seconds": envelope_seconds,
            "opencode_rc": rc,
            "session_id": session_id,
            "test_exit": test_exit,
            "tests_passed": passed,
            "tests_failed": failed,
            "impl_loc": impl_loc,
            "impl_content": impl_content,
            **summary,
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("task")
    ap.add_argument("model")
    ap.add_argument("n", type=int)
    ap.add_argument("--quiet", "-q", action="store_true",
                    help="warnings + errors only")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="debug output")
    args = ap.parse_args()
    _logging.setup_logging(quiet=args.quiet, verbose=args.verbose)

    repo_root = _config.repo_root()
    try:
        task_dir = _task.require(args.task)
    except FileNotFoundError as e:
        log.error("%s", e)
        return 1

    cfg = _config.load()
    task_cfg = _task.load(args.task)

    if args.model not in cfg.slugs:
        log.error("model '%s' has no slug in bench/config.json", args.model)
        return 1
    model_slug = cfg.slugs[args.model]

    _opencode_run.preflight()

    date_stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    out_dir = repo_root / "results" / "perf" / f"{args.task}-{args.model}-{date_stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    log.info("==> perf-bench: %s (%s) x %d", args.model, model_slug, args.n)
    log.info("    out: %s", out_dir)

    runs: list[dict] = []
    for i in range(1, args.n + 1):
        log.info("--- run %d/%d ---", i, args.n)
        try:
            result = run_once(task_dir, task_cfg, model_slug, repo_root)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                OSError, json.JSONDecodeError) as e:
            result = {"ok": False, "reason": f"exception: {e}"}
        runs.append(result)
        (out_dir / f"run-{i}.json").write_text(json.dumps(result, indent=2))
        if result.get("ok"):
            wall = result.get("model_wall_clock_seconds")
            cost = result.get("cost_usd")
            log.info("wall(model)=%ss envelope=%ss cost=$%s tests=%d/%d",
                     wall, result['envelope_seconds'], cost,
                     result['tests_passed'],
                     result['tests_passed'] + result['tests_failed'])
        else:
            log.error("FAILED: %s", result.get('reason'))

    # aggregate
    ok = [r for r in runs if r.get("ok")]
    walls = [r.get("model_wall_clock_seconds") for r in ok]
    envs = [r.get("envelope_seconds") for r in ok]
    costs = [r.get("cost_usd") for r in ok]
    toks = [r.get("tokens_total") for r in ok]
    locs = [r.get("impl_loc") for r in ok]
    test_pass = [r.get("tests_passed") for r in ok]
    test_fail = [r.get("tests_failed") for r in ok]

    summary = {
        "task": args.task,
        "model": args.model,
        "model_slug": model_slug,
        "date": date_stamp,
        "n_requested": args.n,
        "n_ok": len(ok),
        "wall_model_seconds": {
            "median": median_or_none(walls),
            "stdev": stdev_or_none(walls),
            "min": min((w for w in walls if w is not None), default=None),
            "max": max((w for w in walls if w is not None), default=None),
            "raw": walls,
        },
        "envelope_seconds": {
            "median": median_or_none(envs),
            "stdev": stdev_or_none(envs),
            "raw": envs,
        },
        "cost_usd": {
            "median": median_or_none(costs),
            "stdev": stdev_or_none(costs),
            "sum": round(sum(c for c in costs if c is not None), 6),
            "raw": costs,
        },
        "tokens_total": {
            "median": median_or_none(toks),
            "raw": toks,
        },
        "impl_loc": {
            "median": median_or_none(locs),
            "raw": locs,
        },
        "tests": {
            "passed_per_run": test_pass,
            "failed_per_run": test_fail,
            "all_pass": len(ok) > 0 and all(f == 0 for f in test_fail),
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    md = []
    md.append(f"# perf-bench: {args.model} x {args.n} ({date_stamp})\n")
    md.append(f"Model slug: `{model_slug}`\n")
    md.append(f"Runs ok: {len(ok)}/{args.n}\n")
    md.append("\n## Per-run\n")
    md.append("| # | Wall (model) | Envelope | Tokens | Cost USD | Tests | LOC |")
    md.append("|---|---|---|---|---|---|---|")
    for i, r in enumerate(runs, 1):
        if r.get("ok"):
            md.append(
                f"| {i} | {r.get('model_wall_clock_seconds')}s "
                f"| {r.get('envelope_seconds')}s "
                f"| {r.get('tokens_total')} "
                f"| ${r.get('cost_usd')} "
                f"| {r.get('tests_passed')}/{r.get('tests_passed') + r.get('tests_failed')} "
                f"| {r.get('impl_loc')} |"
            )
        else:
            md.append(f"| {i} | FAIL | — | — | — | — | — |")
    md.append("")
    w = summary["wall_model_seconds"]
    c = summary["cost_usd"]
    md.append("## Aggregate\n")
    md.append("| Metric | Median | Stdev | Min | Max |")
    md.append("|---|---|---|---|---|")
    md.append(f"| Wall (model) sec | {w['median']} | {w['stdev']} | {w['min']} | {w['max']} |")
    md.append(f"| Cost USD | {c['median']} | {c['stdev']} | — | — |")
    md.append(f"| Tokens | {summary['tokens_total']['median']} | — | — | — |")
    md.append(f"| LOC | {summary['impl_loc']['median']} | — | — | — |")
    md.append(f"\nTotal cost across {len(ok)} runs: ${c['sum']}")
    md.append(f"\nAll runs pass hidden tests: {summary['tests']['all_pass']}")

    (out_dir / "summary.md").write_text("\n".join(md))

    log.info("==> wrote %s/summary.json and summary.md", out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
