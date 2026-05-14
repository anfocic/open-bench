"""Snapshot test: aggregate_attacks.render_review renders byte-identically.

Pins the round-2 review format against a checked-in fixture matrix.json.
If a change to aggregate_attacks alters the output, regenerate the golden
DELIBERATELY and review the diff before committing:

    python -m bench.scripts._tests.test_aggregate_attacks_snapshot --regen
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from . import conftest  # noqa: F401

from bench.scripts import aggregate_attacks  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MATRIX = FIXTURES / "break_matrix.json"
GOLDEN = FIXTURES / "golden_break_review-2026-05-14.md"


def render() -> str:
    return aggregate_attacks.render_review(json.loads(MATRIX.read_text()))


class TestAggregateAttacksSnapshot(unittest.TestCase):
    def test_review_matches_golden(self) -> None:
        actual = render()
        if not GOLDEN.exists():
            self.fail(
                f"golden file missing: {GOLDEN}. Regenerate with: "
                f"python -m bench.scripts._tests.test_aggregate_attacks_snapshot --regen")
        expected = GOLDEN.read_text()
        if actual != expected:
            import difflib
            diff = "\n".join(difflib.unified_diff(
                expected.splitlines(), actual.splitlines(),
                fromfile="golden", tofile="actual", lineterm=""))
            self.fail(
                "Review output drifted from golden. If the change is "
                "intentional, regenerate with `--regen` and review the "
                "diff.\n\n" + diff)


if __name__ == "__main__":
    if "--regen" in sys.argv:
        GOLDEN.write_text(render())
        print(f"wrote {GOLDEN}")
        sys.exit(0)
    unittest.main()
