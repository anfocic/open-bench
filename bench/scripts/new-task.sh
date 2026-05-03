#!/usr/bin/env bash
# new-task.sh <task-name>
#
# Scaffold a new task under bench/tasks/<task-name>/ with placeholder files.

set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "usage: $0 <task-name>" >&2
    exit 2
fi

name="$1"
repo_root="$(git rev-parse --show-toplevel)"
task_dir="${repo_root}/bench/tasks/${name}"

if [[ -e "${task_dir}" ]]; then
    echo "error: ${task_dir} already exists" >&2
    exit 1
fi

mkdir -p "${task_dir}/tests"

cat > "${task_dir}/PROMPT.md" <<'EOF'
# Task: <one-line summary>

Read `SPEC.md` in this directory. Implement <files> exactly per spec.

## Hard constraints

- <list runtime / dependency / safety constraints>

## Deliverable

<what files, with what public API>

## What to do when finished

1. Run any quick smoke tests.
2. State: "Done. Implementation in <file>."

## What NOT to do

- Do not modify PROMPT.md or SPEC.md.
EOF

cat > "${task_dir}/SPEC.md" <<'EOF'
# <task> — implementation spec

## Public API

```python
def <name>(...) -> ...:
```

### Behaviour

- <bullet list of behaviour>

### Return format

<exact format>

## Out of scope

- <items not to implement>
EOF

cat > "${task_dir}/rubric.md" <<'EOF'
# Rubric: <task>

## Hard-fail
- [ ] <required item>

## Spec compliance — score 0–N
- [ ] <item>

## Hidden test results
| Test | Pass / Fail / Skip | Notes |
|---|---|---|
| | | |

## Code quality — 0–5 each
- [ ] Clarity
- [ ] Conciseness
- [ ] Error handling
- [ ] Comments

## Cost
- LOC, wall-clock, tokens

## Reviewer summary
EOF

cat > "${task_dir}/JUDGE_PROMPT.md" <<'EOF'
# Task: judge implementations of <task>

You are a code reviewer. You will look at one or more implementations
(each provided as a file under `implementations/`) and score each one
against `JUDGE_RUBRIC.md`.

## What's in your packet

- `SPEC.md`, `PROMPT.md` — what was asked.
- `JUDGE_RUBRIC.md` — fill one copy per implementation.
- `implementations/<label>.<ext>` — blinded code files.

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
3. `output/summary.md` (only if multiple impls) — comparison.

## Rules

- Score each impl independently. Fill A's rubric fully before opening B.
- Cite line numbers / function names.
- Don't try to identify the model — labels are randomly assigned.
- No execution; static review only.
EOF

cat > "${task_dir}/JUDGE_RUBRIC.md" <<'EOF'
# Judge rubric: <task>

Implementation reviewed: **`<label>`**
File: `implementations/<label>.<ext>`

## Hard-fail (any miss = fail run)
- [ ] <required item, cite line ref if missing>

Hard-fail result: **pass / fail**
If fail, reasons:

## Spec compliance — score 0–N
- [ ] <item>

Subtotal: __ / N
Notes:

## Code quality — score each 0–5
- [ ] Clarity: __
- [ ] Conciseness: __
- [ ] Error handling: __
- [ ] Comments: __

Subtotal: __ / 20

## One-line summary

## Verdict
ship-with-cleanup / rewrite / unusable
EOF

cat > "${task_dir}/tests/conftest.py" <<'EOF'
import sys
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
EOF

cat > "${task_dir}/tests/test_placeholder.py" <<'EOF'
def test_placeholder():
    assert True
EOF

cat <<EOF

✓ scaffolded ${task_dir}

next: edit
  - ${task_dir}/PROMPT.md
  - ${task_dir}/SPEC.md
  - ${task_dir}/rubric.md
  - ${task_dir}/JUDGE_PROMPT.md
  - ${task_dir}/JUDGE_RUBRIC.md
  - ${task_dir}/tests/test_*.py
EOF
