"""Hidden tests for apply_edit.py.

Models implementing the task never see this file. The harness copies
this directory into the worktree as `_eval_tests/` after the model
finishes, then pytest runs against it.

The central trap of this task is the multi-match-without-replace_all
case. The reference impl in PROMPT.md silently replaces only the first
match; the spec requires raising EditAmbiguous. Tests below cover that
plus the other contract points.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


# --- core: single match -------------------------------------------------


def test_single_match_replaces(apply_edit_module):
    out = apply_edit_module.apply_edit("foo bar baz", "bar", "QUX")
    assert out == "foo QUX baz"


def test_single_match_multiline(apply_edit_module):
    src = "alpha\nbeta\ngamma\n"
    out = apply_edit_module.apply_edit(src, "beta\n", "BETA\n")
    assert out == "alpha\nBETA\ngamma\n"


def test_old_equals_new_returns_unchanged_when_unique(apply_edit_module):
    src = "hello world\n"
    out = apply_edit_module.apply_edit(src, "hello", "hello")
    assert out == src


# --- ValueError: empty old ----------------------------------------------


def test_old_empty_raises_valueerror(apply_edit_module):
    with pytest.raises(ValueError):
        apply_edit_module.apply_edit("anything", "", "x")


def test_old_empty_does_not_raise_edit_error(apply_edit_module):
    # ValueError, specifically — not the task's EditError tree.
    with pytest.raises(ValueError) as excinfo:
        apply_edit_module.apply_edit("anything", "", "x")
    assert not isinstance(excinfo.value, apply_edit_module.EditError)


# --- EditNotFound -------------------------------------------------------


def test_old_missing_raises_notfound(apply_edit_module):
    with pytest.raises(apply_edit_module.EditNotFound):
        apply_edit_module.apply_edit("hello world", "absent", "x")


def test_notfound_inherits_edit_error(apply_edit_module):
    assert issubclass(apply_edit_module.EditNotFound, apply_edit_module.EditError)


def test_notfound_message_includes_old_truncated(apply_edit_module):
    needle = "Z" * 200
    try:
        apply_edit_module.apply_edit("hello", needle, "x")
    except apply_edit_module.EditNotFound as e:
        msg = str(e)
        # Must reference the searched-for string in some form.
        assert "Z" in msg
        # Must not dump the full 200-char needle verbatim.
        assert needle not in msg
    else:
        pytest.fail("EditNotFound was not raised")


# --- EditAmbiguous (the bug) --------------------------------------------


def test_multi_match_default_raises_ambiguous(apply_edit_module):
    src = "foo bar foo bar foo"
    with pytest.raises(apply_edit_module.EditAmbiguous):
        apply_edit_module.apply_edit(src, "foo", "X")


def test_multi_match_default_does_not_silently_replace_first(apply_edit_module):
    """The reference bug: str.replace(..., 1) returns 'X bar foo bar foo'.
    Spec requires raising. Asserting both 'raises' AND 'does not return
    the half-replaced string' makes the failure mode unambiguous."""
    src = "foo bar foo bar foo"
    try:
        result = apply_edit_module.apply_edit(src, "foo", "X")
    except apply_edit_module.EditAmbiguous:
        return
    pytest.fail(
        f"expected EditAmbiguous on multi-match with replace_all=False, "
        f"got result {result!r} (this is the reference-impl bug)"
    )


def test_ambiguous_inherits_edit_error(apply_edit_module):
    assert issubclass(apply_edit_module.EditAmbiguous, apply_edit_module.EditError)


def test_ambiguous_message_includes_count(apply_edit_module):
    src = "x" * 5  # 5 single-char matches
    try:
        apply_edit_module.apply_edit(src, "x", "Y")
    except apply_edit_module.EditAmbiguous as e:
        assert "5" in str(e), f"expected match count '5' in message, got: {e}"
    else:
        pytest.fail("EditAmbiguous was not raised")


def test_ambiguous_two_matches(apply_edit_module):
    """Boundary: exactly 2 matches must raise, not just 3+."""
    with pytest.raises(apply_edit_module.EditAmbiguous):
        apply_edit_module.apply_edit("hello hello", "hello", "hi")


# --- replace_all=True ---------------------------------------------------


def test_multi_match_replace_all_replaces_all(apply_edit_module):
    src = "foo bar foo bar foo"
    out = apply_edit_module.apply_edit(src, "foo", "X", replace_all=True)
    assert out == "X bar X bar X"


def test_replace_all_single_match_still_works(apply_edit_module):
    out = apply_edit_module.apply_edit("hello world", "world", "earth", replace_all=True)
    assert out == "hello earth"


def test_replace_all_zero_match_still_raises_notfound(apply_edit_module):
    with pytest.raises(apply_edit_module.EditNotFound):
        apply_edit_module.apply_edit("hello", "absent", "x", replace_all=True)


# --- byte-exact matching ------------------------------------------------


def test_byte_exact_no_whitespace_normalization(apply_edit_module):
    """Two spaces in old must not match a single space in source."""
    with pytest.raises(apply_edit_module.EditNotFound):
        apply_edit_module.apply_edit("a b c", "a  b", "X")


