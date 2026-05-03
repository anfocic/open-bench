import shutil
import sys
import pathlib

import pytest


# At runtime this conftest lives at <worktree>/_eval_tests/conftest.py.
# Worktree root is one level up — we put it on sys.path so `import sandbox`
# resolves to the model's sandbox.py at the worktree root.
ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _has(binary: str) -> bool:
    return shutil.which(binary) is not None


@pytest.fixture(scope="session", autouse=True)
def require_container_runtime():
    if not (_has("podman") or _has("docker")):
        pytest.skip("no container runtime on PATH", allow_module_level=True)


@pytest.fixture(scope="session")
def sandbox_module():
    try:
        import sandbox
    except ImportError as e:
        pytest.fail(f"could not import sandbox.py from worktree root: {e}")
    if not hasattr(sandbox, "sandbox_run"):
        pytest.fail("sandbox.py has no top-level sandbox_run function")
    return sandbox
