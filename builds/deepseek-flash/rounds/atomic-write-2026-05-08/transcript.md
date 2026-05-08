# atomic-write-deepseek-flash-2026-05-08

**Session ID:** ses_1f884b332ffed2WabhZs1Nd3no

---

## User

"Read PROMPT.md and SPEC.md at the worktree root, then implement atomic_write.py per the spec. Stop when atomic_write.py exists at the worktree root and your own quick smoke check passes."


---

## Assistant (opencode-go/deepseek-v4-flash)

_Thinking:_

Let me start by reading the PROMPT.md and SPEC.md files to understand what needs to be implemented.

_Tool call: read_

_Tool call: read_

---

## Assistant (opencode-go/deepseek-v4-flash)

_Thinking:_

Let me analyze the spec carefully and implement `atomic_write.py`.

Key requirements:
1. Two functions: `atomic_write_text` and `atomic_write_bytes`
2. CLI entry point
3. Temp file in same directory as target
4. `fsync` file descriptor before close
5. `os.replace` for atomic rename
6. `fsync` parent directory after replace
7. Clean up temp file on error
8. Symlink handling: resolve symlinks for path and parent dir
9. Mode preservation if target already exists and mode is None

Let me write the implementation:

```python
import os
import sys
import stat
import tempfile

def atomic_write_text(path, data, *, encoding="utf-8", mode=None):
    if isinstance(data, str):
        data_bytes = data.encode(encoding)
    else:
        data_bytes = data
    _atomic_write(path, data_bytes, mode=mode)

def atomic_write_bytes(path, data, *, mode=None):
    _atomic_write(path, data, mode=mode)

def _atomic_write(path, data, *, mode=None):
    # Resolve symlinks
    try:
        st = os.lstat(path)
        path = os.path.realpath(path)
    except FileNotFoundError:
        # path doesn't exist; we'll create it. If it's a symlink to a non-existent target,
        # realpath returns the path as-is (which is fine).
        resolved = os.path.realpath(path)
        parent = os.path.dirname(resolved)
        # But we should be careful about the target path
    except OSError:
        raise
    
    # Get parent directory
    parent = os.path.dirname(os.path.abspath(path))
    
    # If target already exists and mode is None, capture its mode
    existing_mode = None
    if mode is None:
        try:
            st = os.stat(path)
            existing_mode = stat.S_IMODE(st.st_mode)
        except FileNotFoundError:
            pass
        except OSError:
            raise
    
    # Create temp file in same directory
    fd = None
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(dir=parent)
        
        # Write data
        os.write(fd, data)
        
        # fsync before close
        os.fsync(fd)
        
        # Close
        os.close(fd)
        fd = None
        
        # Set mode if specified, or if we have existing mode
        if mode is not None:
            os.chmod(tmp_path, mode)
        elif existing_mode is not None:
            os.chmod(tmp_path, existing_mode)
        
        # Atomic replace
        os.replace(tmp_path, path)
        
        # fsync parent directory
        # Open parent directory and fsync it
        parent_fd = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
            
    except BaseException:
        # Clean up temp file
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise


def main():
    if len(sys.argv) != 2:
        print("Usage: python atomic_write.py <path>", file=sys.stderr)
        sys.exit(1)
    
    path = sys.argv[1]
    data = sys.stdin.buffer.read()
    
    try:
        atomic_write_bytes(path, data)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

Wait, let me think about symlink handling more carefully.

The spec says:
> If `path` is a symlink, write to the symlink **target**, not replace the symlink itself. (Common gotcha: naive `os.replace` would replace the symlink, breaking the link.) The temp file lives next to the resolved target so the rename stays on the same filesystem.

So if `path` is a symlink to `/some/other/path`, we should:
- Resolve the symlink to get the real target path
- Create temp file in the parent directory of the resolved target
- `os.replace` the resolved target with our temp file

Let me also think about the case where `path` doesn't exist but a parent directory component is a symlink. `os.path.realpath` handles that.

But what if `path` is `None` (doesn't exist at all)? Then `os.path.realpath` returns... let me think. Actually if the file doesn't exist, `os.path.realpath` still works - it resolves all the directory components but the final component is left as-is. Actually, `os.path.realpath` might fail if a parent directory is broken. Let me check the behavior.

Actually, `os.path.realpath` doesn't care about the last component if it doesn't exist. It resolves all ancestors. So `os.path.realpath("some/path/that/doesnt/exist")` would resolve the dirname part but leave the basename.

Wait, but the spec says for symlinks: resolve the symlink to get the target, and put the temp file next to the resolved target. So:

```python
try:
    st = os.lstat(path)
    if stat.S_ISLNK(st.st_mode):
        # It's a symlink. Resolve it to the target.
        target = os.path.realpath(path)
        # Create temp file in the same directory as the resolved target
        parent = os.path.dirname(target)
        path = target  # Replace path with the resolved target
    else:
        parent = os.path.dirname(os.path.abspath(path))
