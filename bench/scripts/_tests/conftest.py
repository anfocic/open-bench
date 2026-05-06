"""Shared sys.path bootstrap for bench/scripts/_tests/.

The scripts under bench/scripts/ use sibling imports (`import _config`),
which means tests need bench/scripts/ on sys.path before importing them.

Each test module imports this once at the top:
    from . import conftest  # noqa: F401

Naming it conftest also makes pytest pick it up automatically if a user
runs the suite under pytest instead of unittest.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
