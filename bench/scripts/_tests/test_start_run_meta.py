"""Pin: start_run.start_run writes a meta.json stub at the run dir.

Replaces the previous .started_at sidecar. capture_run.py reads slug,
worktree, started_at out of this file instead of slicing the dir name.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from . import conftest  # noqa: F401

from bench.scripts import start_run as sr  # noqa: E402


class FakeCfg:
    implementers = ["alpha"]
    slugs = {"alpha": "p/alpha-1"}

    def slug_for(self, name: str) -> str:
        return self.slugs[name]


class TestStartRunMeta(unittest.TestCase):
    def test_writes_meta_with_required_fields(self) -> None:
        # Use a nested repo dir so the worktree path
        # `REPO_ROOT/../eval-<slug>` lands inside our tmp tree.
        outer = Path(tempfile.mkdtemp())
        tmp = outer / "repo"
        tmp.mkdir()
        try:
            task_dir = tmp / "bench" / "tasks" / "weird-task"
            task_dir.mkdir(parents=True)
            (task_dir / "PROMPT.md").write_text("p")
            (task_dir / "SPEC.md").write_text("s")
            # Pre-create worktree dir so shutil.copy2 lands somewhere real
            # (in production, `git worktree add` creates this; we mock git).
            slug = "weird-task-alpha-2026-05-05"
            (outer / f"eval-{slug}").mkdir()

            def fake_git(*args, **kwargs):
                # rev-parse --verify <branch> must raise so start_run
                # treats the branch as not-yet-existing.
                if args[:2] == ("rev-parse", "--verify"):
                    raise RuntimeError("git rev-parse failed (no branch)")
                return ""

            with mock.patch.object(sr, "REPO_ROOT", tmp), \
                 mock.patch.object(sr._task, "REPO_ROOT", tmp), \
                 mock.patch.object(sr._config, "load", return_value=FakeCfg()), \
                 mock.patch.object(sr, "_run_git", side_effect=fake_git), \
                 mock.patch.object(sr, "determine_base_branch", return_value="main"), \
                 mock.patch.dict(os.environ, {"RUN_STAMP": "2026-05-05"}, clear=False):
                rc = sr.start_run("weird-task", "alpha", auto=False)
            self.assertEqual(rc, 0)

            run_dir = tmp / "builds" / "alpha" / "rounds" / "weird-task-2026-05-05"
            meta = json.loads((run_dir / "meta.json").read_text())
            self.assertEqual(meta["task"], "weird-task")
            self.assertEqual(meta["model"], "alpha")
            self.assertEqual(meta["slug"], "weird-task-alpha-2026-05-05")
            self.assertEqual(meta["date_stamp"], "2026-05-05")
            self.assertEqual(meta["branch"], "eval/weird-task-alpha-2026-05-05")
            self.assertIn("worktree", meta)
            self.assertRegex(meta["started_at"], r"^\d{4}-\d{2}-\d{2}T")
        finally:
            shutil.rmtree(outer, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
