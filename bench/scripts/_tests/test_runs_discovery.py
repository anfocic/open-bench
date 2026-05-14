"""Pin: _runs.find_latest_runs reads identity from meta.json, picks the
latest run per model, and skips dirs missing meta / entrypoint / date_stamp.

This is the shared discovery helper extracted from start_judgments.find_runs;
the round-2 attack phase reuses it to discover both attackers and targets.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from . import conftest  # noqa: F401

from bench.scripts import _runs  # noqa: E402


class TestFindLatestRuns(unittest.TestCase):
    def _make_run(self, root: Path, model: str, dir_name: str, *,
                  task: str, date_stamp: str, slug: str,
                  entrypoint: str = "sandbox.py",
                  has_meta: bool = True, has_impl: bool = True) -> Path:
        run = root / "builds" / model / "rounds" / dir_name
        run.mkdir(parents=True)
        if has_impl:
            (run / entrypoint).write_text("# impl\n")
        if has_meta:
            (run / "meta.json").write_text(json.dumps({
                "task": task,
                "model": model,
                "slug": slug,
                "date_stamp": date_stamp,
                "started_at": "2026-05-05T12:00:00Z",
            }))
        return run

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_picks_latest_per_model_by_date_stamp(self) -> None:
        self._make_run(self.tmp, "alpha", "sandbox-2026-05-05",
                       task="sandbox", date_stamp="2026-05-05",
                       slug="sandbox-alpha-2026-05-05")
        self._make_run(self.tmp, "alpha", "sandbox-2026-05-05-r2",
                       task="sandbox", date_stamp="2026-05-05-r2",
                       slug="sandbox-alpha-2026-05-05-r2")
        runs = _runs.find_latest_runs("sandbox", "sandbox.py",
                                      repo_root=self.tmp)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["model"], "alpha")
        self.assertEqual(runs[0]["date_stamp"], "2026-05-05-r2")
        self.assertEqual(runs[0]["meta"]["slug"],
                         "sandbox-alpha-2026-05-05-r2")
        self.assertEqual(
            runs[0]["impl_path"],
            self.tmp / "builds/alpha/rounds/sandbox-2026-05-05-r2/sandbox.py")

    def test_filters_by_task_in_meta_not_dir_prefix(self) -> None:
        self._make_run(self.tmp, "alpha", "sandbox-2026-05-05",
                       task="other-task", date_stamp="2026-05-05",
                       slug="other-task-alpha-2026-05-05")
        self.assertEqual(
            _runs.find_latest_runs("sandbox", "sandbox.py",
                                   repo_root=self.tmp),
            [])

    def test_skips_run_dirs_without_meta(self) -> None:
        self._make_run(self.tmp, "alpha", "sandbox-2026-05-05",
                       task="sandbox", date_stamp="2026-05-05",
                       slug="s", has_meta=False)
        self.assertEqual(
            _runs.find_latest_runs("sandbox", "sandbox.py",
                                   repo_root=self.tmp),
            [])

    def test_skips_run_dirs_missing_entrypoint(self) -> None:
        self._make_run(self.tmp, "alpha", "sandbox-2026-05-05",
                       task="sandbox", date_stamp="2026-05-05",
                       slug="s", has_impl=False)
        self.assertEqual(
            _runs.find_latest_runs("sandbox", "sandbox.py",
                                   repo_root=self.tmp),
            [])

    def test_skips_meta_without_date_stamp(self) -> None:
        run = self.tmp / "builds/alpha/rounds/sandbox-2026-05-05"
        run.mkdir(parents=True)
        (run / "sandbox.py").write_text("# impl\n")
        (run / "meta.json").write_text(
            json.dumps({"task": "sandbox", "model": "alpha"}))
        self.assertEqual(
            _runs.find_latest_runs("sandbox", "sandbox.py",
                                   repo_root=self.tmp),
            [])

    def test_distinct_entrypoint_name(self) -> None:
        """Round 2 discovers exploit.py artifacts under the break-sandbox
        task — the helper is entrypoint-parameterised, not sandbox-bound."""
        self._make_run(self.tmp, "beta", "break-sandbox-2026-05-14",
                       task="break-sandbox", date_stamp="2026-05-14",
                       slug="break-sandbox-beta-2026-05-14",
                       entrypoint="exploit.py")
        runs = _runs.find_latest_runs("break-sandbox", "exploit.py",
                                      repo_root=self.tmp)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["impl_path"].name, "exploit.py")

    def test_empty_when_no_builds_dir(self) -> None:
        self.assertEqual(
            _runs.find_latest_runs("sandbox", "sandbox.py",
                                   repo_root=self.tmp),
            [])

    def test_one_run_per_model_across_models(self) -> None:
        for model in ("alpha", "beta", "gamma"):
            self._make_run(self.tmp, model, "sandbox-2026-05-05",
                           task="sandbox", date_stamp="2026-05-05",
                           slug=f"sandbox-{model}-2026-05-05")
        runs = _runs.find_latest_runs("sandbox", "sandbox.py",
                                      repo_root=self.tmp)
        self.assertEqual({r["model"] for r in runs},
                         {"alpha", "beta", "gamma"})


if __name__ == "__main__":
    unittest.main()