except FileNotFoundError:
    # path doesn't exist at all. Just use its absolute parent.
    parent = os.path.dirname(os.path.abspath(path))
```

Hmm, but `os.path.realpath` on a symlink returns the resolved target. If the target doesn't exist, it returns... I think it returns the path as-is if all directories resolve but the final component doesn't exist. Actually `os.path.realpath` calls `realpath()` C function which resolves all symlinks in the path. If the final component is a symlink, it resolves it. If the final component doesn't exist, it resolves everything up to the last component.

Actually, I think the simplest approach is:

```python
# Resolve the path
real_path = os.path.realpath(path)
parent = os.path.dirname(real_path)
```

But wait - if `path` is a symlink to `/target`, `os.path.realpath(path)` returns `/target`. Then we create the temp in the same dir as `/target` and replace `/target`. This is correct per the spec.

But if `path` doesn't exist and there's no symlink, `os.path.realpath(path)` returns an absolute path with the last component as-is (if it doesn't exist). Its dirname is the parent dir. This is also fine.

What about `os.path.realpath` on a path where the symlink exists but the target doesn't? `os.path.realpath` would resolve the symlink to `/target` (the target path), and then since `/target` doesn't exist, the behavior depends on the OS. On macOS/Linux, `realpath()` returns the path as-is if it doesn't exist. Actually no, `realpath()` returns an error if the path doesn't exist... let me think.

Actually, `os.path.realpath` in Python does NOT fail if the final component doesn't exist. From Python docs: "If the path doesn't exist, it will still be resolved." But that might be implementation dependent (it resolves what it can). Let me check: the Python implementation of `realpath` resolves path components as far as possible, and if the final path doesn't exist, it still returns the resolved path as far as it could go.

Wait, but we want to handle the case where `path` is a symlink. `os.path.realpath(path)` will resolve the symlink. If the target exists, great. If the target doesn't exist... actually `os.path.realpath` will still return the target path (symlink resolution is about the symlink itself, not whether the target exists).

Let me re-read the spec: "If `path` is a symlink, write to the symlink **target**, not replace the symlink itself."

So the simplest approach:
1. Use `os.path.realpath(path)` to get the real path (resolving symlinks)
2. Use the parent of the real path for the temp file
3. Replace the real path

But what if `path` doesn't exist? `os.path.realpath(path)` still works - it returns the absolutized path with symlinks resolved as much as possible. The parent directory must exist (otherwise we'd get FileNotFoundError later), so it will be resolved.

Actually wait - there could be an issue: `os.path.realpath` might not resolve the last component if it's a dangling symlink. But actually `realpath` in C returns ENOENT if the path doesn't exist. In Python, `os.path.realpath` has a more lenient behavior on some platforms. Let me think about what would actually happen...

In CPython (macOS/Linux), `os.path.realpath` ends up calling `realpath()` which does require the path to exist. But Python also has a fallback implementation. Let me not overthink this.

Actually, on modern Python 3.10+, `os.path.realpath` uses `os.realpath()` which can work with non-existent paths (it resolves symlinks where possible and leaves the rest). I think this is safe.

Hmm, let me simplify. The key cases are:
1. `path` exists and is not a symlink → `os.path.realpath(path)` returns the same path (or resolved ancestor symlinks). Temp goes in parent dir. Replace path.
2. `path` exists and IS a symlink → `os.path.realpath(path)` returns the target. Temp goes in target's parent dir. Replace target.
3. `path` doesn't exist → `os.path.realpath(path)` returns the path with resolved ancestors. Temp goes in parent dir. Replace path.
4. `path` is a dangling symlink → `os.path.realpath(path)` returns... depends on implementation. Might work or might fail.

For case 4, I think `os.path.realpath` would still resolve the symlink itself (since the symlink exists) and return the target path. If the target doesn't exist, I think on macOS it should still return the target path. Let me just use `os.path.realpath` and handle exceptions.

Actually, I just realized: `os.path.realpath` might not resolve a dangling symlink. Because `realpath()` C function needs to `stat` every component, and if the last component is a dangling symlink, `stat` will fail. But Python's `os.path.realpath` may have more lenient behavior.

Let me just go with a simpler approach:

```python
try:
    st = os.lstat(path)
    if stat.S_ISLNK(st.st_mode):
        # path is a symlink - resolve it to the target
        target = os.readlink(path)
        if not os.path.isabs(target):
            target = os.path.join(os.path.dirname(path), target)
        target = os.path.abspath(target)
        path = target
