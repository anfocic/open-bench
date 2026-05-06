"""Behavior of bench/scripts/_git.run_git.

The same wrapper used to live in capture_run.py and start_run.py as
identical-ish copies; both now alias to _git.run_git, so tests target
the canonical impl.
"""

from __future__ import annotations

import subprocess
import unittest
from unittest import mock

from . import conftest  # noqa: F401

from bench.scripts import _git  # noqa: E402
from bench.scripts import capture_run  # noqa: E402
from bench.scripts import start_run  # noqa: E402


def _completed(rc: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["git"], returncode=rc, stdout=stdout, stderr=stderr,
    )


class TestRunGit(unittest.TestCase):
    def test_happy_path_returns_stdout(self) -> None:
        with mock.patch("bench.scripts._git.subprocess.run", return_value=_completed(0, "main\n")):
            self.assertEqual(_git.run_git("symbolic-ref", "HEAD"), "main\n")

    def test_nonzero_rc_with_check_raises(self) -> None:
        with mock.patch("bench.scripts._git.subprocess.run",
                        return_value=_completed(1, "", "fatal: not a repo\n")):
            with self.assertRaises(RuntimeError) as ctx:
                _git.run_git("status", check=True)
            self.assertIn("git status failed", str(ctx.exception))
            self.assertIn("not a repo", str(ctx.exception))

    def test_nonzero_rc_with_check_false_returns_stdout(self) -> None:
        with mock.patch("bench.scripts._git.subprocess.run",
                        return_value=_completed(1, "partial output", "warning")):
            self.assertEqual(
                _git.run_git("status", check=False),
                "partial output",
            )

    def test_passes_cwd_and_subprocess_kwargs(self) -> None:
        with mock.patch("bench.scripts._git.subprocess.run",
                        return_value=_completed(0, "")) as run_mock:
            _git.run_git("status", cwd="/tmp/some/path")
            kwargs = run_mock.call_args.kwargs
            self.assertEqual(kwargs["cwd"], "/tmp/some/path")
            self.assertEqual(kwargs["capture_output"], True)
            self.assertEqual(kwargs["text"], True)
            self.assertEqual(kwargs["check"], False)


class TestAliases(unittest.TestCase):
    """capture_run._run_git and start_run._run_git are aliases for run_git."""

    def test_capture_run_alias(self) -> None:
        self.assertIs(capture_run._run_git, _git.run_git)

    def test_start_run_alias(self) -> None:
        self.assertIs(start_run._run_git, _git.run_git)


if __name__ == "__main__":
    unittest.main()
