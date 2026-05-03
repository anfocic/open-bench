# perf-bench: deepseek x 5 (2026-05-03)

Model slug: `opencode-go/deepseek-v4-pro`

Runs ok: 5/5


## Per-run

| # | Wall (model) | Envelope | Tokens | Cost USD | Tests | LOC |
|---|---|---|---|---|---|---|
| 1 | 224.9s | 226.5s | 102524 | $0.052266 | 9/9 | 124 |
| 2 | 539.2s | 540.8s | 740863 | $0.104934 | 9/9 | 139 |
| 3 | 221.9s | 223.5s | 160416 | $0.061031 | 9/9 | 98 |
| 4 | 388.8s | 390.4s | 223571 | $0.071365 | 9/9 | 113 |
| 5 | 248.4s | 250.1s | 168391 | $0.055137 | 9/9 | 130 |

## Aggregate

| Metric | Median | Stdev | Min | Max |
|---|---|---|---|---|
| Wall (model) sec | 248.4 | 138.265 | 221.9 | 539.2 |
| Cost USD | 0.061 | 0.021 | — | — |
| Tokens | 168391 | — | — | — |
| LOC | 124 | — | — | — |

Total cost across 5 runs: $0.344733

All runs pass hidden tests: True