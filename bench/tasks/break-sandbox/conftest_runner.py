"""conftest for the round-2 attack matrix.

`run_attacks.py` copies this file next to the attacker's `exploit.py`
inside each per-pair work dir, as `_eval_tests/conftest.py`. It puts the
work-dir root (where the target `sandbox.py` sits) on `sys.path` and
exposes the target as the `sandbox` fixture, so exploit suites never
import the target at module level — they receive it lazily, exactly as
round-1's tests receive `sandbox_module`.

It is NOT the capture-phase conftest (that one lives in `tests/`).
"""

import pathlib
import sys

import pytest

# At runtime this lives at <work>/_eval_tests/conftest.py; the target
# sandbox.py is one level up at <work>/sandbox.py.
ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def sandbox():
    try:
        import sandbox as _sandbox
    except ImportError as e:  # pragma: no cover - defensive
        pytest.fail(f"could not import target sandbox.py: {e}")
    if not hasattr(_sandbox, "sandbox_run"):
        pytest.fail("target sandbox.py has no top-level sandbox_run function")
    return _sandbox
