# Rubric: sandbox task

Reviewer fills one copy of this per run, stored in `results/reviews/`.

## Hard-fail (any miss = run fails, do not score the rest)

- [ ] `sandbox.py` exists at repo root
- [ ] Top-level `sandbox_run(...)` function with signature matching SPEC
- [ ] Subprocess invocation uses argv list / `shell=False` (no host shell interpolation of `command`)
- [ ] `network` param defaults to `"none"`
- [ ] No external dependencies introduced (no `requirements.txt`, `pyproject.toml` with deps, `pip install`, virtualenv)
- [ ] Stdlib only (no `import` of third-party packages)

## Spec compliance — score 0–10

Award 1 point per item present and correct:

- [ ] All param defaults match SPEC (`image`, `timeout`, `network`, `memory`, `pids`, `cpus`)
- [ ] Resource limits on every podman invocation (`--memory`, `--pids-limit`, `--cpus`, `--cap-drop=ALL`, `--security-opt=no-new-privileges`)
- [ ] Workspace mount semantics correct (`None` = no mount; path = bind r/w at `/workspace` with `-w /workspace`)
- [ ] Output format exactly matches `exit=<n>\n--- stdout ---\n<...>\n--- stderr ---\n<...>`
- [ ] 50KB output truncation
- [ ] Timeout returns exit code 124
- [ ] Decoding uses `errors="replace"` (or equivalent — no `UnicodeDecodeError` on binary output)
- [ ] CLI: argparse + `--` separator works
- [ ] CLI: default workspace = `os.getcwd()`
- [ ] CLI: exit code matches inner container exit

Subtotal: __/10

## Hidden test results

Filled by `capture_run.py`. One row per test:

| Test | Pass / Fail / Skip | Notes |
|---|---|---|
| `test_simple_echo` | | |
| `test_output_format` | | |
| `test_exit_code_nonzero` | | |
| `test_timeout` | | |
| `test_network_default_isolated` | | |
| `test_network_bridge` | | |
| `test_workspace_mount` | | |
| `test_truncation` | | |
| `test_no_host_shell_injection` | | |

Tests passed: __/9

## Code quality — score each 0–5

- [ ] **Clarity** — naming, structure, function decomposition
- [ ] **Conciseness** — no over-engineering, no unused branches, no premature abstraction
- [ ] **Error handling** — proportional to risk, fails loud at boundaries, doesn't swallow
- [ ] **Comments** — only where the *why* is non-obvious; no narration

Subtotal: __/20

## Cost

- LOC added (excluding blank/comment): ___
- Wall-clock time (start → done): ___ minutes
- Token cost (if available): ___

## Reviewer summary

One paragraph: what worked, what didn't, would you ship this implementation
with cleanup, or rewrite from scratch?

## Total score

Hard-fail pass: yes / no
Spec compliance: __/10
Tests passed: __/9
Code quality: __/20
**Total** (only if hard-fail passed): __/39
