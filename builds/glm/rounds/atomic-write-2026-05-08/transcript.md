# atomic-write-glm-2026-05-08

**Session ID:** ses_1f88171ffffefBbYNd41qJAIVJ

---

## User

"Read PROMPT.md and SPEC.md at the worktree root, then implement atomic_write.py per the spec. Stop when atomic_write.py exists at the worktree root and your own quick smoke check passes."


---

## Assistant (opencode-go/glm-5.1)

_Thinking:_

The user wants me to read PROMPT.md and SPEC.md, then implement atomic_write.py per the spec. Let me start by readingboth files.

_Tool call: read_

_Tool call: read_

---

## Assistant (opencode-go/glm-5.1)

_Thinking:_

Now I have a clear understanding of the spec. Let me implement `atomic_write.py`:

Key requirements:
1. Two functions: `atomic_write_text` and `atomic_write_bytes`
2. CLI entry point that reads stdin and writes atomically
3. Stdlib only
4. Temp file in same directory as target
5. fsync file before close, fsync parent dir after replace
6. Clean up temp file on any error
7. Symlink handling: resolve symlinks, write to target
8. Mode handling: if mode is None and target exists, preserve existing mode; if mode is provided, chmod to that mode; otherwise umask-derived
9. CLI: read stdin as bytes, write atomically, exit 0 on success, non-zero on error with stderr message

Let me implement this carefully.

For symlinks: when path is a symlink, we need to resolve it and write to the resolved target. The temp file should live next to the resolved target.

For mode handling:
- If mode is explicitly set → chmod to mode
- If mode is None and target already exists → preserve target's existing mode
- If mode is None and target doesn't exist → let umask decide (default)

Let me write the implementation:

```python
import os
import sys
import tempfile

def _atomic_write(path, data, *, encoding=None, mode=None):
    path = os.fspath(path)
    
    # Resolve symlinks - write to the symlink target
    real_path = os.path.realpath(path)
    
    parent = os.path.dirname(real_path)
    if not os.path.isdir(parent):
        raise FileNotFoundError(f"Parent directory does not exist: {parent}")
    
    # If target exists and is a directory, raise IsADirectoryError
    if os.path.isdir(real_path):
        raise IsADirectoryError(f"Is a directory: {real_path}")
    
    # Capture existing mode if needed
    preserve_mode = None
    if mode is None:
        try:
            preserve_mode = os.stat(real_path).st_mode & 0o7777
        except FileNotFoundError:
            pass
    
    tmp_fd = None
    tmp_path = None
    try:
        # Create temp file in same directory
        fd, tmp_path = tempfile.mkstemp(dir=parent)
        tmp_fd = os.fdopen(fd, 'wb' if encoding is None else 'w', 
                           encoding=encoding if encoding else 'utf-8')
        
        tmp_fd.write(data)
        tmp_fd.flush()
        os.fsync(tmp_fd.fileno())
        tmp_fd.close()
        tmp_fd = None
        
        # Apply mode
        if mode is not None:
            os.chmod(tmp_path, mode)
        elif preserve_mode is not None:
            os.chmod(tmp_path, preserve_mode)
        
        # Atomic replace
        os.replace(tmp_path, real_path)
        tmp_path = None
        
        # fsync parent directory for durability
        parent_fd = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    except BaseException:
        if tmp_fd is not None:
            try:
                tmp_fd.close()
            except Exception:
                pass
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        raise
```

Wait, I need to be careful about a few things:

1. `os.fdopen` returns a file object. When we call `tmp_fd.close()`, it also closes the underlying file descriptor. But we need to fsync before close. Let me adjust.

2. For `atomic_write_text`, encoding is used. For `atomic_write_bytes`, no encoding.

3. The `os.fdopen` call: we need to handle the encoding parameter correctly.

Let me think about this more carefully.

Actually, `tempfile.mkstemp` returns a file descriptor and a path. The file descriptor is already open. We need to:
1. Wrap it with `os.fdopen` for writing
2. Write data
3. Flush and fsync
4. Close
5. os.replace
6. fsync parent dir

