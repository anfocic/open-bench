# open-bench

A comparative benchmark harness for coding LLMs. Drops a task spec into a fresh repo, drives every model in the lineup through a real agent loop, runs a hidden test suite as the objective gate, has the models score each other, and commits the full artifact set — transcripts, diffs, judge rubrics, scores — to the repository.

The full positioning rationale is in [WHY.md](WHY.md). The contribution path (including a 30-minute task-author walkthrough) is in [CONTRIBUTING.md](CONTRIBUTING.md).

## What gets measured

Every implementation in every round produces four numbers:

| Column | Source |
|---|---|
| Hidden-test pass rate | objective gate; runs before any judge sees the code |
| Blinded peer scores | every model judges every implementation under random labels; expert / peer / self tiers tracked separately |
| Model wall-clock | sum of agent-loop turn durations |
| Dollar cost | from each provider's billing dashboard |

Self-bias delta and inter-judge agreement are computed and surfaced every round, including on each model's [own page](https://open-bench.dev/model-royale/model/) — methodology stays first-class, not buried.

## Quickstart

Requires Python 3.11–3.13. The bundled `--auto` driver shells out to [opencode] (tested against 1.14.x); manual flow needs no driver. Authenticate opencode against your providers first (`opencode auth login`) if using `--auto`.

```bash
git clone https://github.com/anfocic/open-bench.git
cd open-bench
pip install -e ".[dev]"

bench-start-run --auto sandbox kimi   # one model, one round
bench-capture-run sandbox kimi        # extract artifacts + run hidden tests
bench-run-all sandbox                 # full round across the lineup
```

Outputs land in `builds/<model>/rounds/` and `results/reviews/`. See [ABOUT.md](ABOUT.md) for the full pipeline and forking guide.

## Engine vs driver

The engine is provider-agnostic: tasks, runs, judging, and aggregation work without any specific agent harness. The bundled `--auto` driver shells out to opencode today; replacing it with Claude Code, Aider, or anything that can take a prompt and write to a worktree is a single-module swap behind `bench/scripts/_opencode_run.py`. The manual flow needs no driver at all — operators paste the prompt into any agent harness, drop the result back as `transcript.md`, and the rest of the pipeline runs unchanged.

## Example task

`bench/tasks/sandbox/` ships as the canonical code-task example — a single-file Python wrapper around Podman/Docker for ephemeral, network-isolated, resource-capped command execution. `bench-start-run sandbox <model>` runs against it out of the box. Recursive joke: the first task is implementing a sandbox to run the rest in.

Add your own task with `bench-new-task <name>`; edit the generated `task.json` to set `task_kind`, entrypoint, and test invocation. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full file-by-file walkthrough.

## Live tournament: Model Royale

[**Model Royale**](https://open-bench.dev/model-royale) is a public weekly tournament built on open-bench: selected open-source coding models, same prompt each week, lowest combined score eliminated until one is left standing. Round 1 (the sandbox task above) shipped 2026-05-05. Round 2 introduces a different scoring modality (reddit user-vote experiment over the same lineup).

Royale is one consumer of the harness, not the harness itself. If you want a different lineup, different rules, or a private comparison, see "Forking" in [ABOUT.md](ABOUT.md).

## What's not here yet

v0.2 carved task-kind logic onto a `_kinds/` plugin registry, but only the `code` kind ships today. Specifically:

- One task kind. The registry exists; new kinds (generation, choice) wait for a second real consumer (round 2 in model-royale) to constrain the contract before the `TaskKind` Protocol is frozen.
- One agent-harness driver (opencode) for `--auto`. Manual flow is driver-agnostic; programmatic alternative drivers wait for a contributor with a real second implementation.
- Worktrees and run artifacts assume one machine; no shared storage / CI mode.
- Installs from a clone (`pip install -e .`); no PyPI release yet.

If those gaps block you, file an issue.

## Read more

- [**WHY.md**](WHY.md) — what's broken about existing benchmarks, what open-bench commits to, and what it explicitly won't measure.
- [**CONTRIBUTING.md**](CONTRIBUTING.md) — local setup, adding a code task in 30 minutes, PR checklist.
- [**ABOUT.md**](ABOUT.md) — pipeline, task configuration, forking guide, layout, limitations.
- [`PLAN_V0_2.md`](PLAN_V0_2.md) — decoupling roadmap (now mostly shipped).
- [`bench/plans/improvements.md`](bench/plans/improvements.md) — known gaps and planned work.

## License

MIT — see [LICENSE](LICENSE).

[opencode]: https://opencode.ai
