import sys
import pathlib

import pytest


# At runtime this conftest lives at <worktree>/_eval_tests/conftest.py.
# Worktree root is one level up — we put it on sys.path so
# `import atomic_write` resolves to the model's atomic_write.py at the
# worktree root.
ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def atomic_write_module():
    try:
        import atomic_write
    except ImportError as e:
        pytest.fail(f"could not import atomic_write.py from worktree root: {e}")
    for name in ("atomic_write_text", "atomic_write_bytes"):
        if not hasattr(atomic_write, name):
            pytest.fail(f"atomic_write.py has no top-level `{name}`")
    return atomic_write
