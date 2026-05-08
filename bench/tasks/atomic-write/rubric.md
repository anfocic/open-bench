# Rubric: atomic-write task

Reviewer fills one copy of this per run, stored in `results/reviews/`.

## Hard-fail (any miss = run fails, do not score the rest)

- [ ] `atomic_write.py` exists at worktree root
- [ ] `atomic_write_text` and `atomic_write_bytes` present with SPEC signatures
- [ ] Stdlib only (no third-party imports, no `requirements.txt` / `pyproject.toml` deps)
- [ ] Temp file created in the same directory as the target
- [ ] File `fsync` before close
- [ ] Parent dir `fsync` after replace

## Spec compliance — score 0–10

Award 1 point per item:

- [ ] Uses `os.replace` for the atomic rename
- [ ] Cleans up temp on every error path
- [ ] Mode preservation when `mode is None` and target exists
- [ ] Explicit `mode` applied when set
- [ ] `FileNotFoundError` on missing parent dir, no temp residue
- [ ] `IsADirectoryError` when path is a dir
- [ ] CLI reads stdin (bytes), writes atomically
- [ ] CLI exit 0 success / non-zero on error with stderr
- [ ] Symlink target write (not replace)
- [ ] Unique temp name (no collision under concurrent writers)

Subtotal: __ / 10

## Hidden test results

Filled by `capture_run.py`. One row per test:

| Test | Pass / Fail / Skip | Notes |
|---|---|---|
| `test_text_basic_write` | | |
| `test_bytes_basic_write` | | |
| `test_replaces_existing` | | |
| `test_no_tmp_residue_on_success` | | |
| `test_no_tmp_residue_on_open_failure` | | |
| `test_missing_parent_raises_filenotfound` | | |
| `test_path_is_directory_raises` | | |
| `test_mode_preserved_when_none_and_target_exists` | | |
| `test_mode_applied_when_set` | | |
| `test_concurrent_writers_no_corruption` | | |
| `test_symlink_writes_to_target` | | |
| `test_cli_stdin_to_path` | | |

Tests passed: __ / 12

## Code quality — score each 0–5

- [ ] **Clarity** — naming, structure, function decomposition
- [ ] **Conciseness** — no over-engineering, no unused branches
- [ ] **Error handling** — proportional, fails loud at boundaries, doesn't swallow
- [ ] **Comments** — only where the *why* is non-obvious

Subtotal: __ / 20

## Cost

- LOC added (excluding blank/comment): ___
- Wall-clock time (start → done): ___ minutes
- Token cost (if available): ___

## Reviewer summary

One paragraph: what worked, what didn't, would you ship this implementation
with cleanup, or rewrite from scratch?

## Total score

Hard-fail pass: yes / no
Spec compliance: __ / 10
Tests passed: __ / 12
Code quality: __ / 20
**Total** (only if hard-fail passed): __ / 42