except FileNotFoundError:
    pass
```

Hmm, but `os.readlink` only resolves one level of symlink. And it doesn't resolve the path components. Better to use `os.path.realpath` which handles all of this.

I think `os.path.realpath` is the right call. Let me just use it:

```python
def atomic_write_bytes(path, data, *, mode=None):
    real_path = os.path.realpath(path)
    parent = os.path.dirname(real_path)
    
    # ... proceed with real_path
```

Actually wait, there's a subtlety. `os.path.realpath(path)` resolves all symlinks in all components. If path = "foo/bar" and foo is a symlink to /somewhere, realpath gives /somewhere/bar. Good. If bar is itself a symlink to /target, realpath gives /target. Also good.

But what if `path` doesn't exist at all? `os.path.realpath` on Python should handle this. Let me check the Python docs:

From Python 3.10 docs: "os.path.realpath(path, *, strict=False)"
"If strict is True, FileNotFoundError is raised if the path doesn't exist."
"strict is False by default, meaning the path is resolved as far as possible and any remainder is appended without checking whether it exists."

So with `strict=False` (default), it handles non-existent paths. Great.

So the plan:
1. `real_path = os.path.realpath(path)`
2. `parent = os.path.dirname(real_path)`
3. Create temp file in `parent`
4. Write, fsync, close
5. Set mode
6. `os.replace(tmp_path, real_path)`
7. fsync parent dir

For mode handling:
- If `mode` is provided, chmod to that mode
- Else if target already exists, get its mode and chmod the new file to match
- Else, the new file gets the default umask-derived mode

The tricky part with mode is that we need to do it BEFORE the replace (so we're modifying the temp file, not the target). But if we do it before the replace, the mode we captured from the old target might differ from the current target. In the concurrent case, this could lead to a race. However, the spec says coordination between writers is the caller's job. So this should be fine.

OK, let me write the final implementation:

```python
import os
import stat
import sys
import tempfile


def atomic_write_text(path, data, *, encoding="utf-8", mode=None):
    data_bytes = data.encode(encoding)
    _atomic_write(path, data_bytes, mode=mode, make_parents=False)


def atomic_write_bytes(path, data, *, mode=None):
    _atomic_write(path, data, mode=mode, make_parents=False)


def _atomic_write(target, data, *, mode):
    # Resolve symlinks: follow the symlink to its target
    real_path = os.path.realpath(target)
    parent = os.path.dirname(real_path)

    # Capture existing mode if not explicitly set
    existing_mode = None
    if mode is None:
        try:
            st = os.stat(real_path)
            existing_mode = stat.S_IMODE(st.st_mode)
        except FileNotFoundError:
            pass

    tmp_fd = None
    tmp_path = None
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

        os.replace(tmp_path, real_path)
        tmp_path = None  # replaced, no longer need cleanup

        # fsync parent directory
        parent_fd = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)

    except BaseException:
        if tmp_fd is not None:
            try:
                os.close(tmp_fd)
            except OSError:
                pass
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise


