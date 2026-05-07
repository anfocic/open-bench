"""CodeTask.extract_artifact in isolation.

These tests exercise the carved-out extract_artifact path without going
through capture_run, so the CodeTask contract is regression-locked
independently of the orchestrator. capture_run-level integration tests
live in test_capture_run_*.py.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from . import conftest  # noqa: F401

from bench.scripts._kinds import code as code_kind
from bench.scripts._kinds.code import CodeTask


class TestCodeTaskExtractArtifact(unittest.TestCase):
    def _layout(self):
        tmp = Path(tempfile.mkdtemp())
        worktree = tmp / "wt"
        worktree.mkdir()
        run_dir = tmp / "run"
        run_dir.mkdir()
        model_dir = tmp / "model"
        model_dir.mkdir()
        task_dir = tmp / "task"
        (task_dir / "tests").mkdir(parents=True)
        (task_dir / "tests" / "test_x.py").write_text("def test_x(): pass\n")
        return tmp, worktree, run_dir, model_dir, task_dir

    def test_returns_expected_dict_shape(self):
        tmp, worktree, run_dir, model_dir, task_dir = self._layout()
        try:
            (worktree / "sandbox.py").write_text("a = 1\nb = 2\n")
            task_cfg = {
                "task_kind": "code",
                "entrypoint": "sandbox.py",
                "test_invocation": ["true"],
                "loc_method": "non_blank_non_comment_lines",
            }

            def fake_git(*args, **kwargs):
                if args[0] == "merge-base":
                    return "abc123\n"
                return ""

            def fake_run(*args, **kwargs):
                # The pytest invocation — return success.
                class P:
                    returncode = 0
                    stdout = "1 passed"
                    stderr = ""
                return P()

            with mock.patch.object(code_kind, "_run_git", side_effect=fake_git), \
                 mock.patch.object(code_kind.subprocess, "run", side_effect=fake_run):
                result = CodeTask().extract_artifact(
                    worktree=worktree,
                    run_dir=run_dir,
                    model_dir=model_dir,
                    task_dir=task_dir,
                    task_cfg=task_cfg,
                    base_branch="main",
                )

            self.assertEqual(result["base_commit"], "abc123")
            self.assertEqual(result["entrypoint"], "sandbox.py")
            self.assertEqual(result["test_exit_code"], 0)
            self.assertEqual(result["impl_loc"], 2)
            # Side-effect files exist.
            self.assertTrue((run_dir / "diff.patch").exists())
            self.assertTrue((run_dir / "test-output.txt").exists())
            # _eval_tests was cleaned up.
            self.assertFalse((worktree / "_eval_tests").exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_missing_tests_dir_raises_filenotfound(self):
        tmp, worktree, run_dir, model_dir, task_dir = self._layout()
        try:
            shutil.rmtree(task_dir / "tests")
            (worktree / "sandbox.py").write_text("# impl\n")
            task_cfg = {
                "task_kind": "code", "entrypoint": "sandbox.py",
                "test_invocation": ["true"],
                "loc_method": "non_blank_non_comment_lines",
            }

            with mock.patch.object(code_kind, "_run_git", return_value="abc"):
                with self.assertRaises(FileNotFoundError) as ctx:
                    CodeTask().extract_artifact(
                        worktree=worktree, run_dir=run_dir, model_dir=model_dir,
                        task_dir=task_dir, task_cfg=task_cfg, base_branch="main",
                    )
            self.assertIn("tests", str(ctx.exception))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_timeout_records_exit_124(self):
        tmp, worktree, run_dir, model_dir, task_dir = self._layout()
        try:
            (worktree / "sandbox.py").write_text("# impl\n")
            task_cfg = {
                "task_kind": "code", "entrypoint": "sandbox.py",
                "test_invocation": ["sleep", "10"],
                "loc_method": "non_blank_non_comment_lines",
            }

            def fake_run(*args, **kwargs):
                if kwargs.get("timeout") is not None:
                    raise subprocess.TimeoutExpired(
                        cmd=args[0], timeout=kwargs["timeout"],
                        output=b"slow", stderr=b"err",
                    )
                class P:
                    returncode = 0
                    stdout = ""
                    stderr = ""
                return P()

            with mock.patch.object(code_kind, "_run_git", return_value="abc"), \
                 mock.patch.object(code_kind.subprocess, "run", side_effect=fake_run), \
                 mock.patch.dict(os.environ, {"CAPTURE_TEST_TIMEOUT": "1"}, clear=False):
                result = CodeTask().extract_artifact(
                    worktree=worktree, run_dir=run_dir, model_dir=model_dir,
                    task_dir=task_dir, task_cfg=task_cfg, base_branch="main",
                )

            self.assertEqual(result["test_exit_code"], 124)
            test_output = (run_dir / "test-output.txt").read_text()
            self.assertIn("slow", test_output)
            self.assertIn("err", test_output)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_promotes_entrypoint_to_model_dir(self):
        tmp, worktree, run_dir, model_dir, task_dir = self._layout()
        try:
            (worktree / "sandbox.py").write_text("x = 1\n")
            task_cfg = {
                "task_kind": "code", "entrypoint": "sandbox.py",
                "test_invocation": ["true"],
                "loc_method": "non_blank_non_comment_lines",
            }

            def fake_git(*args, **kwargs):
                if args[0] == "merge-base":
                    return "abc"
                if args[0] == "ls-files" and "--others" in args:
                    return "sandbox.py\n"
                return ""

            def fake_run(*args, **kwargs):
                class P:
                    returncode = 0; stdout = ""; stderr = ""
                return P()

            with mock.patch.object(code_kind, "_run_git", side_effect=fake_git), \
                 mock.patch.object(code_kind.subprocess, "run", side_effect=fake_run):
                CodeTask().extract_artifact(
                    worktree=worktree, run_dir=run_dir, model_dir=model_dir,
                    task_dir=task_dir, task_cfg=task_cfg, base_branch="main",
                )

            self.assertTrue((model_dir / "sandbox.py").exists())
            self.assertEqual((model_dir / "sandbox.py").read_text(), "x = 1\n")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
