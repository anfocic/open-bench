# bench — model implementation eval framework

Standard setup for testing how different models implement a given spec via
opencode. Each task is a frozen spec + hidden tests + rubric. Each model gets
its own git worktree, runs in opencode, and produces artifacts. After all
implementations are captured, every model also serves as a judge of the
others' code. Multi-judge scoring is aggregated into a single review.

The single source of truth for which models compete (and which optional
expert judges score them) is `bench/config.json`.

## Layout

```
bench/
├── tasks/<task>/
│   ├── PROMPT.md       what the model sees (paste this into opencode)
│   ├── SPEC.md         frozen task spec
│   ├── rubric.md       scoring sheet (filled in per run)
│   └── tests/          HIDDEN — copied into worktree only at capture time
└── scripts/                # python -m bench.scripts.<name>
    ├── new_task.py
    ├── start_run.py
    ├── capture_run.py
    ├── run_all.py
    ├── start_judgments.py
    └── aggregate_judges.py

# Run artifacts live under builds/ and results/ at the repo root:
#   builds/<model>/sandbox.py                     current code (latest round)
#   builds/<model>/rounds/<task>-<date>/          round archive
#     ├── sandbox.py        snapshot
#     ├── diff.patch
#     ├── test-output.txt
#     ├── transcript.md     opencode session export
#     └── meta.json
#   results/reviews/<task>-<date>.md              aggregated multi-judge review
#   results/perf/<task>-<model>-<date>/           n=5 perf runs
#   results/judgments/<task>-<date>/              judge packets (gitignored)
```

## Run protocol

For each model under test:

### Auto-drive (recommended)

```
python3 -m bench.scripts.start_run --auto <task> <model>
```

`--auto` calls `opencode run` non-interactively against the worktree using
the slug from `bench/config.json`, then chains to `capture_run.py` on
success. Uses `--dangerously-skip-permissions`; trust the task content
before running. On a non-zero opencode exit the worktree is preserved for
inspection and capture is skipped.

### Manual

1. **Start a run** (creates an isolated worktree with PROMPT.md + SPEC.md):
   ```
   python3 -m bench.scripts.start_run <task> <model>
   ```

2. **Open opencode in the worktree**, set the model, paste `PROMPT.md`:
   ```
   cd <worktree>
   opencode
   /model <model-slug>
   ```
   Let it run until it says it's done.

3. **Capture artifacts**:
   ```
   python3 -m bench.scripts.capture_run <task> <model>
   ```
   This:
   - finds the opencode session whose working dir matches the worktree
     (via `opencode session list --format json`), exports it to
     `<run-dir>/opencode_session.json`, and populates `meta.json` with
     cost, token splits, model slug, harness version, and wall-clock
   - copies hidden tests into the worktree under `_eval_tests/`
   - runs `python -m pytest _eval_tests/ -v` from the worktree root
   - saves `diff.patch`, edited file copies, test output, meta
   - removes `_eval_tests/` so the diff stays clean
   - prints the run dir path

   If `opencode` isn't on PATH, the session-capture step is skipped and the
   flow degrades to a hand-saved `transcript.md`.

4. **Judge** (multi-judge phase — see "Judgment phase" below).
5. **Review** — `aggregate_judges.py` produces
   `results/reviews/<task>-<date>.md`. Cross-model observations and the
   recommendation are the human-written sections; everything else is
   derived from the JSON inputs.

## Judgment phase

After all implementations are captured, every implementation is scored by
multiple judges. A judge produces a filled rubric and a structured
`scores.json` per implementation.

**Judge panel** (configured in `bench/config.json`):
- **Each implementer model** — judges every implementation *except its own*
  (kimi judges deepseek + minimax; deepseek judges kimi + minimax; etc.).
  This peer tier is always on.
- **Expert judges** (opt-in) — any opencode model not in the implementer
  set, listed under `expert_judges` with a slug in the `slugs` map.
  Enables the peer-vs-expert delta (self-bias check). Empty by default.

**Blinding:** judges see implementations as `A.py`, `B.py`, `C.py` with
random label assignments per judge. The mapping lives in
`results/judgments/<task>-<date>/pairings.json` and is only read by the
aggregator. Judges should not try to identify the model behind a label.

**What judges do not see:**
- The hidden test suite or its results — judging is static code review
  against the spec. Test outcomes are pulled from each run's
  `test-output.txt` directly by the aggregator and shown alongside
  judge scores so judge↔test agreement is its own signal.

### Setup

```
# Auto-drive every judge with a slug in bench/config.json:
python3 -m bench.scripts.start_judgments --auto <task>

# Or build packets only and drive each judge yourself:
python3 -m bench.scripts.start_judgments <task>
```

Either form:
- finds the latest captured run per model under `builds/<model>/rounds/<task>-*/`
- creates `results/judgments/<task>-<date>/` with one dir per judge
- per judge, writes a `packet/` containing `PROMPT.md`, `SPEC.md`,
  `JUDGE_PROMPT.md`, `JUDGE_RUBRIC.md`, and `implementations/<label>.py`
  for each impl that judge is supposed to review
- writes `pairings.json` (the blinded mapping per judge) and
  `runs_index.json` (which run each impl came from)

`--auto` then runs each judge with a slug in config through `opencode run`
sequentially. Any judge label without a slug is left for manual driving
and listed in the closing output.

### Per-judge output

Each judge produces, per implementation:
- `output/<label>_rubric.md` — filled JUDGE_RUBRIC.md
- `output/<label>_scores.json` — structured scores (schema in JUDGE_PROMPT.md)
- `output/summary.md` (only if multiple impls reviewed) — comparison

For manual judges, point them at `results/judgments/<task>-<date>/<judge>/packet/`
and have them write to the sibling `output/` directory.

### Aggregate

