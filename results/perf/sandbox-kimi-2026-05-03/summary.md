# perf-bench: kimi x 5 (2026-05-03)

Model slug: `opencode-go/kimi-k2.6`

Runs ok: 5/5


## Per-run

| # | Wall (model) | Envelope | Tokens | Cost USD | Tests | LOC |
|---|---|---|---|---|---|---|
| 1 | 153.5s | 155.0s | 111241 | $0.012741 | 9/9 | 134 |
| 2 | 66.8s | 68.4s | 91856 | $0.009376 | 9/9 | 116 |
| 3 | 43.8s | 45.5s | 75242 | $0.010523 | 9/9 | 107 |
| 4 | 309.7s | 311.3s | 193208 | $0.031054 | 9/9 | 146 |
| 5 | 83.1s | 84.7s | 109400 | $0.010917 | 9/9 | 128 |

## Aggregate

| Metric | Median | Stdev | Min | Max |
|---|---|---|---|---|
| Wall (model) sec | 83.1 | 107.772 | 43.8 | 309.7 |
| Cost USD | 0.011 | 0.009 | — | — |
| Tokens | 109400 | — | — | — |
| LOC | 128 | — | — | — |

Total cost across 5 runs: $0.074611

All runs pass hidden tests: True