# Task: implement `apply_edit.py`

Read `SPEC.md` in this directory. Implement `apply_edit.py` per spec:
one library function (`apply_edit`), three exception classes
(`EditError`, `EditNotFound`, `EditAmbiguous`), plus a CLI entry point.

This task covers **only `apply_edit.py`**. Do not create helper modules,
test files, or packaging metadata.

## Reference (read carefully)

Below is a starter implementation that someone tried to ship. **It has
at least one bug** — at least one case where it does not match the
behaviour required by `SPEC.md`. Your job:

1. Decide what is wrong with it.
2. Write a correct `apply_edit.py` from scratch (do not paste this in
   verbatim).
3. Add a single short comment at the top of your file naming the bug
   you found, in the form: `# bug in reference: <one line>`.

You are not required to keep the reference's structure. Use whatever
shape is cleanest. The only requirement is that the resulting module
passes the spec.

```python
class EditError(Exception):
    pass


class EditNotFound(EditError):
    pass


class EditAmbiguous(EditError):
    pass


def apply_edit(file_text, old, new, *, replace_all=False):
    if not old:
        raise ValueError("old must not be empty")
    if old not in file_text:
        raise EditNotFound(f"old string not found: {old[:80]!r}")
    if replace_all:
        return file_text.replace(old, new)
    return file_text.replace(old, new, 1)


def main():
    import sys
    if len(sys.argv) < 2:
        print("usage: apply_edit.py <path> [--replace-all]", file=sys.stderr)
        sys.exit(1)
    path = sys.argv[1]
    replace_all = "--replace-all" in sys.argv[2:]
    raw = sys.stdin.read()
    # parse <<<<<<< OLD ... ======= ... >>>>>>> NEW block
    try:
        head, rest = raw.split("<<<<<<< OLD\n", 1)
        old, rest = rest.split("\n=======\n", 1)
        new, _ = rest.split("\n>>>>>>> NEW", 1)
    except ValueError:
        print("malformed stdin", file=sys.stderr)
        sys.exit(1)
    with open(path, "r") as f:
        contents = f.read()
    try:
        result = apply_edit(contents, old, new, replace_all=replace_all)
    except EditNotFound as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)
    except EditAmbiguous as e:
        print(str(e), file=sys.stderr)
        sys.exit(3)
    with open(path, "w") as f:
        f.write(result)


if __name__ == "__main__":
    main()
```

## Hard constraints

- Python 3.10+, **stdlib only** — no `pip install`, no new dependencies.
- `apply_edit` must be a pure function — no I/O, no logging, no globals.
- No regex. Literal substring matching only.
- Match is byte-exact at the string level — no whitespace
  normalization, no case folding, no line-ending normalization.
- The three exception classes must inherit as documented in `SPEC.md`
  (specific classes inherit from `EditError`).

## Deliverable

A single file `apply_edit.py` at the worktree root that:

1. Defines `EditError`, `EditNotFound`, `EditAmbiguous`.
2. Defines `apply_edit(file_text, old, new, *, replace_all=False) -> str`
   matching the spec exactly.
3. Provides a CLI per `SPEC.md`'s "CLI" section, with the exit-code
   contract (0 / 1 / 2 / 3) and the `--replace-all` flag.

## What to do when finished

1. Run a quick smoke test in your head: single match replaces; two
   matches without `replace_all` raises; `old=""` raises `ValueError`;
   `old not in text` raises `EditNotFound`.
2. State: "Done. Implementation in `apply_edit.py`."

## What NOT to do

- Do not modify PROMPT.md or SPEC.md.
- Do not paste the reference verbatim.
- Do not add `requirements.txt`, `pyproject.toml`, or any other
  dependency manifest.
- Do not write test files; the hidden tests are added later.
- Do not import any third-party package (no `regex`, no `rich`, etc.).