Let me also handle the case where `path` is a symlink properly. The spec says: "If path is a symlink, write to the symlink target, not replace the symlink itself." So we use `os.path.realpath(path)` to resolve symlinks.

But wait - there's a subtlety. When we do `os.replace(tmp_path, real_path)`, where real_path is the resolved path, this should work correctly. The temp file is created next to the resolved target, and we replace the resolved target.

Actually, let me reconsider. What if the path doesn't exist yet but the parent directory exists and is a symlink? `os.path.realpath` would resolve the parent directory symlink, which is fine.

What about the `IsADirectoryError` check? We should check the resolved path.

Let me refactor:

```python
def _atomic_write(path, data, *, encoding=None, mode=None):
    path = os.fspath(path)
    real_path = os.path.realpath(path)
    parent = os.path.dirname(real_path)
    
    # Check parent exists
    if not os.path.isdir(parent):
        raise FileNotFoundError(f"Parent directory does not exist: {parent}")
    
    # Check target is not a directory
    try:
        if os.path.isdir(real_path):
            raise IsADirectoryError(f"Is a directory: {real_path}")
    except FileNotFoundError:
        pass  # Target doesn't exist yet, which is fine
    
    # Determine mode
    apply_mode = mode
    if apply_mode is None:
        try:
            apply_mode = os.stat(real_path).st_mode & 0o7777
        except FileNotFoundError:
            apply_mode = None  # Let umask decide
    
    tmp_path = None
    file_obj = None
    try:
        fd, tmp_path = tempfile.mkstemp(dir=parent)
        if encoding is not None:
            file_obj = os.fdopen(fd, 'w', encoding=encoding)
        else:
            file_obj = os.fdopen(fd, 'wb')
        
        file_obj.write(data)
        file_obj.flush()
        os.fsync(file_obj.fileno())
        file_obj.close()
        file_obj = None
        
        if apply_mode is not None:
            os.chmod(tmp_path, apply_mode)
        
        os.replace(tmp_path, real_path)
        tmp_path = None  # Successfully replaced, don't clean up
        
        # fsync parent directory
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
        if tmp_path is not None and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        raise
```

Wait, but there's a conflict with `os.path.isdir`. If the path exists and is a directory, `os.path.isdir` returns True. But what if the path doesn't exist? Then `os.path.isdir` returns False and we skip the check. But we should still check - if the path doesn't exist, that's fine. If it exists as a file, also fine. If it exists as a directory, raise IsADirectoryError.

Actually, I had it right. Let me re-check:

```python
try:
    if os.path.isdir(real_path):
        raise IsADirectoryError(...)
except FileNotFoundError:
    pass
```

But `os.path.isdir` won't raise FileNotFoundError - it just returns False if the path doesn't exist. So this simpler code works:

```python
if os.path.isdir(real_path):
    raise IsADirectoryError(...)
```

This handles all cases: if path doesn't exist, `isdir` returns False and we proceed. If path exists as file, `isdir` returns False and we proceed. If path exists as directory, we raise.

Actually wait, I need to be more careful. What if the path is a symlink pointing to a directory? `os.path.isdir` follows symlinks, so it would return True. But we've already resolved the symlink with `realpath`, so this should be fine.

Hmm, but actually the spec says "If path is a symlink, write to the symlink target, not replace the symlink itself." So we resolve the path first, then check if it's a directory. That's what we're doing.

Let me also think about the edge case where `path` doesn't exist but the parent does. In this case, `os.path.realpath(path)` would still resolve the parent directory part, but the final component wouldn't resolve. For example, if path is `/foo/bar` and `/foo` exists but `/foo/bar` doesn't, then `os.path.realpath(path)` returns `/foo/bar` (with the parent resolved). This is the correct behavior.

But wait, what if `path` is a symlink that points to a non-existent target? `os.path.realpath` resolves symlinks but doesn't check if the final target exists. So if `/foo/link` is a symlink to `/foo/nonexistent`, then `realpath` would resolve to `/foo/nonexistent`. That's fine - we'd check the parent directory and proceed.

