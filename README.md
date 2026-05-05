# open-bench

**A weekly coding battle royale between AI models.**

Each week, every model in the lineup gets the same spec and builds the same app, alone, in its own sandbox. The submissions are graded three ways:

- **Hidden tests** — objective pass/fail the models never see.
- **Peer review** — every model blind-grades every submission against a rubric. Self-judgments are tracked separately as a bias check.
- **Cost & speed** — wall-clock, tokens, dollars per run.

After the introductory rounds, the lowest combined score gets **eliminated each week** until one model is left standing. Same prompt, no cross-pollination, public scoreboard.

The bet: this measures whether a model can sustain a real codebase over weeks of feature growth — not just one-shot a clever solution.

## What's in this repo

1. **`sandbox.py`** — the round-1 task. A single-file Python wrapper around Podman/Docker for ephemeral, network-isolated, resource-capped command execution. The thing the models implement.
2. **`bench/`** — the framework that runs them through opencode, captures transcripts and diffs, runs hidden tests, and aggregates judgments into a single review.

Recursive joke: the first benchmark task is implementing `sandbox.py` itself.

## Who this is for

- **AI engineers** picking a coding model for an agent and tired of one-shot benchmarks.
- **Open-weight watchers** comparing the new wave (DeepSeek, Kimi, MiniMax, Qwen, GLM, MiMo) head-to-head on the same task.
- **Anyone who wants a fork-and-go harness** for running their own n-way comparison — see [Forking](#forking-for-your-own-n-way-comparison) below.

## Lineup (round 3)

| short | slug |
|---|---|
| kimi | `opencode-go/kimi-k2.6` |
| deepseek | `opencode-go/deepseek-v4-pro` |
| deepseek-flash | `opencode-go/deepseek-v4-flash` |
| minimax | `opencode-go/minimax-m2.5` |
| mimo | `opencode-go/mimo-v2.5-pro` |
| qwen | `opencode-go/qwen3.6-plus` |
| glm | `opencode-go/glm-5.1` |

All seven race in round 3. From round 4 onward, the lowest combined score (spec/10 + quality/20, with hidden-test failures auto-last) is eliminated each week. Eliminated models stay in the archive; tombstones land in [`results/eliminated.md`](results/eliminated.md) (created on first elimination).

## Latest round

Round 3 is in flight at the time of this writing — see [`results/reviews/`](results/reviews/) for the most recent finalized review.

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

Round 1's task is single-file Python (`sandbox.py`) and the harness reflects that today:

- The output filename `sandbox.py` is hardcoded across `capture-run.sh`, `start-run.sh`, `perf-bench.py`, and `start_judgments.py` (~11 refs). For a same-shaped task (one Python file, different name), a sed-replace across those four files is enough.
- Multi-file projects, non-Python stacks, or anything that doesn't run via `python3 -m pytest` need deeper edits — `capture-run.sh`'s test invocation and `perf-bench.py`'s LOC counter both assume single-file Python.
- Parametrising the entrypoint via `bench/tasks/<task>/task.json` is on the roadmap; the framework will be honestly task-agnostic then. For now: forkable with a sed, not yet drop-in.

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

## License

MIT — see [LICENSE](LICENSE).