def test_byte_exact_no_leading_whitespace_strip(apply_edit_module):
    """Source uses tabs; old uses spaces. A whitespace-normalising impl would
    match. A byte-exact impl must not."""
    src = "\tindented = 1\n"
    with pytest.raises(apply_edit_module.EditNotFound):
        apply_edit_module.apply_edit(src, "    indented = 1", "X")


def test_byte_exact_no_case_folding(apply_edit_module):
    with pytest.raises(apply_edit_module.EditNotFound):
        apply_edit_module.apply_edit("Hello", "hello", "x")


def test_preserves_crlf_line_endings(apply_edit_module):
    src = "alpha\r\nbeta\r\ngamma\r\n"
    out = apply_edit_module.apply_edit(src, "beta", "BETA")
    assert out == "alpha\r\nBETA\r\ngamma\r\n"
    # And no \n got smuggled in:
    assert "\n" not in out.replace("\r\n", "")


def test_does_not_touch_lines_that_dont_match(apply_edit_module):
    src = "line1\nline2\nline3\n"
    out = apply_edit_module.apply_edit(src, "line2", "LINE2")
    assert out == "line1\nLINE2\nline3\n"


# --- structural / hard-fail style ---------------------------------------


def test_exception_inheritance(apply_edit_module):
    assert issubclass(apply_edit_module.EditError, Exception)
    assert issubclass(apply_edit_module.EditNotFound, apply_edit_module.EditError)
    assert issubclass(apply_edit_module.EditAmbiguous, apply_edit_module.EditError)
    # Specific subclasses must not be the same class.
    assert apply_edit_module.EditNotFound is not apply_edit_module.EditAmbiguous


def test_no_regex_or_thirdparty_imports():
    """Read the module source and confirm: no `import re`, no third-party imports."""
    src_path = Path(__file__).resolve().parent.parent / "apply_edit.py"
    src = src_path.read_text()
    # Crude but sufficient: any import line referencing `re` as a top-level module.
    bad = []
    for line in src.splitlines():
        s = line.strip()
        if s.startswith("import re") or s.startswith("from re "):
            bad.append(line)
    assert not bad, f"apply_edit.py imports regex: {bad!r}"


def test_apply_edit_does_not_mutate_input(apply_edit_module):
    """Pure function: caller's string identity must remain valid (strings
    are immutable in Python anyway, but this catches anything that
    reassigns globals or does sneaky things)."""
    src = "hello world"
    apply_edit_module.apply_edit(src, "world", "earth")
    assert src == "hello world"


# --- CLI ---------------------------------------------------------------


def _cli_run(stdin_text: str, file_path: Path, *extra: str) -> subprocess.CompletedProcess:
    cli = file_path.parent / "apply_edit.py"
    return subprocess.run(
        [sys.executable, str(cli), str(file_path), *extra],
        input=stdin_text,
        text=True,
        capture_output=True,
        timeout=10,
    )


def _edit_block(old: str, new: str) -> str:
    return f"<<<<<<< OLD\n{old}\n=======\n{new}\n>>>>>>> NEW\n"


def test_cli_single_match_exit_0(tmp_path: Path):
    f = tmp_path / "apply_edit.py"
    target = tmp_path / "target.txt"
    # CLI lives at the worktree root, alongside this temp file's parent
    # would normally be the worktree. Copy the impl in:
    impl = (Path(__file__).resolve().parent.parent / "apply_edit.py").read_text()
    f.write_text(impl)
    target.write_text("foo bar baz\n")
    proc = _cli_run(_edit_block("bar", "QUX"), target)
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    assert target.read_text() == "foo QUX baz\n"


def test_cli_notfound_exit_2(tmp_path: Path):
    f = tmp_path / "apply_edit.py"
    target = tmp_path / "target.txt"
    impl = (Path(__file__).resolve().parent.parent / "apply_edit.py").read_text()
    f.write_text(impl)
    target.write_text("hello world\n")
    proc = _cli_run(_edit_block("absent", "x"), target)
    assert proc.returncode == 2, f"expected exit 2 (EditNotFound), got {proc.returncode}; stderr: {proc.stderr}"
    # Target unchanged.
    assert target.read_text() == "hello world\n"


def test_cli_ambiguous_exit_3(tmp_path: Path):
    f = tmp_path / "apply_edit.py"
    target = tmp_path / "target.txt"
    impl = (Path(__file__).resolve().parent.parent / "apply_edit.py").read_text()
    f.write_text(impl)
    target.write_text("foo foo foo\n")
    proc = _cli_run(_edit_block("foo", "bar"), target)
    assert proc.returncode == 3, f"expected exit 3 (EditAmbiguous), got {proc.returncode}; stderr: {proc.stderr}"
    # Target unchanged — no half-applied edit on disk.
    assert target.read_text() == "foo foo foo\n"


def test_cli_replace_all_flag(tmp_path: Path):
    f = tmp_path / "apply_edit.py"
    target = tmp_path / "target.txt"
    impl = (Path(__file__).resolve().parent.parent / "apply_edit.py").read_text()
    f.write_text(impl)
    target.write_text("foo foo foo\n")
    proc = _cli_run(_edit_block("foo", "X"), target, "--replace-all")
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    assert target.read_text() == "X X X\n"
