"""Reference-oracle filtering in aggregate_attacks.

Two layers: unit tests for the pure filter helpers (`_bogus_by_attacker`,
`_filter_reference_bogus`), and a snapshot over a fixture matrix that
carries a `reference` section — pinning that bogus exploits drop out of
every scoreboard and the `## Reference oracle` section renders.

Regenerate the golden DELIBERATELY after an intended format change:

    python -m bench.scripts._tests.test_aggregate_attacks_reference --regen
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from . import conftest  # noqa: F401

from bench.scripts import aggregate_attacks  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MATRIX = FIXTURES / "break_matrix_with_reference.json"
PLAIN_MATRIX = FIXTURES / "break_matrix.json"
GOLDEN = FIXTURES / "golden_break_review_with_reference-2026-05-14.md"


def render() -> str:
    return aggregate_attacks.render_review(json.loads(MATRIX.read_text()))


class TestFilterHelpers(unittest.TestCase):
    def test_bogus_by_attacker(self) -> None:
        matrix = json.loads(MATRIX.read_text())
        bogus = aggregate_attacks._bogus_by_attacker(matrix)
        self.assertEqual(bogus["alpha"], {"test_escape_fs__x"})
        self.assertEqual(bogus["beta"], set())
        self.assertEqual(bogus["gamma"], {"test_escape_shellinj__e"})

    def test_filter_is_noop_without_reference(self) -> None:
        matrix = json.loads(PLAIN_MATRIX.read_text())
        self.assertIs(aggregate_attacks._filter_reference_bogus(matrix),
                      matrix)

    def test_filter_drops_bogus_and_recomputes(self) -> None:
        matrix = json.loads(MATRIX.read_text())
        filtered = aggregate_attacks._filter_reference_bogus(matrix)
        by_pair = {(p["attacker"], p["target"]): p
                   for p in filtered["pairs"]}

        # alpha's fs__x escaped the reference -> dropped from both alpha pairs
        ab = by_pair[("alpha", "beta")]
        self.assertEqual(ab["escaped"], [])
        self.assertEqual(ab["n_escaped"], 0)
        self.assertFalse(any(ab["by_class"].values()))

        ag = by_pair[("alpha", "gamma")]
        self.assertEqual(ag["escaped"], ["test_escape_network__y"])
        self.assertEqual(ag["n_escaped"], 1)
        self.assertTrue(ag["by_class"]["network"])
        self.assertFalse(ag["by_class"]["fs"])

        # gamma's shellinj__e escaped the reference -> dropped
        self.assertEqual(by_pair[("gamma", "beta")]["escaped"], [])

        # untouched pair stays the same object (no needless copy)
        self.assertIs(by_pair[("beta", "gamma")],
                      next(p for p in matrix["pairs"]
                           if (p["attacker"], p["target"]) == ("beta",
                                                               "gamma")))

    def test_filter_does_not_mutate_input(self) -> None:
        matrix = json.loads(MATRIX.read_text())
        aggregate_attacks._filter_reference_bogus(matrix)
        ab = next(p for p in matrix["pairs"]
                  if (p["attacker"], p["target"]) == ("alpha", "beta"))
        self.assertEqual(ab["escaped"], ["test_escape_fs__x"])


class TestReferenceSnapshot(unittest.TestCase):
    def test_review_matches_golden(self) -> None:
        actual = render()
        if not GOLDEN.exists():
            self.fail(
                f"golden file missing: {GOLDEN}. Regenerate with: "
                f"python -m bench.scripts._tests."
                f"test_aggregate_attacks_reference --regen")
        expected = GOLDEN.read_text()
        if actual != expected:
            import difflib
            diff = "\n".join(difflib.unified_diff(
                expected.splitlines(), actual.splitlines(),
                fromfile="golden", tofile="actual", lineterm=""))
            self.fail(
                "Review output drifted from golden. If intentional, "
                "regenerate with `--regen` and review the diff.\n\n" + diff)

    def test_reference_section_and_bogus_note_present(self) -> None:
        actual = render()
        self.assertIn("## Reference oracle", actual)
        self.assertIn("Escaped reference (excluded)", actual)
        self.assertIn("Exploits excluded as bogus", actual)
        # alpha's fs__x escaped every target it attacked -> universal
        self.assertIn("`test_escape_fs__x` (universal)", actual)
        # gamma's shellinj__e did not -> no universal tag
        self.assertIn("`test_escape_shellinj__e`", actual)
        self.assertNotIn("`test_escape_shellinj__e` (universal)", actual)


if __name__ == "__main__":
    if "--regen" in sys.argv:
        GOLDEN.write_text(render())
        print(f"wrote {GOLDEN}")
        sys.exit(0)
    unittest.main()
