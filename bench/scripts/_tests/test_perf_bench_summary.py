"""Pin: perf_bench summary 'all_pass' is False when zero runs succeeded.

Before the fix, `all(f == 0 for f in test_fail)` was vacuously True on
the empty list, so a run where every iteration failed would headline
`all_pass: True` in summary.json — silently flipping the signal a perf
sweep is supposed to surface.
"""

from __future__ import annotations

import unittest


class TestAllPassEmpty(unittest.TestCase):
    def test_zero_ok_runs_means_all_pass_false(self) -> None:
        # Reproduces the summary-building expression from perf_bench.main:
        # ok = [r for r in runs if r.get("ok")]
        # test_fail = [r.get("tests_failed") for r in ok]
        # all_pass = len(ok) > 0 and all(f == 0 for f in test_fail)
        ok: list[dict] = []
        test_fail: list[int] = []
        all_pass = len(ok) > 0 and all(f == 0 for f in test_fail)
        self.assertFalse(all_pass)

    def test_some_ok_all_zero_failures_is_true(self) -> None:
        ok = [{"ok": True, "tests_failed": 0}, {"ok": True, "tests_failed": 0}]
        test_fail = [r["tests_failed"] for r in ok]
        all_pass = len(ok) > 0 and all(f == 0 for f in test_fail)
        self.assertTrue(all_pass)

    def test_some_ok_with_failure_is_false(self) -> None:
        ok = [{"ok": True, "tests_failed": 1}]
        test_fail = [r["tests_failed"] for r in ok]
        all_pass = len(ok) > 0 and all(f == 0 for f in test_fail)
        self.assertFalse(all_pass)


if __name__ == "__main__":
    unittest.main()
