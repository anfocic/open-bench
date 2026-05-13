# Task: judge implementations of `apply_edit.py`

You are a code reviewer. You will look at one or more implementations
of `apply_edit.py` (each provided as a file under `implementations/`)
and score each one against `JUDGE_RUBRIC.md`.

## What's in your packet

- `SPEC.md`, `PROMPT.md` — what was asked. PROMPT.md contains a
  *buggy* reference implementation; the task is to spot the bug and
  ship a correct version.
- `JUDGE_RUBRIC.md` — fill one copy per implementation.
- `implementations/<label>.py` — blinded code files.

You do **not** see the hidden test suite or its results. Score from the
code alone.

## What to produce, per implementation

1. `output/<label>_rubric.md` — filled JUDGE_RUBRIC.md, citing line numbers.
2. `output/<label>_scores.json`:

   ```json
   {
     "hard_fail": "pass",
     "hard_fail_reasons": [],
     "spec_compliance": 8,
     "spec_compliance_notes": [],
     "code_quality": {
       "clarity": 4, "conciseness": 5,
       "error_handling": 3, "comments": 5
     },
     "verdict": "ship-with-cleanup",
     "one_line_summary": "..."
   }
   ```

   Allowed values:
   - `hard_fail`: `"pass"` or `"fail"`
   - `spec_compliance`: integer 0–10
   - each `code_quality` field: integer 0–5
   - `verdict`: `"ship-with-cleanup"`, `"rewrite"`, or `"unusable"`

3. `output/summary.md` (only if multiple impls) — short comparison
   noting which impls correctly diagnosed the reference bug, which
   inherited it, and which over-corrected (e.g. forbidding multi-match
   even with `replace_all=True`).

## Rules

- **Score each implementation independently first.** Don't anchor on
  the first one you read. Fill A's rubric and scores fully before
  opening B.
- **Cite evidence.** A line number or function name beats a vague claim.
- **Don't try to identify the model.** Labels are randomly assigned.
- **No execution.** Static review only.
- **Hard-fails are gates.** If `hard_fail` is `"fail"`, still fill the
  rest so the reviewer has data.

## What "hard fail" means here

Any one of these:

- `apply_edit.py` missing or in the wrong location.
- `apply_edit` signature doesn't match SPEC (`file_text, old, new, *,
  replace_all=False`).
- Any of `EditError`, `EditNotFound`, `EditAmbiguous` missing.
- `EditNotFound` or `EditAmbiguous` does not inherit from `EditError`.
- External Python dependency introduced (any non-stdlib import).
- `apply_edit` itself does I/O, logging, or mutates global state.
- Uses regex (`re`) instead of literal substring matching.

Quote the offending line.

## The bug to look for

The reference in PROMPT.md silently replaces only the first occurrence
when `old` matches multiple times and `replace_all=False`, instead of
raising `EditAmbiguous`. This is the central bug of the task.

When grading **spec compliance**, the multi-match-raises-EditAmbiguous
item is the most load-bearing — an impl that inherits the reference's
bug should lose that point and probably not be `ship-with-cleanup`.

## What goes in `code_quality`

- **Clarity** (0–5): naming, structure. Is the multi-match branch
  obvious or buried?
- **Conciseness** (0–5): the correct version is small. Penalise bloat
  (e.g. a regex-engine reimplementation) and false cleverness.
- **Error handling** (0–5): the three exception types used in the
  right places; CLI exit codes match the spec.
- **Comments** (0–5): a `# bug in reference:` comment naming the actual
  bug is high signal. Vague "fixed a bug" or no diagnosis is low.
  Narration of obvious lines is low signal.

Done.
