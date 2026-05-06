"""Behavior of bench/scripts/_stats helpers (and their thin wrappers).

The shared module covers:
- _stats.median            None-tolerant exact median
- _stats.median_rounded    rounded variant (used by perf-bench)
- _stats.stdev_rounded     rounded sample stdev (used by perf-bench)
- _stats.mode              most-frequent item over a stream
- _stats.mode_of_counts    argmax over a pre-aggregated count map

Wrappers in aggregate_judges (compute_median) and perf_bench
(median_or_none, stdev_or_none) are kept thin for back-compat; they're
verified to delegate correctly so callers see no behavior change.
"""

from __future__ import annotations

import unittest

from . import conftest  # noqa: F401

from bench.scripts import _stats  # noqa: E402
from bench.scripts import aggregate_judges  # noqa: E402
from bench.scripts import perf_bench  # noqa: E402


class TestStatsMedian(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertIsNone(_stats.median([]))

    def test_all_none(self) -> None:
        self.assertIsNone(_stats.median([None, None, None]))

    def test_single(self) -> None:
        self.assertEqual(_stats.median([7.0]), 7.0)

    def test_mixed_with_none(self) -> None:
        self.assertEqual(_stats.median([None, 4.0, 6.0, None]), 5.0)

    def test_odd_count(self) -> None:
        self.assertEqual(_stats.median([1.0, 2.0, 9.0]), 2.0)

    def test_even_count(self) -> None:
        self.assertEqual(_stats.median([1.0, 2.0, 3.0, 4.0]), 2.5)


class TestStatsMedianRounded(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertIsNone(_stats.median_rounded([]))

    def test_default_3dp(self) -> None:
        self.assertEqual(_stats.median_rounded([1.0001, 2.0002, 3.0003]), 2.0)
        self.assertEqual(_stats.median_rounded([0.12345, 0.6789]), 0.401)

    def test_custom_digits(self) -> None:
        self.assertEqual(_stats.median_rounded([0.12345, 0.6789], digits=2), 0.4)


class TestStatsStdevRounded(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertIsNone(_stats.stdev_rounded([]))

    def test_single(self) -> None:
        self.assertIsNone(_stats.stdev_rounded([5.0]))

    def test_two_values(self) -> None:
        self.assertEqual(_stats.stdev_rounded([1.0, 3.0]), 1.414)

    def test_drops_none(self) -> None:
        self.assertEqual(_stats.stdev_rounded([None, 1.0, 3.0]), 1.414)


class TestStatsMode(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertIsNone(_stats.mode([]))

    def test_single_winner(self) -> None:
        self.assertEqual(_stats.mode(["a", "b", "a", "c", "a"]), "a")

    def test_tie_breaks_on_insertion_order(self) -> None:
        self.assertEqual(_stats.mode(["b", "a", "b", "a"]), "b")
        self.assertEqual(_stats.mode(["a", "b", "a", "b"]), "a")


class TestStatsModeOfCounts(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertIsNone(_stats.mode_of_counts({}))

    def test_single_winner(self) -> None:
        self.assertEqual(_stats.mode_of_counts({"a": 1, "b": 5, "c": 3}), "b")

    def test_tie_breaks_on_iteration_order(self) -> None:
        self.assertEqual(_stats.mode_of_counts({"x": 2, "y": 2}), "x")
        self.assertEqual(_stats.mode_of_counts({"y": 2, "x": 2}), "y")

    def test_tuple_keys(self) -> None:
        counts = {("p1", "m1"): 3, ("p2", "m2"): 5, ("p1", "m2"): 1}
        self.assertEqual(_stats.mode_of_counts(counts), ("p2", "m2"))


class TestComputeMedianWrapper(unittest.TestCase):
    """aggregate_judges.compute_median is now a thin wrapper around _stats.median."""

    def test_delegates(self) -> None:
        self.assertIsNone(aggregate_judges.compute_median([]))
        self.assertEqual(aggregate_judges.compute_median([1.0, 2.0, 3.0]), 2.0)


class TestPerfBenchWrappers(unittest.TestCase):
    """perf-bench.median_or_none / stdev_or_none delegate to _stats.*_rounded."""

    def test_median_or_none(self) -> None:
        self.assertIsNone(perf_bench.median_or_none([]))
        self.assertEqual(perf_bench.median_or_none([1.0, 3.0]), 2.0)
        self.assertEqual(perf_bench.median_or_none([0.12345, 0.6789]), 0.401)

    def test_stdev_or_none(self) -> None:
        self.assertIsNone(perf_bench.stdev_or_none([5.0]))
        self.assertEqual(perf_bench.stdev_or_none([1.0, 3.0]), 1.414)


if __name__ == "__main__":
    unittest.main()
