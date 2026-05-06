"""Pin behavior of the duplicated stat helpers before they're consolidated.

Three helpers are exercised in their current homes:
- aggregate_judges.compute_median (drops None, returns None on empty)
- perf-bench.median_or_none (rounds to 3 dp)
- perf-bench.stdev_or_none   (needs >=2 values, rounds to 3 dp)

The modal-pick logic embedded in aggregate_judges (max-by-count over a
counter dict) and in _opencode.summarize (modal model_counts pick) is
covered indirectly by the snapshot test — extracting them into a shared
mode() in PR2 must not change the snapshot output.

perf-bench.py uses a hyphen in its name, so it's loaded via importlib
rather than a normal `import`.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from . import conftest  # noqa: F401

import aggregate_judges  # noqa: E402

_PB_PATH = Path(__file__).resolve().parent.parent / "perf-bench.py"
_pb_spec = importlib.util.spec_from_file_location("perf_bench", _PB_PATH)
assert _pb_spec is not None and _pb_spec.loader is not None
perf_bench = importlib.util.module_from_spec(_pb_spec)
_pb_spec.loader.exec_module(perf_bench)


class TestComputeMedian(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertIsNone(aggregate_judges.compute_median([]))

    def test_all_none(self) -> None:
        self.assertIsNone(aggregate_judges.compute_median([None, None, None]))

    def test_single_value(self) -> None:
        self.assertEqual(aggregate_judges.compute_median([7.0]), 7.0)

    def test_mixed_with_none(self) -> None:
        self.assertEqual(aggregate_judges.compute_median([None, 4.0, 6.0, None]), 5.0)

    def test_odd_count(self) -> None:
        self.assertEqual(aggregate_judges.compute_median([1.0, 2.0, 9.0]), 2.0)

    def test_even_count(self) -> None:
        self.assertEqual(aggregate_judges.compute_median([1.0, 2.0, 3.0, 4.0]), 2.5)


class TestMedianOrNone(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertIsNone(perf_bench.median_or_none([]))

    def test_all_none(self) -> None:
        self.assertIsNone(perf_bench.median_or_none([None, None]))

    def test_rounds_to_3dp(self) -> None:
        self.assertEqual(perf_bench.median_or_none([1.0, 2.0, 3.0]), 2.0)
        self.assertEqual(perf_bench.median_or_none([1.0001, 2.0002, 3.0003]), 2.0)
        self.assertEqual(perf_bench.median_or_none([0.12345, 0.6789]), 0.401)


class TestStdevOrNone(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertIsNone(perf_bench.stdev_or_none([]))

    def test_single_value(self) -> None:
        self.assertIsNone(perf_bench.stdev_or_none([5.0]))

    def test_two_values(self) -> None:
        self.assertEqual(perf_bench.stdev_or_none([1.0, 3.0]), 1.414)

    def test_drops_none(self) -> None:
        self.assertEqual(perf_bench.stdev_or_none([None, 1.0, 3.0]), 1.414)

    def test_all_none(self) -> None:
        self.assertIsNone(perf_bench.stdev_or_none([None, None, None]))


if __name__ == "__main__":
    unittest.main()