Actually, I just realized there might be an issue. `os.path.realpath(path)` resolves symlinks in the path. But what if the path itself doesn't exist yet (we're creating a new file)? `realpath` still works - it resolves what it can and leaves the rest as-is.

But there's a subtle issue: what if `path` is `/some/dir/link/filename` where `link` is a symlink? `realpath` would resolve `link` to its target, which is correct.

OK I think the implementation is sound. Let me also handle the case for the `os.path.isdir` check differently. Instead of calling `os.path.isdir` on `real_path`, I should handle the case where `path` itself (before resolving) might be a symlink pointing to a directory. But actually, since we've resolved with `realpath`, `real_path` is the actual path. If `real_path` is an existing directory, we should raise. If it doesn't exist, we should proceed. If it's an existing file, we should replace it.

Wait, but there's another subtlety. What about the check for `IsADirectoryError`? The spec says: "IsADirectoryError — path exists and is a directory". Note it says `path`, not `real_path`. But since we're writing to the resolved target, we should check `real_path`. I think the spec means that if the location we'd write to is a directory, we should error.

OK, let me also think about the case where `path` is a dangling symlink. `os.path.realpath('/foo/dangling_link')` where `dangling_link` -> `/nonexistent`. In this case, `realpath` would return `/nonexistent`. Then we'd check if the parent directory of `/nonexistent` exists, which might not, so we'd get a FileNotFoundError. That's the correct behavior.

But wait, what if `path` is a symlink but the target exists and is a directory? `realpath` resolves to the directory, then `isdir` returns True, and we raise IsADirectoryError. Good.

