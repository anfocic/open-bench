# perf-bench: minimax x 5 (2026-05-03)

Model slug: `opencode-go/minimax-m2.7`

Runs ok: 5/5


## Per-run

| # | Wall (model) | Envelope | Tokens | Cost USD | Tests | LOC |
|---|---|---|---|---|---|---|
| 1 | 280.8s | 282.4s | 531108 | $0.050611 | 8/9 | 116 |
| 2 | 187.8s | 189.4s | 366898 | $0.035059 | 9/9 | 112 |
| 3 | 136.2s | 137.9s | 241680 | $0.023907 | 9/9 | 124 |
| 4 | 113.0s | 114.6s | 181233 | $0.014986 | 9/9 | 100 |
| 5 | 160.7s | 162.3s | 206729 | $0.021853 | 9/9 | 140 |

## Aggregate

| Metric | Median | Stdev | Min | Max |
|---|---|---|---|---|
| Wall (model) sec | 160.7 | 65.017 | 113.0 | 280.8 |
| Cost USD | 0.024 | 0.014 | — | — |
| Tokens | 241680 | — | — | — |
| LOC | 116 | — | — | — |

Total cost across 5 runs: $0.146416

All runs pass hidden tests: False