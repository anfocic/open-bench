"""Pin numeric guards in _opencode.summarize.

A malformed session export with non-numeric `time.created` /
`time.completed` would previously crash via int math in the
`min(started_ms, time["created"])` reduction. This test feeds an export
where one assistant message has a string created-time and asserts
summarize returns sensibly without raising.
"""

from __future__ import annotations

import unittest

from . import conftest  # noqa: F401

from unittest import mock

from bench.scripts import _opencode  # noqa: E402


def _msg(role: str, **info) -> dict:
    return {"info": {"role": role, **info}}


class TestSummarizeNumericGuards(unittest.TestCase):
    def test_string_created_time_skipped_not_crash(self) -> None:
        session = {
            "messages": [
                _msg("assistant",
                     cost=0.01, tokens={"total": 100, "input": 50, "output": 50},
                     providerID="x", modelID="m",
                     time={"created": "not-a-number", "completed": 2000}),
                _msg("assistant",
                     cost=0.02, tokens={"total": 200, "input": 100, "output": 100},
                     providerID="x", modelID="m",
                     time={"created": 1000, "completed": 3000}),
            ],
        }
        out = _opencode.summarize(session)
        # Only the second message contributes a numeric created; wall-clock
        # is computed from numeric fields only.
        self.assertEqual(out["model_slug"], "x/m")
        self.assertAlmostEqual(out["cost_usd"], 0.03, places=6)
        self.assertEqual(out["tokens_total"], 300)
        # 1000 .. 3000 ms = 2.0s
        self.assertEqual(out["model_wall_clock_seconds"], 2.0)

    def test_bool_created_time_treated_as_invalid(self) -> None:
        session = {
            "messages": [
                _msg("assistant",
                     cost=0.0, tokens={"total": 0},
                     providerID="x", modelID="m",
                     time={"created": True, "completed": False}),
            ],
        }
        out = _opencode.summarize(session)
        # Bool is excluded (subclass-of-int trap), so wall-clock is None.
        self.assertIsNone(out["model_wall_clock_seconds"])

    def test_missing_time_field_does_not_crash(self) -> None:
        session = {
            "messages": [
                _msg("assistant",
                     cost=0.0, tokens={"total": 0},
                     providerID="x", modelID="m"),
            ],
        }
        out = _opencode.summarize(session)
        self.assertIsNone(out["model_wall_clock_seconds"])


class TestFindSessionSortNoneTolerant(unittest.TestCase):
    """Pin: find_session sort key tolerates explicit `null` in `updated`.

    `s.get("updated", 0)` only handles missing keys; an explicit
    `"updated": null` previously crashed `sort` with a TypeError when
    comparing None to int.
    """

    def test_explicit_null_updated_does_not_crash(self):
        sessions_json = '''[
            {"id": "a", "directory": "/tmp/foo", "updated": null},
            {"id": "b", "directory": "/tmp/foo", "updated": 1000},
            {"id": "c", "directory": "/tmp/foo"}
        ]'''
        with mock.patch.object(_opencode, "available", return_value=True), \
             mock.patch.object(_opencode.subprocess, "check_output",
                               return_value=sessions_json):
            sid = _opencode.find_session_for_directory("/tmp/foo")
        # The explicit-int session should win the sort.
        self.assertEqual(sid, "b")


if __name__ == "__main__":
    unittest.main()
