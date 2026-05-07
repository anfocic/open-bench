"""CodeTask.aggregate in isolation.

Snapshot coverage already lives in test_aggregate_judges.py (drives the
same method against the checked-in golden). These tests pin the smaller
contract: return type, section headers, and per-impl test-output.txt
fallback when the file is missing.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from . import conftest  # noqa: F401

from bench.scripts._kinds.code import CodeTask, _quality_total


class TestCodeTaskAggregate(unittest.TestCase):
    def _layout(self):
        tmp = Path(tempfile.mkdtemp())
        repo_root = tmp
        judgment_dir = tmp / "results" / "judgments" / "sandbox-2026-05-07"
        judgment_dir.mkdir(parents=True)
        (judgment_dir / "claude").mkdir()
        (judgment_dir / "claude" / "output").mkdir()

        # One impl, one judge, no test-output.txt → exercises the
        # missing-output warning path inside aggregate.
        pairings = {"claude": {"alpha": "A"}}
        runs_index = {
            "alpha": {
                "path": "builds/alpha/rounds/sandbox-2026-05-07",
                "slug": "anthropic/claude-x",
                "date_stamp": "2026-05-07",
            }
        }
        judgment_meta = {
            "task": "sandbox",
            "date_stamp": "2026-05-07",
            "judges": ["claude"],
            "impl_models": ["alpha"],
        }
        (judgment_dir / "claude" / "output" / "A_scores.json").write_text(
            json.dumps({
                "spec_compliance": 8,
                "code_quality": {
                    "clarity": 4, "conciseness": 4,
                    "error_handling": 4, "comments": 3,
                },
                "verdict": "ship",
                "hard_fail": "pass",
                "one_line_summary": "looks fine",
            })
        )
        return tmp, repo_root, judgment_dir, pairings, runs_index, judgment_meta

    def test_returns_markdown_with_expected_headers(self):
        tmp, repo_root, judgment_dir, pairings, runs_index, judgment_meta = self._layout()
        try:
            md = CodeTask().aggregate(
                judgment_dir=judgment_dir,
                judgment_meta=judgment_meta,
                pairings=pairings,
                runs_index=runs_index,
                repo_root=repo_root,
            )
            self.assertIsInstance(md, str)
            self.assertIn("# Review: sandbox (2026-05-07)", md)
            for header in (
                "## Scoreboard",
                "## Per-judge ranking by spec compliance",
                "## Self-bias check",
                "## Inter-judge agreement",
                "## Per-implementation detail",
                "## Cost & efficiency",
                "## Judging cost & efficiency",
                "## Cross-model observations",
                "## Recommendation",
                "## Spec changes suggested",
            ):
                self.assertIn(header, md)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_missing_test_output_file_renders_dashes_not_crash(self):
        tmp, repo_root, judgment_dir, pairings, runs_index, judgment_meta = self._layout()
        try:
            md = CodeTask().aggregate(
                judgment_dir=judgment_dir,
                judgment_meta=judgment_meta,
                pairings=pairings,
                runs_index=runs_index,
                repo_root=repo_root,
            )
            # Scoreboard tests column should be "—" since no test-output.txt
            # exists for alpha.
            scoreboard_row = next(
                ln for ln in md.splitlines() if ln.startswith("| alpha |")
            )
            self.assertIn(" — ", scoreboard_row)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestLoadJudgeScoresMalformed(unittest.TestCase):
    """Pin: scores file with non-dict top level is demoted to None, not raised."""

    def test_top_level_list_is_treated_as_missing(self):
        from bench.scripts._kinds.code import _load_judge_scores
        tmp = Path(tempfile.mkdtemp())
        try:
            judge_dir = tmp / "claude"
            (judge_dir / "output").mkdir(parents=True)
            (judge_dir / "output" / "A_scores.json").write_text("[]")
            (judge_dir / "output" / "B_scores.json").write_text("\"oops\"")
            result = _load_judge_scores(judge_dir, {"alpha": "A", "beta": "B"})
            self.assertIsNone(result["alpha"])
            self.assertIsNone(result["beta"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestQualityTotal(unittest.TestCase):
    def test_bool_true_not_counted_as_one(self):
        q = {"clarity": True, "conciseness": 4,
             "error_handling": 4, "comments": 4}
        self.assertIsNone(_quality_total(q))

    def test_all_real_scores_sum(self):
        q = {"clarity": 5, "conciseness": 4,
             "error_handling": 4, "comments": 4}
        self.assertEqual(_quality_total(q), 17)

    def test_missing_key_returns_none(self):
        self.assertIsNone(_quality_total(
            {"clarity": 5, "conciseness": 4, "error_handling": 4}
        ))


if __name__ == "__main__":
    unittest.main()
