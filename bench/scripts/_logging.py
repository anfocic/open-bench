"""Shared logging setup for bench/scripts entry points.

All bench loggers live under the `bench.*` namespace and route to a
single stderr handler. Default format is bare `%(message)s` so the
output reads like the previous `print(..., file=sys.stderr)` calls;
`--verbose` swaps in a richer format with timestamp/level/name.

Each entry point's `main()` adds `--quiet` / `--verbose` flags and calls
`setup_logging(quiet=args.quiet, verbose=args.verbose)` once before any
work. Helper modules use `get_logger(__name__)` to acquire a logger.
"""

from __future__ import annotations

import logging
import sys

_BASE = "bench"


def setup_logging(quiet: bool = False, verbose: bool = False) -> None:
    """Configure the bench.* logger tree once. Idempotent."""
    if quiet and verbose:
        raise SystemExit("--quiet and --verbose are mutually exclusive")
    level = logging.WARNING if quiet else (logging.DEBUG if verbose else logging.INFO)
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s" if verbose else "%(message)s"
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(fmt))
    root = logging.getLogger(_BASE)
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Return a `bench.<name>` logger. Pass `__name__` from inside the
    package and we strip any `bench.scripts.` prefix for legibility.

    When called from a script run via `python -m bench.scripts.X`, the
    script's `__name__` is `"__main__"`; in that case we recover the
    real module name from sys.modules['__main__'].__spec__ if available,
    else fall back to "main"."""
    short = name
    if short == "__main__":
        import sys
        spec = getattr(sys.modules.get("__main__"), "__spec__", None)
        short = spec.name if spec else "main"
    for prefix in ("bench.scripts.", "bench."):
        if short.startswith(prefix):
            short = short[len(prefix):]
            break
    return logging.getLogger(f"{_BASE}.{short}")
