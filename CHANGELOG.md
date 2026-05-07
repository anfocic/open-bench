# Changelog

All notable changes to this project will be documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.2] — unreleased

First two structural steps of v0.2 plugin work: configurable config /
tasks paths so a downstream consumer (e.g. a separate `royale/` tree)
can drive the harness without forking, and the empty plugin scaffolding
(`_kinds/` registry, `task_kind` field) that PRs to come will fill in
as logic is carved out of `capture_run` / `start_judgments` /
`aggregate_judges`.

### Added
- `bench/scripts/_kinds/` package with a registry of task kinds.
  Currently one kind (`code`, empty `CodeTask` class). Methods grow
  as carve-out PRs land.
- `task_kind` field on `_task.load()` (default: `"code"`); existing
  `task.json` files don't need updating.
- `_task.kind_for(name)` resolves a task to its plugin instance via
  the registry.
- `OPENBENCH_CONFIG` env var overrides the path to `config.json`
  (default: `<repo_root>/bench/config.json`).
- `OPENBENCH_TASKS_DIR` env var overrides the directory holding task
  definitions (default: `<repo_root>/bench/tasks`).
- `_task.tasks_dir()`, `_task.task_dir(name)`, `_task.require(name, files=[])`
  helpers; `~` in env-var paths is expanded.

### Changed
- `start_run`, `capture_run`, `start_judgments`, `perf_bench` now route
  task-dir resolution + required-files validation through
  `_task.require()`. Callers no longer recompute the path or repeat the
  `is_dir()` check.
- `new_task` scaffolds under `_task.tasks_dir()` so `OPENBENCH_TASKS_DIR`
  is honoured at scaffold time too.

### Fixed
- `capture_run` now validates the task directory up front. A typo'd
  task name previously surfaced as `"no tests dir at .../tests"`; the
  message now points at the task directory itself.
- `start_run` error on missing task files now names the specific
  missing file rather than `"missing PROMPT.md or SPEC.md"`.

## [0.1.1] — 2026-05-07

Pre-publish polish on top of 0.1.0. No behaviour change.

### Added
- README quickstart (`pip install -e ".[dev]"` → `bench-start-run`) and
  "what's not here yet" section setting v0.1 vs v0.2/v1.0 expectations.
- `PLAN_V0_2.md` linked from README — pluggable task kinds + v1.0 roadmap.

### Changed
- `requires-python` now bounded `>=3.11,<3.14` (tested upper bound).
- ABOUT.md run-it section uses the `bench-*` console scripts instead of
  `python3 -m bench.scripts.*` and the long-removed `run-all.py`.

### Fixed
- `capture_run` pathspec falls back to entrypoint basename for
  extensionless task entrypoints. (#42)
- `start_run.determine_base_branch` test coverage for fallback paths. (#42)

## [0.1.0] — 2026-05-06

First versioned release. Captures the senior-review refactor trilogy
plus follow-up fixes.

### Added
- `bench/scripts/` is now a real Python package; `python3 -m bench.scripts.X`
  is the canonical invocation. (#29)
- Run identity stamped into `meta.json` / `runs_index.json` /
  `judgment_meta.json`; readers no longer slice directory names. (#30)
- `--quiet` / `--verbose` flags on every entry point; status routes
  through `logging`. (#35)
- Property-based tests (`hypothesis`) for `_pytest_parse`. (#36)
- `_pytest_parse` tolerates ANSI color codes and pytest-xdist worker
  prefixes. (#37)
- `CAPTURE_TEST_TIMEOUT` env var (default 300s) bounds hidden-test
  execution; timeouts record `test_exit_code=124`. (#38)
- `pyproject.toml`; `pip install -e ".[dev]"` installs the package and
  puts seven CLIs on PATH (`bench-new-task`, `bench-start-run`,
  `bench-capture-run`, `bench-run-all`, `bench-judgments`,
  `bench-aggregate`, `bench-perf`).

### Changed
- `_config.repo_root()` and `aggregate_judges` config are lazy — no
  subprocess or disk I/O at import time. (#29)
- `perf-bench.py` renamed to `perf_bench.py`. (#29)
- 13 emoji rule violations (✓ ✗ ▶) removed from script output. (#35)

### Removed
- `bench/scripts/{capture-run,start-run,run-all,new-task}.sh` shim
  wrappers — direct `python3 -m bench.scripts.<name>` (or the new
  `bench-<name>` CLI) replaces them. (#34)
- `requirements-dev.txt` — replaced by `[project.optional-dependencies] dev`
  in `pyproject.toml`.
