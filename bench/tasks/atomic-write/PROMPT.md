# Task: implement `atomic_write.py`

Read `SPEC.md` in this directory. Implement `atomic_write.py` exactly per
spec: two library functions (`atomic_write_text`, `atomic_write_bytes`)
plus a CLI entry point for use in shell pipelines.

This task covers **only `atomic_write.py`**. Do not create helper modules,
test files, or packaging metadata.

## Hard constraints

- Python 3.10+, **stdlib only** — no `pip install`, no new dependencies.
- The temp file must live in the **same directory** as the target so the
  final `os.replace` is on the same filesystem (cross-fs renames are not
  atomic on POSIX).
- The file must be `fsync`'d before close, and the **parent directory**
  must be `fsync`'d after the replace, so a power loss between writes
  doesn't surface a missing or empty file.
- On any error during the write (disk full, permission, interrupted
  syscall, etc.) the temp file must be cleaned up — no `.tmp` residue
  on disk after a failed call.
- Concurrent writers to the same target must not corrupt each other:
  the result must be the full content of one writer or the other, never
  a mix.
- The replace must be atomic from the perspective of any concurrent
  reader: a reader either sees the old content in full, or the new
  content in full — never a truncated intermediate.

## Deliverable

A single file `atomic_write.py` at the worktree root that:

1. Exposes two top-level functions:

   ```python
   def atomic_write_text(path, data, *, encoding="utf-8", mode=None) -> None: ...
   def atomic_write_bytes(path, data, *, mode=None) -> None: ...
   ```

2. Provides a CLI that reads stdin and writes atomically to a target
   path:

   ```
   python atomic_write.py <path>
   ```

## What to do when finished

1. Run a quick smoke test: write a small file, verify the target exists
   and matches what you wrote, verify no `.tmp` files remain in the dir.
2. State: "Done. Implementation in `atomic_write.py`."

## What NOT to do

- Do not modify PROMPT.md or SPEC.md.
- Do not add `requirements.txt`, `pyproject.toml`, or any other dependency manifest.
- Do not write test files; the hidden tests are added later.
