"""Regression: capture_run reads slug/worktree from meta.json, not the dir name.

Pins the bug previously latent in capture_run.py:87 — `run_basename[len(task)+1:]`
silently mis-slices when `task` contains dashes. The test puts a deliberately
non-matching `slug` and `worktree` in meta.json so any fallback to dir-name
slicing would diverge from the values capture() actually uses.
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

from bench.scripts import capture_run as cr  # noqa: E402


class TestCaptureRunReadsMeta(unittest.TestCase):
    def test_uses_meta_worktree_not_dirname_derived(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        try:
            task = "sandbox"
            model = "alpha"
            run_dir = tmp / "builds" / model / "rounds" / "sandbox-2026-05-05"
            run_dir.mkdir(parents=True)

            # Worktree path NOT derivable from the dir name. If capture()
            # were still slicing, it would compute
            # `eval-sandbox-alpha-2026-05-05` and fail to find this path.
            worktree = tmp / "custom-worktree-location"
            worktree.mkdir()
            (worktree / "sandbox.py").write_text("# impl\n")
            meta = {
                "task": task,
                "model": model,
                "slug": "totally-different-slug",
                "date_stamp": "2026-05-05",
                "branch": "eval/x",
                "worktree": str(worktree),
                "started_at": "2026-05-05T12:00:00Z",
            }
            (run_dir / "meta.json").write_text(json.dumps(meta))

            with mock.patch.object(cr, "REPO_ROOT", tmp), \
                 mock.patch.object(cr._task._config, "repo_root", lambda: tmp), \
                 mock.patch.object(cr, "find_run_dir", return_value=run_dir), \
                 mock.patch.object(cr, "determine_base_branch",
                                  side_effect=RuntimeError("__stop_capture__")):
                with self.assertRaises(RuntimeError) as ctx:
                    cr.capture(task, model)

            # Reaching determine_base_branch means the worktree existed
            # and impl_path was found — only true when capture() reads
            # meta["worktree"] (the custom path) rather than slicing.
            self.assertIn("__stop_capture__", str(ctx.exception))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_missing_meta_returns_error(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        try:
            run_dir = tmp / "builds" / "alpha" / "rounds" / "sandbox-2026-05-05"
            run_dir.mkdir(parents=True)
            # No meta.json present.
            with mock.patch.object(cr, "REPO_ROOT", tmp), \
                 mock.patch.object(cr._task._config, "repo_root", lambda: tmp), \
                 mock.patch.object(cr, "find_run_dir", return_value=run_dir):
                rc = cr.capture("sandbox", "alpha")
            self.assertEqual(rc, 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
