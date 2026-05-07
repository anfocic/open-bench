# open-bench

**An n-way coding-eval harness for AI models.**

Drop in a spec, a prompt, and a hidden test suite. open-bench runs every model in your lineup through [opencode], captures transcripts and diffs, runs the hidden tests, and grades each submission three ways:

- **Hidden tests** — objective pass/fail the models never see.
- **Peer review** — every model blind-grades every submission against a rubric. Self-judgments are tracked separately as a bias check.
- **Cost & speed** — wall-clock, tokens, dollars per run.

Output: a peer-median scoreboard, per-judge rankings, self-bias delta, inter-judge agreement, hidden-test results.

The bet: this measures whether a model can sustain a real codebase over weeks of feature growth — not just one-shot a clever solution.

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

Outputs land in `builds/<model>/rounds/` and `results/reviews/`. See [ABOUT.md](ABOUT.md) for the full pipeline, task configuration, and how to fork it for your own n-way comparison.

## Example task

`bench/tasks/sandbox/` ships as the canonical code-task example — a single-file Python wrapper around Podman/Docker for ephemeral, network-isolated, resource-capped command execution. `bench-start-run sandbox <model>` runs against it out of the box. Recursive joke: the first task is implementing a sandbox to run the rest in.

Add your own task with `bench-new-task <name>`; edit the generated `task.json` to set entrypoint and test invocation.

## Live tournament: Model Royale

[**Model Royale**](https://open-bench.dev/royale) is a public weekly tournament built on open-bench: seven open-weight models, same prompt each week, lowest combined score eliminated until one is left standing. Round 1 (the sandbox task above) shipped 2026-05-05. Round 2 introduces a generation-task modality (reddit user-vote evaluation).

Royale is one consumer of the harness, not the harness itself. If you want a different lineup, different rules, or a private comparison, see "Forking" in [ABOUT.md](ABOUT.md).

## What's not here yet

v0.1 is single-task-kind, opencode-only, single-machine. Specifically:

- One task kind (code; entrypoint + pytest + LOC). Generation/choice land in v0.2 — see [`PLAN_V0_2.md`](PLAN_V0_2.md).
- Implementer + judge runs both go through opencode. No first-class Anthropic/OpenAI providers yet.
- Worktrees and run artifacts assume one machine; no shared storage / CI mode.
- Installs from a clone (`pip install -e .`); no PyPI release yet.

If those gaps block you, file an issue — the v1.0 roadmap in `PLAN_V0_2.md` covers them.

## Read more

- [**ABOUT.md**](ABOUT.md) — pipeline, task configuration, forking guide, layout, limitations.
- [`PLAN_V0_2.md`](PLAN_V0_2.md) — decoupling roadmap (pluggable task kinds, provider abstractions, model-royale carve-out).
- [`bench/plans/improvements.md`](bench/plans/improvements.md) — known gaps and planned work.

## License

MIT — see [LICENSE](LICENSE).

[opencode]: https://opencode.ai
