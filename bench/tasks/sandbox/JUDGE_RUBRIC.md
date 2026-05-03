# Judge rubric: sandbox task

Fill one copy per implementation, saved as `output/<label>_rubric.md`.
Also write `output/<label>_scores.json` with the structured form (see
JUDGE_PROMPT.md).

Implementation reviewed: **`<label>`** (e.g. `A`, `B`, `C`)
File: `implementations/<label>.py`

## Hard-fail (any miss = fail run)

Cite line numbers when something fails.

- [ ] `sandbox.py` exists at the expected location (provided as `<label>.py`)
- [ ] Top-level `sandbox_run(...)` function with signature matching SPEC
- [ ] Subprocess invocation uses argv list / `shell=False` (no host shell
      interpolation of `command`)
- [ ] `network` param defaults to `"none"`
- [ ] No external Python dependencies (stdlib only — `import` statements
      reference only stdlib modules)

Hard-fail result: **pass / fail**
If fail, reasons (with line refs):

## Spec compliance — score 0–10

Award 1 point per item present and correct. Cite line numbers for the
items you award and for the ones you don't.

- [ ] All param defaults match SPEC (`image`, `timeout`, `network`,
      `memory`, `pids`, `cpus`)
- [ ] Resource limits on every podman invocation (`--memory`,
      `--pids-limit`, `--cpus`, `--cap-drop=ALL`,
      `--security-opt=no-new-privileges`)
- [ ] Workspace mount semantics correct (`None` = no mount; path = bind
      r/w at `/workspace` with `-w /workspace`)
- [ ] Output format matches `exit=<n>\n--- stdout ---\n<...>\n--- stderr
      ---\n<...>`
- [ ] 50KB output truncation
- [ ] Timeout returns exit code 124
- [ ] Decoding uses `errors="replace"` (or equivalent — no
      `UnicodeDecodeError` on binary output)
- [ ] CLI: argparse + `--` separator works
- [ ] CLI: default workspace = `os.getcwd()`
- [ ] CLI: exit code matches inner container exit

Subtotal: __ / 10
Notes:

## Hidden tests

**Skip — reviewer fills from `<model>/<task>-<date>/test-output.txt`.**

You did not see the test suite. The aggregator wires objective test
results into the final review.

## Code quality — score each 0–5

- [ ] **Clarity** — naming, structure, function decomposition (0–5): __
- [ ] **Conciseness** — no over-engineering, no unused branches (0–5): __
- [ ] **Error handling** — proportional, fails loud at boundaries (0–5): __
- [ ] **Comments** — only where the *why* is non-obvious (0–5): __

Subtotal: __ / 20

## One-line summary

(One sentence — what stood out.)

## Verdict

ship-with-cleanup / rewrite / unusable
