"""Pin clean error paths in aggregate_judges.main.

- Missing `judgment_meta.json` → log.error + return 1.
- judgment_meta.json present but missing `date_stamp` → log.error + return 1
  (regression: previously raised an unguarded KeyError).

Also pins the bool-as-int fix in _quality_total / split_judge_scores: a
judge writing `"spec_compliance": true` is silently *not* counted as 1.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from . import conftest  # noqa: F401

from bench.scripts import aggregate_judges as aj  # noqa: E402
from bench.scripts._kinds.code import _quality_total  # noqa: E402


def _make_judgment_dir(tmp: Path, *, with_date_stamp: bool, with_meta: bool = True) -> Path:
    jdir = tmp / "results" / "judgments" / "sandbox-2026-05-05"
    jdir.mkdir(parents=True)
    (jdir / "pairings.json").write_text("{}")
    (jdir / "runs_index.json").write_text("{}")
    if with_meta:
        meta = {"task": "sandbox", "judges": [], "impl_models": []}
        if with_date_stamp:
            meta["date_stamp"] = "2026-05-05"
        (jdir / "judgment_meta.json").write_text(json.dumps(meta))
    return jdir


class TestAggregateJudgmentMetaErrors(unittest.TestCase):
    def test_missing_judgment_meta_returns_1(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        try:
            _make_judgment_dir(tmp, with_date_stamp=False, with_meta=False)
            with mock.patch.object(aj, "REPO_ROOT", tmp), \
                 mock.patch.object(sys, "argv",
                                  ["aggregate_judges", "sandbox"]):
                rc = aj.main()
            self.assertEqual(rc, 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_missing_date_stamp_returns_1_not_keyerror(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        try:
            _make_judgment_dir(tmp, with_date_stamp=False)
            with mock.patch.object(aj, "REPO_ROOT", tmp), \
                 mock.patch.object(sys, "argv",
                                  ["aggregate_judges", "sandbox"]):
                # Should not raise KeyError; should clean-error and return 1.
                rc = aj.main()
            self.assertEqual(rc, 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestQualityTotalRejectsBool(unittest.TestCase):
    def test_bool_true_not_counted_as_one(self) -> None:
        q = {"clarity": True, "conciseness": 4, "error_handling": 4, "comments": 4}
        # _quality_total expects 4 numeric keys; True is a bool, not a score.
        self.assertIsNone(_quality_total(q))

    def test_all_real_scores_sum(self) -> None:
        q = {"clarity": 5, "conciseness": 4, "error_handling": 4, "comments": 4}
        self.assertEqual(_quality_total(q), 17)


if __name__ == "__main__":
    unittest.main()
