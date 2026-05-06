"""Shared stat helpers for bench/ scripts.

Consolidates three patterns that lived independently:
- aggregate_judges.compute_median  (None-tolerant median)
- perf-bench.median_or_none / stdev_or_none  (rounded to 3dp)
- aggregate_judges modal-verdict via manual dict counter,
  _opencode.summarize modal-pick on (provider, model)

The two median entry points are kept distinct because they round
differently: callers in aggregate_judges want the exact statistics.median
output, while perf-bench reports rounded summaries to JSON.
"""

from __future__ import annotations

import statistics
from collections import Counter
from typing import Iterable, Mapping, TypeVar


T = TypeVar("T")


def _drop_none(xs: Iterable[float | None]) -> list[float]:
    return [x for x in xs if x is not None]


def median(xs: Iterable[float | None]) -> float | None:
    """Median of values, ignoring None. Returns None for empty input."""
    clean = _drop_none(xs)
    return statistics.median(clean) if clean else None


def median_rounded(xs: Iterable[float | None], digits: int = 3) -> float | None:
    """Median rounded to `digits` decimal places. Returns None for empty input."""
    m = median(xs)
    return None if m is None else round(m, digits)


def stdev_rounded(xs: Iterable[float | None], digits: int = 3) -> float | None:
    """Sample stdev rounded to `digits` dp. Needs >=2 non-None values."""
    clean = _drop_none(xs)
    return round(statistics.stdev(clean), digits) if len(clean) >= 2 else None


def mode(items: Iterable[T]) -> T | None:
    """Most-frequent item. Returns None for empty input.

    Ties are broken by Counter.most_common's stable order (insertion).
    """
    counter = Counter(items)
    if not counter:
        return None
    return counter.most_common(1)[0][0]


def mode_of_counts(counts: Mapping[T, int]) -> T | None:
    """Argmax over a pre-aggregated count map. Returns None for empty input.

    Ties are broken by mapping iteration order (insertion order in CPython
    3.7+ dicts, matching the original `max(items(), key=...)` pattern).
    """
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: kv[1])[0]
