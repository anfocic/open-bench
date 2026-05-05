#!/usr/bin/env python3
"""new_task.py <task-name>

Scaffold a new task under bench/tasks/<task-name>/ with placeholder files,
including a task.json with sensible defaults.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(
    __import__("subprocess").check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True
    ).strip()
)


PROMPT_TEMPLATE = """\
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
"""

SPEC_TEMPLATE = """\
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
"""

RUBRIC_TEMPLATE = """\
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
"""

JUDGE_PROMPT_TEMPLATE = """\
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
"""

JUDGE_RUBRIC_TEMPLATE = """\
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
"""

CONFTEST_TEMPLATE = """\
import sys
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
"""

PLACEHOLDER_TEST_TEMPLATE = """\
def test_placeholder():
    assert True
"""

TASK_JSON_TEMPLATE = {
    "entrypoint": "<filename>.py",
    "language": "python",
    "test_runner": "pytest",
    "test_invocation": ["python3", "-m", "pytest", "_eval_tests/", "-v", "--tb=short"],
    "loc_method": "non_blank_non_comment_lines",
}


def main() -> int:
    p = argparse.ArgumentParser(description="Scaffold a new bench task.")
    p.add_argument("name", help="task name (directory under bench/tasks/)")
    args = p.parse_args()

    task_dir = REPO_ROOT / "bench" / "tasks" / args.name
    if task_dir.exists():
        print(f"error: {task_dir} already exists", file=sys.stderr)
        return 1

    tests_dir = task_dir / "tests"
    tests_dir.mkdir(parents=True)

    (task_dir / "PROMPT.md").write_text(PROMPT_TEMPLATE)
    (task_dir / "SPEC.md").write_text(SPEC_TEMPLATE)
    (task_dir / "rubric.md").write_text(RUBRIC_TEMPLATE)
    (task_dir / "JUDGE_PROMPT.md").write_text(JUDGE_PROMPT_TEMPLATE)
    (task_dir / "JUDGE_RUBRIC.md").write_text(JUDGE_RUBRIC_TEMPLATE)
    (task_dir / "task.json").write_text(json.dumps(TASK_JSON_TEMPLATE, indent=2) + "\n")
    (tests_dir / "conftest.py").write_text(CONFTEST_TEMPLATE)
    (tests_dir / "test_placeholder.py").write_text(PLACEHOLDER_TEST_TEMPLATE)

    print()
    print(f"✓ scaffolded {task_dir}")
    print()
    print("next: edit")
    print(f"  - {task_dir}/PROMPT.md")
    print(f"  - {task_dir}/SPEC.md")
    print(f"  - {task_dir}/task.json  (set entrypoint filename)")
    print(f"  - {task_dir}/rubric.md")
    print(f"  - {task_dir}/JUDGE_PROMPT.md")
    print(f"  - {task_dir}/JUDGE_RUBRIC.md")
    print(f"  - {task_dir}/tests/test_*.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())