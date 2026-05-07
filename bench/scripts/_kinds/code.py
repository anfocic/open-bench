"""Code task kind: entrypoint + pytest + LOC.

`extract_artifact` is the per-task code-specific subset of capture: it
computes the diff against the base branch, copies modified source files
into the run dir, promotes the entrypoint to the model dir, runs the
hidden test suite, and counts LOC. The orchestrator (`capture_run.py`)
remains responsible for run-dir lifecycle, meta.json, transcript
handling, and operator-facing UX.

`assemble_packet` and `score` are the per-judge code-specific subset of
the judgment phase: packet assembly (the four task files +
blinded `implementations/<label><suffix>` layout) and the per-judge
opencode invocation. The orchestrator (`start_judgments.py`) remains
responsible for run discovery, label assignment, pairings/runs_index/
judgment_meta.json, and the threadpool fanout across judges.

`aggregate` grows in a subsequent PR.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import time
from typing import Any

from .. import _git
from .. import _logging
from .. import _opencode_run
from .. import _task

log = _logging.get_logger(__name__)
_run_git = _git.run_git


class CodeTask:
    def extract_artifact(
        self,
        *,
        worktree: pathlib.Path,
        run_dir: pathlib.Path,
        model_dir: pathlib.Path,
        task_dir: pathlib.Path,
        task_cfg: dict[str, Any],
        base_branch: str,
    ) -> dict[str, Any]:
        """Capture the code-specific artifacts of a finished run.

        Side effects (filesystem):
          - writes <run_dir>/diff.patch
          - copies each modified source file matching the entrypoint
            extension/basename into <run_dir>/<rel>
          - promotes <run_dir>/<entrypoint> to <model_dir>/<entrypoint>
          - writes <run_dir>/test-output.txt
          - ephemerally copies task tests into <worktree>/_eval_tests/,
            runs them, removes the dir on the way out

        Returns the subset of meta.json fields owned by the code-task:
        base_commit, entrypoint, impl_loc, test_exit_code.
        """
        entrypoint = task_cfg["entrypoint"]
        test_invocation = task_cfg["test_invocation"]
        loc_method = task_cfg["loc_method"]

        base = _run_git("merge-base", "HEAD", base_branch,
                         cwd=worktree, check=False).strip()
        if not base:
            base = _run_git("rev-parse", base_branch, cwd=worktree).strip()

        diff_lines: list[str] = []
        diff_lines.append(_run_git(
            "diff", f"{base}...HEAD", "--", ".", ":!PROMPT.md", ":!SPEC.md",
            cwd=worktree, check=False))
        diff_lines.append(_run_git(
            "diff", "HEAD", "--", ".", ":!PROMPT.md", ":!SPEC.md",
            cwd=worktree, check=False))

        untracked = _run_git(
            "ls-files", "--others", "--exclude-standard",
            cwd=worktree).strip().splitlines()
        for f in untracked:
            f = f.strip()
            if not f or f in ("PROMPT.md", "SPEC.md", "transcript.md"):
                continue
            if f.startswith("_eval_tests/"):
                continue
            fpath = worktree / f
            if not fpath.exists():
                continue
            try:
                result = subprocess.run(
                    ["git", "diff", "--no-index", "--no-color",
                     "/dev/null", str(fpath)],
                    cwd=worktree, capture_output=True, text=True, check=False,
                )
                diff_lines.append(result.stdout)
            except OSError:
                # git binary missing or fpath unreadable — skip; the rest
                # of the diff still captures.
                pass

        (run_dir / "diff.patch").write_text("\n".join(diff_lines))

        suffix = pathlib.Path(entrypoint).suffix
        # Empty suffix → fall back to entrypoint basename. Otherwise `*""`
        # expands to `*` and matches every path in the worktree.
        pathspec = f"*{suffix}" if suffix else pathlib.Path(entrypoint).name
        modified_ext = _run_git(
            "diff", "--name-only", base, "--", pathspec,
            cwd=worktree, check=False).strip().splitlines()
        modified_ext += _run_git(
            "diff", "--name-only", "HEAD", "--", pathspec,
            cwd=worktree, check=False).strip().splitlines()
        untracked_ext = _run_git(
            "ls-files", "--others", "--exclude-standard", pathspec,
            cwd=worktree).strip().splitlines()

        all_modified = sorted(set(
            f.strip() for f in modified_ext + untracked_ext
            if f.strip() and not f.strip().startswith("_eval_tests/")
        ))

        for rel in all_modified:
            src = worktree / rel
            if not src.is_file():
                continue
            dest = run_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

        if (run_dir / entrypoint).exists():
            shutil.copy2(run_dir / entrypoint, model_dir / entrypoint)

        eval_dir = worktree / "_eval_tests"
        if eval_dir.exists():
            shutil.rmtree(eval_dir)
        eval_dir.mkdir()

        tests_src = task_dir / "tests"
        if not tests_src.is_dir():
            shutil.rmtree(eval_dir, ignore_errors=True)
            raise FileNotFoundError(f"no tests dir at {tests_src}")

        shutil.copytree(tests_src, eval_dir, dirs_exist_ok=True)

        test_timeout = int(os.environ.get("CAPTURE_TEST_TIMEOUT", "300"))
        try:
            proc = subprocess.run(
                test_invocation,
                cwd=str(worktree),
                capture_output=True,
                text=True,
                timeout=test_timeout,
            )
            test_exit = proc.returncode
            test_stdout = proc.stdout
            test_stderr = proc.stderr
        except subprocess.TimeoutExpired as e:
            log.error("hidden tests timed out after %ds — recording exit 124. "
                      "Override with CAPTURE_TEST_TIMEOUT=<seconds>.",
                      test_timeout)
            test_exit = 124
            test_stdout = (e.stdout.decode(errors="replace")
                           if isinstance(e.stdout, bytes)
                           else (e.stdout or ""))
            test_stderr = (e.stderr.decode(errors="replace")
                           if isinstance(e.stderr, bytes)
                           else (e.stderr or ""))
        (run_dir / "test-output.txt").write_text(
            test_stdout + "\n--- stderr ---\n" + test_stderr)

        shutil.rmtree(eval_dir, ignore_errors=True)

        impl_path = worktree / entrypoint
        loc = _task.loc_count(impl_path, loc_method) if impl_path.exists() else 0

        return {
            "base_commit": base,
            "entrypoint": entrypoint,
            "impl_loc": loc,
            "test_exit_code": test_exit,
        }

    def assemble_packet(
        self,
        *,
        task_dir: pathlib.Path,
        judge_dir: pathlib.Path,
        impls: list[dict],
        mapping: dict[str, str],
        entrypoint: str,
    ) -> None:
        """Write one judge's packet at judge_dir.

        Side effects (filesystem):
          - <judge_dir>/packet/{PROMPT.md, SPEC.md, JUDGE_PROMPT.md,
            JUDGE_RUBRIC.md} (each copied from task_dir if present)
          - <judge_dir>/packet/implementations/<label><suffix> per impl
            in mapping, blinded
          - <judge_dir>/packet/README.md cover note
          - <judge_dir>/output/ (empty — judge fills it)
        """
        packet = judge_dir / "packet"
        impl_dir = packet / "implementations"
        output = judge_dir / "output"
        impl_dir.mkdir(parents=True, exist_ok=True)
        output.mkdir(parents=True, exist_ok=True)

        for fname in ["PROMPT.md", "SPEC.md", "JUDGE_PROMPT.md", "JUDGE_RUBRIC.md"]:
            src = task_dir / fname
            if src.exists():
                shutil.copy2(src, packet / fname)

        suffix = pathlib.Path(entrypoint).suffix
        for impl in impls:
            if impl["model"] not in mapping:
                continue
            label = mapping[impl["model"]]
            shutil.copy2(impl["impl_path"], impl_dir / f"{label}{suffix}")

        labels = sorted(mapping.values())
        cover = packet / "README.md"
        cover.write_text(
            f"# Judgment packet\n\n"
            f"Implementations to review (blinded labels): {', '.join(labels)}\n\n"
            f"Read PROMPT.md and SPEC.md first to understand what was asked.\n"
            f"Then read JUDGE_PROMPT.md for your task and the output format.\n"
            f"Score each implementation independently. Write outputs to ../output/.\n"
        )

    def score(
        self,
        *,
        judge: str,
        judge_dir: pathlib.Path,
        slug: str,
        message: str,
        log_path: pathlib.Path | None,
        out_root_name: str,
    ) -> tuple[int, float]:
        """Drive a single judge through `opencode run`.

        Returns (rc, elapsed_seconds). Caller is responsible for skipping
        judges whose slug isn't in config — this helper assumes the slug
        exists. With log_path=None, opencode inherits stdout (sequential
        mode); with log_path set, output is redirected so concurrent
        judges' streams don't interleave.
        """
        title = f"{out_root_name}-{judge}"
        started = time.monotonic()
        rc = _opencode_run.run(
            directory=judge_dir,
            model=slug,
            message=message,
            title=title,
            log_path=log_path,
        )
        return rc, time.monotonic() - started
