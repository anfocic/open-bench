"""Pin behavior of aggregate_judges.parse_pytest_output before extraction.

Covers pytest -v output (the shape currently used by aggregate_judges):
all-passed, mixed pass/fail/skip, and collection-error. The -q shape used
by perf-bench is not pinned here — that parser is fixed in PR2 and gets
its own tests added there.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from . import conftest  # noqa: F401  — sys.path bootstrap

import aggregate_judges  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text()


class TestParsePytestOutputVerbose(unittest.TestCase):
    def test_all_passed(self) -> None:
        result = aggregate_judges.parse_pytest_output(_read("pytest_v_passed.txt"))
        self.assertEqual(result["passed"], 9)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["errors"], 0)
        self.assertEqual(len(result["per_test"]), 9)
        self.assertEqual(result["per_test"]["test_simple_echo"], "PASSED")
        self.assertEqual(result["per_test"]["test_no_host_shell_injection"], "PASSED")

    def test_mixed_pass_fail_skip(self) -> None:
        result = aggregate_judges.parse_pytest_output(_read("pytest_v_failed.txt"))
        self.assertEqual(result["passed"], 4)
        self.assertEqual(result["failed"], 4)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["errors"], 0)
        self.assertEqual(result["per_test"]["test_output_format"], "FAILED")
        self.assertEqual(result["per_test"]["test_network_bridge"], "SKIPPED")
        self.assertEqual(result["per_test"]["test_simple_echo"], "PASSED")

    def test_collection_error(self) -> None:
        result = aggregate_judges.parse_pytest_output(_read("pytest_v_collection_error.txt"))
        self.assertEqual(result["passed"], 0)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["errors"], 1)
        self.assertEqual(result["per_test"], {})

    def test_empty_input(self) -> None:
        result = aggregate_judges.parse_pytest_output("")
        self.assertEqual(result["passed"], 0)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["per_test"], {})


if __name__ == "__main__":
    unittest.main()
