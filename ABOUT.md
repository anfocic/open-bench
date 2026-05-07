# About open-bench

Long-form companion to the [README](README.md). Covers what's in the repo, who it's for, how the harness works, how to run it locally, how to fork it for your own lineup, layout, and limitations.

## What's in this repo

1. **`bench/`** — the harness: orchestration (`start_run`, `_opencode`), artifact capture (`capture_run`), scoring (`start_judgments`), aggregation (`aggregate_judges`), and CLI entry points.
2. **`bench/tasks/sandbox/`** — the canonical code-task example: a single-file Python wrapper around Podman/Docker for ephemeral, network-isolated, resource-capped command execution. Ships with the package so `bench-start-run sandbox <model>` works out of the box.

Tournament results, lineup decisions, and per-round writeups live downstream in [Model Royale](https://open-bench.dev/royale), not here. open-bench is the engine; Royale is one consumer.

## Who this is for

- **AI engineers** picking a coding model for an agent and tired of one-shot benchmarks.
- **Researchers** running n-way comparisons across an arbitrary lineup with their own tasks.
- **Anyone who wants a fork-and-go harness** for a private comparison — see [Forking](#forking-for-your-own-n-way-comparison) below.

## How it works

Drop a spec in `bench/tasks/<task>/SPEC.md`, write `PROMPT.md` (what the model sees), and a hidden test suite (it doesn't). Each model runs through opencode and produces its implementation. The task's `task.json` defines the entrypoint filename, test invocation, and LOC counting method — defaults match a single-file Python target. Implementations are graded by every model in the lineup (including itself — self-judgments are surfaced separately as a bias check, not counted in the headline scoreboard). Optional expert tier via `expert_judges` in `bench/config.json`. Output: peer-median scoreboard, per-judge ranking, self-bias delta, inter-judge agreement, hidden-test results.

## Install

```bash
git clone https://github.com/anfocic/open-bench.git
cd open-bench
pip install -e ".[dev]"
```

This puts the `bench-*` console scripts on `PATH`. Requires Python 3.11–3.13 and [opencode] 1.14+ authenticated against the providers in `bench/config.json`.

## Run it

End-to-end (canonical single round):

```bash
JUDGE_CONCURRENCY=3 bench-run-all sandbox
```

Judges run in parallel (cap with `JUDGE_CONCURRENCY` or the `--concurrency` flag on `bench-judgments`); implementer phase is still sequential.

Per-model perf (n=5 with median + stdev):

```bash
bench-perf sandbox kimi 5
```

One implementer at a time:

```bash
bench-start-run --auto sandbox kimi   # auto-drive
bench-capture-run sandbox kimi
```

Multiple samples per model on the same date — set `RUN_STAMP` to disambiguate worktree/branch names:

```bash
RUN_STAMP="$(date +%F)-r2" bench-start-run --auto sandbox kimi
```

Stdlib + pytest only on the local side; no extra runtime dependencies.

> **`--auto` runs `opencode run --dangerously-skip-permissions`.** Model has full host filesystem access during the session. Trust your task content.

## Forking for your own n-way comparison

Edit `bench/config.json`:

```json
{
  "implementers": ["a", "b", "c"],
  "expert_judges": [],
  "harness": "opencode",
  "slugs": {
    "a": "opencode-go/<provider-model-id>",
    "b": "opencode-go/<provider-model-id>",
    "c": "opencode-go/<provider-model-id>"
  }
}
```

Labels become `builds/<label>/` dirs. Add a new task with `bench-new-task <name>`. Discover provider slugs with `opencode models <provider>`.

### Pointing the harness at a different tree

Two env vars override where the harness looks for config and tasks:

| Env var | Default | Purpose |
|---|---|---|
| `OPENBENCH_CONFIG` | `<repo_root>/bench/config.json` | The implementer / judge / slug config. |
| `OPENBENCH_TASKS_DIR` | `<repo_root>/bench/tasks` | Directory holding task definitions. Tasks are resolved as `<dir>/<task-name>/`. |

Both expand `~` and accept absolute or relative paths. With these set, a downstream consumer (e.g. a sibling `royale/` tree) can drive `bench-*` CLIs against its own config + tasks without forking the harness:

```bash
OPENBENCH_CONFIG=royale/config.json \
  OPENBENCH_TASKS_DIR=royale/tasks \
  bench-run-all reddit-vote
```

### Task configuration

Each task directory (`bench/tasks/<task>/`) can optionally contain a `task.json` that defines:

| Field | Default | Purpose |
|---|---|---|
| `entrypoint` | `sandbox.py` | Filename the model produces |
| `language` | `python` | Informational; drives test-runner defaults |
| `test_runner` | `pytest` | String id for messaging |
| `test_invocation` | `["python3", "-m", "pytest", "_eval_tests/", "-v", "--tb=short"]` | Argv to run hidden tests |
| `loc_method` | `non_blank_non_comment_lines` | How to count implementation lines |

If `task.json` is absent, the defaults assume a single-file Python target with pytest. To add a different task, run `bench-new-task <name>` and edit the generated `task.json` to set the entrypoint and test invocation.

## Layout

```
bench/
├── tasks/<task>/         # SPEC.md, PROMPT.md, hidden tests/, judge rubric
├── scripts/              # start_run, capture_run, perf_bench, aggregate_judges
└── config.json           # implementers, judges, harness, model slugs

builds/                   # the apps themselves — one per model
└── <model>/
    ├── <entrypoint>      # latest captured impl (filename from task.json)
    └── rounds/
        └── <task>-<date>/  # round archive: impl, diff, transcript, tests, meta

results/
├── reviews/              # aggregated multi-judge reviews (auto-generated)
├── perf/                 # n=5 perf runs (median + stdev per model)
└── judgments/            # per-judge packets (gitignored)
```

## Limitations

- v0.1 ships one task kind (code, ~100-LOC scale on the example). Generation/choice land in v0.2 — see [`PLAN_V0_2.md`](PLAN_V0_2.md).
- Harness-locked to opencode for both implementers and judges. Provider abstractions are v1.0 work.
- n=5 perf is the floor where median means anything; stdev with n=5 is itself noisy.
- A different judge panel would likely produce a different consensus. Inter-judge variance is reported in each review.
- Self-judging is included for bias measurement but excluded from headline medians. The peer-blind scoreboard remains the canonical signal.

[opencode]: https://opencode.ai
