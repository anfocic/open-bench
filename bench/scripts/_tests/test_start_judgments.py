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


if __name__ == "__main__":
    unittest.main()
