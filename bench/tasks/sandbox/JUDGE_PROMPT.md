# Task: judge implementations of sandbox.py

You are a code reviewer. You will look at one or more implementations of
`sandbox.py` (each provided as a file) and score each one against the rubric.

## What's in your packet

- `SPEC.md` — the contract every implementation was asked to satisfy.
- `PROMPT.md` — what the implementer was told. Read both — the `Hard
  constraints` block in PROMPT.md is enforced.
- `JUDGE_RUBRIC.md` — the scoring sheet. Fill one copy per implementation.
- `implementations/` — one Python file per implementation, named with
  blinded labels (`A.py`, `B.py`, ...). You do **not** know which model
  produced which file, and you should not try to guess.

You will **not** receive the hidden test suite or its results. Your scoring
must come from reading the code against the spec, not from execution
outcomes you could verify.

## What to produce

For each implementation in `implementations/`:

1. **Filled rubric** at `output/<label>_rubric.md` — a copy of
   JUDGE_RUBRIC.md with every checkbox / numeric field filled in. Cite
   line numbers from the implementation file when noting a finding.

2. **Structured scores** at `output/<label>_scores.json` — exactly this
   shape (no extra fields):

   ```json
   {
     "hard_fail": "pass",
     "hard_fail_reasons": [],
     "spec_compliance": 8,
     "spec_compliance_notes": [
       "missing --pids-limit (line 42 omits it)",
       "..."
     ],
     "code_quality": {
       "clarity": 4,
       "conciseness": 5,
       "error_handling": 3,
       "comments": 5
     },
     "verdict": "ship-with-cleanup",
     "one_line_summary": "Solid argv handling but skips two resource caps."
   }
   ```

   Allowed values:
   - `hard_fail`: `"pass"` or `"fail"`
   - `spec_compliance`: integer 0–10
   - each `code_quality` field: integer 0–5
   - `verdict`: `"ship-with-cleanup"`, `"rewrite"`, or `"unusable"`

3. **Cross-implementation summary** at `output/summary.md` (only if you
   judged more than one) — a few paragraphs comparing them: where they
   converged, where they diverged, what each got most right or wrong.

## Rules

- **Score each implementation independently first.** Don't anchor on the
  first one you read. Fill A's rubric and scores fully before opening B.
- **Cite evidence.** A line number or function name beats a vague claim.
- **Don't try to identify the model.** Labels are randomly assigned per
  judge — guessing would just bias you.
- **No execution.** You're doing static review. If something would need a
  runtime check, note it in your spec compliance notes and move on.
- **Hard-fails are gates.** If `hard_fail` is `"fail"`, the implementation
  is unusable as-is. Still fill the rest of the rubric so the reviewer
  has data, but note the gate.

## What "hard fail" means here

Any one of these:

- `sandbox.py` missing or in the wrong location
- `sandbox_run` function absent or with wrong signature
- Subprocess invocation uses the host shell to interpolate `command`
  (e.g. `subprocess.run(f"podman ... sh -c \"{command}\"", shell=True)`).
  Quote the offending line.
- `network` parameter does not default to `"none"`
- External Python dependency introduced (any non-stdlib import beyond
  what `python3 -c "import x"` resolves out of the box)

## What goes in `code_quality`

- **Clarity** (0–5): naming, structure, function decomposition. Can a
  reader follow it without scrolling back?
- **Conciseness** (0–5): no over-engineering, no unused branches, no
  premature abstraction. Penalise both bloat and false cleverness.
- **Error handling** (0–5): proportional. Validates at boundaries, doesn't
  swallow internal errors, doesn't paranoid-wrap stdlib calls.
- **Comments** (0–5): only where the *why* is non-obvious; no narration.
  Penalise both noisy comments and missing ones at genuinely tricky spots.

Done.
