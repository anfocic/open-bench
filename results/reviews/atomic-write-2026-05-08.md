# Review: atomic-write (2026-05-08)

Multi-judge blind review of 7 implementations. Each implementation was scored by 0 expert judges (—) and the 7 peer models that didn't produce it. Judges saw only the code + spec, not the hidden test results — those come from each run's `test-output.txt` and are shown separately as objective signal.

Judgment dir: `results/judgments/atomic-write-2026-05-08/`

> **Note:** 1 judge has not yet produced output: kimi. Tables below show partial data; re-run `bench/scripts/aggregate_judges.py atomic-write` once outputs land.

## Scoreboard

Three medians shown so reader can compare expert vs peer consensus. Hidden test results are objective (pulled from each run's `test-output.txt`) and shown alongside for triangulation.

| Impl | Hard-fail | Spec — all | Spec — expert | Spec — peer | Quality — all | Quality — expert | Quality — peer | Tests | Verdict (mode) |
|---|---|---|---|---|---|---|---|---|---|
| deepseek | pass | 9 | — | 9 | 14 | — | 14 | 12/12 | ship-with-cleanup |
| deepseek-flash | pass | 8 | — | 8 | 13 | — | 13 | 12/12 | ship-with-cleanup |
| glm | pass | 9 | — | 9 | 12 | — | 12 | 12/12 | ship-with-cleanup |
| kimi | pass | 10 | — | 10 | 14 | — | 14 | 12/12 | ship-with-cleanup |
| mimo | pass | 10 | — | 10 | 19 | — | 19 | 12/12 | ship-with-cleanup |
| minimax | pass | 9 | — | 9 | 15 | — | 15 | 12/12 | ship-with-cleanup |
| qwen | pass | 9 | — | 9 | 15 | — | 15 | 12/12 | ship-with-cleanup |

## Per-judge ranking by spec compliance

How each judge ranked the implementations (highest spec score first). If a judge gave equal scores, ordering is alphabetical.

| Judge | 1st | 2nd | 3rd |
|---|---|---|---|
| deepseek | deepseek (10) | kimi (10) | mimo (10) |
| deepseek-flash | glm (10) | kimi (10) | mimo (10) |
| glm | deepseek-flash (10) | glm (10) | mimo (10) |
| kimi | — | — | — |
| mimo | glm (9) | kimi (9) | mimo (9) |
| minimax | deepseek (10) | deepseek-flash (10) | glm (10) |
| qwen | deepseek (10) | kimi (10) | mimo (10) |

## Self-bias check

Δ = `self − peer median`. Positive = the model scored its own code higher than peers did (overrating itself). Self-judgments are excluded from the headline scoreboard above so the medians there are not self-inflated.

| Impl | Self spec | Peer med spec | Δ spec | Self qual | Peer med qual | Δ qual |
|---|---|---|---|---|---|---|
| deepseek | 10 | 9 | 1 | 14 | 14 | 0 |
| deepseek-flash | 9 | 8 | 1 | 15 | 13 | 2 |
| glm | 10 | 9 | 1 | 12 | 12 | 0 |
| kimi | — | 10 | — | — | 14 | — |
| mimo | 9 | 10 | -1 | 17 | 19 | -2 |
| minimax | 10 | 9 | 1 | 16 | 15 | 1 |
| qwen | 9 | 9 | 0 | 16 | 15 | 1 |

## Inter-judge agreement

Spec-score variance across judges per implementation. High range = judges disagreed on the same code. Worth investigating.

| Impl | Min spec | Max spec | Range | Stdev | Judges who scored |
|---|---|---|---|---|---|
| deepseek | 8 | 10 | 2 | 0.82 | deepseek, deepseek-flash, glm, mimo, minimax, qwen |
| deepseek-flash | 7 | 10 | 3 | 1.21 | deepseek, deepseek-flash, glm, mimo, minimax, qwen |
| glm | 9 | 10 | 1 | 0.55 | deepseek, deepseek-flash, glm, mimo, minimax, qwen |
| kimi | 9 | 10 | 1 | 0.52 | deepseek, deepseek-flash, glm, mimo, minimax, qwen |
| mimo | 9 | 10 | 1 | 0.41 | deepseek, deepseek-flash, glm, mimo, minimax, qwen |
| minimax | 8 | 10 | 2 | 0.82 | deepseek, deepseek-flash, glm, mimo, minimax, qwen |
| qwen | 7 | 9 | 2 | 0.82 | deepseek, deepseek-flash, glm, mimo, minimax, qwen |

**Best impl per judge:**

- **deepseek** — chosen best by: deepseek, minimax, qwen
- **deepseek-flash** — chosen best by: glm
- **glm** — chosen best by: deepseek-flash, mimo

## Per-implementation detail

### deepseek

Run: `builds/deepseek/rounds/atomic-write-2026-05-08`

| Judge | Tier | Hard-fail | Spec /10 | Quality /20 | Verdict | Note |
|---|---|---|---|---|---|---|
| deepseek | self | pass | 10 | 14 | ship-with-cleanup | Lean and correct: minimal code that hits every spec requirement, but bare wit... |
| deepseek-flash | peer | pass | 9 | 15 | ship-with-cleanup | Minimal and mostly correct implementation, concise but lacking comments and w... |
| glm | peer | pass | 9 | 12 | ship-with-cleanup | Shortest and most direct implementation; passes all hard-fails but uses full ... |
| kimi | peer | (no scores file) | — | — | — | — |
| mimo | peer | pass | 8 | 14 | ship-with-cleanup | Most concise implementation with clean structure — except Exception instead o... |
| minimax | peer | pass | 10 | 14 | ship-with-cleanup | Minimal, correct implementation. No comments. May be missing explicit FileNot... |
| qwen | peer | pass | 10 | 14 | ship-with-cleanup | Fully spec-compliant with explicit error checks and correct fsync ordering, b... |

**Hidden test results** (objective):

- `test_bytes_basic_write` — PASSED
- `test_cli_stdin_to_path` — PASSED
- `test_concurrent_writers_no_corruption` — PASSED
- `test_missing_parent_raises_filenotfound` — PASSED
- `test_mode_applied_when_set` — PASSED
- `test_mode_preserved_when_none_and_target_exists` — PASSED
- `test_no_tmp_residue_on_open_failure` — PASSED
- `test_no_tmp_residue_on_success` — PASSED
- `test_path_is_directory_raises` — PASSED
- `test_replaces_existing` — PASSED
- `test_symlink_writes_to_target` — PASSED
- `test_text_basic_write` — PASSED

### deepseek-flash

Run: `builds/deepseek-flash/rounds/atomic-write-2026-05-08`

| Judge | Tier | Hard-fail | Spec /10 | Quality /20 | Verdict | Note |
|---|---|---|---|---|---|---|
| deepseek | peer | pass | 8 | 13 | ship-with-cleanup | Functional but bare: lacks explicit exception guards for SPEC-mandated error ... |
| deepseek-flash | self | pass | 9 | 15 | ship-with-cleanup | Minimal and correct implementation, hurt only by a missing IsADirectoryError ... |
| glm | peer | pass | 10 | 12 | ship-with-cleanup | Correct spec-compliant implementation with proper mode handling before replac... |
| kimi | peer | (no scores file) | — | — | — | — |
| mimo | peer | pass | 7 | 15 | ship-with-cleanup | Minimal, correct implementation with proper fsync and cleanup — missing IsADi... |
| minimax | peer | pass | 10 | 16 | ship-with-cleanup | Robust atomic write implementation with proper fsync, temp-in-same-dir, and m... |
| qwen | peer | pass | 8 | 13 | ship-with-cleanup | Solid atomic write with correct fsync ordering and thorough cleanup, but lack... |

**Hidden test results** (objective):

- `test_bytes_basic_write` — PASSED
- `test_cli_stdin_to_path` — PASSED
- `test_concurrent_writers_no_corruption` — PASSED
- `test_missing_parent_raises_filenotfound` — PASSED
- `test_mode_applied_when_set` — PASSED
- `test_mode_preserved_when_none_and_target_exists` — PASSED
- `test_no_tmp_residue_on_open_failure` — PASSED
- `test_no_tmp_residue_on_success` — PASSED
- `test_path_is_directory_raises` — PASSED
- `test_replaces_existing` — PASSED
- `test_symlink_writes_to_target` — PASSED
- `test_text_basic_write` — PASSED

### glm

Run: `builds/glm/rounds/atomic-write-2026-05-08`

| Judge | Tier | Hard-fail | Spec /10 | Quality /20 | Verdict | Note |
|---|---|---|---|---|---|---|
| deepseek | peer | pass | 9 | 12 | ship-with-cleanup | Functional but muddled: encoding-sentinel dispatch is fragile, nested excepti... |
| deepseek-flash | peer | pass | 10 | 12 | ship-with-cleanup | Functionally correct but has a latent double-close bug in the error handling ... |
| glm | self | pass | 10 | 12 | ship-with-cleanup | Solid spec-compliant implementation with correct mode handling and full durab... |
| kimi | peer | (no scores file) | — | — | — | — |
| mimo | peer | pass | 9 | 14 | ship-with-cleanup | Elegant encoding-parameter pattern avoids code duplication — solid error hand... |
| minimax | peer | pass | 10 | 14 | ship-with-cleanup | Functional implementation with correct fsync and mode handling. No explanator... |
| qwen | peer | pass | 9 | 11 | ship-with-cleanup | Spec-compliant except for missing FileNotFoundError, but the encoding-as-disc... |

**Hidden test results** (objective):

- `test_bytes_basic_write` — PASSED
- `test_cli_stdin_to_path` — PASSED
- `test_concurrent_writers_no_corruption` — PASSED
- `test_missing_parent_raises_filenotfound` — PASSED
- `test_mode_applied_when_set` — PASSED
- `test_mode_preserved_when_none_and_target_exists` — PASSED
- `test_no_tmp_residue_on_open_failure` — PASSED
- `test_no_tmp_residue_on_success` — PASSED
- `test_path_is_directory_raises` — PASSED
- `test_replaces_existing` — PASSED
- `test_symlink_writes_to_target` — PASSED
- `test_text_basic_write` — PASSED

### kimi

Run: `builds/kimi/rounds/atomic-write-2026-05-08`

| Judge | Tier | Hard-fail | Spec /10 | Quality /20 | Verdict | Note |
|---|---|---|---|---|---|---|
| deepseek | peer | pass | 10 | 13 | ship-with-cleanup | Best exception specificity with proper errno codes and strerror messages, but... |
| deepseek-flash | peer | pass | 10 | 15 | ship-with-cleanup | Correct implementation with good structure but lacks explanatory comments for... |
| glm | peer | pass | 9 | 12 | ship-with-cleanup | Professionally structured with errno-based exceptions and O_EXCL atomic creat... |
| kimi | self | (no scores file) | — | — | — | — |
| mimo | peer | pass | 9 | 15 | ship-with-cleanup | Robust implementation with explicit error checks and UUID-based temp files — ... |
| minimax | peer | pass | 10 | 15 | ship-with-cleanup | Solid implementation with proper errno-based exceptions and UUID-based unique... |
| qwen | peer | pass | 10 | 13 | ship-with-cleanup | Fully spec-compliant with good errno-based error messages and atomic O_EXCL f... |

**Hidden test results** (objective):

- `test_bytes_basic_write` — PASSED
- `test_cli_stdin_to_path` — PASSED
- `test_concurrent_writers_no_corruption` — PASSED
- `test_missing_parent_raises_filenotfound` — PASSED
- `test_mode_applied_when_set` — PASSED
- `test_mode_preserved_when_none_and_target_exists` — PASSED
- `test_no_tmp_residue_on_open_failure` — PASSED
- `test_no_tmp_residue_on_success` — PASSED
- `test_path_is_directory_raises` — PASSED
- `test_replaces_existing` — PASSED
- `test_symlink_writes_to_target` — PASSED
- `test_text_basic_write` — PASSED

### mimo

Run: `builds/mimo/rounds/atomic-write-2026-05-08`

| Judge | Tier | Hard-fail | Spec /10 | Quality /20 | Verdict | Note |
|---|---|---|---|---|---|---|
| deepseek | peer | pass | 10 | 19 | ship-with-cleanup | Polished implementation: correct durability ordering, comprehensive error han... |
| deepseek-flash | peer | pass | 10 | 19 | ship-with-cleanup | Solid, well-structured implementation covering all spec requirements with cle... |
| glm | peer | pass | 10 | 16 | ship-with-cleanup | Best-in-class implementation: fchmod on fd before close for optimal atomicity... |
| kimi | peer | (no scores file) | — | — | — | — |
| mimo | self | pass | 9 | 17 | ship-with-cleanup | Clean, well-decomposed implementation with correct symlink handling and robus... |
| minimax | peer | pass | 10 | 19 | ship-with-cleanup | Exemplary implementation with clear documentation, proper symlink handling, a... |
| qwen | peer | pass | 10 | 18 | ship-with-cleanup | Best-structured implementation: clean helper decomposition, uses fchmod on op... |

**Hidden test results** (objective):

- `test_bytes_basic_write` — PASSED
- `test_cli_stdin_to_path` — PASSED
- `test_concurrent_writers_no_corruption` — PASSED
- `test_missing_parent_raises_filenotfound` — PASSED
- `test_mode_applied_when_set` — PASSED
- `test_mode_preserved_when_none_and_target_exists` — PASSED
- `test_no_tmp_residue_on_open_failure` — PASSED
- `test_no_tmp_residue_on_success` — PASSED
- `test_path_is_directory_raises` — PASSED
- `test_replaces_existing` — PASSED
- `test_symlink_writes_to_target` — PASSED
- `test_text_basic_write` — PASSED

### minimax

Run: `builds/minimax/rounds/atomic-write-2026-05-08`

| Judge | Tier | Hard-fail | Spec /10 | Quality /20 | Verdict | Note |
|---|---|---|---|---|---|---|
| deepseek | peer | pass | 9 | 15 | ship-with-cleanup | Well-structured with idiomatic CLI and good symlink handling; explicit mode a... |
| deepseek-flash | peer | pass | 10 | 17 | ship-with-cleanup | Very clean implementation with excellent structure and all spec items handled... |
| glm | peer | pass | 9 | 13 | ship-with-cleanup | Feature-complete with explicit error checks and symlink handling; marred by c... |
| kimi | peer | (no scores file) | — | — | — | — |
| mimo | peer | pass | 8 | 13 | ship-with-cleanup | Well-structured implementation with good helpers — bare except, unused return... |
| minimax | self | pass | 10 | 16 | rewrite | Well-structured implementation with good documentation but applies mode AFTER... |
| qwen | peer | pass | 10 | 17 | ship-with-cleanup | Well-structured with good helper decomposition and full spec compliance, but ... |

**Hidden test results** (objective):

- `test_bytes_basic_write` — PASSED
- `test_cli_stdin_to_path` — PASSED
- `test_concurrent_writers_no_corruption` — PASSED
- `test_missing_parent_raises_filenotfound` — PASSED
- `test_mode_applied_when_set` — PASSED
- `test_mode_preserved_when_none_and_target_exists` — PASSED
- `test_no_tmp_residue_on_open_failure` — PASSED
- `test_no_tmp_residue_on_success` — PASSED
- `test_path_is_directory_raises` — PASSED
- `test_replaces_existing` — PASSED
- `test_symlink_writes_to_target` — PASSED
- `test_text_basic_write` — PASSED

### qwen

Run: `builds/qwen/rounds/atomic-write-2026-05-08`

| Judge | Tier | Hard-fail | Spec /10 | Quality /20 | Verdict | Note |
|---|---|---|---|---|---|---|
| deepseek | peer | pass | 9 | 15 | ship-with-cleanup | Clean, well-typed implementation with good decomposition; sole spec gap is mi... |
| deepseek-flash | peer | pass | 9 | 16 | ship-with-cleanup | Clean and correct implementation with good structure, missing only an IsADire... |
| glm | peer | pass | 9 | 12 | ship-with-cleanup | Correct mode handling with before-replace application; missing explicit IsADi... |
| kimi | peer | (no scores file) | — | — | — | — |
| mimo | peer | pass | 7 | 14 | ship-with-cleanup | Lean, correct implementation with good error handling and type checks — missi... |
| minimax | peer | pass | 9 | 16 | ship-with-cleanup | Clean, well-structured implementation with type hints. Missing explicit IsADi... |
| qwen | self | pass | 9 | 16 | ship-with-cleanup | Clean and minimal implementation with correct fsync ordering and thorough cle... |

**Hidden test results** (objective):

- `test_bytes_basic_write` — PASSED
- `test_cli_stdin_to_path` — PASSED
- `test_concurrent_writers_no_corruption` — PASSED
- `test_missing_parent_raises_filenotfound` — PASSED
- `test_mode_applied_when_set` — PASSED
- `test_mode_preserved_when_none_and_target_exists` — PASSED
- `test_no_tmp_residue_on_open_failure` — PASSED
- `test_no_tmp_residue_on_success` — PASSED
- `test_path_is_directory_raises` — PASSED
- `test_replaces_existing` — PASSED
- `test_symlink_writes_to_target` — PASSED
- `test_text_basic_write` — PASSED

## Cost & efficiency

Per-implementation cost data, pulled from `builds/<model>/rounds/<task>-<date>/meta.json`. Hand-edit those files after capture to fill in input/output token splits and exact model slugs from each provider's dashboard.

Wall-clock is *model-only* (sum of opencode turn durations from the session export), not the human-perceived envelope. Single-shot, expect ~25% run-to-run variance.

| Impl | Model slug | LOC | Wall-clock (model) | Tokens | Cost USD | Tests passed | Cost / passing test |
|---|---|---|---|---|---|---|---|
| deepseek | `opencode-go/deepseek-v4-pro` | 51 | 3m28s | 98406 | $0.05 | 12 | $0.0043 |
| deepseek-flash | `opencode-go/deepseek-v4-flash` | 62 | 2m05s | 102660 | $0.00 | 12 | $0.0004 |
| glm | `opencode-go/glm-5.1` | 68 | 1m38s | 72679 | $0.06 | 12 | $0.0049 |
| kimi | `opencode-go/kimi-k2.6` | 72 | 5m46s | 115710 | $0.08 | 12 | $0.0067 |
| mimo | `opencode-go/mimo-v2.5-pro` | 93 | 0m49s | 80700 | $0.03 | 12 | $0.0028 |
| minimax | `opencode-go/minimax-m2.5` | 105 | 0m20s | 99838 | $0.01 | 12 | $0.0008 |
| qwen | `opencode-go/qwen3.6-plus` | 77 | 0m53s | 115738 | $0.02 | 12 | $0.0018 |

## Judging cost & efficiency

Per-judge wall-clock and cost. Hand-edit each `results/judgments/<task>-<date>/<judge>/judge_meta.json` to fill in tokens / cost / model slug from dashboards.

| Judge | Tier | Harness | Model | Wall-clock | Tokens | Cost USD |
|---|---|---|---|---|---|---|
| deepseek | peer | — | — | — | — | — |
| deepseek-flash | peer | — | — | — | — | — |
| glm | peer | — | — | — | — | — |
| kimi | peer | — | — | — | — | — |
| mimo | peer | — | — | — | — | — |
| minimax | peer | — | — | — | — | — |
| qwen | peer | — | — | — | — | — |

## Cross-model observations

- **All 7 implementations passed all 12 hidden tests.** The objective gate did not discriminate this round — the judge axis is where signal lives.
- **LOC spread 51 → 105** despite every model hitting the same test outcomes. 2× variance for the same observable behaviour is a quality signal: deepseek (51), deepseek-flash (62), glm (68), kimi (72), qwen (77), mimo (93), minimax (105).
- **mimo wins quality decisively** at 19/20, well above the next cluster (15-15-14-14-13-12). It also ties for top spec compliance at 10/10. Spec-quality dominance from a model that is also the second-cheapest and second-fastest is unusual on this task.
- **minimax is fastest (0:20) and cheapest ($0.01) but produced the longest implementation (105 LOC).** Terse-time, verbose-code tradeoff worth naming — fast generation does not imply concise code.
- **Self-bias direction matches round 1.** Four of six self-judges overrate spec by +1 (deepseek, deepseek-flash, glm, minimax). mimo underrates itself by -1 spec and -2 quality — counter to the field. qwen is calibrated at 0/+1.
- **Inter-judge agreement is tight.** Most spec-score stdevs land in 0.4-1.2, ranges of 1-3. The task is well-specified enough that judges converge — round 1 by contrast had judges disagreeing more sharply.
- **kimi judge dropped out** mid-review. Its `judge.log` shows it read all 7 implementation files but never emitted scores — likely a token-budget or session-timeout issue, not a methodology problem. Re-run on a fresh session would resolve.

## Recommendation

**mimo's `atomic_write.py` is the round winner** — top spec, top quality, low cost. As the canonical reference for an open-source-models-only implementation of crash-safe file writes, this is the one to use.

## Spec changes suggested

- **The 12/12 universal pass suggests the hidden suite is not discriminating enough.** Every model in the lineup produces something that looks correct under static black-box testing. To raise the gate for round 2 of this task, add fault-injection tests: monkeypatch `os.replace` (or the underlying syscall) to fail mid-rename and verify temp cleanup, monkeypatch `os.fsync` to raise and verify the call site handles it, and verify directory-fsync is actually invoked (not silently skipped). The existing tests assert outcomes; the next iteration should assert the durability ordering.
- **Symlink semantics test is permissive.** It accepts either "write through to target" or "replace the symlink" as valid outcomes. SPEC says "write to the target", so a stricter test should fail implementations that replace the symlink instead.
