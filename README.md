# open-bench

Three open-weight Chinese models (Kimi K2.6, DeepSeek V4 Pro, MiniMax M2.7) each build their own copy of the same app over multiple weeks — one round per week, every round graded by hidden tests, peer-judged blind, and rubric-scored before the next round extends the spec. Round 1 is `sandbox.py`; later rounds bolt features onto each model's own codebase. Three parallel codebases, identical prompts, no cross-pollination. The bet: which model is the best long-haul solo builder, not just the best one-shot coder.

Two things in one repo:

1. **`sandbox.py`** — single-file Python wrapper around Podman/Docker for ephemeral, network-isolated, resource-capped command execution. The thing the models implement.
2. **`bench/`** — framework that runs them through opencode, captures transcripts and diffs, runs hidden tests, aggregates judgments into a single review.

Recursive joke: the first benchmark task is implementing `sandbox.py` itself.

## Latest round (2026-05-03)

| | kimi-k2.6 | deepseek-v4-pro | minimax-m2.7 |
|---|---|---|---|
| Hidden tests pass-rate (n=5) | 5/5 | 5/5 | 4/5 |
| Spec score (median /10) | 10 | 10 | 7.5 |
| Code quality (median /20) | 16.5 | 19 | 14.5 |
| Cost / run (median) | $0.011 | $0.061 | $0.024 |
| Wall-clock / run (median) | 1m23s | 4m08s | 2m41s |
| Tokens / run (median) | 109k | 168k | 242k |

Total bill for the round (15 perf runs + 6 judging packets): $1.13.

Full review: [`results/reviews/sandbox-2026-05-03.md`](results/reviews/sandbox-2026-05-03.md). Per-run perf data: `results/perf/sandbox-<model>-2026-05-03/`.

## How it works

Drop a spec in `bench/tasks/<task>/SPEC.md`, write `PROMPT.md` (what the model sees), and a hidden test suite (it doesn't). Each model runs through opencode and produces a `sandbox.py`. Implementations are graded by the other implementers — blinded labels, no self-judging. Optional expert tier via `expert_judges` in `bench/config.json`. Output: scoreboard, per-judge ranking, peer-vs-expert delta when configured, inter-judge agreement, hidden-test results.

## Run it

End-to-end (canonical single round):

```bash
bench/scripts/run-all.sh sandbox
```

Per-model perf (n=5 with median + stdev):

```bash
bench/scripts/perf-bench.py sandbox kimi 5
```

One implementer at a time:

```bash
bench/scripts/start-run.sh --auto sandbox kimi   # auto-drive
bench/scripts/capture-run.sh sandbox kimi
```

Cost: ~$1.20 to fully reproduce the latest round. Stdlib + pytest only on the local side; no requirements file.

> **`--auto` runs `opencode run --dangerously-skip-permissions`.** Model has full host filesystem access during the session. Trust your task content.

## Forking for your own three-way comparison

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

Labels become `builds/<label>/` dirs. Add a new task with `bench/scripts/new-task.sh <name>`.

### Forking caveats (read before swapping the task)

Round 1's task is single-file Python (`sandbox.py`) and the harness reflects that today:

- The output filename `sandbox.py` is hardcoded across `capture-run.sh`, `start-run.sh`, `perf-bench.py`, and `start_judgments.py` (~11 refs). For a same-shaped task (one Python file, different name), a sed-replace across those four files is enough.
- Multi-file projects, non-Python stacks, or anything that doesn't run via `python3 -m pytest` need deeper edits — `capture-run.sh`'s test invocation and `perf-bench.py`'s LOC counter both assume single-file Python.
- Parametrising the entrypoint via `bench/tasks/<task>/task.json` is on the roadmap for round 2; the framework will be honestly task-agnostic then. For now: forkable with a sed, not yet drop-in.

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

[opencode]: https://opencode.ai

## License

MIT — see [LICENSE](LICENSE).