def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <path>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    data = sys.stdin.buffer.read()

    try:
        atomic_write_bytes(path, data)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

Wait, I need to think about `os.write` vs writing in chunks. `os.write` doesn't guarantee it writes all data. I should use a loop or `os.write` with check. Actually, in practice for most cases it will write everything, but to be safe I should loop.

Actually, Python's `os.write` can write fewer bytes than requested. From docs: "Write the bytes-like object, data, to the file descriptor, fd. Return the number of bytes written." So I should loop.

```python
def _write_all(fd, data):
    while data:
        n = os.write(fd, data)
        data = data[n:]
```

Or I could just use `os.write(fd, data)` and check the return value. Or use `io.FileIO` which handles this. But the spec says stdlib only and the tempfile module returns a raw fd, so let me write in chunks.

Actually, let me just use a `with` statement for the temp file:

Hmm, but the issue is we need the fd for fsync. If we use a tempfile.NamedTemporaryFile, it gives us a file object, and we can call .raw.fsync or something. But it's more complex. Let me stick with the raw fd approach.

Actually wait, let me reconsider. Using `tempfile.mkstemp` returns a raw fd. To use it conveniently, I could open it with `os.fdopen`:

```python
tmp_fd, tmp_path = tempfile.mkstemp(dir=parent)
with os.fdopen(tmp_fd, 'wb') as f:
    f.write(data)
    f.flush()
    os.fsync(f.fileno())
```

But `os.fdopen` would close the fd when the file object is closed, which is fine. And `f.write(data)` will write all the data since FileIO write handles this.

Hmm, but actually `os.fsync(f.fileno())` - will the file descriptor be valid? Yes, because `os.fdopen` creates a new file object that owns the fd. `fileno()` returns the underlying fd. But after `os.fsync`, when we close the file object, it closes the fd. That's fine.

Actually, I think the mkstemp + os.fdopen approach is cleanest:

```python
tmp_fd, tmp_path = tempfile.mkstemp(dir=parent)
with os.fdopen(tmp_fd, 'wb') as f:
    f.write(data)
    f.flush()
    os.fsync(tmp_fd)
```

Wait, but inside the `with` block, `tmp_fd` is the file descriptor number. `f.fileno()` would be the same. Let me use `f.fileno()` for clarity, or just `tmp_fd` since they're the same.

Actually, I think the cleanest approach is:

```python
tmp_fd, tmp_path = tempfile.mkstemp(dir=parent)
try:
    with os.fdopen(tmp_fd, 'wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    # At this point, the file object is closed and data is on disk
    
    # Handle mode
    ...
    
    os.replace(tmp_path, real_path)
    tmp_path = None
    
    # fsync parent
    ...
except BaseException:
    if tmp_path is not None:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    raise
```

Wait, but `os.fdopen` with a `with` statement will close the fd when exiting the `with` block. So after the `with` block, `tmp_fd` is no longer valid. This is fine - we don't need the fd anymore after the write+fsync.

But the `os.fdopen` can raise. If `os.fdopen` raises, `tmp_fd` is not yet owned by a file object, so we need to close it ourselves. Let me handle this:

Actually, `os.fdopen` takes ownership of the fd. It will close the fd when the file object is closed (via `with`). If `os.fdopen` fails... I think it would be an unusual case. Let me keep it simple and handle the cleanup in the except block.

Wait, hmm. If `os.fdopen` succeeds but then `f.write` raises, the `with` block will close `f`, which closes the fd. Then the temp file still exists on disk. In the except block, we try to unlink it. Good.

If `os.fdopen` fails, `tmp_fd` is still valid, and we need to close it. But `tmp_path` is also set. So we close the fd and unlink the temp path in the except block.

This seems right. Let me finalize the implementation.

One more thing: for the cleanup loop, when `os.replace` succeeds, we set `tmp_path = None` to avoid unlinking. But the fd is already closed by the `with` block, so we don't need to worry about `tmp_fd`.

