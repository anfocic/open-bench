"""Coverage for start_run.determine_base_branch fallback chain.

The function probes BASE_BRANCH env var → origin/HEAD → main → master and
raises if all fail. Previously only the happy path (origin/HEAD) was
exercised, so a regression in the fallback ordering or the final raise
could ship silently.
"""

from __future__ import annotations

import os
import pathlib
import unittest
from unittest import mock

from . import conftest  # noqa: F401

from bench.scripts import start_run as sr  # noqa: E402


REPO = pathlib.Path("/tmp/fake-repo")


class TestDetermineBaseBranch(unittest.TestCase):
    def setUp(self) -> None:
        # Strip a real BASE_BRANCH from the test env so it doesn't shadow.
        self._env_patch = mock.patch.dict(os.environ, {}, clear=False)
        self._env_patch.start()
        os.environ.pop("BASE_BRANCH", None)

    def tearDown(self) -> None:
        self._env_patch.stop()

    def test_env_var_wins(self) -> None:
        os.environ["BASE_BRANCH"] = "develop"
        with mock.patch.object(sr, "_run_git") as g:
            self.assertEqual(sr.determine_base_branch(REPO), "develop")
        # Should short-circuit before any git call.
        g.assert_not_called()

    def test_origin_head_happy_path(self) -> None:
        def fake(*args, **kwargs):
            if args[:2] == ("symbolic-ref", "--short"):
                return "origin/main\n"
            raise AssertionError(f"unexpected git call: {args}")
        with mock.patch.object(sr, "_run_git", side_effect=fake):
            self.assertEqual(sr.determine_base_branch(REPO), "main")

    def test_origin_head_returns_non_origin_prefix_falls_through(self) -> None:
        # If `git symbolic-ref` returns something not prefixed with origin/
        # (e.g. detached, or a rare config), we should fall through to the
        # main/master probe rather than blindly returning the value.
        calls = []

        def fake(*args, **kwargs):
            calls.append(args[0])
            if args[:2] == ("symbolic-ref", "--short"):
                return ""  # check=False path: empty stdout on failure
            if args[0] == "rev-parse" and args[-1] == "main":
                return "abc123\n"
            raise RuntimeError(f"git {args} failed: not found")

        with mock.patch.object(sr, "_run_git", side_effect=fake):
            self.assertEqual(sr.determine_base_branch(REPO), "main")
        self.assertIn("symbolic-ref", calls)
        self.assertIn("rev-parse", calls)

    def test_falls_back_to_master_when_main_missing(self) -> None:
        def fake(*args, **kwargs):
            if args[:2] == ("symbolic-ref", "--short"):
                return ""
            if args[0] == "rev-parse" and args[-1] == "main":
                raise RuntimeError("git rev-parse failed: unknown revision main")
            if args[0] == "rev-parse" and args[-1] == "master":
                return "def456\n"
            raise AssertionError(f"unexpected git call: {args}")
        with mock.patch.object(sr, "_run_git", side_effect=fake):
            self.assertEqual(sr.determine_base_branch(REPO), "master")

    def test_raises_when_all_probes_fail(self) -> None:
        def fake(*args, **kwargs):
            if args[:2] == ("symbolic-ref", "--short"):
                return ""
            if args[0] == "rev-parse":
                raise RuntimeError(f"git rev-parse failed: {args[-1]} unknown")
            raise AssertionError(f"unexpected: {args}")
        with mock.patch.object(sr, "_run_git", side_effect=fake):
            with self.assertRaises(RuntimeError) as ctx:
                sr.determine_base_branch(REPO)
        msg = str(ctx.exception)
        self.assertIn("origin/HEAD", msg)
        self.assertIn("main", msg)
        self.assertIn("master", msg)
        self.assertIn("BASE_BRANCH", msg)


if __name__ == "__main__":
    unittest.main()