```
python3 -m bench.scripts.aggregate_judges <task>
```

Reads `pairings.json`, every judge's `*_scores.json`, and each run's
`test-output.txt`. Produces `results/reviews/<task>-<date>.md` with:
- top-level scoreboard (median spec / quality, mode verdict, objective tests)
- per-implementation detail (every judge's row + per-test pass/fail)
- skeleton sections for human cross-model observations and recommendation

## Adding a new task

```
python3 -m bench.scripts.new_task <task-name>
```

Then edit:
- `bench/tasks/<task-name>/SPEC.md` — full implementation spec
- `bench/tasks/<task-name>/PROMPT.md` — what the model sees
- `bench/tasks/<task-name>/JUDGE_PROMPT.md` — what each judge sees
- `bench/tasks/<task-name>/JUDGE_RUBRIC.md` — what each judge fills
- `bench/tasks/<task-name>/tests/` — hidden tests
- `bench/tasks/<task-name>/rubric.md` — scoring rows (long-form)

## Models & API keys

opencode handles authentication itself — credentials are not stored in this
repo.

### Recommended: native provider keys (one per provider)

Three keys, three dashboards. The advantage is **per-provider visibility**:
each provider's console shows true tokens, request counts, latency, prompt
cache hit rate, and exact model revisions billed. That visibility is the
whole point of running this benchmark — wrapping all three behind a proxy
hides the metadata we care about most.

| Provider | Base URL | Env var | Console |
|---|---|---|---|
| Moonshot (Kimi) | `https://api.moonshot.ai/v1` (intl) or `https://api.moonshot.cn/v1` (CN) | `MOONSHOT_API_KEY` | platform.moonshot.ai / .cn |
| DeepSeek | `https://api.deepseek.com/v1` | `DEEPSEEK_API_KEY` | platform.deepseek.com |
| MiniMax | `https://api.minimaxi.com/v1` (intl) or `https://api.minimax.chat/v1` (CN) | `MINIMAX_API_KEY` | minimaxi.com / minimax.chat |

All three speak the OpenAI Chat Completions API, so they slot into
opencode's provider config as OpenAI-compatible providers. Steps:

1. Sign up on each console, generate an API key, fund the account.
2. Export the keys (e.g. in `~/.zshrc` or a `.envrc`):
   ```
   export MOONSHOT_API_KEY=...
   export DEEPSEEK_API_KEY=...
   export MINIMAX_API_KEY=...
   ```
3. Configure opencode to know about each provider. Either:
   - run `opencode auth login` if it lists them as built-in providers, or
   - add them to opencode's config file (`~/.config/opencode/config.json`
     or per-project `.opencode/config.json`) as OpenAI-compatible
     providers, with `baseURL` pointing at the endpoints above.
4. In an opencode session, switch with `/model <provider>/<model>`. Verify
   the current model slugs from each provider's docs — they change:
   - Kimi: e.g. `kimi-k2-0905-preview`, `moonshot-v1-128k`
   - DeepSeek: e.g. `deepseek-chat`, `deepseek-reasoner`
   - MiniMax: e.g. `MiniMax-M2`, `abab7-chat-preview`

**Cost / token capture is automatic.** `capture_run.py` calls
`opencode export <session>` and sums per-message cost + tokens into
`meta.json` (fields: `input_tokens`, `output_tokens`, `tokens_total`,
`cost_usd`, `model_slug`, `model_wall_clock_seconds`). No dashboard
round-trip needed. Provider-side metrics (cache hit rate, latency
distribution) are still in each console if you want them, but the
benchmark numbers don't require hand-editing meta.json.

### Alternative: OpenRouter (one key, all models)

If juggling three dashboards is more cost than the visibility is worth, use
OpenRouter as a single gateway. Trade-offs:

- ✓ one key, one bill
- ✗ ~5% markup
- ✗ provider-side metrics hidden behind the OR layer (no native cache hit
  rate, no provider-specific quirks visible)

```
export OPENROUTER_API_KEY=...
# then in opencode: /model openrouter/<slug>
```

Slugs at https://openrouter.ai/models. Don't mix native and OpenRouter
within a single benchmark round — pick one path per round so cost/latency
numbers are comparable.

### Recording the model slug per run

The `<model>` argument to `start_run.py` is your **short label** (`kimi`,
`deepseek`, `minimax`) — used in directory names and review tables. The
**actual model slug** (e.g. `opencode-go/kimi-k2.6`) is the value set
under `slugs` in `bench/config.json` and is also pulled out of the
exported opencode session into `meta.json` at capture time, so the
review knows which exact build was tested.

## Transcript capture

`capture_run.py` finds the opencode session whose working directory
matches the worktree, exports it as JSON, archives that JSON as
`<run-dir>/opencode_session.json`, and renders a markdown
`transcript.md` from it.

Override paths:
- If `<worktree>/transcript.md` exists (hand-saved), it takes precedence
  over the auto-rendered version.
- If `opencode` is not on PATH or no session matches the worktree
  directory, the run dir gets a placeholder transcript with instructions.

## Rules for fair comparison

- **Identical prompt** to all models. PROMPT.md is the single source.
- **Hidden tests** never enter the worktree until capture. Models score on
  spec compliance, not gaming the test file.
- **No human edits** during the run. If you intervene, note it in the
  transcript and call out the deviation in the review.
- **Same time budget** ideally — track wall-clock in `meta.json`.

## What "done" means for a run

A run produces enough artifacts for an offline reviewer to grade it without
the worktree:

- [ ] `diff.patch` exists and is non-empty
- [ ] `files/` has at least one file
- [ ] `test-output.txt` exists (even if all tests failed)
- [ ] `meta.json` has model + date + wall-clock
- [ ] `transcript.md` exists (placeholder OK if export not possible)
