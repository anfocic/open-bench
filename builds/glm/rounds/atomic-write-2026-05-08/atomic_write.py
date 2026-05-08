"""Atomic file writes: either fully succeed or leave previous contents intact."""

import os
import sys
import tempfile


def _atomic_write(path, data, *, encoding=None, mode=None):
    path = os.fspath(path)
    real_path = os.path.realpath(path)
    parent = os.path.dirname(real_path)

    if os.path.isdir(real_path):
        raise IsADirectoryError(f"Is a directory: {real_path}")

    apply_mode = mode
    if apply_mode is None:
        try:
            apply_mode = os.stat(real_path).st_mode & 0o7777
        except FileNotFoundError:
            pass

    tmp_path = None
    file_obj = None
    try:
        fd, tmp_path = tempfile.mkstemp(dir=parent)
        try:
            if encoding is not None:
                file_obj = os.fdopen(fd, "w", encoding=encoding)
            else:
                file_obj = os.fdopen(fd, "wb")
            file_obj.write(data)
            file_obj.flush()
            os.fsync(file_obj.fileno())
            file_obj.close()
        except BaseException:
            os.close(fd)
            raise
        file_obj = None

        if apply_mode is not None:
            os.chmod(tmp_path, apply_mode)

        os.replace(tmp_path, real_path)
        tmp_path = None

        parent_fd = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    except BaseException:
        if file_obj is not None:
            try:
                file_obj.close()
            except Exception:
                pass
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        raise


def atomic_write_text(path, data, *, encoding="utf-8", mode=None) -> None:
    _atomic_write(path, data, encoding=encoding, mode=mode)


def atomic_write_bytes(path, data, *, mode=None) -> None:
    _atomic_write(path, data, encoding=None, mode=mode)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path>", file=sys.stderr)
        sys.exit(1)
    try:
        data = sys.stdin.buffer.read()
        atomic_write_bytes(sys.argv[1], data)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)