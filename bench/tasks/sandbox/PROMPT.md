# Task: implement `sandbox.py`

Read `SPEC.md` in this directory. Implement `sandbox.py` exactly per spec:
the `sandbox_run(...)` function, and the standalone CLI entry point.

This task covers **only `sandbox.py`**. The mia harness integration files
(`tools/sandbox.py`, `repl/tool_registry.py`, `permissions.py`) are out of
scope — do not create them.

## Hard constraints

- Python 3.10+, **stdlib only** — no `pip install`, no new dependencies.
- Use `subprocess.run(argv, shell=False)` (or equivalent argv-list form).
  Never invoke a host shell to interpolate `command`.
- `network` parameter defaults to `"none"`. Any deviation is a fail.
- Every podman invocation includes `--memory`, `--pids-limit`, `--cpus`,
  `--cap-drop=ALL`, `--security-opt=no-new-privileges`.
- Output truncated at 50,000 bytes total.
- Output format must match the example in SPEC.md exactly:
  ```
  exit=<n>
  --- stdout ---
  <stdout>
  --- stderr ---
  <stderr>
  ```

## Deliverable

A single file `sandbox.py` at the repo root that:
1. Exposes `sandbox_run(command, workspace=None, image="debian:stable-slim", timeout=60, network="none", memory="2g", pids=512, cpus=2.0)` returning the formatted output string.
2. Has a `__main__` block exposing the CLI shape from SPEC.md.

## What to do when finished

1. Run any quick smoke tests you wrote (e.g. `python sandbox.py "echo hi"`).
2. Print the final `sandbox.py` contents to confirm.
3. State: "Done. Implementation in sandbox.py."

You may write your own scratch tests in `model_tests/` if useful — they will
not be graded, but they may appear in the diff.

## What NOT to do

- Do not modify `PROMPT.md` or `SPEC.md`.
- Do not add a `requirements.txt`, `pyproject.toml`, `Pipfile`, or any
  dependency manifest.
- Do not create a virtualenv.
- Do not implement persistent sandboxes, image allowlists, or any item under
  "Future (v0.2+)" in SPEC.md.
- Do not split the implementation across multiple modules — one file.
