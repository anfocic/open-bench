# Judge rubric: atomic-write task

Fill one copy per implementation, saved as `output/<label>_rubric.md`.
Also write `output/<label>_scores.json` with the structured form (see
JUDGE_PROMPT.md).

Implementation reviewed: **`<label>`** (e.g. `A`, `B`, `C`)
File: `implementations/<label>.py`

## Hard-fail (any miss = fail run)

Cite line numbers when something fails.

- [ ] `atomic_write.py` provided as `<label>.py`
- [ ] Top-level `atomic_write_text(path, data, *, encoding="utf-8", mode=None)` matches SPEC signature
- [ ] Top-level `atomic_write_bytes(path, data, *, mode=None)` matches SPEC signature
- [ ] No external Python dependencies (stdlib-only imports)
- [ ] Temp file created in the **same directory** as the target (not `tempfile.gettempdir()` or a hardcoded `/tmp`)
- [ ] File is `fsync`'d before close
- [ ] Parent directory is `fsync`'d after `os.replace`

Hard-fail result: **pass / fail**
If fail, reasons (with line refs):

## Spec compliance — score 0–10

Award 1 point per item present and correct. Cite line numbers.

- [ ] Uses `os.replace` (not `os.rename` — Windows differs) for the atomic step
- [ ] Cleans up the temp file on **every** error path (try/except/finally or context manager that survives mid-write exceptions)
- [ ] If target exists and `mode is None`, the new file inherits the target's pre-existing mode bits (`os.stat` then `os.chmod`)
- [ ] If `mode` is set explicitly, applies it (`os.chmod`) before the replace
- [ ] Raises `FileNotFoundError` cleanly when the parent directory doesn't exist (and leaves no temp residue)
- [ ] Raises `IsADirectoryError` when `path` is an existing directory
- [ ] CLI: `python atomic_write.py <path>` reads stdin (bytes mode) and writes atomically
- [ ] CLI: exits 0 on success, non-zero on any error with a stderr message
- [ ] Symlink targets: writes to the resolved target, not replacing the symlink itself (or explicitly documented if not handling)
- [ ] Concurrent writers: uses a unique temp name (e.g. `tempfile.NamedTemporaryFile(dir=...)` or pid+rand suffix) so two concurrent calls don't collide on the temp filename

Subtotal: __ / 10
Notes:

## Code quality — score each 0–5

- [ ] **Clarity** — naming, structure, function decomposition: __
- [ ] **Conciseness** — no over-engineering, no unused branches: __
- [ ] **Error handling** — temp cleanup on every failure path; specific exception types per SPEC: __
- [ ] **Comments** — only at the genuinely non-obvious points (parent-dir fsync rationale, temp-in-same-dir constraint, symlink semantics): __

Subtotal: __ / 20

## One-line summary

## Verdict

ship-with-cleanup / rewrite / unusable
