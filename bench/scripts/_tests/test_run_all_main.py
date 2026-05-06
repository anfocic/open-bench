"""Regression test: run_all.main propagates judge / aggregate rc into exit code.

Before the fix, lines 118-126 captured rc_judge and rc_agg from
subprocess.run().returncode but the final `return 1 if fail_models else 0`
ignored both — judge or aggregate could fail silently while run_all
exited 0. This test pins the corrected behavior.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from unittest import mock

from . import conftest  # noqa: F401

import run_all  # noqa: E402


def _completed(rc: int) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=["python"], returncode=rc)


class FakeCfg:
    implementers = ["alpha"]


class TestRunAllExitCode(unittest.TestCase):
    def _run(self, *, impl_rc: int, judge_rc: int, agg_rc: int) -> int:
        argv = ["run_all.py", "sandbox", "--concurrency", "1"]
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(run_all._config, "load", return_value=FakeCfg()), \
             mock.patch.object(run_all, "start_run", return_value=impl_rc), \
             mock.patch.object(
                 run_all.subprocess, "run",
                 side_effect=[_completed(judge_rc), _completed(agg_rc)],
             ):
            return run_all.main()

    def test_all_zero_returns_zero(self) -> None:
        self.assertEqual(self._run(impl_rc=0, judge_rc=0, agg_rc=0), 0)

    def test_impl_failure_returns_one(self) -> None:
        self.assertEqual(self._run(impl_rc=2, judge_rc=0, agg_rc=0), 1)

    def test_judge_failure_returns_one(self) -> None:
        self.assertEqual(self._run(impl_rc=0, judge_rc=3, agg_rc=0), 1)

    def test_aggregate_failure_returns_one(self) -> None:
        self.assertEqual(self._run(impl_rc=0, judge_rc=0, agg_rc=4), 1)

    def test_all_failures_returns_one(self) -> None:
        self.assertEqual(self._run(impl_rc=2, judge_rc=3, agg_rc=4), 1)


if __name__ == "__main__":
    unittest.main()
