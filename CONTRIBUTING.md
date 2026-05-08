# Contributing to open-bench

open-bench is a benchmark harness for coding LLMs. Tasks define the work,
the harness runs every model in the lineup through it, hidden tests gate
the result, models judge each other, and the full artifact set lands in
the repo. The most useful contribution is a new task.

This guide covers:

- [Local setup](#local-setup)
- [Adding a code task in 30 minutes](#adding-a-code-task-in-30-minutes)
- [Running the harness end-to-end](#running-the-harness-end-to-end)
- [PR checklist](#pr-checklist)
- [Code style](#code-style)
- [What's out of scope today](#whats-out-of-scope-today)
- [Where to ask questions](#where-to-ask-questions)

---

## Local setup

```bash
git clone https://github.com/anfocic/open-bench.git
cd open-bench
pip install -e ".[dev]"
python -m pytest bench/scripts/_tests/ -q
```

The install puts seven `bench-*` CLIs on `PATH` (`bench-new-task`,
`bench-start-run`, `bench-capture-run`, `bench-run-all`,
`bench-judgments`, `bench-aggregate`, `bench-perf`). The test suite
should report 144+ passing.

If you want to run against a different config or task tree without
forking, set `OPENBENCH_CONFIG` and `OPENBENCH_TASKS_DIR` to absolute
paths.

---

## Adding a code task in 30 minutes

The path of least resistance is `bench-new-task`:

```bash
bench-new-task my-task
```

That scaffolds `bench/tasks/my-task/` with the six files every code task
needs. Walk through each:

### `task.json`

```json
{
  "task_kind": "code",
  "entrypoint": "<filename>.<ext>",
  "language": "python",
  "test_runner": "pytest",
  "test_invocation": ["python3", "-m", "pytest", "_eval_tests/", "-v", "--tb=short"],
  "loc_method": "non_blank_non_comment_lines"
}
```

`task_kind` is `"code"` for now (the only kind that ships). `entrypoint`
is the single file the model is asked to produce. `loc_method` is one of
`non_blank_non_comment_lines` or `wc_l`.

### `PROMPT.md`

What the model reads first. State the deliverable, the hard constraints,
and the file path. Keep it under ~50 lines — anything longer competes
with `SPEC.md` for the model's attention.

### `SPEC.md`

The contract. Function signatures, expected I/O shapes, edge cases the
model must handle. The judge models read this when scoring spec
compliance, so be explicit. Ambiguity here turns into inter-judge
disagreement later.

### `tests/`

The hidden test suite. The harness copies this dir into the model's
worktree as `_eval_tests/` *after* the model has finished implementing,
then runs `test_invocation` against it. Models never see these tests.

A useful test suite has:

- A "golden path" test that anything resembling a correct
  implementation will pass.
- Boundary tests for every constraint named in `SPEC.md`.
- One or two tests for failure modes the spec explicitly forbids
  (e.g. SPEC says `network="none"` is the default — write a test that
  verifies a model didn't accept `network="host"` silently).

If a test depends on extra setup, put a `conftest.py` next to it. The
worktree's import path includes `_eval_tests/`.

### `JUDGE_PROMPT.md`

What each judge sees when scoring. Tell them the four-key code rubric
(`clarity`, `conciseness`, `error_handling`, `comments`), the spec
compliance scale (0-10), the output schema (`<label>_scores.json` and
`<label>_rubric.md` per implementation). The existing `sandbox` task is
a good template — copy and adapt.

### `JUDGE_RUBRIC.md`

The scoring rubric. Defines what each axis means and what 0/5/10 looks
like. Stable across tasks; usually copy-paste from `sandbox` and tweak.

### `rubric.md`

Operator-facing notes on what the rubric is intended to measure. Not
read by judges; read by humans when reviewing the round.

---

## Running the harness end-to-end

Once your task scaffolding is in place, smoke-test it locally with one
model:

```bash
# implement
bench-start-run my-task <model-name>          # creates a fresh worktree, opens the prompt
# (drive the agent harness manually OR add --auto for opencode)
bench-capture-run my-task <model-name>        # extract diff, run hidden tests, commit artifact

# judge (only meaningful with 2+ implementations)
bench-judgments my-task                       # builds blinded packets per judge
bench-aggregate my-task                       # writes results/reviews/my-task-<date>.md
```

For an end-to-end run across the full lineup, `bench-run-all my-task`.

The engine is provider-agnostic — `--auto` shells out to opencode by
default but the manual flow needs no driver. Replacing opencode with a
different agent harness is a single-module change behind
`bench/scripts/_opencode_run.py`.

---

## PR checklist

Before opening a PR:

- [ ] Tests pass: `python -m pytest bench/scripts/_tests/ -q`
- [ ] If you touched harness code, the snapshot test
      `test_aggregate_judges.py::TestAggregateSnapshot` is still
      byte-identical against the golden fixture (or you regenerated
      the fixture deliberately and explained why in the PR body).
- [ ] One logical change per PR. For multi-step refactors, stack the
      PRs and merge bottom-up.
- [ ] Branch name: `feat/...`, `fix/...`, `docs/...`, `test/...`,
      `refactor/...`. Never push to `main`.
- [ ] Commit messages follow Conventional Commits
      (`feat(bench): ...`, `fix(bench): ...`, `docs: ...`).
- [ ] No AI tool attribution in commits or PR bodies. Commits stand
      on their own.
- [ ] If the change affects user-facing behaviour, add a line to
      `CHANGELOG.md`.

---

## Code style

The repo follows a small set of opinionated rules. Most are enforced
by the existing test suite and review patterns rather than tooling.

- **No comments unless WHY is non-obvious.** Don't write what the
  code does — well-named identifiers do that. Do write comments when
  there's a non-local invariant, a workaround for a specific bug,
  or behaviour that would surprise a reader.
- **No docstrings on self-explanatory functions.** Reserve them for
  the public API of a module (where the constraint or contract isn't
  obvious from the signature).
- **Behaviour preservation in refactors.** When carving code out of
  one module into another, the on-disk artifacts, exit codes, and
  error messages must stay byte-identical. The snapshot test exists
  precisely to catch silent drift.
- **Test before fix.** New behaviour gets a failing test first, then
  the implementation. Bug fixes start with a reproducer test.
- **`logging` over `print`** for status, warnings, errors. `print`
  is reserved for multi-line UX blocks (table output, "next steps"
  guidance) where users expect output regardless of `--quiet`.
- **No emojis** in code, commits, or PR bodies.

---

## What's out of scope today

The following are explicitly not accepted in PRs right now. Most are
deferred to a future version, not rejected on principle.

| Out of scope | Why | When |
|---|---|---|
| New task kinds (`generation`, `choice`, etc.) beyond `code` | The `_kinds/` registry exists but the contract is intentionally not frozen — waiting for a second real consumer to constrain the shape. | After model-royale ships round 2 (reddit user-vote experiment). |
| `TaskKind` Protocol / ABC | Same reason — defer until 2+ implementations force the boundary. | v0.3 most likely. |
| New agent-harness drivers (Claude Code, Aider, Gemini CLI) | The `_opencode_run` module is the only driver today; no Protocol yet. | When a contributor wants to ship a second one and is willing to negotiate the contract. |
| Eval-framework features (custom rubric DSL, judge plugins, dataset loaders) | open-bench is a benchmark, not an eval framework. `inspect_ai`, `promptfoo`, `braintrust` exist for that. | Probably never; the niche is comparative methodology. |
| Cosmetic frontend changes that don't trace to a methodology decision | Frontend follows methodology, not the other way around. | Always — methodology PRs first, frontend reflects them. |

---

## Where to ask questions

- **GitHub Issues** for bugs, broken tasks, missing features.
- **GitHub Discussions** for methodology questions, "is this a good task
  idea" conversations, and anything that needs more than a comment
  thread.
- **Pull request comments** when iterating on an open PR.

There is no Discord or Slack. Empty real-time channels are reverse
social proof; we'll add one when there's a community that would fill it.
