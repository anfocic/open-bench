"""Regression: hidden tests honor a timeout instead of hanging capture.

Before the fix, capture_run.py invoked subprocess.run on the hidden test
suite without a timeout — a hung implementation hung capture indefinitely.
Now CAPTURE_TEST_TIMEOUT (default 300s) kicks in and the run records
exit 124 with whatever stdout/stderr was produced before the kill.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from . import conftest  # noqa: F401

from bench.scripts import capture_run as cr  # noqa: E402


class TestCaptureRunTimeout(unittest.TestCase):
    def test_timeout_records_exit_124(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        try:
            task = "sandbox"
            model = "alpha"
            run_dir = tmp / "builds" / model / "rounds" / "sandbox-2026-05-05"
            run_dir.mkdir(parents=True)
            worktree = tmp / "wt"
            worktree.mkdir()
            (worktree / "sandbox.py").write_text("# impl\n")
            (run_dir / "meta.json").write_text(json.dumps({
                "task": task, "model": model, "slug": "x",
                "date_stamp": "2026-05-05", "branch": "x",
                "worktree": str(worktree),
                "started_at": "2026-05-05T00:00:00Z",
            }))

            tests_src = tmp / "bench" / "tasks" / task / "tests"
            tests_src.mkdir(parents=True)
            (tests_src / "test_x.py").write_text("def test_x(): pass\n")

            # Make subprocess.run raise TimeoutExpired on the hidden-test
            # invocation; everything else (git diff via _run_git, opencode
            # probes) is mocked or trivially short.
            real_run = subprocess.run

            def fake_run(*args, **kwargs):
                if kwargs.get("timeout") is not None:
                    raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"],
                                                    output=b"slow stdout",
                                                    stderr=b"slow stderr")
                return real_run(*args, **kwargs)

            with mock.patch.object(cr, "REPO_ROOT", tmp), \
                 mock.patch.object(cr._task, "REPO_ROOT", tmp), \
                 mock.patch.object(cr, "find_run_dir", return_value=run_dir), \
                 mock.patch.object(cr, "_run_git", return_value=""), \
                 mock.patch.object(cr, "determine_base_branch", return_value="main"), \
                 mock.patch.object(cr._opencode, "available", return_value=False), \
                 mock.patch.object(cr.subprocess, "run", side_effect=fake_run), \
                 mock.patch.dict(os.environ, {"CAPTURE_TEST_TIMEOUT": "1"}, clear=False):
                rc = cr.capture(task, model)

            self.assertEqual(rc, 0)
            test_output = (run_dir / "test-output.txt").read_text()
            self.assertIn("slow stdout", test_output)
            self.assertIn("slow stderr", test_output)
            meta = json.loads((run_dir / "meta.json").read_text())
            self.assertEqual(meta["test_exit_code"], 124)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
