import sys
import pathlib

import pytest


# At runtime this conftest lives at <worktree>/_eval_tests/conftest.py.
# Worktree root is one level up — we put it on sys.path so
# `import apply_edit` resolves to the model's apply_edit.py at the
# worktree root.
ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def apply_edit_module():
    try:
        import apply_edit
    except ImportError as e:
        pytest.fail(f"could not import apply_edit.py from worktree root: {e}")
    for name in ("apply_edit", "EditError", "EditNotFound", "EditAmbiguous"):
        if not hasattr(apply_edit, name):
            pytest.fail(f"apply_edit.py has no top-level `{name}`")
    return apply_edit
