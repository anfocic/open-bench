#!/usr/bin/env python3
"""start_run.py [--auto] <task> <model>

Creates an isolated git worktree on a fresh branch, drops PROMPT.md +
SPEC.md at the worktree root, and prints the next steps.

With --auto, drives `opencode run` non-interactively against the
worktree using the model slug from bench/config.json, then chains to
capture_run.py on success. Uses --dangerously-skip-permissions; see
README warning before using.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
import pathlib
import shutil
import sys
import threading

from . import _config
from . import _git
from . import _logging
from . import _opencode_run
from . import _task

log = _logging.get_logger(__name__)

REPO_ROOT = _config.repo_root()
_run_git = _git.run_git


def determine_base_branch(repo_root: pathlib.Path) -> str:
    base = os.environ.get("BASE_BRANCH", "")
    if base:
        return base
    try:
        head = _run_git("symbolic-ref", "--short", "refs/remotes/origin/HEAD",
                         cwd=repo_root, check=False).strip()
        if head.startswith("origin/"):
            return head[len("origin/"):]
    except RuntimeError:
        # _run_git only raises RuntimeError on git failure; fall through
        # to the main/master probe.
        pass
    for cand in ("main", "master"):
        try:
            _run_git("rev-parse", "--verify", cand, cwd=repo_root)
            return cand
        except RuntimeError:
            continue
    raise RuntimeError(
        "cannot determine base branch (tried origin/HEAD, main, master). "
        "Set BASE_BRANCH=<your-default-branch>"
    )


def start_run(task: str, model: str, auto: bool = False,
              worktree_lock: threading.Lock | None = None,
              log_path: pathlib.Path | None = None) -> int:
    task_cfg = _task.load(task)
    entrypoint = task_cfg["entrypoint"]

    try:
        task_dir = _task.require(task, ["PROMPT.md", "SPEC.md"])
    except FileNotFoundError as e:
        log.error("%s", e)
        return 1

    cfg = _config.load()
    if model not in cfg.implementers:
        log.warning("'%s' not in bench/config.json implementers — proceeding "
                    "anyway; add it to config if intentional", model)

    date_stamp = os.environ.get(
        "RUN_STAMP",
        dt.datetime.now(dt.timezone.utc).date().isoformat(),
    )
    slug = f"{task}-{model}-{date_stamp}"
    branch = f"eval/{slug}"
    worktree_dir = (REPO_ROOT / ".." / f"eval-{slug}").resolve()

    lock_ctx = worktree_lock if worktree_lock is not None else contextlib.nullcontext()
    with lock_ctx:
        existing = _run_git("worktree", "list", "--porcelain", cwd=REPO_ROOT, check=False)
        existing_paths = {
            line[len("worktree "):]
            for line in existing.splitlines()
            if line.startswith("worktree ")
        }
        if str(worktree_dir) in existing_paths:
            log.error("worktree already exists at %s — remove with: "
                      "git worktree remove %s", worktree_dir, worktree_dir)
            return 1

        try:
            _run_git("rev-parse", "--verify", branch, cwd=REPO_ROOT)
            log.error("branch %s already exists — delete with: git branch -D %s",
                      branch, branch)
            return 1
        except RuntimeError:
            pass

        base_branch = determine_base_branch(REPO_ROOT)
        base = _run_git("rev-parse", base_branch, cwd=REPO_ROOT).strip()

        _run_git("worktree", "add", "-b", branch, str(worktree_dir), base, cwd=REPO_ROOT)

        shutil.copy2(task_dir / "PROMPT.md", worktree_dir / "PROMPT.md")
        shutil.copy2(task_dir / "SPEC.md", worktree_dir / "SPEC.md")

        run_dir = REPO_ROOT / "builds" / model / "rounds" / f"{task}-{date_stamp}"
        run_dir.mkdir(parents=True, exist_ok=True)
        run_meta = {
            "task": task,
            "model": model,
            "slug": slug,
            "date_stamp": date_stamp,
            "branch": branch,
            "worktree": str(worktree_dir),
            "started_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        (run_dir / "meta.json").write_text(json.dumps(run_meta, indent=2) + "\n")

    log.info("worktree ready: path=%s branch=%s base=%s",
             worktree_dir, branch, base)

    if not auto:
        # Multi-line operator instructions — kept as print so it renders
        # as a UX block regardless of log level.
        print()
        print("next steps")
        print(f"  1. cd {worktree_dir}")
        print(f"  2. open opencode, set model: {model}")
        print("  3. paste PROMPT.md into the session and let it run")
        print(f"  4. when finished, drop the session export at: {worktree_dir}/transcript.md")
        print("  5. capture artifacts:")
        print(f"     python3 -m bench.scripts.capture_run {task} {model}")
        print()
        return 0

    log.info("--auto: driving opencode against %s", worktree_dir)

    slug_str = cfg.slug_for(model)
    message = (
        f"Read PROMPT.md and SPEC.md at the worktree root, then implement "
        f"{entrypoint} per the spec. Stop when {entrypoint} exists at the worktree "
        f"root and your own quick smoke check passes."
    )

    rc = _opencode_run.run(
        directory=str(worktree_dir),
        model=slug_str,
        message=message,
        title=slug,
        log_path=log_path,
    )

    if rc != 0:
        log.error("opencode run exited %d; not capturing. "
                  "worktree preserved at %s — inspect, then retry or run "
                  "capture_run manually", rc, worktree_dir)
        return rc

    log.info("--auto: chaining to capture_run")

    from .capture_run import capture
    return capture(task, model)


def main() -> int:
    p = argparse.ArgumentParser(description="Start a run for a task + model.")
    p.add_argument("--auto", action="store_true",
                   help="drive opencode non-interactively, then capture")
    p.add_argument("task", help="task name under bench/tasks/")
    p.add_argument("model", help="model short name (e.g. kimi, deepseek)")
    p.add_argument("--quiet", "-q", action="store_true",
                   help="warnings + errors only")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="debug output")
    args = p.parse_args()
    _logging.setup_logging(quiet=args.quiet, verbose=args.verbose)
    return start_run(args.task, args.model, auto=args.auto)


if __name__ == "__main__":
    sys.exit(main())