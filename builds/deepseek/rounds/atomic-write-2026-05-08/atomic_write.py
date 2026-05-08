import os
import sys
import tempfile


def atomic_write_text(path, data, *, encoding="utf-8", mode=None):
    _atomic_write(path, data.encode(encoding), mode)


def atomic_write_bytes(path, data, *, mode=None):
    _atomic_write(path, data, mode)


def _atomic_write(path, data_bytes, mode):
    real_path = os.path.realpath(path)
    parent_dir = os.path.dirname(real_path)

    if not os.path.isdir(parent_dir):
        raise FileNotFoundError(f"No such directory: '{parent_dir}'")

    if os.path.isdir(real_path):
        raise IsADirectoryError(f"Is a directory: '{real_path}'")

    target_mode = None
    if mode is not None:
        target_mode = mode
    elif os.path.isfile(real_path):
        target_mode = os.stat(real_path).st_mode

    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(dir=parent_dir)
        try:
            os.write(fd, data_bytes)
            os.fsync(fd)
        finally:
            os.close(fd)

        if target_mode is not None:
            os.chmod(tmp_path, target_mode)

        os.replace(tmp_path, real_path)

        dfd = os.open(parent_dir, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except Exception:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <path>", file=sys.stderr)
        sys.exit(1)

    try:
        atomic_write_bytes(sys.argv[1], sys.stdin.buffer.read())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
