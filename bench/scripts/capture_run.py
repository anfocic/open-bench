#!/usr/bin/env python3
"""capture_run.py <task> <model>

Captures artifacts from a finished run:
  - copies hidden tests into the worktree (ephemerally), runs them, removes
  - saves diff.patch, edited files, transcript, meta.json
  - promotes the implementation file to builds/<model>/<entrypoint>

Run AFTER the model has finished its session in the worktree.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import sys
from typing import Any

from . import _config
from . import _git
from . import _logging
from . import _opencode
from . import _task

log = _logging.get_logger(__name__)

REPO_ROOT = _config.repo_root()
_run_git = _git.run_git


def find_run_dir(model_dir: pathlib.Path, task: str) -> pathlib.Path | None:
    """Find the most recent run dir for this task+model."""
    rounds_dir = model_dir / "rounds"
    if not rounds_dir.is_dir():
        return None
    prefix = f"{task}-"
    candidates = sorted(
        d for d in rounds_dir.iterdir()
        if d.is_dir() and d.name.startswith(prefix)
    )
    return candidates[-1] if candidates else None


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


def capture(task: str, model: str) -> int:
    task_cfg = _task.load(task)
    entrypoint = task_cfg["entrypoint"]
    test_invocation = task_cfg["test_invocation"]
    loc_method = task_cfg["loc_method"]

    try:
        task_dir = _task.require(task)
    except FileNotFoundError as e:
        log.error("%s", e)
        return 1
    model_dir = REPO_ROOT / "builds" / model

    run_dir = find_run_dir(model_dir, task)
    if run_dir is None:
        log.error("no run dir for %s-* under %s/ — did you call start_run first?",
                  task, model_dir)
        return 1

    meta_path = run_dir / "meta.json"
    if not meta_path.exists():
        log.error("%s missing — start_run was not used to create this run dir, "
                  "or it predates the meta.json stamp", meta_path)
        return 1
    run_meta = json.loads(meta_path.read_text())
    slug = run_meta["slug"]
    worktree_dir = pathlib.Path(run_meta["worktree"])
    if not worktree_dir.is_dir():
        log.error("worktree not found at %s", worktree_dir)
        return 1

    impl_path = worktree_dir / entrypoint
    if not impl_path.exists():
        if os.environ.get("ALLOW_EMPTY_IMPL") != "1":
            log.error(
                "%s is missing — the model has not produced an implementation. "
                "Did you run the opencode session in the worktree? "
                "Set ALLOW_EMPTY_IMPL=1 to capture an empty run.", impl_path)
            return 1
        log.warning("%s missing; ALLOW_EMPTY_IMPL=1, continuing", entrypoint)

    started_at = run_meta.get("started_at", "unknown")
    ended_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    run_dir.mkdir(parents=True, exist_ok=True)

    base_branch = determine_base_branch(REPO_ROOT)
    base = _run_git("merge-base", "HEAD", base_branch, cwd=worktree_dir, check=False).strip()
    if not base:
        try:
            base = _run_git("rev-parse", base_branch, cwd=REPO_ROOT).strip()
        except RuntimeError as e:
            log.error("could not resolve base branch '%s' (merge-base + "
                      "rev-parse both failed): %s", base_branch, e)
            return 1

    diff_lines: list[str] = []

    diff_out = _run_git("diff", f"{base}...HEAD", "--", ".", ":!PROMPT.md", ":!SPEC.md",
                         cwd=worktree_dir, check=False)
    diff_lines.append(diff_out)

    diff_out = _run_git("diff", "HEAD", "--", ".", ":!PROMPT.md", ":!SPEC.md",
                         cwd=worktree_dir, check=False)
    diff_lines.append(diff_out)

    untracked = _run_git("ls-files", "--others", "--exclude-standard",
                          cwd=worktree_dir).strip().splitlines()

    for f in untracked:
        f = f.strip()
        if not f or f in ("PROMPT.md", "SPEC.md", "transcript.md"):
            continue
        if f.startswith("_eval_tests/"):
            continue
        fpath = worktree_dir / f
        if not fpath.exists():
            continue
        try:
            result = subprocess.run(
                ["git", "diff", "--no-index", "--no-color", "/dev/null", str(fpath)],
                cwd=worktree_dir, capture_output=True, text=True, check=False,
            )
            diff_lines.append(result.stdout)
        except OSError:
            # git binary missing or fpath unreadable — skip this entry; the
            # rest of the diff still captures.
            pass

    (run_dir / "diff.patch").write_text("\n".join(diff_lines))

    suffix = pathlib.Path(entrypoint).suffix
    # Empty suffix → fall back to the entrypoint basename. Otherwise `*""`
    # expands to `*`, which matches every path in the worktree and defeats
    # the filter (would copy unrelated files into the run dir).
    pathspec = f"*{suffix}" if suffix else pathlib.Path(entrypoint).name
    modified_ext = _run_git("diff", "--name-only", base, "--", pathspec,
                             cwd=worktree_dir, check=False).strip().splitlines()
    modified_ext += _run_git("diff", "--name-only", "HEAD", "--", pathspec,
                              cwd=worktree_dir, check=False).strip().splitlines()
    untracked_ext = _run_git("ls-files", "--others", "--exclude-standard", pathspec,
                              cwd=worktree_dir).strip().splitlines()

    all_modified = sorted(set(
        f.strip() for f in modified_ext + untracked_ext
        if f.strip() and not f.strip().startswith("_eval_tests/")
    ))

    for rel in all_modified:
        src = worktree_dir / rel
        if not src.is_file():
            continue
        dest = run_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

    if (run_dir / entrypoint).exists():
        shutil.copy2(run_dir / entrypoint, model_dir / entrypoint)

    eval_dir = worktree_dir / "_eval_tests"
    if eval_dir.exists():
        shutil.rmtree(eval_dir)
    eval_dir.mkdir()

    tests_src = task_dir / "tests"
    if not tests_src.is_dir():
        log.error("no tests dir at %s", tests_src)
        shutil.rmtree(eval_dir, ignore_errors=True)
        return 1

    shutil.copytree(tests_src, eval_dir, dirs_exist_ok=True)

    test_timeout = int(os.environ.get("CAPTURE_TEST_TIMEOUT", "300"))
    try:
        proc = subprocess.run(
            test_invocation,
            cwd=str(worktree_dir),
            capture_output=True,
            text=True,
            timeout=test_timeout,
        )
        test_exit = proc.returncode
        test_stdout = proc.stdout
        test_stderr = proc.stderr
    except subprocess.TimeoutExpired as e:
        log.error("hidden tests timed out after %ds — recording exit 124. "
                  "Override with CAPTURE_TEST_TIMEOUT=<seconds>.", test_timeout)
        test_exit = 124  # convention: command timed out
        test_stdout = (e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes)
                       else (e.stdout or ""))
        test_stderr = (e.stderr.decode(errors="replace") if isinstance(e.stderr, bytes)
                       else (e.stderr or ""))
    (run_dir / "test-output.txt").write_text(test_stdout + "\n--- stderr ---\n" + test_stderr)

    shutil.rmtree(eval_dir, ignore_errors=True)

    opencode_session_json = run_dir / "opencode_session.json"
    opencode_summary_json = run_dir / ".opencode_summary.json"
    transcript_path = run_dir / "transcript.md"
    for p in (opencode_session_json, opencode_summary_json):
        p.unlink(missing_ok=True)

    try:
        if _opencode.available():
            session_id = _opencode.find_session_for_directory(str(worktree_dir))
            if session_id:
                session = _opencode.export_session(session_id)
                if session:
                    opencode_session_json.write_text(json.dumps(session, indent=2) + "\n")
                    summary = _opencode.summarize(session)
                    opencode_summary_json.write_text(json.dumps(summary, indent=2) + "\n")
                    worktree_transcript = worktree_dir / "transcript.md"
                    if not worktree_transcript.exists():
                        transcript_path.write_text(_opencode.render_transcript(session))
                    log.info("opencode session captured: %s "
                             "(cost $%.4f, %s tokens, model %s)",
                             session_id, summary['cost_usd'],
                             summary['tokens_total'], summary['model_slug'])
            else:
                log.info("no opencode session found for worktree — "
                         "falling back to transcript.md")
    except (subprocess.CalledProcessError, OSError, json.JSONDecodeError,
            _opencode.OpencodeNotAvailable) as e:
        log.warning("opencode capture failed (%s); skipping auto-capture", e)

    worktree_transcript = worktree_dir / "transcript.md"
    if worktree_transcript.exists():
        shutil.copy2(worktree_transcript, transcript_path)
    elif not transcript_path.exists():
        transcript_path.write_text(
            "# transcript missing\n\n"
            "No `transcript.md` found at worktree root and no opencode session\n"
            "matching this worktree. To capture the session manually, either:\n"
            f"  - export the session via `opencode export <sessionID> > {worktree_dir}/session.json`\n"
            f"  - or copy the terminal scrollback to {worktree_transcript}\n"
            "then re-run capture_run.py.\n"
        )

    loc = _task.loc_count(impl_path, loc_method) if impl_path.exists() else 0

    opencode_version = "unknown"
    try:
        opencode_version = subprocess.check_output(
            ["opencode", "--version"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, OSError):
        # opencode not installed, or installed but exited non-zero —
        # leave 'unknown' in meta.json; not a failure of capture.
        pass

    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    auto_meta = {
        "task": task,
        "model": model,
        "slug": slug,
        "started_at": started_at,
        "ended_at": ended_at,
        "base_commit": base,
        "worktree": str(worktree_dir),
        "test_exit_code": test_exit,
        "impl_loc": loc,
        "entrypoint": entrypoint,
        "opencode_version": opencode_version,
        "python_version": python_version,
    }

    meta_path = run_dir / "meta.json"
    existing_meta: dict[str, Any] = {}
    if meta_path.exists():
        try:
            existing_meta = json.loads(meta_path.read_text())
        except json.JSONDecodeError:
            existing_meta = {}

    existing_meta.update(auto_meta)

    if opencode_summary_json.exists():
        try:
            summary = json.loads(opencode_summary_json.read_text())
            existing_meta.update({k: v for k, v in summary.items() if v is not None})
            opencode_summary_json.unlink()
        except (json.JSONDecodeError, OSError):
            pass

    meta_path.write_text(json.dumps(existing_meta, indent=2) + "\n")

    test_status = "all passed" if test_exit == 0 else f"exit {test_exit}"
    # Multi-line operator summary — kept as print so it renders as a UX
    # block regardless of log level.
    print()
    print("captured")
    print(f"  run dir:     {run_dir}")
    print(f"  test exit:   {test_exit}  ({test_status})")
    print(f"  {entrypoint}:  {loc} LOC")
    print()
    print(f"artifacts (in {run_dir})")
    print(f"  - {entrypoint}            (also copied to {model_dir}/{entrypoint} = current)")
    print(f"  - diff.patch")
    print(f"  - test-output.txt")
    print(f"  - transcript.md")
    print(f"  - meta.json")
    print()
    print(f"next: review with results/reviews/TEMPLATE.md → "
          f"results/reviews/{task}-"
          f"{dt.datetime.now(dt.timezone.utc).date().isoformat()}.md")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Capture artifacts from a finished run.")
    p.add_argument("task", help="task name under bench/tasks/")
    p.add_argument("model", help="model short name (e.g. kimi, deepseek)")
    p.add_argument("--quiet", "-q", action="store_true",
                   help="warnings + errors only")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="debug output")
    args = p.parse_args()
    _logging.setup_logging(quiet=args.quiet, verbose=args.verbose)
    return capture(args.task, args.model)


if __name__ == "__main__":
    sys.exit(main())