What if `path` itself is a directory (not a symlink)? Then `realpath` returns the same path (since it's not a symlink), `isdir` returns True, and we raise IsADirectoryError. Good.

I think my implementation is solid. Let me also think about the `os.replace` step. `os.replace` is atomic on POSIX when source and destination are on the same filesystem. Since we create the temp file in the same directory as the target, they're on the same filesystem. Good.

One more thing: the spec says "If the target already existed and mode is None, the new file inherits the target's pre-existing mode bits." My implementation handles this correctly - if mode is None, I look up the existing file's mode, and if the file exists, I apply that mode. If the file doesn't exist, I don't apply any mode (umask decides).

Let me finalize the code now.

Actually, I want to also handle the `FileNotFoundError` case properly. When the parent directory doesn't exist, `os.path.isdir` returns False. But I want to distinguish between "parent doesn't exist" and "parent exists but path's parent is not a directory". Actually, `os.path.isdir` returns True only if the path exists AND is a directory. If the parent path doesn't exist, it returns False. So my check should be:

```python
if not os.path.isdir(parent):
    raise FileNotFoundError(f"Parent directory does not exist: {parent}")
```

This handles both cases: parent doesn't exist at all, or parent exists but is not a directory. Though the error message could be more precise, but FileNotFoundError is the right exception per spec.

Hmm, but actually if `parent` exists as a regular file, `os.path.isdir` returns False, and we'd raise FileNotFoundError. That's a bit misleading but per the spec, FileNotFoundError is the right exception for "parent directory doesn't exist". And if the parent is a file, the `mkstemp` would fail with a different error anyway. Let me simplify:

Actually wait, let me re-read the spec's error conditions:
- `FileNotFoundError` — parent directory doesn't exist (no temp residue)
- `IsADirectoryError` — `path` exists and is a directory
- `PermissionError` — can't create temp file or replace target
- `OSError` — any other I/O failure

So I should raise FileNotFoundError specifically when the parent directory doesn't exist. If the parent exists but is a file (not a directory), that's more of an OSError or NotADirectoryError. But since the spec only lists these specific exceptions, I'll just check for non-existence of parent directory:

Actually, I think the simplest approach is:
1. If parent is not a directory (either doesn't exist or isn't a dir), the `tempfile.mkstemp` call will fail naturally with appropriate exceptions (FileNotFoundError if parent doesn't exist, or OSError).
2. I just need to handle the IsADirectoryError case explicitly.

Hmm, but `tempfile.mkstemp(dir=parent)` will raise FileNotFoundError if parent doesn't exist, and that's the right error. But I want to ensure no temp residue in that case too. Since mkstemp fails before creating a file, there's nothing to clean up. So maybe I don't need the explicit check.

But actually, it's good practice to check upfront so we can give a clean error and ensure no temp residue. Let me keep the check.

Wait, there's actually a race condition here. Between checking `os.path.isdir(parent)` and calling `mkstemp`, the directory could be removed. But that's fine - `mkstemp` would fail and we'd raise FileNotFoundError. The check is just for early validation.

Actually, for robustness, I think I should let the natural exceptions propagate from `mkstemp` and focus on cleanup in the error handler. The explicit checks are nice for early errors but not strictly necessary.

Let me simplify and not do the explicit checks, relying on the natural errors:

```python
def _atomic_write(path, data, *, encoding=None, mode=None):
    path = os.fspath(path)
    real_path = os.path.realpath(path)
    parent = os.path.dirname(real_path)
    
    # Determine mode to apply
    apply_mode = mode
    if apply_mode is None:
        try:
            st = os.stat(real_path)
            apply_mode = st.st_mode & 0o7777
        except FileNotFoundError:
            pass
    
    # Check if target is a directory (by resolved path)
    if os.path.isdir(real_path):
        raise IsADirectoryError(f"Is a directory: {real_path}")
    
    tmp_path = None
    file_obj = None
    try:
        fd, tmp_path = tempfile.mkstemp(dir=parent)
        if encoding is not None:
            file_obj = os.fdopen(fd, 'w', encoding=encoding)
        else:
            file_obj = os.fdopen(fd, 'wb')
        
        file_obj.write(data)
        file_obj.flush()
        os.fsync(file_obj.fileno())
        file_obj.close()
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
```

Wait, I need to handle one more thing. The `os.stat(real_path)` call for mode detection happens before we create the temp file. If the target doesn't exist, we get FileNotFoundError (which is caught by the try/except), so `apply_mode` stays None. That's correct.

But there's a race: between `os.stat` and the `os.replace`, another process could delete the target file. In that case, we'd apply the old mode to the new file, which is the best we can do (we can't know the mode was changed between our check and the replace). This is fine per the spec.

Actually wait, there's another subtle issue. We check the mode with `os.stat(real_path)` before creating the temp file. But if `real_path` doesn't exist yet, `os.stat` raises `FileNotFoundError` which we catch, and `apply_mode` stays None (no explicit mode, letting umask decide). This is correct per the spec.

But also: what about the `IsADirectoryError` check? If `path` is a dangling symlink (pointing to non-existent target), then `real_path` won't be a directory, so we'd skip the check and proceed. When we do `os.replace(tmp_path, real_path)`, it would create the file at the resolved path. That... might not be what we want. Actually, it is what we want per the spec: "write to the symlink target".

But what about the case where `path` is a symlink AND the symlink target is a directory? Then `real_path` would be an actual directory path, and `os.path.isdir(real_path)` would return True, and we'd raise IsADirectoryError. Good.

One more edge case: what if `path` is a symlink to a symlink? `os.path.realpath` resolves all symlinks, so we'd get the final target. Good.

OK, I think the implementation is solid. Let me also handle the CLI part:

```python
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path>", file=sys.stderr)
        sys.exit(1)
    try:
        data = sys.stdin.buffer.read()
        atomic_write_bytes(sys.argv[1], data)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
```

Let me put it all together now.

_Tool call: write_

---

## Assistant (opencode-go/glm-5.1)

_Thinking:_

Now let me run a smoke test: write a small file, verify it exists with the right content, and check no .tmp files remain.

_Tool call: bash_

---

## Assistant (opencode-go/glm-5.1)

Done. Implementation in `atomic_write.py`.

---
