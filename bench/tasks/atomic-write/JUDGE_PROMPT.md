# Task: judge implementations of `atomic_write.py`

You are a code reviewer. You will look at one or more implementations
of `atomic_write.py` (each provided as a file under `implementations/`)
and score each one against `JUDGE_RUBRIC.md`.

## What's in your packet

- `SPEC.md`, `PROMPT.md` — what was asked.
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

3. `output/summary.md` (only if multiple impls) — a few paragraphs
   comparing where they converged, where they diverged, what each got
   most right or wrong.

## Rules

- **Score each implementation independently first.** Don't anchor on the
  first one you read. Fill A's rubric and scores fully before opening B.
- **Cite evidence.** A line number or function name beats a vague claim.
- **Don't try to identify the model.** Labels are randomly assigned per
  judge — guessing would just bias you.
- **No execution.** Static review only. If a check requires runtime
  behaviour (e.g. "does this actually fsync?"), note it in spec
  compliance and move on.
- **Hard-fails are gates.** If `hard_fail` is `"fail"`, the implementation
  is unusable as-is. Still fill the rest so the reviewer has data.

## What "hard fail" means here

Any one of these:

- `atomic_write.py` missing or in the wrong location.
- `atomic_write_text` or `atomic_write_bytes` absent, or signature
  doesn't match the SPEC kwargs (`encoding`, `mode`).
- External Python dependency introduced (any non-stdlib import).
- The temp file is created in `tempfile.gettempdir()` or any directory
  other than the target's parent (cross-fs `os.replace` is not atomic
  → silent durability failure).
- The implementation never `fsync`s the file before close (data may be
  lost on crash even if the rename completed).
- The implementation never `fsync`s the parent directory after replace
  (the rename itself may not survive a crash).

Quote the offending line.

## What goes in `code_quality`

- **Clarity** (0–5): naming, structure, function decomposition. Can a
  reader follow what the algorithm guarantees without scrolling?
- **Conciseness** (0–5): no over-engineering, no unused branches, no
  premature abstraction. Penalise both bloat and false cleverness.
- **Error handling** (0–5): proportional. Cleans up the temp file on
  every failure path; raises specific exceptions per SPEC; doesn't
  paranoid-wrap stdlib calls. The exception specificity (FileNotFound /
  IsADirectory / Permission) is part of the contract.
- **Comments** (0–5): the WHY-is-non-obvious bar. This task has several
  non-obvious requirements (parent-dir fsync, temp-in-same-dir,
  symlink semantics) — a comment naming the constraint at the relevant
  line is high signal. Narration of what the next line does is low
  signal. Reward the former, penalise the latter.

Done.
