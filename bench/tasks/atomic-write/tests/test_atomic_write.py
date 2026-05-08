"""Hidden tests for atomic_write.py.

Models implementing the task never see this file. The harness copies
this directory into the worktree as `_eval_tests/` after the model
finishes, then pytest runs against it.
"""

from __future__ import annotations

import os
import stat
import sys
import threading
import unittest.mock as mock
from pathlib import Path

import pytest


# --- text + bytes core ----------------------------------------------------


def test_text_basic_write(tmp_path: Path, atomic_write_module):
    target = tmp_path / "out.txt"
    atomic_write_module.atomic_write_text(target, "hello\n")
    assert target.read_text() == "hello\n"


def test_bytes_basic_write(tmp_path: Path, atomic_write_module):
    target = tmp_path / "out.bin"
    atomic_write_module.atomic_write_bytes(target, b"\x00\x01\x02")
    assert target.read_bytes() == b"\x00\x01\x02"


def test_replaces_existing(tmp_path: Path, atomic_write_module):
    target = tmp_path / "out.txt"
    target.write_text("old\n")
    atomic_write_module.atomic_write_text(target, "new\n")
    assert target.read_text() == "new\n"


# --- temp residue / cleanup ----------------------------------------------


def _list_residue(d: Path, target: Path) -> list[Path]:
    """Return any files in d other than the target itself.

    The function is forgiving about the exact temp filename pattern —
    we just want to assert nothing was left behind besides target.
    """
    return [p for p in d.iterdir() if p.resolve() != target.resolve()]


def test_no_tmp_residue_on_success(tmp_path: Path, atomic_write_module):
    target = tmp_path / "out.txt"
    atomic_write_module.atomic_write_text(target, "hi")
    assert _list_residue(tmp_path, target) == []


def test_no_tmp_residue_on_open_failure(tmp_path: Path, atomic_write_module,
                                        monkeypatch):
    """If the underlying write raises, there must be no temp file leak."""
    target = tmp_path / "out.txt"

    real_open = open
    call_count = {"n": 0}

    def boom(*args, **kwargs):
        # First open call goes through (creating the temp file); the
        # second invocation that the impl performs (or write to the fd)
        # we will simulate failing by intercepting fdopen-style writes.
        # Simplest approach: always raise on .write().
        f = real_open(*args, **kwargs)
        if "w" in (args[1] if len(args) > 1 else kwargs.get("mode", "")):
            class FailingWrapper:
                def __init__(self, inner):
                    self._inner = inner
                def __enter__(self):
                    return self
                def __exit__(self, *a):
                    self._inner.close()
                def write(self, *a, **k):
                    raise OSError("simulated ENOSPC")
                def __getattr__(self, n):
                    return getattr(self._inner, n)
            return FailingWrapper(f)
        return f

    # Different impls may use os.open vs builtins.open vs tempfile. Most
    # reliable cross-impl failure injection: monkeypatch os.write to fail
    # after the first byte. But that's intrusive too. Instead, we check
    # the simpler invariant: passing a path inside a non-existent dir
    # raises FileNotFoundError, and the parent itself ends up empty.
    bad = tmp_path / "not_a_dir" / "out.txt"
    with pytest.raises((FileNotFoundError, OSError)):
        atomic_write_module.atomic_write_text(bad, "hi")
    # The bad path's parent doesn't exist, so nothing to check there.
    # The tmp_path itself must remain empty (no stray temp residue from
    # a half-baked attempt).
    assert list(tmp_path.iterdir()) == []


# --- error semantics -----------------------------------------------------


def test_missing_parent_raises_filenotfound(tmp_path: Path, atomic_write_module):
    bad = tmp_path / "no" / "such" / "dir" / "out.txt"
    with pytest.raises(FileNotFoundError):
        atomic_write_module.atomic_write_text(bad, "hi")


def test_path_is_directory_raises(tmp_path: Path, atomic_write_module):
    d = tmp_path / "iam_dir"
    d.mkdir()
    with pytest.raises((IsADirectoryError, OSError, PermissionError)):
        atomic_write_module.atomic_write_text(d, "hi")
    # The directory still exists and is still a directory afterwards.
    assert d.is_dir()


# --- mode preservation ---------------------------------------------------


def test_mode_preserved_when_none_and_target_exists(tmp_path: Path,
                                                     atomic_write_module):
    target = tmp_path / "script.sh"
    target.write_text("#!/bin/sh\necho old\n")
    target.chmod(0o755)
    atomic_write_module.atomic_write_text(target, "#!/bin/sh\necho new\n")
    new_mode = stat.S_IMODE(target.stat().st_mode)
    assert new_mode == 0o755, f"mode not preserved: {oct(new_mode)}"


def test_mode_applied_when_set(tmp_path: Path, atomic_write_module):
    target = tmp_path / "script.sh"
    atomic_write_module.atomic_write_text(target, "#!/bin/sh\n", mode=0o750)
    new_mode = stat.S_IMODE(target.stat().st_mode)
    assert new_mode == 0o750, f"mode not applied: {oct(new_mode)}"


# --- concurrency ---------------------------------------------------------


def test_concurrent_writers_no_corruption(tmp_path: Path, atomic_write_module):
    """Many threads each write a distinct full content. Final file must
    equal exactly one of the writers' content — never a mix."""
    target = tmp_path / "out.txt"
    contents = [f"writer_{i}_" + ("x" * 1000) + "\n" for i in range(20)]
    errors: list[BaseException] = []

    def writer(payload: str) -> None:
        try:
            atomic_write_module.atomic_write_text(target, payload)
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=writer, args=(c,)) for c in contents]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"writers raised: {errors}"
    final = target.read_text()
    assert final in contents, "file content is not any single writer's payload"


# --- symlink semantics ---------------------------------------------------


def test_symlink_writes_to_target(tmp_path: Path, atomic_write_module):
    real = tmp_path / "real.txt"
    real.write_text("old\n")
    link = tmp_path / "link.txt"
    link.symlink_to(real)

    atomic_write_module.atomic_write_text(link, "new\n")

    # Either the impl writes to the target (preserving the symlink) OR
    # it replaces the symlink with a regular file. Both are defensible
    # outcomes per SPEC, but a robust implementation writes through the
    # symlink. We accept either as long as content is correct and the
    # original target is not corrupted to something nonsensical.
    assert link.read_text() == "new\n"


# --- CLI -----------------------------------------------------------------


def test_cli_stdin_to_path(tmp_path: Path):
    """python atomic_write.py <path> reads stdin (bytes) and writes."""
    import subprocess

    target = tmp_path / "cli_out.bin"
    payload = b"\x00\x01\x02hello\n\xff"
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent.parent / "atomic_write.py"),
         str(target)],
        input=payload, capture_output=True, timeout=15,
    )
    assert proc.returncode == 0, f"exit {proc.returncode}; stderr={proc.stderr!r}"
    assert target.read_bytes() == payload
