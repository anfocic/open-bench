"""Property-based tests for bench.scripts._pytest_parse.parse_pytest_output.

P1 (never raises): parser tolerates arbitrary unicode input and returns
the documented schema with non-negative integer counts.

P2 (verbose roundtrip): synthetic `-v`-style output with adversarial
test IDs (parametrize brackets, hyphens, digits, underscores) round-trips
through the parser — per_test mapping and counts come back exactly.
"""

from __future__ import annotations

import unittest

from hypothesis import given
from hypothesis import strategies as st

from . import conftest  # noqa: F401

from bench.scripts._pytest_parse import parse_pytest_output  # noqa: E402


class TestPytestParseRobustness(unittest.TestCase):
    @given(st.text(max_size=4096))
    def test_never_raises_and_returns_schema(self, s: str) -> None:
        result = parse_pytest_output(s)
        self.assertGreaterEqual(
            set(result.keys()),
            {"passed", "failed", "skipped", "errors", "per_test"},
        )
        for k in ("passed", "failed", "skipped", "errors"):
            self.assertIsInstance(result[k], int)
            self.assertGreaterEqual(result[k], 0)
        self.assertIsInstance(result["per_test"], dict)


_TEST_ID = st.from_regex(
    r"\Atest_[a-z][a-z0-9_]{0,20}(?:\[[a-z0-9_\-]+\])?\Z",
)


class TestPytestParseVerboseRoundtrip(unittest.TestCase):
    @given(st.lists(
        st.tuples(_TEST_ID,
                  st.sampled_from(["PASSED", "FAILED", "SKIPPED", "ERROR"])),
        min_size=1, max_size=20, unique_by=lambda t: t[0],
    ))
    def test_v_per_test_roundtrip(self, rows) -> None:
        body = "\n".join(
            f"_eval_tests/test_sandbox.py::{name} {verdict}                     [ 50%]"
            for name, verdict in rows
        )
        label_for = {"PASSED": "passed", "FAILED": "failed",
                     "SKIPPED": "skipped", "ERROR": "error"}
        counts = {v: 0 for v in label_for.values()}
        for _, verdict in rows:
            counts[label_for[verdict]] += 1
        parts = [f"{n} {label}" for label, n in counts.items() if n]
        border = "============================= "
        summary = border + ", ".join(parts) + " in 1.23s " + border
        out = parse_pytest_output(body + "\n\n" + summary)
        self.assertEqual(out["per_test"],
                         {name: verdict for name, verdict in rows})
        self.assertEqual(out["passed"], counts["passed"])
        self.assertEqual(out["failed"], counts["failed"])
        self.assertEqual(out["skipped"], counts["skipped"])
        self.assertEqual(out["errors"], counts["error"])


if __name__ == "__main__":
    unittest.main()
