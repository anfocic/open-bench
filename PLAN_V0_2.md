# open-bench v0.2 — Decoupling Plan

Goal: break the harness's coupling to the code-task shape so contributors can
run their own task kinds (text generation, multiple choice, classification,
human-vote evaluation) without forking the codebase.

Driver: round 2 (reddit user-vote experiment) is a different evaluation
modality than round 1, and the harness as built only fits code-task shape.

## Sequencing (do not invert)

1. Ship round 2 reddit experiment as a **separate pipeline** first. Reuses
   the model-invocation parts of the harness (worktrees, opencode runs,
   parallel orchestration) but runs its own capture/scoring code. Goal: a
   working second use case end-to-end.
2. After (1) works, extract the shared orchestration core out of
   `start_run.py` / `_opencode.py`.
3. Refactor `CodeTask` and `GenerationTask` from the now-two real
   implementations — driven by code, not speculation.
4. Publish v0.2 with the plugin interface and a "writing a task kind" doc.

Doing the abstraction before round 2 = guessing at the right plugin shape.
Two real implementations is the minimum honest input to plugin design.

## Architecture

The split already exists in the code — formalize it.

| Layer | Today | Task-agnostic? |
|---|---|---|
| Orchestration | `start_run.py`, `_opencode.py`, `run_all.py` | Yes (largely) |
| Artifact extraction | `capture_run.py` (`*.py` copy, hidden tests, LOC) | No — code-specific |
| Scoring | `start_judgments.py` (code judges) | No — code-specific |
| Aggregation | `aggregate_judges.py` (rubric, self-bias) | Partial — stats generic, schema code |

## Plugin Interface

```python
class TaskKind(Protocol):
    def prepare_workspace(self, worktree: Path, task_dir: Path) -> None: ...
    def extract_artifact(self, worktree: Path, run_dir: Path) -> dict: ...
    def score(self, run_dir: Path, judges: list[str]) -> dict: ...
    def aggregate(self, run_dirs: list[Path]) -> dict: ...
```

Built-in kinds shipped with v0.2:

- `code` — current behavior (entrypoint + pytest + LOC + code-judge rubric)
- `generation` — text artifact + LLM-judge on prompt-defined rubric. Covers
  reddit-vote, translation, summarization, math word problems.
- `choice` — multiple-choice / classification, accuracy only.

`task.json` gets `task_kind: code | generation | choice`. `_task.load()`
resolves to the right plugin instance.

## Work breakdown

| File | Change | Effort |
|---|---|---|
| `bench/scripts/_task.py` | add `kind` field, return plugin instance | 30 min |
| `bench/scripts/_kinds/__init__.py` | registry, `task_kind` → plugin lookup | 30 min |
| `bench/scripts/_kinds/code.py` | extract current code-task logic into plugin | 4h |
| `bench/scripts/_kinds/generation.py` | new — text artifact + LLM judge | 3h |
| `bench/scripts/_kinds/choice.py` | new — accuracy-only | 1h |
| `bench/scripts/capture_run.py` | delegate `extract_artifact` to plugin | 2h |
| `bench/scripts/start_judgments.py` | delegate `score` to plugin | 2h |
| `bench/scripts/aggregate_judges.py` | split into generic stats + code-rubric rendering (691 LOC — biggest job) | 3h |
| `docs/task_kinds.md` | external-contributor onboarding | 1h |
| `bench/scripts/_tests/test_kinds_*.py` | unit tests per kind | 2h |

Total: ~19h focused.

## Round-2-driven prerequisite work (before plugin extraction)

These get done *for round 2 itself*, then become inputs to the plugin design:

- [ ] Generation pipeline that produces text artifacts from each model on a
      shared prompt (reuse `_opencode.py` runner). Output: `answer.md` per
      `(model, run)`.
- [ ] Vote-collection schema: how reddit votes get ingested. JSON file?
      One row per (post_id, model_label, vote_count, total_votes, blinded)?
- [ ] Blinding workflow: randomized A/B/C/D labels per post, mapping stored
      out-of-band; reveal happens post-vote.
- [ ] Aggregation script for vote data — separate from `aggregate_judges`
      for now, will inform `GenerationTask.aggregate` later.
