"""Shared pytest output parser for bench/ scripts.

Originally lived inside aggregate_judges.py and parsed only the verbose
(`-v`) shape, anchoring on the `===` summary border. perf-bench.py uses
the quiet (`-q`) shape which has no `===` border — it had its own
ad-hoc reverse-line scanner. Both now share this parser, which falls
back to a non-anchored summary-line regex when no `===` lines exist.
"""

from __future__ import annotations

import re


_PER_TEST_RE = re.compile(
    r"^(?P<path>_eval_tests/[^:]+)::(?P<name>[\w\[\]\-]+)\s+"
    r"(?P<verdict>PASSED|FAILED|SKIPPED|ERROR)",
    re.MULTILINE,
)


def parse_pytest_output(text: str) -> dict:
    """Extract pass/fail counts and per-test status from pytest output.

    Handles both `-v` (verbose, with `===` summary borders) and `-q`
    (quiet, single trailing summary line). Returns:

        {"passed": int, "failed": int, "skipped": int, "errors": int,
         "per_test": {test_name: VERDICT, ...}}

    Counters default to 0 when their label is absent. `per_test` is
    populated only from `-v`-style per-test lines (`-q` doesn't emit
    them); callers that need per-test verdicts must run pytest with
    `-v`.
    """
    border_lines = [
        line for line in text.splitlines()
        if line.startswith("=")
        and any(k in line for k in ("passed", "failed", "skipped", "error"))
    ]

    if border_lines:
        # Anchored on `===` borders (pytest -v / default verbosity).
        haystack = "\n".join(border_lines)
    else:
        # No border — search every line for the summary regex (pytest -q).
        haystack = text

    counts = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}
    for label, key in (("passed", "passed"), ("failed", "failed"),
                       ("skipped", "skipped"), ("error", "errors")):
        m = re.search(rf"(\d+)\s+{label}", haystack)
        if m:
            counts[key] = int(m.group(1))

    per_test = {
        m.group("name"): m.group("verdict")
        for m in _PER_TEST_RE.finditer(text)
    }

    return {**counts, "per_test": per_test}
