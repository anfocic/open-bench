# `apply_edit.py` — implementation spec

A single-file Python module providing one operation: **search-replace
patching of file contents**. This is the primitive that agent harnesses
(Cursor, aider, Claude Code, etc.) use to translate model-emitted edits
into actual file changes.

The point of the function is not "replace text". `str.replace` already
does that. The point is to apply edits **safely** — raising loudly when
the edit is ambiguous or impossible, never silently mutating the wrong
location.

## Public API

```python
def apply_edit(
    file_text: str,
    old: str,
    new: str,
    *,
    replace_all: bool = False,
) -> str: ...
```

Returns a new string with `old` replaced by `new` in `file_text`. The
input is never mutated (strings are immutable anyway, but: no other
side effects).

### Exceptions

Three exception types, all module-level:

```python
class EditError(Exception): ...
class EditNotFound(EditError): ...
class EditAmbiguous(EditError): ...
```

The two specific subclasses must inherit from `EditError` so callers
can catch either the specific failure or `EditError` as a base.

### Behaviour

| Case | What must happen |
|---|---|
| `old` is the empty string | Raise `ValueError`. An empty needle is never a valid edit. |
| `old` does not appear in `file_text` | Raise `EditNotFound`. |
| `old` appears exactly once | Return `file_text` with that single occurrence replaced by `new`. |
| `old` appears 2+ times **and** `replace_all=False` | Raise `EditAmbiguous`. **Do not silently replace the first match.** This is the whole reason this function exists rather than `str.replace`. |
| `old` appears 2+ times **and** `replace_all=True` | Replace every occurrence. Return the new string. |
| `old == new` | Still validated for presence/ambiguity per the rules above; if it would otherwise succeed, return `file_text` unchanged. |

### Whitespace, line endings, encoding

- Match is **byte-exact** at the string level — no whitespace
  normalization, no leading/trailing strip, no case folding. Indentation
  must match exactly.
- `file_text` may contain `\n`, `\r\n`, or a mix. The function operates
  on the string as given; it does not normalize line endings.
- The input is `str`, not `bytes`. Callers handle encoding.

### Error messages

Exception messages must be informative enough for an agent to react:

- `EditNotFound`: include the first ~80 chars of `old` (truncated with
  `…` if longer) so logs show what was searched for.
- `EditAmbiguous`: include the match count, e.g.
  `"old string matched 4 times; pass replace_all=True to replace all"`.

## CLI

```
python apply_edit.py <path> <<EOF
<<<<<<< OLD
<old text>
=======
<new text>
>>>>>>> NEW
EOF
```

The CLI reads a single edit block from stdin in the format above
(literal `<<<<<<< OLD`, `=======`, `>>>>>>> NEW` markers; no leading
spaces), applies it to the file at `<path>`, and writes the result back
to that path.

- Exit 0 on a successful single-match edit.
- Exit 2 on `EditNotFound`. Print the exception message to stderr.
- Exit 3 on `EditAmbiguous`. Print the exception message to stderr.
- Exit 1 on any other error (missing file, malformed stdin, etc.) with
  a stderr message.
- `--replace-all` flag: if passed, set `replace_all=True` for the call.

The CLI must not require any third-party libraries.

## Hard constraints

- Python 3.10+, **stdlib only**.
- Pure function semantics for `apply_edit`: no logging, no I/O, no
  global state. The CLI is a separate `main()` that does I/O.
- No regex matching — search is literal substring. (Regex is what
  half of these tools get wrong; this task is the simple version.)

## Out of scope

- Multi-block patches (one edit per call only).
- Fuzzy / context-aware matching. The point is strict matching.
- Unified-diff parsing.
- File I/O inside `apply_edit` itself.