- [ ] Decide whether reddit votes are sole signal or pair with judge models
      (recommendation in chat: pair, don't replace — secondary "human
      preference" column).

## Decoupling sub-tasks (post round-2)

- [ ] Carve `CodeTask` out of `capture_run.py`. The pathspec/diff/copy logic
      (lines 161-180 today) and the hidden-test capture (`_run_hidden_tests`)
      both belong on `CodeTask`. `capture()` becomes:
      `kind = _task.kind_for(task); kind.extract_artifact(worktree, run_dir)`.
- [ ] Carve scoring out of `start_judgments.py`. The blinded `implementations/`
      dir + the rubric prompt are code-task choices, not framework choices.
- [ ] Split `aggregate_judges.py`:
    - `_stats.py` already has the math; move more in (mean, stddev, paired diff)
    - `_kinds/code.py` owns code-rubric tables, self-bias-on-code-quality
    - `aggregate_judges` becomes orchestrator that calls
      `kind.aggregate(run_dirs)` and renders.
- [ ] Verify `_tests/` still passes after each carve-out (regression budget:
      zero — every existing test must keep passing on `task_kind: code`).

## Risks / things to watch

- **Premature abstraction.** Designing `GenerationTask` against one example
  (reddit) bakes reddit's quirks into the interface. Mitigation: build round
  2 as a non-plugin pipeline first, then extract.
- **Aggregation is the hard part.** `aggregate_judges.py` is 691 LOC and
  conflates statistics, rendering, and code-rubric semantics. Splitting it
  cleanly takes more than the listed 3h if the rubric parts turn out to be
  more entangled than they look. Budget contingency.
- **Backwards compat.** v0.1.x `task.json` files lack `task_kind`. Default
  to `code` when absent — round-1 behavior must stay byte-identical.
- **`task.json` schema validation.** Add validator at this point too;
  contributors will produce malformed configs.

## Roadmap beyond v0.2

v0.2 is the "pluggable task kinds" milestone — runnable by Python users who
want to add their own task kind on top of opencode. It is not the finish
line for "anybody downloads and uses it."

### Usability ceiling per version

| User intent | v0.1 (now) | v0.2 (post-decoupling) | v1.0 (target) |
|---|---|---|---|
| Reproduce existing rounds | Yes | Yes | Yes |
| Add new code task (config only) | Yes | Yes | Yes |
| Add generation / choice task | No | Yes | Yes |
| Use providers other than opencode for impl runs | Edge cases | Edge cases | Yes (first-class) |
| Use judges other than opencode | No | No | Yes |
| Run on shared infra / CI / multi-machine | No | No | Yes |
| Run without opencode installed | No | No | Yes |
| Define new task kinds without writing Python (config only) | No | No | Yes (common cases) |
| Install from PyPI with tagged releases | No (`-e` from clone) | No | Yes |

### v1.0 work (post-v0.2)

| Workstream | Why | Rough effort |
|---|---|---|
| `Runner` protocol — `OpencodeRunner`, `AnthropicRunner`, `OpenAIRunner` impls. Decouple impl runs from opencode session files. | Most users won't have opencode; direct API access is more portable | 12-16h |
| `Judge` protocol — same shape, decouple judge layer from `_opencode.py` | Lets users mix judge providers, run cheaper/faster judges | 6-8h |
| `RunStore` protocol — local-fs impl, S3 impl optional. Drop hardcoded `../eval-{slug}` worktree path. | Multi-machine + CI requires shared storage. Currently every path assumes one machine. | 8-10h |
| Config-only task kinds for common cases — declarative `task.json` schemas for "generation with rubric X", "choice with answer key Y", so non-Python users can author tasks | Lowers contributor floor from "Python developer" to "JSON author" | 6h |
| PyPI publish + tagged releases + version policy | Real installer story | 2h once, 30 min per release |
| Docs: README rewrite, task-author guide, contributing, troubleshooting, provider setup | "Anybody downloads and uses it" requires onboarding that doesn't depend on reading source | 8-12h |
| Examples directory: 3+ task kinds with full configs, end-to-end | Copy-paste beats docs for first-touch | 4h |

Total v1.0: ~50-60h beyond v0.2.

### Public framing

When publishing v0.2, surface the roadmap in README so contributors know
what's coming and don't open issues that v1.0 covers:

> v0.2 = pluggable task kinds. v1.0 = provider-agnostic, multi-machine,
> docs-first. Track progress in PLAN_V0_2.md.

This sets expectations and deflects "why no X provider" / "how do I run
this on Y infra" issues until v1.0.

## Out of scope for v0.2

Still deferred from senior review (LOW priority, gated on real triggers):

- `perf_bench.py` end-to-end test (needs session/git mocking infra)
- `aggregate_judges.render_self_bias_check` 2x call dedup (perf)
- Subprocess error-handling consistency (1h, defer until a confusing error)
- Hardcoded `../eval-{slug}` worktree path (defer until non-writable parent dir)
- `start_judgments._drive_one_judge` non-deterministic exit code (docs only)

Storage abstraction (`RunStore` protocol with local-fs impl), provider
abstraction for judges (currently opencode-only), and run dedup /
resumability are also deferred — they pay off at scale you don't have yet.

## Pre-publish checklist (v0.1.1, separate from v0.2)

Worth doing before going public regardless of v0.2 timeline:

- [ ] README quickstart: `pip install` → `bench-start-run sandbox kimi` →
      expected output. First-touch friction is the #1 reason public
      releases fail to convert lookers into users.
- [ ] Pin Python version + opencode version in `pyproject.toml`. Avoid
      "works on my machine" reports.
- [ ] One paragraph in README on what *isn't* there yet (single task,
      opencode-only judges, single-machine assumption). Sets expectations,
      deflects "why no X" issues.
- [ ] Tag `v0.1.1` after PR #42 merges. Versioned baseline for round 2.
