"""Property-based tests for bench.scripts._pytest_parse.parse_pytest_output.

P1 (never raises): parser tolerates arbitrary unicode input and returns
the documented schema with non-negative integer counts.

P2 (verbose roundtrip): synthetic `-v`-style output with adversarial
test IDs (parametrize brackets, hyphens, digits, underscores) round-trips
through the parser — per_test mapping and counts come back exactly.

P3 (ANSI tolerance): wrapping every line in ANSI color codes does not
change the parser's output.

P4 (xdist tolerance): prefixing per-test lines with `[gwN] ` worker
tags does not change the per_test mapping.
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

_ANSI = st.sampled_from([
    "", "\x1b[0m", "\x1b[1m", "\x1b[31m", "\x1b[32m", "\x1b[1;32m", "\x1b[2K",
])


def _build_v_text(rows: list[tuple[str, str]]) -> str:
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
    return body + "\n\n" + summary


class TestPytestParseVerboseRoundtrip(unittest.TestCase):
    @given(st.lists(
        st.tuples(_TEST_ID,
                  st.sampled_from(["PASSED", "FAILED", "SKIPPED", "ERROR"])),
        min_size=1, max_size=20, unique_by=lambda t: t[0],
    ))
    def test_v_per_test_roundtrip(self, rows) -> None:
        out = parse_pytest_output(_build_v_text(rows))
        label_for = {"PASSED": "passed", "FAILED": "failed",
                     "SKIPPED": "skipped", "ERROR": "error"}
        counts = {v: 0 for v in label_for.values()}
        for _, verdict in rows:
            counts[label_for[verdict]] += 1
        self.assertEqual(out["per_test"],
                         {name: verdict for name, verdict in rows})
        self.assertEqual(out["passed"], counts["passed"])
        self.assertEqual(out["failed"], counts["failed"])
        self.assertEqual(out["skipped"], counts["skipped"])
        self.assertEqual(out["errors"], counts["error"])


class TestPytestParseAnsiTolerance(unittest.TestCase):
    @given(
        rows=st.lists(
            st.tuples(_TEST_ID,
                      st.sampled_from(["PASSED", "FAILED", "SKIPPED", "ERROR"])),
            min_size=1, max_size=10, unique_by=lambda t: t[0],
        ),
        pre=_ANSI, post=_ANSI,
    )
    def test_ansi_does_not_break_parse(self, rows, pre, post) -> None:
        plain = _build_v_text(rows)
        colored = "\n".join(pre + line + post for line in plain.splitlines())
        self.assertEqual(parse_pytest_output(colored),
                         parse_pytest_output(plain))


class TestPytestParseXdistTolerance(unittest.TestCase):
    @given(
        rows=st.lists(
            st.tuples(_TEST_ID,
                      st.sampled_from(["PASSED", "FAILED", "SKIPPED", "ERROR"])),
            min_size=1, max_size=10, unique_by=lambda t: t[0],
        ),
        worker=st.integers(min_value=0, max_value=15),
    )
    def test_xdist_prefix_does_not_break_parse(self, rows, worker) -> None:
        plain = _build_v_text(rows)
        # Tag only the per-test lines (those starting with `_eval_tests/`).
        prefixed = "\n".join(
            (f"[gw{worker}] " + line) if line.startswith("_eval_tests/") else line
            for line in plain.splitlines()
        )
        self.assertEqual(parse_pytest_output(prefixed)["per_test"],
                         parse_pytest_output(plain)["per_test"])


if __name__ == "__main__":
    unittest.main()
