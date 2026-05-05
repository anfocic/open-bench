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

## Read more

- [**ABOUT.md**](ABOUT.md) — how the harness works, how to run it locally, how to fork it for your own n-way comparison, task configuration, layout, limitations.
- [`bench/plans/improvements.md`](bench/plans/improvements.md) — known gaps and planned work.

## License

MIT — see [LICENSE](LICENSE).
