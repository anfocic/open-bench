# `atomic_write.py` — implementation spec

A single-file Python module providing crash-safe file writes that
**either fully succeed or leave the previous contents intact** — no
partial writes, no `.tmp` residue, no torn data visible to readers.

## Library API

### `atomic_write_text(path, data, *, encoding="utf-8", mode=None) -> None`

Atomically write the string `data` to `path`.

| Parameter | Type | Default | Behaviour |
|---|---|---|---|
| `path` | `str` or `os.PathLike` | required | target path |
| `data` | `str` | required | content to write |
| `encoding` | `str` | `"utf-8"` | text encoding |
| `mode` | `int` or `None` | `None` | if set, `chmod` the new file to this mode (octal). If `None` and the target already exists, preserve the target's existing mode; otherwise the new file gets the default umask-derived mode. |

Raises:

- `FileNotFoundError` — parent directory doesn't exist (no temp residue)
- `IsADirectoryError` — `path` exists and is a directory
- `PermissionError` — can't create temp file or replace target
- `OSError` — any other I/O failure (disk full, etc.); temp file is cleaned up

### `atomic_write_bytes(path, data, *, mode=None) -> None`

Same contract as `atomic_write_text` but for bytes. No `encoding` parameter.

## Durability requirements

In order, every write must:

1. Open a temp file in the **same directory** as `path` (not `tempfile.gettempdir()` — cross-filesystem `os.replace` is not atomic).
2. Write all bytes.
3. `fsync` the file descriptor.
4. Close the temp file.
5. `os.replace(tmp, path)` — atomic rename.
6. `fsync` the **parent directory** (so the rename itself is durable).
7. If the target already existed and `mode is None`, the new file inherits the target's pre-existing mode bits.

If any of steps 1–6 raise, the temp file (if it was created) must be removed before the exception propagates.

## CLI

```
python atomic_write.py <path>
```

Reads stdin (bytes mode, no decoding) and writes the contents to `path`
atomically using the bytes API. Exits 0 on success, non-zero on any
error with a message on stderr.

## Concurrency contract

Two threads (or processes) calling `atomic_write_text(path, ...)` with
different content must result in `path` containing **one writer's full
content**, never a mix. No reader at any wall-clock instant sees a
truncated or partially-written file.

## Symlinks

If `path` is a symlink, write to the symlink **target**, not replace
the symlink itself. (Common gotcha: naive `os.replace` would replace
the symlink, breaking the link.) The temp file lives next to the
resolved target so the rename stays on the same filesystem.

## Examples

```python
from atomic_write import atomic_write_text, atomic_write_bytes

atomic_write_text("config.json", '{"version": 2}\n')
atomic_write_bytes("blob.dat", b"\x00\x01\x02")
atomic_write_text("script.sh", "#!/bin/sh\necho hi\n", mode=0o755)
```

```bash
echo '{"version": 2}' | python atomic_write.py config.json
```

## Out of scope

- Locking (advisory or mandatory) — readers see atomic transitions; coordination between writers is the caller's job.
- Backup of previous contents — this is a write primitive, not a versioning system.
- Append semantics — atomic appends are a separate problem.
- Network filesystems — POSIX-atomic semantics on NFS/CIFS are filesystem-specific; we target local filesystems (ext4, APFS, btrfs, xfs).
