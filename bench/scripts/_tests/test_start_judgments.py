"""Pin: start_judgments.find_runs reads identity from meta.json, not dir names.

Also pins that runs_index.json is written with the richer per-model schema
(path/slug/date_stamp/started_at) and a top-level judgment_meta.json is
emitted alongside it.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from . import conftest  # noqa: F401

from bench.scripts import _opencode_run  # noqa: E402
from bench.scripts import start_judgments as sj  # noqa: E402


class TestFindRunsMetaDriven(unittest.TestCase):
    def _make_run(self, root: Path, model: str, dir_name: str, *,
                  task: str, date_stamp: str, slug: str,
                  has_meta: bool = True, has_impl: bool = True) -> None:
        run = root / "builds" / model / "rounds" / dir_name
        run.mkdir(parents=True)
        if has_impl:
            (run / "sandbox.py").write_text("# impl\n")
        if has_meta:
            (run / "meta.json").write_text(json.dumps({
                "task": task,
                "model": model,
                "slug": slug,
                "date_stamp": date_stamp,
                "started_at": "2026-05-05T12:00:00Z",
            }))

    def test_picks_latest_per_model_by_meta_date_stamp(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        try:
            self._make_run(tmp, "alpha", "sandbox-2026-05-05",
                           task="sandbox", date_stamp="2026-05-05",
                           slug="sandbox-alpha-2026-05-05")
            self._make_run(tmp, "alpha", "sandbox-2026-05-05-r2",
                           task="sandbox", date_stamp="2026-05-05-r2",
                           slug="sandbox-alpha-2026-05-05-r2")
            with mock.patch.object(sj, "REPO_ROOT", tmp):
                runs = sj.find_runs("sandbox", "sandbox.py")
            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0]["model"], "alpha")
            self.assertEqual(runs[0]["date_stamp"], "2026-05-05-r2")
            self.assertEqual(runs[0]["meta"]["slug"], "sandbox-alpha-2026-05-05-r2")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_filters_by_task_in_meta_not_dir_prefix(self) -> None:
        """A run whose dir name happens to start with the task name but
        whose meta declares a different task is excluded."""
        tmp = Path(tempfile.mkdtemp())
        try:
            self._make_run(tmp, "alpha", "sandbox-2026-05-05",
                           task="other-task", date_stamp="2026-05-05",
                           slug="other-task-alpha-2026-05-05")
            with mock.patch.object(sj, "REPO_ROOT", tmp):
                runs = sj.find_runs("sandbox", "sandbox.py")
            self.assertEqual(runs, [])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_skips_run_dirs_without_meta(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        try:
            self._make_run(tmp, "alpha", "sandbox-2026-05-05",
                           task="sandbox", date_stamp="2026-05-05",
                           slug="sandbox-alpha-2026-05-05",
                           has_meta=False)
            with mock.patch.object(sj, "REPO_ROOT", tmp):
                runs = sj.find_runs("sandbox", "sandbox.py")
            self.assertEqual(runs, [])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestAutoDriveJudgesParallel(unittest.TestCase):
    """Pin the ThreadPoolExecutor branch of auto_drive_judges (concurrency>1)."""

    def _make_cfg(self, slugs: dict[str, str]):
        class Cfg:
            def __init__(self, slugs):
                self.slugs = slugs
            def slug_for(self, name):
                return self.slugs[name]
        return Cfg(slugs)

    def test_parallel_branch_per_judge_logpath_and_failure_aggregation(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            out_root = tmp / "results" / "judgments" / "sandbox-2026-05-07"
            for j in ("alpha", "beta", "gamma"):
                (out_root / j).mkdir(parents=True)

            cfg = self._make_cfg({"alpha": "a/x", "beta": "b/x", "gamma": "c/x"})

            captured: list[tuple[str, Path]] = []

            class FakeKind:
                def score(self, *, judge, judge_dir, slug, message,
                          log_path, out_root_name):
                    captured.append((judge, log_path))
                    rcs = {"alpha": 0, "beta": 3, "gamma": 0}
                    return rcs[judge], 0.01

            with mock.patch.object(sj, "REPO_ROOT", tmp), \
                 mock.patch.object(_opencode_run, "preflight",
                                   return_value=None):
                rc = sj.auto_drive_judges(
                    out_root, ["alpha", "beta", "gamma"], cfg, FakeKind(),
                    concurrency=2,
                )

            self.assertEqual(rc, 3)
            self.assertEqual(len(captured), 3)
            for judge, log_path in captured:
                self.assertEqual(log_path, out_root / judge / "judge.log")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
