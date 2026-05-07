# open-bench

**A weekly coding battle royale between AI models.**

Each week, every model in the lineup gets the same spec and builds the same app, alone, in its own sandbox. The submissions are graded three ways:

- **Hidden tests** — objective pass/fail the models never see.
- **Peer review** — every model blind-grades every submission against a rubric. Self-judgments are tracked separately as a bias check.
- **Cost & speed** — wall-clock, tokens, dollars per run.

Rounds 1 and 2 are baseline runs — everyone plays both, on the same prompt extended slightly between rounds, so the round-1 result isn't a fluke before anyone is cut. From round 3 onward, the lowest combined score gets **eliminated each week** until one model is left standing. Same prompt within a round, no cross-pollination, public scoreboard.

The bet: this measures whether a model can sustain a real codebase over weeks of feature growth — not just one-shot a clever solution.

## Lineup (round 1)

| short | slug |
|---|---|
| kimi | `opencode-go/kimi-k2.6` |
| deepseek | `opencode-go/deepseek-v4-pro` |
| deepseek-flash | `opencode-go/deepseek-v4-flash` |
| minimax | `opencode-go/minimax-m2.5` |
| mimo | `opencode-go/mimo-v2.5-pro` |
| qwen | `opencode-go/qwen3.6-plus` |
| glm | `opencode-go/glm-5.1` |

All seven race in rounds 1 and 2 (the baseline). From round 3 onward, the lowest combined score (spec/10 + quality/20, with hidden-test failures auto-last) is eliminated each week. Eliminated models stay in the archive; tombstones land in [`results/eliminated.md`](results/eliminated.md) (created on first elimination).

## Latest round

The most recent finalized scoreboard lives at [`results/reviews/`](results/reviews/) — one file per round, named `sandbox-<date>.md`. The latest of those is the canonical answer.

## Previous rounds

| Round | Date | Review | Champion (spec / quality) |
|---|---|---|---|
| 1 | 2026-05-05 | [sandbox-2026-05-05.md](results/reviews/sandbox-2026-05-05.md) | kimi (9.5 / 18.5) |

Updated when each round's review lands. Per-run artifacts (transcripts, diffs, meta.json) live alongside under [`builds/<model>/rounds/`](builds/).

## Quickstart

Requires Python 3.11–3.13 and [opencode] (tested against 1.14.x). Authenticate opencode against your providers first (`opencode auth login`).

```bash
git clone https://github.com/anfocic/open-bench.git
cd open-bench
pip install -e ".[dev]"

bench-start-run --auto sandbox kimi   # one model, one round
bench-capture-run sandbox kimi        # extract artifacts + run hidden tests
bench-run-all sandbox                 # full round across the lineup
```

Outputs land in `builds/<model>/rounds/` and `results/reviews/`. See [ABOUT.md](ABOUT.md) for the full pipeline, task configuration, and forking guide.

## What's not here yet

v0.1 is a single-task, opencode-only, single-machine harness. Specifically:

- One task kind (code; entrypoint + pytest + LOC). Generation/choice tasks land in v0.2 — see [`PLAN_V0_2.md`](PLAN_V0_2.md).
- Implementer + judge runs both go through opencode. No first-class Anthropic/OpenAI providers yet.
- Worktrees and run artifacts assume one machine; no shared storage / CI mode.
- Installs from a clone (`pip install -e .`); no PyPI release yet.

If those gaps block you, file an issue — the v1.0 roadmap in `PLAN_V0_2.md` covers them.

## Read more

- [**ABOUT.md**](ABOUT.md) — how the harness works, how to run it locally, how to fork it for your own n-way comparison, task configuration, layout, limitations.
- [`PLAN_V0_2.md`](PLAN_V0_2.md) — decoupling roadmap (pluggable task kinds, provider abstractions).
- [`bench/plans/improvements.md`](bench/plans/improvements.md) — known gaps and planned work.

## License

MIT — see [LICENSE](LICENSE).
