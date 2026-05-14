"""Pin: run_attacks escape-gate parsing and matrix construction.

No container is spun — the per-pair pytest subprocess is stubbed with
canned output, so this exercises the inverted-polarity bucketing
(PASS = escaped), the by_class rollup, the timeout flag, self-pair
exclusion, and the invalid-attacker filter.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from . import conftest  # noqa: F401

from bench.scripts import run_attacks  # noqa: E402


CANNED_STDOUT = """\
============================= test session starts =============================
_eval_tests/exploit.py::test_escape_fs__host_read PASSED                  [ 25%]
_eval_tests/exploit.py::test_escape_network__dns FAILED                   [ 50%]
_eval_tests/exploit.py::test_escape_privesc__mount ERROR                  [ 75%]
_eval_tests/exploit.py::test_escape_fs__symlink PASSED                    [100%]
========================= 2 passed, 1 failed, 1 error =========================
"""


class TestClassOf(unittest.TestCase):
    def test_parses_known_classes(self) -> None:
        self.assertEqual(run_attacks.class_of("test_escape_fs__x"), "fs")
        self.assertEqual(
            run_attacks.class_of("test_escape_network__a_b"), "network")

    def test_unknown_returns_none(self) -> None:
        self.assertIsNone(run_attacks.class_of("test_something_else"))
        self.assertIsNone(run_attacks.class_of("test_escape_bogus__x"))


class TestRunPair(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.target = {"model": "tgt", "impl_path": self.tmp / "sandbox.py"}
        self.attacker = {"model": "atk", "impl_path": self.tmp / "exploit.py"}
        self.target["impl_path"].write_text("# sandbox\n")
        self.attacker["impl_path"].write_text("# exploit\n")
        self.conftest = self.tmp / "conftest_runner.py"
        self.conftest.write_text("# conftest\n")

    def test_inverted_polarity_bucketing(self) -> None:
        fake = mock.Mock(stdout=CANNED_STDOUT, stderr="", returncode=1)
        with mock.patch.object(run_attacks.subprocess, "run",
                               return_value=fake):
            result, _raw = run_attacks.run_pair(
                self.attacker, self.target, self.conftest, timeout=60)
        self.assertEqual(
            result["escaped"],
            ["test_escape_fs__host_read", "test_escape_fs__symlink"])
        self.assertEqual(result["held"], ["test_escape_network__dns"])
        self.assertEqual(result["errored"], ["test_escape_privesc__mount"])
        self.assertEqual(result["n_escaped"], 2)
        self.assertEqual(result["n_held"], 1)
        self.assertEqual(result["n_errored"], 1)
        self.assertFalse(result["timed_out"])

    def test_by_class_rollup(self) -> None:
        fake = mock.Mock(stdout=CANNED_STDOUT, stderr="", returncode=1)
        with mock.patch.object(run_attacks.subprocess, "run",
                               return_value=fake):
            result, _raw = run_attacks.run_pair(
                self.attacker, self.target, self.conftest, timeout=60)
        self.assertEqual(
            result["by_class"],
            {"network": False, "fs": True, "resource": False,
             "privesc": False, "shellinj": False})

    def test_timeout_flagged_with_partial_output(self) -> None:
        exc = run_attacks.subprocess.TimeoutExpired(cmd="pytest", timeout=1)
        exc.stdout = "_eval_tests/exploit.py::test_escape_fs__x PASSED\n"
        exc.stderr = ""
        with mock.patch.object(run_attacks.subprocess, "run",
                               side_effect=exc):
            result, _raw = run_attacks.run_pair(
                self.attacker, self.target, self.conftest, timeout=1)
        self.assertTrue(result["timed_out"])
        self.assertEqual(result["escaped"], ["test_escape_fs__x"])


class TestMatrixMain(unittest.TestCase):
    def test_excludes_self_pairs_and_invalid_attackers(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)

        task_dir = tmp / "bench" / "tasks" / "break-sandbox"
        task_dir.mkdir(parents=True)
        (task_dir / "conftest_runner.py").write_text("# conftest\n")

        def fake_find(task, entrypoint, repo_root=None):
            if task == "break-sandbox":
                return [
                    {"model": "alpha", "impl_path": tmp / "a.py",
                     "meta": {"test_exit_code": 0}},
                    {"model": "beta", "impl_path": tmp / "b.py",
                     "meta": {"test_exit_code": 0}},
                    {"model": "gamma", "impl_path": tmp / "g.py",
                     "meta": {"test_exit_code": 1}},  # failed capture gate
                ]
            return [
                {"model": "alpha", "impl_path": tmp / "as.py", "meta": {}},
                {"model": "beta", "impl_path": tmp / "bs.py", "meta": {}},
            ]

        calls: list[tuple[str, str]] = []

        def fake_run_pair(attacker, target, conftest_src, timeout):
            calls.append((attacker["model"], target["model"]))
            return ({
                "attacker": attacker["model"], "target": target["model"],
                "escaped": [], "held": [], "errored": [], "timed_out": False,
                "by_class": {c: False for c in run_attacks.ATTACK_CLASSES},
                "n_escaped": 0, "n_held": 0, "n_errored": 0,
            }, "raw")

        argv = ["run_attacks", "--date", "2026-05-14", "-q"]
        with mock.patch.object(run_attacks, "_has", return_value=True), \
             mock.patch.object(run_attacks._config, "repo_root",
                               return_value=tmp), \
             mock.patch.object(run_attacks._task, "require",
                               return_value=task_dir), \
             mock.patch.object(run_attacks._runs, "find_latest_runs",
                               side_effect=fake_find), \
             mock.patch.object(run_attacks, "read_exploit_catalog",
                               return_value=[]), \
             mock.patch.object(run_attacks, "run_pair",
                               side_effect=fake_run_pair), \
             mock.patch.object(run_attacks.sys, "argv", argv):
            rc = run_attacks.main()

        self.assertEqual(rc, 0)
        # gamma failed the gate -> excluded as attacker; self-pairs skipped
        self.assertEqual(sorted(calls),
                         [("alpha", "beta"), ("beta", "alpha")])

        matrix = json.loads(
            (tmp / "results/attacks/break-sandbox-2026-05-14/matrix.json")
            .read_text())
        self.assertEqual(matrix["attackers"], ["alpha", "beta"])
        self.assertEqual(matrix["targets"], ["alpha", "beta"])
        self.assertEqual(len(matrix["pairs"]), 2)


if __name__ == "__main__":
    unittest.main()
