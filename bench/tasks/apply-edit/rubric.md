# Rubric: apply-edit task

Reviewer fills one copy of this per run, stored in `results/reviews/`.

## Hard-fail (any miss = run fails, do not score the rest)

- [ ] `apply_edit.py` exists at worktree root
- [ ] `apply_edit(file_text, old, new, *, replace_all=False)` present with SPEC signature
- [ ] `EditError`, `EditNotFound`, `EditAmbiguous` defined
- [ ] `EditNotFound` and `EditAmbiguous` inherit from `EditError`
- [ ] Stdlib only (no third-party imports, no dep manifests)
- [ ] No regex (`import re`) — literal substring match only
- [ ] `apply_edit` is pure: no I/O / logging / globals

## Spec compliance — score 0–10

Award 1 point per item:

- [ ] `old == ""` → `ValueError`
- [ ] `old not in file_text` → `EditNotFound`
- [ ] `EditNotFound` message includes (a truncated form of) `old`
- [ ] Single match → returns text with that occurrence replaced
- [ ] Multi-match w/ `replace_all=False` → raises `EditAmbiguous` (the bug)
- [ ] `EditAmbiguous` message includes match count
- [ ] Multi-match w/ `replace_all=True` → replaces all
- [ ] Byte-exact match (no whitespace/case/line-ending normalization)
- [ ] CLI exit codes 0 / 2 / 3 / 1 per spec
- [ ] CLI `--replace-all` flag wired through

Subtotal: __ / 10

## Hidden test results

Filled by `capture_run.py`. One row per test:

| Test | Pass / Fail / Skip | Notes |
|---|---|---|
| `test_single_match_replaces` | | |
| `test_old_empty_raises_valueerror` | | |
| `test_old_missing_raises_notfound` | | |
| `test_notfound_message_includes_old_truncated` | | |
| `test_multi_match_default_raises_ambiguous` | | |
| `test_ambiguous_message_includes_count` | | |
| `test_multi_match_replace_all_replaces_all` | | |
| `test_byte_exact_no_whitespace_normalization` | | |
| `test_byte_exact_no_case_folding` | | |
| `test_preserves_crlf_line_endings` | | |
| `test_old_equals_new_returns_unchanged_when_unique` | | |
| `test_exception_inheritance` | | |
| `test_no_regex_or_thirdparty_imports` | | |
| `test_cli_single_match_exit_0` | | |
| `test_cli_notfound_exit_2` | | |
| `test_cli_ambiguous_exit_3` | | |
| `test_cli_replace_all_flag` | | |

Tests passed: __ / 17

## Code quality — score each 0–5

- [ ] **Clarity** — naming, structure, function decomposition
- [ ] **Conciseness** — no over-engineering, no unused branches
- [ ] **Error handling** — distinct exceptions per spec, CLI exit codes correct
- [ ] **Comments** — `# bug in reference:` line naming the bug; otherwise WHY-non-obvious only

Subtotal: __ / 20

## Bug diagnosis (informational)

- [ ] Model identified the multi-match-silent-replace bug correctly: yes / no / vague
- Quote of the model's `# bug in reference:` line:

## Cost

- LOC added (excluding blank/comment): ___
- Wall-clock time (start → done): ___ minutes
- Token cost (if available): ___

## Reviewer summary

One paragraph: did the model spot the bug, ship a clean fix, or
inherit the reference's bug? Any over-correction?

## Total score

Hard-fail pass: yes / no
Spec compliance: __ / 10
Tests passed: __ / 17
Code quality: __ / 20
**Total** (only if hard-fail passed): __ / 47
