"""Snapshot test: aggregate_judges renders a known review byte-identically.

Re-runs the aggregate flow against checked-in judgment data
(results/judgments/sandbox-2026-05-05/) and diffs the rendered review
against bench/scripts/_tests/fixtures/golden_review-2026-05-05.md.

PR2's parser swap and dedup must keep this byte-identical. PR3's type-
hint additions must keep it byte-identical. If a refactor changes the
output, regenerate the golden DELIBERATELY:

    python -m bench.scripts._tests.test_aggregate_judges --regen

and review the diff before committing.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from . import conftest  # noqa: F401

from bench.scripts import aggregate_judges  # noqa: E402
from bench.scripts._kinds.code import CodeTask  # noqa: E402

REPO_ROOT = aggregate_judges.REPO_ROOT
GOLDEN = Path(__file__).resolve().parent / "fixtures" / "golden_review-2026-05-05.md"
TASK = "sandbox"
DATE = "2026-05-05"


def render() -> str:
    judgment_dir = REPO_ROOT / "results" / "judgments" / f"{TASK}-{DATE}"
    pairings = json.loads((judgment_dir / "pairings.json").read_text())
    runs_index = json.loads((judgment_dir / "runs_index.json").read_text())
    judgment_meta = json.loads((judgment_dir / "judgment_meta.json").read_text())

    return CodeTask().aggregate(
        judgment_dir=judgment_dir,
        judgment_meta=judgment_meta,
        pairings=pairings,
        runs_index=runs_index,
        repo_root=REPO_ROOT,
    )


class TestAggregateSnapshot(unittest.TestCase):
    def test_review_matches_golden(self) -> None:
        actual = render()
        if not GOLDEN.exists():
            self.fail(
                f"golden file missing: {GOLDEN}. "
                f"Regenerate with: python -m bench.scripts._tests.test_aggregate_judges --regen",
            )
        expected = GOLDEN.read_text()
        if actual != expected:
            # Build a unified diff for legibility on failure.
            import difflib
            diff = "\n".join(difflib.unified_diff(
                expected.splitlines(),
                actual.splitlines(),
                fromfile="golden",
                tofile="actual",
                lineterm="",
            ))
            self.fail(
                "Review output drifted from golden. If the change is intentional, "
                "regenerate with `python -m bench.scripts._tests.test_aggregate_judges --regen` "
                "and review the diff.\n\n" + diff,
            )


if __name__ == "__main__":
    if "--regen" in sys.argv:
        GOLDEN.write_text(render())
        print(f"wrote {GOLDEN}")
        sys.exit(0)
    unittest.main()
