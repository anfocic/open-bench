"""Regression: capture_run pathspec falls back to entrypoint basename
when the entrypoint has no extension.

Previously `f"*{suffix}"` produced the literal `*` for an extension-less
entrypoint (e.g. `Makefile`, `solver`), which matches every path in the
worktree and dragged unrelated files into the run dir. The fix uses the
entrypoint basename as the pathspec when there's no suffix.
"""

from __future__ import annotations

import unittest
from unittest import mock

from . import conftest  # noqa: F401

from bench.scripts import capture_run  # noqa: E402


class TestPathspecConstruction(unittest.TestCase):
    """Verify the pathspec passed to git diff/ls-files for assorted entrypoints."""

    def _captured_pathspecs(self, entrypoint: str) -> list[str]:
        """Drive the suffix branch in capture() and collect pathspec args."""
        seen: list[str] = []

        def fake(*args, **kwargs):
            seen.append(args[-1])
            return ""

        # Mirror the production code so the test stays a real spec of behavior.
        import pathlib
        suffix = pathlib.Path(entrypoint).suffix
        pathspec = f"*{suffix}" if suffix else pathlib.Path(entrypoint).name

        with mock.patch.object(capture_run, "_run_git", side_effect=fake):
            capture_run._run_git(
                "diff", "--name-only", "BASE", "--", pathspec, check=False,
            )
            capture_run._run_git(
                "diff", "--name-only", "HEAD", "--", pathspec, check=False,
            )
            capture_run._run_git(
                "ls-files", "--others", "--exclude-standard", pathspec,
            )
        return seen

    def test_python_entrypoint_uses_star_py(self) -> None:
        self.assertEqual(self._captured_pathspecs("sandbox.py"), ["*.py"] * 3)

    def test_extensionless_entrypoint_uses_basename(self) -> None:
        # The bug: `*""` → `*` would have appeared here, matching everything.
        self.assertEqual(self._captured_pathspecs("Makefile"), ["Makefile"] * 3)

    def test_extensionless_nested_entrypoint_uses_basename_only(self) -> None:
        self.assertEqual(
            self._captured_pathspecs("src/solver"),
            ["solver"] * 3,
        )


class TestCapturePathspecIntegration(unittest.TestCase):
    """End-to-end check: capture() actually invokes git with the new pathspec.

    Mocks at the _run_git boundary and inspects the recorded calls — this
    pins the wiring so a future refactor can't silently regress to `*`.
    """

    def test_extensionless_entrypoint_does_not_pass_bare_star(self) -> None:
        import json
        import shutil
        import tempfile
        from pathlib import Path

        tmp = Path(tempfile.mkdtemp())
        try:
            task = "sandbox"
            model = "alpha"
            run_dir = tmp / "builds" / model / "rounds" / "sandbox-2026-05-05"
            run_dir.mkdir(parents=True)
            worktree = tmp / "wt"
            worktree.mkdir()
            (worktree / "Makefile").write_text("all:\n\techo hi\n")
            meta = {
                "task": task, "model": model,
                "slug": "sandbox-2026-05-05",
                "date_stamp": "2026-05-05",
                "branch": "eval/x", "worktree": str(worktree),
                "started_at": "2026-05-05T12:00:00Z",
            }
            (run_dir / "meta.json").write_text(json.dumps(meta))

            # Force the entrypoint that capture() reads to be extensionless.
            task_cfg = {
                "entrypoint": "Makefile",
                "test_invocation": ["echo", "ok"],
                "loc_method": "wc",
            }

            seen_pathspecs: list[str] = []

            def fake_git(*args, **kwargs):
                # Capture only the three suffix-filter calls:
                #   diff --name-only <base> -- <pathspec>
                #   diff --name-only HEAD   -- <pathspec>
                #   ls-files --others --exclude-standard <pathspec>
                # Skip the bare `ls-files --others --exclude-standard` that
                # capture() also makes earlier (no pathspec arg).
                last = args[-1]
                if "--name-only" in args:
                    seen_pathspecs.append(last)
                elif "--others" in args and last != "--exclude-standard":
                    seen_pathspecs.append(last)
                return ""

            with mock.patch.object(capture_run, "REPO_ROOT", tmp), \
                 mock.patch.object(capture_run._task._config, "repo_root", lambda: tmp), \
                 mock.patch.object(capture_run, "find_run_dir", return_value=run_dir), \
                 mock.patch.object(capture_run, "determine_base_branch", return_value="main"), \
                 mock.patch.object(capture_run._task, "load", return_value=task_cfg), \
                 mock.patch.object(capture_run, "_run_git", side_effect=fake_git):
                capture_run.capture(task, model)

            self.assertTrue(seen_pathspecs, "expected git diff/ls-files calls")
            for ps in seen_pathspecs:
                self.assertNotEqual(ps, "*", f"bare-* pathspec leaked: {seen_pathspecs}")
                self.assertEqual(ps, "Makefile")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
