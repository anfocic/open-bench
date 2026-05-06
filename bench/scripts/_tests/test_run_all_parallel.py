"""Coverage for run_all.main's threadpool branch.

The existing test_run_all_main.py covers --concurrency 1 only. The
parallel branch (lock, per-model log files, fan-out via
ThreadPoolExecutor, ok/fail tally under results_lock, fail-tail dump)
is what most users actually hit. Mutations in this path would slip
through the sequential test.

These tests stub start_run, the post-implementer subprocess calls, and
config; they exercise the real ThreadPoolExecutor + as_completed wiring
plus the rc-aggregation logic.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from . import conftest  # noqa: F401

from bench.scripts import run_all  # noqa: E402


def _completed(rc: int) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=["python"], returncode=rc)


class FakeCfg:
    """Minimal stand-in for _config.Config in run_all.main."""
    def __init__(self, implementers: list[str]) -> None:
        self.implementers = implementers


class TestRunAllParallel(unittest.TestCase):
    def _run(self, *, models: list[str], rc_by_model: dict[str, int],
             judge_rc: int = 0, agg_rc: int = 0,
             concurrency: int = 3) -> tuple[int, Path]:
        tmp = Path(tempfile.mkdtemp())

        def fake_start_run(task, model, auto, worktree_lock=None,
                           log_path=None):
            assert auto is True
            assert worktree_lock is not None
            assert log_path is not None
            log_path.write_text(f"log for {model}\nexit {rc_by_model[model]}\n")
            return rc_by_model[model]

        argv = ["run_all.py", "sandbox", "--concurrency", str(concurrency)]
        with mock.patch.object(run_all, "REPO_ROOT", tmp), \
             mock.patch.object(sys, "argv", argv), \
             mock.patch.object(run_all._config, "load",
                               return_value=FakeCfg(models)), \
             mock.patch.object(run_all, "start_run",
                               side_effect=fake_start_run), \
             mock.patch.object(
                 run_all.subprocess, "run",
                 side_effect=[_completed(judge_rc), _completed(agg_rc)],
             ):
            rc = run_all.main()
        return rc, tmp

    def test_all_models_pass_returns_zero(self) -> None:
        rc, tmp = self._run(
            models=["alpha", "beta", "gamma"],
            rc_by_model={"alpha": 0, "beta": 0, "gamma": 0},
        )
        try:
            self.assertEqual(rc, 0)
            for m in ("alpha", "beta", "gamma"):
                self.assertTrue(
                    (tmp / "builds" / m / "last-impl.log").exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_one_model_fails_returns_one(self) -> None:
        rc, tmp = self._run(
            models=["alpha", "beta"],
            rc_by_model={"alpha": 0, "beta": 2},
        )
        try:
            self.assertEqual(rc, 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_judge_phase_failure_propagates(self) -> None:
        rc, tmp = self._run(
            models=["alpha"],
            rc_by_model={"alpha": 0},
            judge_rc=3,
        )
        try:
            self.assertEqual(rc, 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_aggregate_phase_failure_propagates(self) -> None:
        rc, tmp = self._run(
            models=["alpha"],
            rc_by_model={"alpha": 0},
            agg_rc=4,
        )
        try:
            self.assertEqual(rc, 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_subprocess_children_get_verbosity_flags(self) -> None:
        """run_all.main propagates --quiet/--verbose to subprocess kids."""
        tmp = Path(tempfile.mkdtemp())
        captured_argvs: list[list[str]] = []

        def fake_run(argv, **kw):
            captured_argvs.append(list(argv))
            return _completed(0)

        argv = ["run_all.py", "sandbox", "--concurrency", "2", "--verbose"]
        try:
            with mock.patch.object(run_all, "REPO_ROOT", tmp), \
                 mock.patch.object(sys, "argv", argv), \
                 mock.patch.object(run_all._config, "load",
                                   return_value=FakeCfg(["alpha"])), \
                 mock.patch.object(run_all, "start_run", return_value=0), \
                 mock.patch.object(run_all.subprocess, "run",
                                   side_effect=fake_run):
                rc = run_all.main()
            self.assertEqual(rc, 0)
            # Two subprocess calls: judgments + aggregate. Each carries --verbose.
            self.assertEqual(len(captured_argvs), 2)
            for sub_argv in captured_argvs:
                self.assertIn("--verbose", sub_argv)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
