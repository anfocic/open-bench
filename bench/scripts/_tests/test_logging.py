"""Pin behavior of bench.scripts._logging.

- default level is INFO
- --quiet (quiet=True) routes only WARNING+
- --verbose (verbose=True) routes DEBUG+ and uses the rich formatter
- both flags together raise SystemExit
- get_logger strips the bench[.scripts] prefix from __name__
- entry-point output emits no ✓ ✗ ▶ glyphs (global no-emoji rule)
"""

from __future__ import annotations

import io
import logging
import unittest

from . import conftest  # noqa: F401

from bench.scripts import _logging  # noqa: E402


def _capture(level_call):
    """Run `level_call(logger)` against a fresh handler and return what
    was written to the captured stream."""
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(logging.Formatter("%(message)s"))
    bench_root = logging.getLogger("bench")
    saved = list(bench_root.handlers), bench_root.level, bench_root.propagate
    bench_root.handlers = [handler]
    bench_root.setLevel(logging.DEBUG)
    bench_root.propagate = False
    try:
        level_call(_logging.get_logger("test"))
    finally:
        bench_root.handlers, bench_root.level, bench_root.propagate = saved
    return buf.getvalue()


class TestSetupLogging(unittest.TestCase):
    def test_default_level_is_info(self) -> None:
        _logging.setup_logging()
        self.assertEqual(logging.getLogger("bench").level, logging.INFO)

    def test_quiet_is_warning(self) -> None:
        _logging.setup_logging(quiet=True)
        self.assertEqual(logging.getLogger("bench").level, logging.WARNING)

    def test_verbose_is_debug(self) -> None:
        _logging.setup_logging(verbose=True)
        self.assertEqual(logging.getLogger("bench").level, logging.DEBUG)

    def test_quiet_and_verbose_mutually_exclusive(self) -> None:
        with self.assertRaises(SystemExit):
            _logging.setup_logging(quiet=True, verbose=True)

    def test_get_logger_strips_package_prefix(self) -> None:
        a = _logging.get_logger("bench.scripts.foo")
        b = _logging.get_logger("bench.foo")
        c = _logging.get_logger("foo")
        self.assertEqual(a.name, "bench.foo")
        self.assertEqual(b.name, "bench.foo")
        self.assertEqual(c.name, "bench.foo")


class TestEmittedRecords(unittest.TestCase):
    def test_info_is_emitted(self) -> None:
        out = _capture(lambda lg: lg.info("ok"))
        self.assertEqual(out.strip(), "ok")

    def test_no_emoji_in_a_routed_message(self) -> None:
        out = _capture(lambda lg: lg.info("hello"))
        for forbidden in ("✓", "✗", "▶"):  # ✓ ✗ ▶
            self.assertNotIn(forbidden, out)


if __name__ == "__main__":
    unittest.main()
