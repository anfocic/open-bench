"""Crash-safe atomic file writes — stdlib only, Python 3.10+."""

import os
import sys
import tempfile


def _fsync_path(path: str) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_write_core(path: str, data: bytes, mode: int | None) -> None:
    path = os.path.realpath(path)
    parent = os.path.dirname(path) or "."

    if not os.path.isdir(parent):
        raise FileNotFoundError(f"parent directory does not exist: {parent!r}")

    existing_mode: int | None = None
    if mode is None and os.path.exists(path):
        try:
            existing_mode = os.stat(path).st_mode & 0o7777
        except OSError:
            pass

    tmp_fd = None
    tmp_path: str | None = None
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=parent)
        os.write(tmp_fd, data)
        os.fsync(tmp_fd)
        os.close(tmp_fd)
        tmp_fd = None

        if mode is not None:
            os.chmod(tmp_path, mode)
        elif existing_mode is not None:
            os.chmod(tmp_path, existing_mode)

        os.replace(tmp_path, path)
        tmp_path = None

        _fsync_path(parent)
    except BaseException:
        if tmp_fd is not None:
            try:
                os.close(tmp_fd)
            except OSError:
                pass
        if tmp_path is not None and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise


def atomic_write_text(
    path: str | os.PathLike,
    data: str,
    *,
    encoding: str = "utf-8",
    mode: int | None = None,
) -> None:
    if not isinstance(data, str):
        raise TypeError("data must be str")
    _atomic_write_core(os.fspath(path), data.encode(encoding), mode)


def atomic_write_bytes(
    path: str | os.PathLike,
    data: bytes,
    *,
    mode: int | None = None,
) -> None:
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("data must be bytes")
    _atomic_write_core(os.fspath(path), bytes(data), mode)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <path>", file=sys.stderr)
        sys.exit(1)
    try:
        raw = sys.stdin.buffer.read()
        atomic_write_bytes(sys.argv[1], raw)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
