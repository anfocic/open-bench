# About open-bench

This is the long-form companion to the [README](README.md). It covers what's in the repo, who it's for, how the harness works, how to run it locally, how to fork it, layout, and limitations.

## What's in this repo

1. **`sandbox.py`** — the round-1 task. A single-file Python wrapper around Podman/Docker for ephemeral, network-isolated, resource-capped command execution. The thing the models implement.
2. **`bench/`** — the framework that runs them through opencode, captures transcripts and diffs, runs hidden tests, and aggregates judgments into a single review.

Recursive joke: the first benchmark task is implementing `sandbox.py` itself.

## Who this is for

- **AI engineers** picking a coding model for an agent and tired of one-shot benchmarks.
- **Open-weight watchers** comparing the new wave (DeepSeek, Kimi, MiniMax, Qwen, GLM, MiMo) head-to-head on the same task.
- **Anyone who wants a fork-and-go harness** for running their own n-way comparison — see [Forking](#forking-for-your-own-n-way-comparison) below.

## How it works

Drop a spec in `bench/tasks/<task>/SPEC.md`, write `PROMPT.md` (what the model sees), and a hidden test suite (it doesn't). Each model runs through opencode and produces a `sandbox.py`. Implementations are graded by every model in the lineup (including itself — self-judgments are surfaced separately as a bias check, not counted in the headline scoreboard). Optional expert tier via `expert_judges` in `bench/config.json`. Output: peer-median scoreboard, per-judge ranking, self-bias delta, inter-judge agreement, hidden-test results.

## Run it

End-to-end (canonical single round):

```bash
JUDGE_CONCURRENCY=3 bench/scripts/run-all.sh sandbox
```

Judges run in parallel (cap with `JUDGE_CONCURRENCY` or the `--concurrency` flag on `start_judgments.py`); implementer phase is still sequential.

Per-model perf (n=5 with median + stdev):

```bash
bench/scripts/perf-bench.py sandbox kimi 5
```

One implementer at a time:

```bash
bench/scripts/start-run.sh --auto sandbox kimi   # auto-drive
bench/scripts/capture-run.sh sandbox kimi
```

Multiple samples per model on the same date — set `RUN_STAMP` to disambiguate worktree/branch names:

```bash
RUN_STAMP="$(date +%F)-r2" bench/scripts/start-run.sh --auto sandbox kimi
```

Stdlib + pytest only on the local side; no requirements file.

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

Labels become `builds/<label>/` dirs. Add a new task with `bench/scripts/new-task.sh <name>`. Discover provider slugs with `opencode models <provider>`.

### Forking caveats (read before swapping the task)

The current task is single-file Python (`sandbox.py`) and the harness reflects that today:

- The output filename `sandbox.py` is hardcoded across `capture-run.sh`, `start-run.sh`, `perf-bench.py`, and `start_judgments.py` (~11 refs). For a same-shaped task (one Python file, different name), a sed-replace across those four files is enough.
- Multi-file projects, non-Python stacks, or anything that doesn't run via `python3 -m pytest` need deeper edits — `capture-run.sh`'s test invocation and `perf-bench.py`'s LOC counter both assume single-file Python.
- Parametrising the entrypoint via `bench/tasks/<task>/task.json` is on the roadmap; the framework will be honestly task-agnostic then. For now: forkable with a sed, not yet drop-in. See [`bench/plans/improvements.md`](bench/plans/improvements.md).

## Layout

```
bench/
├── tasks/<task>/         # SPEC.md, PROMPT.md, hidden tests/, judge rubric
├── scripts/              # start-run, capture-run, perf-bench, aggregate_judges
└── config.json           # implementers, judges, harness, model slugs

builds/                   # the apps themselves — one per model
└── <model>/
    ├── sandbox.py        # latest captured impl
    └── rounds/
        └── <task>-<date>/  # round archive: impl, diff, transcript, tests, meta

results/
├── reviews/              # aggregated multi-judge reviews (auto-generated)
├── perf/                 # n=5 perf runs (median + stdev per model)
└── judgments/            # per-judge packets (gitignored)
```

## Limitations

- One ~100-LOC task; standard contract-following territory, not novel reasoning.
- Harness-locked to opencode. Different harness changes the numbers.
- n=5 perf is the floor where median means anything; stdev with n=5 is itself noisy.
- A different judge panel would likely produce a different consensus. Inter-judge variance is reported in each review.
- Self-judging is included for bias measurement but excluded from headline medians. The peer-blind scoreboard remains the canonical signal.

[opencode]: https://opencode.ai
