"""Path bootstrap for bench/scripts/_tests/.

Tests run from anywhere; ensure the repo root (parent of `bench/`) is on
sys.path so `from bench.scripts import _config` resolves without an
install step.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
