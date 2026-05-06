"""Regression test: capture_run.main parses argv exactly once.

Before the fix at capture_run.py:318, the function called p.parse_args()
twice (once for .task, once for .model) — harmless on the happy path but
wasteful and a sign of bigger problems if argparse ever has side effects
(e.g. with mutually-exclusive groups or env-driven defaults).
"""

from __future__ import annotations

import sys
import unittest
from unittest import mock

from . import conftest  # noqa: F401

import capture_run  # noqa: E402


class TestCaptureMainParseArgs(unittest.TestCase):
    def test_parse_args_called_once(self) -> None:
        argv = ["capture_run.py", "sandbox", "kimi"]
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(capture_run, "capture", return_value=0) as cap, \
             mock.patch.object(
                capture_run.argparse.ArgumentParser,
                "parse_args",
                autospec=True,
                wraps=capture_run.argparse.ArgumentParser.parse_args,
             ) as parse_mock:
            rc = capture_run.main()
        self.assertEqual(rc, 0)
        self.assertEqual(parse_mock.call_count, 1)
        cap.assert_called_once_with("sandbox", "kimi")


if __name__ == "__main__":
    unittest.main()
