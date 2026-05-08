# atomic-write-deepseek-2026-05-08

**Session ID:** ses_1f884b2a1ffetmjgE3LD5Nm27B

---

## User

"Read PROMPT.md and SPEC.md at the worktree root, then implement atomic_write.py per the spec. Stop when atomic_write.py exists at the worktree root and your own quick smoke check passes."


---

## Assistant (opencode-go/deepseek-v4-pro)

_Thinking:_

Let me start by reading the two specification files to understand what needs to be implemented.

_Tool call: read_

_Tool call: read_

---

## Assistant (opencode-go/deepseek-v4-pro)

_Thinking:_

Let me analyze the spec carefully:

1. **Library API**: Two functions:
   - `atomic_write_text(path, data, *, encoding="utf-8", mode=None) -> None`
   - `atomic_write_bytes(path, data, *, mode=None) -> None`

2. **Durability requirements**:
   - Temp file in same directory as target
   - Write all bytes
   - fsync the file descriptor
   - Close the temp file
   - os.replace(tmp, path) — atomic rename
   - fsync the parent directory
   - If target existed and mode is None, preserve target's mode

3. **Error handling**: On any error during write, clean up temp file

4. **CLI**: `python atomic_write.py <path>` reads stdin (bytes mode) and writes atomically

5. **Symlinks**: If path is a symlink, write to the target, not replace the symlink. The temp file lives next to the resolved target.

Let me think about the symlink handling carefully:
- `os.path.realpath(path)` resolves all symlinks to get the target path
- `os.path.dirname(os.path.realpath(path))` gives the directory for the temp file
- But wait — should we resolve just the basename or the full path? The spec says "write to the symlink **target**, not replace the symlink itself." and "The temp file lives next to the resolved target so the rename stays on the same filesystem."

So:
- Target directory for temp file = `os.path.dirname(os.path.realpath(path))`
- The final target path we write to = `os.path.realpath(path)` — this is the actual file the symlink points to
- Wait, but `os.replace` replaces at the given path. If `path` is a symlink, `os.replace(tmp, path)` would replace the symlink itself with the new file. So we need to replace at the resolved target.

Actually, let me reconsider. If we use `os.replace(tmp, real_target)` where `real_target` is the symlink's target, then the symlink still points to the same path (the original target location), and we're replacing the contents at that target. But wait — `os.replace` replaces the file at the given path. If we call `os.replace(tmp, real_target)`, it replaces the file that the symlink points to. The symlink itself is untouched, and now points to the new file content. That's what the spec wants.

But what about cross-filesystem concerns? If the symlink target is on a different filesystem, `os.replace` won't be atomic. The spec says "The temp file lives next to the resolved target so the rename stays on the same filesystem." So we put the temp file in `os.path.dirname(real_target)`.

Now for mode inheritance:
- If the target already exists (via the resolved path) and `mode is None`, get the existing mode.
- After the replace, `os.chmod` the new file to that mode.

Wait, but there's a subtlety. If the target is a symlink, we need to get the mode of the symlink target (the real file), then after replacing, chmod the new file. But `os.stat` follows symlinks by default, so `os.stat(path)` gives us the target's mode, which is what we want.

But wait — we should use `os.lstat(path)` to check if it's a symlink? No, the spec says "If `path` is a symlink, write to the symlink **target**". So we use `os.path.realpath()` to resolve it, and then `os.stat(real_path)` to get the mode if it exists.

Let me also think about file descriptors. The spec says:
1. Open a temp file
2. Write all bytes
3. fsync the file descriptor
4. Close the temp file
5. os.replace
6. fsync parent directory

Using `tempfile.mkstemp` or manual temp file creation. `tempfile.mkstemp(dir=target_dir)` creates a temp file in the specified directory. But the spec says "stdlib only", which is fine since `tempfile` is stdlib.

Actually, let me think about the temp file naming. For concurrency, each writer needs a unique temp file name. `tempfile.mkstemp` handles this. Or I could use `tempfile.NamedTemporaryFile` with `delete=False` and `dir=target_dir`.

Let me use `tempfile.NamedTemporaryFile` with `delete=False` in the target directory. Then:
1. Write data
2. `os.fsync(f.fileno())`
3. Close the file
4. `os.replace(tmp_path, target_path)`
5. `os.fsync(os.open(parent_dir, os.O_RDONLY))`
6. If mode is not None and set: `os.chmod(target_path, mode)`

Wait, mode handling:
- If `mode` is set: `os.chmod` the new file to that mode (should this happen before or after replace? Before, since we want the file to have the right mode from the start. But `os.replace` preserves mode on some systems... Actually, the spec says "if set, chmod the new file to this mode". I think we should chmod the temp file before the replace, so the final file has the right mode.)
- If `mode is None` and target exists: get the target's existing mode, then after replace, chmod to that mode (or chmod the temp file before replace).

