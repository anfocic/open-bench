"""Behavior of bench/scripts/_pytest_parse.parse_pytest_output.

Covers both shapes pytest emits:
- `-v`: per-test lines plus `===` summary borders (used by aggregate_judges)
- `-q`: dot/F char map plus a single trailing summary line (used by perf-bench)

aggregate_judges.parse_pytest_output is now an alias to the canonical
implementation; same calls are pinned through it for back-compat.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from . import conftest  # noqa: F401

from bench.scripts import _pytest_parse  # noqa: E402
from bench.scripts import aggregate_judges  # noqa: E402

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


class TestAggregateAlias(unittest.TestCase):
    """aggregate_judges.parse_pytest_output is an alias for back-compat."""

    def test_alias_identity(self) -> None:
        self.assertIs(aggregate_judges.parse_pytest_output,
                      _pytest_parse.parse_pytest_output)


if __name__ == "__main__":
    unittest.main()
