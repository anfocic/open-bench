# Harness improvements

## 1. Task parametrization — DONE

Implemented. All scripts now read `bench/tasks/<task>/task.json` via `bench/scripts/_task.py`. Defaults reproduce round-1 behaviour when `task.json` is absent. Shell scripts replaced by Python equivalents; thin `.sh` shims delegate for backwards-compatible CLI. See ABOUT.md for the `task.json` schema.

## 2. Implementer parallelization — deferred

### Problem

The round-1 task is single-file Python at `bench/tasks/sandbox/`. Four scripts hardcode the literal string `sandbox.py` (~11 references):

- `bench/scripts/start-run.sh` — drops `PROMPT.md` and `SPEC.md` into the worktree and (via the `--auto` driver) instructs opencode to "implement `sandbox.py`".
- `bench/scripts/capture-run.sh` — copies `sandbox.py` from the worktree to `builds/<model>/sandbox.py` and `builds/<model>/rounds/<task>-<date>/sandbox.py`. Runs `python3 -m pytest _eval_tests/`. Counts LOC of `sandbox.py`.
- `bench/scripts/perf-bench.py` — invokes `start-run.sh` then reads `sandbox.py` for LOC.
- `bench/scripts/start_judgments.py` — copies each impl's `sandbox.py` into the per-judge packet under `implementations/<label>.py`.

The judge prompt (in `bench/tasks/sandbox/JUDGE_PROMPT.md`) also names `sandbox.py` directly. Acceptable because the judge prompt is per-task; that's the right place for the name.

Round 2 extends the same `sandbox.py` task — works as-is. Any later round that needs a different entrypoint (e.g. `cli.py`, multi-file, a Go file) breaks the harness today.

### Design

Add `bench/tasks/<task>/task.json` as the single source of truth for task shape:

```json
{
  "entrypoint": "sandbox.py",
  "language": "python",
  "test_runner": "pytest",
  "test_invocation": ["python3", "-m", "pytest", "-v", "--tb=short"],
  "loc_method": "non_blank_non_comment_lines"
}
```

Fields:
- `entrypoint` — the filename the model produces. The capture script copies this to `builds/<model>/<entrypoint>` and into the run dir. Multi-file tasks: leave `entrypoint` as the "front door" file (e.g. `main.py` or `cli.py`); a follow-up `extra_files` field can list others without breaking the round-1 schema.
- `language` — informational for now; later drives test-runner defaults and judge-prompt boilerplate.
- `test_runner` — string id used for messaging (`pytest`, `cargo test`, `swift test`).
- `test_invocation` — argv list to run from `_eval_tests/` working dir. capture-run.sh shells out to this. For round 1 that's the current `python3 -m pytest -v --tb=short`.
- `loc_method` — controls the LOC counter (round 1 currently uses `grep -cvE '^\s*(#|$)'`). Add a Python helper that switches on this. Initial values: `non_blank_non_comment_lines` (round 1), `wc_l` (raw line count for non-Python).

Single shared loader:

```python
# bench/scripts/_task.py
def load(task: str) -> dict:
    """Read bench/tasks/<task>/task.json; return defaults if missing."""
    ...
```

Defaults (when `task.json` is absent) reproduce the round-1 hardcoded values, so the change is backwards compatible — existing `bench/tasks/sandbox/` works untouched until we drop a `task.json` next to it.

### Refactor map

| Script | Current ref | After |
|---|---|---|
| `start-run.sh` | `"implement sandbox.py per the spec"` in the auto-drive message | Read `task.json.entrypoint`; substitute into the message. The message stays in shell to avoid threading another Python invocation in. |
| `start-run.sh` | "Stop when sandbox.py exists at the worktree root" | Same substitution. |
| `capture-run.sh` | `"${worktree_dir}/sandbox.py"` (LOC count, copy) | `"${worktree_dir}/${entrypoint}"` resolved at top of script via a tiny inline python3 read of task.json. |
| `capture-run.sh` | `cp "${run_dir}/sandbox.py" "${model_dir}/sandbox.py"` | Same with entrypoint variable. |
| `capture-run.sh` | `python3 -m pytest _eval_tests/ -v --tb=short` | `${test_invocation[@]}` — execute the argv from task.json. |
| `start_judgments.py` | `impl = run_entry / "sandbox.py"` | `impl = run_entry / task["entrypoint"]` |
| `start_judgments.py` | Packet copy: `impl_dir / f"{label}.py"` | Preserve original extension: `impl_dir / f"{label}{Path(entrypoint).suffix}"` |
| `perf-bench.py` | LOC of `sandbox.py` | LOC of `task["entrypoint"]` via `_task.loc_count(...)`. |
| `bench/tasks/sandbox/JUDGE_PROMPT.md` | Names `sandbox.py` | Stays — per-task asset, correct place. |