Actually, wait. Let me re-read: "if set, `chmod` the new file to this mode (octal). If `None` and the target already exists, preserve the target's existing mode; otherwise the new file gets the default umask-derived mode."

So:
- mode is set → chmod the temp file to mode before replace
- mode is None and target exists → get target's mode, chmod temp to that mode before replace
- mode is None and target doesn't exist → leave as default (umask-derived)

Wait, but the spec's step 7 says: "If the target already existed and `mode is None`, the new file inherits the target's pre-existing mode bits."

This suggests we should:
1. Before doing anything, check if the target exists and get its mode (resolving symlinks)
2. Set the temp file's mode appropriately before the replace

Let me structure it:

```python
def _atomic_write(path, data, mode = None):
    real_path = os.path.realpath(path)
    target_dir = os.path.dirname(real_path)
    
    # Check if target exists and capture mode
    target_mode = None
    if mode is not None:
        target_mode = mode
    elif os.path.exists(real_path) and not os.path.isdir(real_path):
        # Raise IsADirectoryError if path is a directory
        if os.path.isdir(real_path):
            raise IsADirectoryError(...)
        target_mode = os.stat(real_path).st_mode
    
    # Create temp file in same directory
    try:
        fd, tmp_path = tempfile.mkstemp(dir=target_dir)
        try:
            os.write(fd, data)
            os.fsync(fd)
        except:
            os.close(fd)
            os.unlink(tmp_path)
            raise
        os.close(fd)
        
        if target_mode is not None:
            os.chmod(tmp_path, target_mode)
        
        os.replace(tmp_path, real_path)
        
        # fsync parent directory
        dfd = os.open(target_dir, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except:
        # Clean up temp file if it exists
        if 'tmp_path' in locals():
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise
```

Wait, the order of mode setting: if mode is specified, chmod the temp file; if mode is None and target exists, chmod the temp file. In both cases, we should probably chmod after writing and before replacing.

But there's a race condition: between checking if the target exists and doing the replace, someone could have deleted it. Or the mode could have changed. But the spec says this is fine — concurrency between writers is the caller's problem.

Let me also think about the error raising:
- `FileNotFoundError` — parent directory doesn't exist. This would be triggered when trying to create the temp file in a non-existent directory. `tempfile.mkstemp` raises `FileNotFoundError` in this case... actually, let me check. On Python 3.10+, `tempfile.mkstemp(dir=...)` should raise `FileNotFoundError` if dir doesn't exist. But to be safe, I can check beforehand.
- `IsADirectoryError` — path exists and is a directory. The check for this: if the resolved path exists and is a directory (before creating temp file)
- `PermissionError` — can't create temp file or replace target
- `OSError` — any other I/O failure

Let me also think about the `exists` race. If we check `os.path.isdir(real_path)` at the start and it's not a dir, but then by the time we do `os.replace`, it has become a dir, `os.replace` might behave weirdly. But the spec handles this via the general error contract.

One more thing: the temp file cleanup on error. I need to make sure the temp file is removed regardless of which step fails.

Let me also think about the parent directory check. If `path` is something like `/nonexistent/dir/file.txt`, then `os.path.dirname(os.path.realpath(path))` might give `/nonexistent/dir` (or just `/nonexistent` if `realpath` doesn't error). Actually, `os.path.realpath` can return valid paths for non-existent files — it just resolves symlinks in the existing part of the path.

Hmm, I think checking the parent dir exists is a good pre-flight check:
```python
parent_dir = os.path.dirname(real_path)
if not os.path.isdir(parent_dir):
    raise FileNotFoundError(f"No such directory: '{parent_dir}'")
```

Also need to check that `real_path` is not a directory.

Let me also think about data writing. For text, we encode to bytes first:
```python
def atomic_write_text(path, data, *, encoding="utf-8", mode=None):
    _atomic_write(path, data.encode(encoding), mode)
```

For bytes:
```python
def atomic_write_bytes(path, data, *, mode=None):
    _atomic_write(path, data, mode)
```

And the CLI:
```python
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <path>", file=sys.stderr)
        sys.exit(1)
    try:
        atomic_write_bytes(sys.argv[1], sys.stdin.buffer.read())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
```

Let me also handle the case where `path` is a symlink to a non-existent target. In that case, `os.path.realpath` would return... hmm, it follows symlinks. If the symlink target doesn't exist, `realpath` returns the path with the unresolved component. Let me think about this.

Actually, there's `os.path.realpath` which eliminates symlinks, but if the symlink target doesn't exist, it would return a path where the non-existent part is preserved. For example:
- `/tmp/link -> /tmp/nonexistent/file.txt`
- `os.path.realpath('/tmp/link')` returns `/tmp/nonexistent/file.txt`

That should be fine — the temp file goes in `/tmp/nonexistent/`, which would fail with FileNotFoundError since `/tmp/nonexistent` doesn't exist (the parent dir check would catch this).

Actually wait, what about symlinks? If the path is a symlink and we need to write to the target, but the target's parent directory doesn't exist, that's a FileNotFoundError. Fine.

What if the symlink target exists but is on a different filesystem? The temp file is in the same dir as the target, so the rename is on the same filesystem. But what if creating the temp file crosses a filesystem boundary? No, that's not possible — the temp file is in the same directory.

What if the target is a broken symlink? `os.path.realpath` would return a path that doesn't exist. The parent dir check might pass, the target exists check would fail (file doesn't exist), and we'd create a new file at the target path. That seems correct — we write to the target of the symlink, creating it if it doesn't exist.

