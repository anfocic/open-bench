# Judge rubric: apply-edit task

Fill one copy per implementation, saved as `output/<label>_rubric.md`.
Also write `output/<label>_scores.json` with the structured form (see
JUDGE_PROMPT.md).

Implementation reviewed: **`<label>`** (e.g. `A`, `B`, `C`)
File: `implementations/<label>.py`

## Hard-fail (any miss = fail run)

Cite line numbers when something fails.

- [ ] `apply_edit.py` provided as `<label>.py`
- [ ] Top-level `apply_edit(file_text, old, new, *, replace_all=False) -> str` matches SPEC signature
- [ ] Module defines `EditError`, `EditNotFound`, `EditAmbiguous`
- [ ] `EditNotFound` and `EditAmbiguous` both inherit from `EditError`
- [ ] No external Python dependencies (stdlib-only imports)
- [ ] No regex — literal substring match only
- [ ] `apply_edit` is pure: no I/O, no global state, no logging inside it

Hard-fail result: **pass / fail**
If fail, reasons (with line refs):

## Spec compliance — score 0–10

Award 1 point per item present and correct. Cite line numbers.

- [ ] `old == ""` raises `ValueError` (not `EditError`, not silent return)
- [ ] `old not in file_text` raises `EditNotFound`
- [ ] `EditNotFound` message includes (a truncated form of) `old`
- [ ] Single match: returns `file_text` with that one occurrence replaced
- [ ] **Multi-match w/ `replace_all=False`: raises `EditAmbiguous`** (NOT silently replaces first — this is the bug in the reference)
- [ ] `EditAmbiguous` message includes the match count
- [ ] Multi-match w/ `replace_all=True`: replaces every occurrence
- [ ] Match is byte-exact: no whitespace normalization, no case folding, no line-ending normalization
- [ ] CLI exit codes match spec (0 success, 2 not-found, 3 ambiguous, 1 other)
- [ ] CLI `--replace-all` flag wired through to the call

Subtotal: __ / 10
Notes:

## Code quality — score each 0–5

- [ ] **Clarity** — naming, structure, function decomposition: __
- [ ] **Conciseness** — no over-engineering, no unused branches: __
- [ ] **Error handling** — distinct exception types per spec; CLI exit-code contract honoured: __
- [ ] **Comments** — at minimum a `# bug in reference:` line naming what was wrong; otherwise comments only at non-obvious points: __

Subtotal: __ / 20

## Bug-diagnosis bonus (informational, not scored)

Did the model correctly identify the bug in the reference? The expected
diagnosis is: *"silently replaces only the first occurrence on
multi-match instead of raising `EditAmbiguous`"*. Note in the rubric
whether the model's `# bug in reference:` comment matches.

## One-line summary

## Verdict

ship-with-cleanup / rewrite / unusable
