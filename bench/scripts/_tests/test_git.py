"""Pin behavior of capture_run._run_git (identical copy lives in start_run).

PR2 extracts both into bench/scripts/_git.py:run_git(); these tests must
keep passing after that move with only the import path updated.
"""

from __future__ import annotations

import subprocess
import unittest
from unittest import mock

from . import conftest  # noqa: F401

import capture_run  # noqa: E402
import start_run  # noqa: E402


def _completed(rc: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["git"], returncode=rc, stdout=stdout, stderr=stderr,
    )


class TestRunGitCaptureRun(unittest.TestCase):
    def test_happy_path_returns_stdout(self) -> None:
        with mock.patch("capture_run.subprocess.run", return_value=_completed(0, "main\n")):
            self.assertEqual(capture_run._run_git("symbolic-ref", "HEAD"), "main\n")

    def test_nonzero_rc_with_check_raises(self) -> None:
        with mock.patch("capture_run.subprocess.run",
                        return_value=_completed(1, "", "fatal: not a repo")):
            with self.assertRaises(RuntimeError) as ctx:
                capture_run._run_git("status", check=True)
            self.assertIn("git status failed", str(ctx.exception))
            self.assertIn("not a repo", str(ctx.exception))

    def test_nonzero_rc_with_check_false_returns_stdout(self) -> None:
        with mock.patch("capture_run.subprocess.run",
                        return_value=_completed(1, "partial output", "warning")):
            self.assertEqual(
                capture_run._run_git("status", check=False),
                "partial output",
            )

    def test_passes_cwd(self) -> None:
        with mock.patch("capture_run.subprocess.run",
                        return_value=_completed(0, "")) as run_mock:
            capture_run._run_git("status", cwd="/tmp/some/path")
            kwargs = run_mock.call_args.kwargs
            self.assertEqual(kwargs["cwd"], "/tmp/some/path")
            self.assertEqual(kwargs["capture_output"], True)
            self.assertEqual(kwargs["text"], True)
            self.assertEqual(kwargs["check"], False)


class TestRunGitStartRun(unittest.TestCase):
    """start_run holds an identical copy. Both must behave the same."""

    def test_happy_path_returns_stdout(self) -> None:
        with mock.patch("start_run.subprocess.run", return_value=_completed(0, "main\n")):
            self.assertEqual(start_run._run_git("symbolic-ref", "HEAD"), "main\n")

    def test_nonzero_rc_with_check_raises(self) -> None:
        with mock.patch("start_run.subprocess.run",
                        return_value=_completed(1, "", "fatal: bad")):
            with self.assertRaises(RuntimeError):
                start_run._run_git("status", check=True)


if __name__ == "__main__":
    unittest.main()