But wait, if the target is a broken symlink, `os.path.isdir(real_path)` returns False (doesn't exist). So we proceed, create a temp file, and replace. After replace, the symlink now points to a real file. Correct.

Now there's one thing I'm not sure about: should we check `os.path.isdir(real_path)` vs checking `real_path` doesn't resolve to a directory? The spec says `IsADirectoryError` if the path exists AND is a directory. So we check `os.path.isdir(real_path)` and raise if True.

Wait, but what about the symlink case? If `/tmp/link -> /tmp/somedir`, then `os.path.isdir(real_path)` where `real_path = /tmp/somedir` returns True if `/tmp/somedir` exists and is a directory. The spec says write to the target, so we should raise `IsADirectoryError` in this case. Good.

But should we also check if the path itself (not the symlink) is a directory? Like if someone passes `/tmp/somedir` directly? `real_path` would be `/tmp/somedir`, and `os.path.isdir` would be True. So that's handled.

Alright, I think I have a solid plan. Let me also think about edge cases:

1. Empty data — should work fine, creates an empty file
2. Large data — should work, but memory. Since we read all data into memory anyway (for both the library and CLI), this is inherent
3. Concurrent writes — handled by unique temp file names (mkstemp) + atomic replace

Let me now check: should I use `tempfile.mkstemp` or `tempfile.NamedTemporaryFile`? 

`tempfile.mkstemp` gives me back an fd and a path. I can write to the fd, fsync, close, then use the path for renaming. This is clean.

`tempfile.NamedTemporaryFile` creates and opens a file, but when it closes, it deletes the file (by default). I'd need `delete=False`, write, fsync, close, rename, and potentially clean up myself. That also works.

I'll go with `tempfile.mkstemp` since it's simpler and gives more control.

Here's my implementation plan:

```python
import os
import sys
import tempfile

def _atomic_write(path, data_bytes, mode):
    real_path = os.path.realpath(path)
    parent_dir = os.path.dirname(real_path)
    
    if not os.path.isdir(parent_dir):
        raise FileNotFoundError(f"No such directory: '{parent_dir}'")
    
    if os.path.isfile(real_path):  # or os.path.exists
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

def atomic_write_text(path, data, *, encoding="utf-8", mode=None):
    _atomic_write(path, data.encode(encoding), mode)

def atomic_write_bytes(path, data, *, mode=None):
    _atomic_write(path, data, mode)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <path>", file=sys.stderr)
        sys.exit(1)
    try:
        atomic_write_bytes(sys.argv[1], sys.stdin.buffer.read())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
```

Wait, I need to be more careful about the `os.path.isfile(real_path)` check. If `real_path` doesn't exist, `os.path.isfile` returns False (correct). If it exists and is a regular file, returns True (correct). If it exists and is a directory, `os.path.isfile` returns False, but then `os.path.isdir` returns True, and we raise. 

But there's also the case of other special file types (fifo, socket, etc.). The spec doesn't mention these explicitly. I think handling them gracefully (treating them as targets to replace) is reasonable.

Actually, wait. If `real_path` is a directory, we need to catch that early. Let me restructure:

```python
if os.path.lexists(real_path) and os.path.isdir(real_path):
    raise IsADirectoryError(...)
```

Using `os.path.lexists` to also catch broken symlinks... no, actually `os.path.isdir` returns False for broken symlinks. And `os.path.isdir` follows symlinks, so it would correctly identify a symlink to a directory.

Hmm, let me think about this differently. The key checks are:
1. Parent directory must exist (FileNotFoundError if not)
2. If the resolved path exists and is a directory, raise IsADirectoryError
3. Otherwise, proceed

For (2), `os.path.isdir(real_path)` handles both direct directories and symlinks to directories.

One more thing: should I check if `real_path` exists as a file before checking parent dir? No, parent dir check should come first because it's a prerequisite for creating the temp file.

Let me finalize and write the code.

Actually, I just realized something. The symlink spec says "write to the symlink target". But `os.path.realpath` resolves ALL symlinks in the chain. If only the last component is a symlink, we want to replace the target of that symlink. If intermediate components are symlinks, we follow them too. That seems right — we always end up at the final real file.

For the `os.stat(real_path).st_mode` — `os.stat` follows symlinks, so it gives us the mode of the symlink target. Good.

What about `os.path.isdir(real_path)` — also follows symlinks. Good.

I think I'm ready to write. Let me be careful about one thing: the `os.path.isdir` check. I should call it before `os.path.isdir(parent_dir)`? No, parent dir first.

Also, when checking `os.path.isfile(real_path)` for mode inheritance — this would return False for symlinks to non-existent files (broken symlinks). In that case, we don't try to inherit mode (target doesn't exist — same as if the file wasn't there). Good.

But what if `real_path` is a non-regular file (e.g., a special device)? `os.path.isfile` would return False, we skip mode inheritance, and the new file gets default permissions. That seems reasonable.

Alright, I'm confident in the implementation. Let me write it.

Oh wait, one more edge case. What if the data is empty bytes (b"")? `os.write(fd, b"")` writes 0 bytes, which is fine. `os.fsync(fd)` after that should also be fine. `os.replace` replaces the target with an empty file. Correct.

What about `os.chmod` on the temp file with `target_mode`? If `target_mode` is, say, `0o644`, we set the temp to 644, then replace. The replace preserves the inode's mode on Linux... actually, `os.replace` replaces the directory entry, not the inode. The new file's inode becomes the target, and the old file's inode is unlinked. So the mode should travel with the temp file's inode. So setting it on the temp before the replace is correct.

But wait, on some systems, `os.replace` might preserve the original target's permissions on the new file. Let me check... On Linux, `renameat2(RENAME_NOREPLACE)` and `rename(2)` — actually, `rename()` replaces the old dentry with the new dentry. The old inode is unlinked, and the new inode takes its place. Permissions are from the new inode. So setting mode on the temp file before `os.replace()` is correct.

On macOS (APFS), `rename` behaves similarly — it's an atomic swap of directory entries. The new inode's metadata (including permissions) stays with the new inode.

OK, I'm confident. Let me write the file.

One more thing about the CLI: `sys.stdin.buffer.read()` reads all stdin as bytes. That's the correct behavior per spec ("Reads stdin (bytes mode, no decoding)").

Let me also think about whether `tempfile.mkstemp` could raise `PermissionError` or `FileNotFoundError`. On Python 3.10+, both are subclasses of `OSError`. If the parent dir doesn't exist, `mkstemp` should raise `FileNotFoundError` (subclass of OSError). If we don't have permission to create a file in the directory, it raises `PermissionError`. The spec says to let these propagate.

One more thing: I should handle the case where creating the temp file itself fails. In that case, `tmp_path` would be undefined or None, and I shouldn't try to unlink it.

Let me finalize the implementation now.

Actually, I should also consider: what if `os.chmod` fails? The temp file should still be cleaned up. My current implementation catches all exceptions and cleans up `tmp_path`.

Wait, there's a subtle issue. The `PermissionError` — the spec says we should raise it if we can't create the temp file OR can't replace the target. My implementation already does this — `tempfile.mkstemp` raises `PermissionError` if we can't create in the dir, and `os.replace` raises `PermissionError` if we can't write to the target dir.

But in the `except` block, if we catch a `PermissionError` during `tempfile.mkstemp`, `tmp_path` is `None` so we don't try to unlink. Good.

If we catch it during `os.replace`, `tmp_path` is set, so we unlink the temp. Good.

What about errors during `os.unlink` in the cleanup? If the unlink itself fails (e.g., no permission), we catch it with the inner try/except and ignore it. The original exception still propagates. Good.

Alright, I think this is solid. Let me write the file now.

_Tool call: write_

---

## Assistant (opencode-go/deepseek-v4-pro)

_Thinking:_

Now let me run the smoke tests as specified in PROMPT.md:
1. Write a small file
2. Verify the target exists and matches what I wrote
3. Verify no .tmp files remain in the directory

_Tool call: bash_

---

## Assistant (opencode-go/deepseek-v4-pro)

_Thinking:_

All smoke tests passed. Let me verify one more thing: the CLI works too.

_Tool call: bash_

---

## Assistant (opencode-go/deepseek-v4-pro)

_Thinking:_

All tests pass — both library API and CLI. The implementation is complete.

Done. Implementation in `atomic_write.py`.

---
