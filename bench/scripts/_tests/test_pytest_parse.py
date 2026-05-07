"""Behavior of bench/scripts/_pytest_parse.parse_pytest_output.

Covers both shapes pytest emits:
- `-v`: per-test lines plus `===` summary borders (used by aggregate_judges)
- `-q`: dot/F char map plus a single trailing summary line (used by perf-bench)
"""

from __future__ import annotations

import unittest
from pathlib import Path

from . import conftest  # noqa: F401

from bench.scripts import _pytest_parse  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text()


class TestParsePytestOutputVerbose(unittest.TestCase):
    def test_all_passed(self) -> None:
        result = _pytest_parse.parse_pytest_output(_read("pytest_v_passed.txt"))
        self.assertEqual(result["passed"], 9)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["errors"], 0)
        self.assertEqual(len(result["per_test"]), 9)
        self.assertEqual(result["per_test"]["test_simple_echo"], "PASSED")
        self.assertEqual(result["per_test"]["test_no_host_shell_injection"], "PASSED")

    def test_mixed_pass_fail_skip(self) -> None:
        result = _pytest_parse.parse_pytest_output(_read("pytest_v_failed.txt"))
        self.assertEqual(result["passed"], 4)
        self.assertEqual(result["failed"], 4)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["errors"], 0)
        self.assertEqual(result["per_test"]["test_output_format"], "FAILED")
        self.assertEqual(result["per_test"]["test_network_bridge"], "SKIPPED")
        self.assertEqual(result["per_test"]["test_simple_echo"], "PASSED")

    def test_collection_error(self) -> None:
        result = _pytest_parse.parse_pytest_output(_read("pytest_v_collection_error.txt"))
        self.assertEqual(result["passed"], 0)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["errors"], 1)
        self.assertEqual(result["per_test"], {})

    def test_empty_input(self) -> None:
        result = _pytest_parse.parse_pytest_output("")
        self.assertEqual(result["passed"], 0)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["per_test"], {})


class TestParsePytestOutputQuiet(unittest.TestCase):
    def test_all_passed(self) -> None:
        result = _pytest_parse.parse_pytest_output(_read("pytest_q_passed.txt"))
        self.assertEqual(result["passed"], 9)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["errors"], 0)
        # -q output has no per-test lines
        self.assertEqual(result["per_test"], {})

    def test_mixed_pass_fail_skip(self) -> None:
        result = _pytest_parse.parse_pytest_output(_read("pytest_q_failed.txt"))
        self.assertEqual(result["passed"], 4)
        self.assertEqual(result["failed"], 4)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["errors"], 0)


class TestSummaryRegexAnchored(unittest.TestCase):
    """Pin: count regex requires word boundary, so a per-test name like
    `test_5_passed_thing` doesn't get scraped as a count when no border
    summary line filters it out (the `-q` no-border path).
    """

    def test_test_name_with_passed_token_doesnt_skew_count(self):
        text = "test_5_passed_thing FAILED\n2 passed, 1 failed in 0.05s\n"
        result = _pytest_parse.parse_pytest_output(text)
        self.assertEqual(result["passed"], 2)
        self.assertEqual(result["failed"], 1)


if __name__ == "__main__":
    unittest.main()
