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
import os
import pathlib
import shutil
import subprocess
import sys
import threading

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _config  # noqa: E402
import _opencode_run  # noqa: E402
import _task  # noqa: E402

REPO_ROOT = _config.REPO_ROOT


def _run_git(*args: str, cwd: pathlib.Path | None = None, check: bool = True) -> str:
    result = subprocess.run(
        ["git"] + list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def determine_base_branch(repo_root: pathlib.Path) -> str:
    base = os.environ.get("BASE_BRANCH", "")
    if base:
        return base
    try:
        head = _run_git("symbolic-ref", "--short", "refs/remotes/origin/HEAD",
                         cwd=repo_root, check=False).strip()
        if head.startswith("origin/"):
            return head[len("origin/"):]
    except Exception:
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

    task_dir = REPO_ROOT / "bench" / "tasks" / task
    if not task_dir.is_dir():
        print(f"error: no task at {task_dir}", file=sys.stderr)
        return 1

    if not (task_dir / "PROMPT.md").exists() or not (task_dir / "SPEC.md").exists():
        print("error: task missing PROMPT.md or SPEC.md", file=sys.stderr)
        return 1

    cfg = _config.load()
    if model not in cfg.implementers:
        print(f"  warn: '{model}' not in bench/config.json implementers", file=sys.stderr)
        print("        proceeding anyway — add it to config if this is intentional", file=sys.stderr)

    date_stamp = os.environ.get("RUN_STAMP", dt.date.today().isoformat())
    slug = f"{task}-{model}-{date_stamp}"
    branch = f"eval/{slug}"
    worktree_dir = (REPO_ROOT / ".." / f"eval-{slug}").resolve()

    lock_ctx = worktree_lock if worktree_lock is not None else contextlib.nullcontext()
    with lock_ctx:
        existing = _run_git("worktree", "list", "--porcelain", cwd=REPO_ROOT, check=False)
        if f"worktree {worktree_dir}" in existing:
            print(f"error: worktree already exists at {worktree_dir}", file=sys.stderr)
            print(f"       remove with: git worktree remove {worktree_dir}", file=sys.stderr)
            return 1

        try:
            _run_git("rev-parse", "--verify", branch, cwd=REPO_ROOT)
            print(f"error: branch {branch} already exists", file=sys.stderr)
            print(f"       delete with: git branch -D {branch}", file=sys.stderr)
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
        (run_dir / ".started_at").write_text(
            dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        )

    print()
    print("✓ worktree ready")
    print(f"  path:    {worktree_dir}")
    print(f"  branch:  {branch}")
    print(f"  base:    {base}")

    if not auto:
        print()
        print("next steps")
        print(f"  1. cd {worktree_dir}")
        print(f"  2. open opencode, set model: {model}")
        print("  3. paste PROMPT.md into the session and let it run")
        print(f"  4. when finished, drop the session export at: {worktree_dir}/transcript.md")
        print("  5. capture artifacts:")
        print(f"     {REPO_ROOT}/bench/scripts/capture_run.py {task} {model}")
        print()
        return 0

    print()
    print(f"▶ --auto: driving opencode against {worktree_dir}")
    print()

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
        print()
        print(f"✗ opencode run exited {rc}; not capturing")
        print(f"  worktree preserved at: {worktree_dir}")
        print("  inspect, then either retry or run capture_run.py manually")
        return rc

    print()
    print("▶ --auto: chaining to capture_run.py")

    from capture_run import capture
    return capture(task, model)


def main() -> int:
    p = argparse.ArgumentParser(description="Start a run for a task + model.")
    p.add_argument("--auto", action="store_true",
                   help="drive opencode non-interactively, then capture")
    p.add_argument("task", help="task name under bench/tasks/")
    p.add_argument("model", help="model short name (e.g. kimi, deepseek)")
    args = p.parse_args()
    return start_run(args.task, args.model, auto=args.auto)


if __name__ == "__main__":
    sys.exit(main())