Actually, there's a subtlety with the exception handling. If we catch `BaseException` and then unlink, we shouldn't let those cleanup errors propagate. We just swallow them as the spec says (temp file must be cleaned up, no .tmp residue after failure).

Let me write out the final version now.

Actually, one more thought on the mode preservation. The spec says:
> If `mode` is provided, chmod to that mode. If `None` and the target already exists, preserve the target's existing mode; otherwise the new file gets the default umask-derived mode.

I should capture the mode of the existing file BEFORE writing to the temp file, to avoid a race condition. But in concurrent scenarios, the captured mode could be stale by the time we apply it. But that's acceptable per the spec (coordination is the caller's job).

Alright, let me finalize:

```python
import os
import stat
import sys
import tempfile


def atomic_write_text(path, data, *, encoding="utf-8", mode=None):
    _atomic_write(path, data.encode(encoding), mode=mode)


def atomic_write_bytes(path, data, *, mode=None):
    _atomic_write(path, data, mode=mode)


def _atomic_write(path, data, *, mode):
    real_path = os.path.realpath(path)
    parent = os.path.dirname(real_path)

    existing_mode = None
    if mode is None:
        try:
            existing_mode = stat.S_IMODE(os.stat(real_path).st_mode)
        except FileNotFoundError:
            pass

    tmp_fd = None
    tmp_path = None
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=parent)
        with os.fdopen(tmp_fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        tmp_fd = None

        if mode is not None:
            os.chmod(tmp_path, mode)
        elif existing_mode is not None:
            os.chmod(tmp_path, existing_mode)

        os.replace(tmp_path, real_path)
        tmp_path = None

        dir_fd = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except BaseException:
        if tmp_fd is not None:
            try:
                os.close(tmp_fd)
            except OSError:
                pass
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    data = sys.stdin.buffer.read()
    try:
        atomic_write_bytes(path, data)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

This looks good. Let me also think about edge cases:

1. `os.path.realpath` on a non-existent path: With `strict=False` (default), it works fine.
2. `os.path.dirname` of a path without directories: `os.path.dirname("foo")` returns `""`. Then `tempfile.mkstemp(dir="")` would create in the current directory. That's correct behavior.
3. What if `parent` is `"/"`? `os.listdir("/")` would fail on permissions? Wait, we're not listing, we're just opening and fsyncing. `os.open("/", os.O_RDONLY)` should work. Good.
4. What about a trailing slash in the path? `os.path.realpath` would normalize it.

Let me also think about whether `f.write` guarantees writing all bytes. On a file-like object returned by `os.fdopen`, `.write()` does not guarantee writing everything. But `BytesIO.write` does. Actually, for `os.fdopen` with mode `'wb'`, the underlying is `FileIO`, and its `.write()` method does write everything (it loops internally in CPython's implementation). But it's not guaranteed by the spec. To be safe, I could use `f.write(data)` and check - but in practice for local files, FileIO.write always writes everything. Let me keep it simple and just use `f.write(data)`.

Actually, you know what, let me just write the data in a loop with the raw fd to be safe, since this is a system-level utility:

Hmm, the os.write loop approach is more complex. Let me just use the file object approach. FileIO.write in CPython IS guaranteed to write all bytes for regular files. For simplicity and readability, `with os.fdopen(...) as f: f.write(data); f.flush(); os.fsync(f.fileno())` is clean.

OK, I'm satisfied with the implementation. Let me write it.

_Tool call: write_

---

## Assistant (opencode-go/deepseek-v4-flash)

_Thinking:_

Now let me run a quick smoke test: write a small file, verify the target exists and matches, verify no .tmp files remain.

Now the smoke check:

_Tool call: bash_

---

## Assistant (opencode-go/deepseek-v4-flash)

_Thinking:_

I forgot to import `stat` in the test script. Let me fix it.

_Tool call: bash_

---

## Assistant (opencode-go/deepseek-v4-flash)

_Thinking:_

All smoke tests passed. Done.

Done. Implementation in `atomic_write.py`.

---