### Rollout

1. Add `_task.py` loader with defaults.
2. Convert scripts one at a time, smallest first: `start_judgments.py` → `perf-bench.py` → `capture-run.sh` → `start-run.sh`. After each, re-run `OPENCODE_RUN_DRYRUN=1 run-all.sh sandbox` to confirm no regressions.
3. Drop `bench/tasks/sandbox/task.json` with the round-1 values.
4. Update README — remove the "Forking caveats" section claiming the framework isn't task-agnostic.

### Verification

- Dry-run the full pipeline against the existing `sandbox` task. All paths and argvs identical to today.
- Add a second tiny throwaway task (`bench/tasks/hello/`) with `entrypoint: hello.py`. Run end-to-end. Confirm builds land at `builds/<model>/hello.py`, judges receive `<label>.py` (still matches Python suffix from entrypoint), aggregator finds them.
- Delete the throwaway task.

### Out of scope for this round

- Multi-file tasks (`extra_files` field). Add when first multi-file task appears.
- Non-Python tasks. Will surface bugs in the LOC counter and test runner that we can't see ahead of time.
- A schema validator for `task.json`. Three fields + defaults; not worth the dependency.

---

## 2. Implementer parallelization

### Problem

`bench/scripts/run-all.sh` runs each implementer sequentially:

```bash
for model in "${implementers[@]}"; do
    "${script_dir}/start-run.sh" --auto "${task}" "${model}"
done
```

7 models × ~3min each = ~21min. Judge phase (already parallelized, see PR #2) is ~9min at concurrency=3. Round wallclock is dominated by the implementer loop.

### Why we deferred

- Judge phase parallelization was the bigger win (49 sessions vs 7 implementer sessions).
- Implementer parallelization adds a `git worktree add` race. `start-run.sh` calls `git worktree add -b <branch> <path> <base>`, which acquires `.git/index.lock`. Two concurrent invocations will see one win the lock and the other retry/fail. Need to either serialize the worktree creation (small critical section) or restructure to create all worktrees up-front then dispatch.
- Pain isn't real yet at 21min/round.

### Design (when ready)

Apply the prototype from `start_judgments._drive_one_judge`:

```python
# new file: bench/scripts/run_all.py — replaces run-all.sh
def _drive_one_implementer(task, model, log_path, lock):
    with lock:                 # serialize the git-worktree-add critical section
        prepare_worktree(...)  # the part of start-run.sh up through `git worktree add`
    # everything after is independent: the opencode session and capture-run.sh
    return run_opencode_and_capture(...)

with ThreadPoolExecutor(max_workers=concurrency) as pool, \
     threading.Lock() as worktree_lock:
    futures = {pool.submit(_drive_one_implementer, task, m, log_paths[m], worktree_lock): m
               for m in implementers}
    ...
```

Two concrete questions to resolve at implementation time:

1. **Port `start-run.sh` and `capture-run.sh` to Python**, or keep them as shell and dispatch via `subprocess.run` from a Python orchestrator? The shell scripts are already Python-flavored at the edges (heredoc'd python3 blocks). Porting cleanly to one language reduces glue. ~150 LOC of bash → ~250 LOC of Python.
2. **Concurrency cap default.** Same question as the judge phase: default 3, env override `IMPL_CONCURRENCY=N` (mirroring `JUDGE_CONCURRENCY`). Watch for opencode-go gateway throttling — same single-key constraint as judges.

### Verification

Same pattern as the judge parallelization PR:
1. `OPENCODE_RUN_DRYRUN=1 IMPL_CONCURRENCY=1` — sequential, byte-identical to today.
2. `IMPL_CONCURRENCY=4` dry-run — 4 worktrees created (lock-serialized), 4 sessions dispatched (parallel), all complete.
3. Real round at concurrency=3 — confirm wallclock drops from ~21min to ~9min, no test regressions, no worktree conflicts.

### Future work (after this lands)

Hoist the `_drive_one_*` + `ThreadPoolExecutor + per-target log + as_completed summary` pattern into a shared `bench/scripts/_parallel.py` module. Two call sites then justifies the abstraction.
