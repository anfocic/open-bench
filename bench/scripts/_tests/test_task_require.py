"""_task.require() consolidates task-dir-and-required-files validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from . import conftest  # noqa: F401

from bench.scripts import _task


def _setup_tasks_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    tasks = tmp_path / "tasks"
    tasks.mkdir()
    monkeypatch.setenv("OPENBENCH_TASKS_DIR", str(tasks))
    return tasks


def test_missing_task_dir_raises_with_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks = _setup_tasks_dir(tmp_path, monkeypatch)
    with pytest.raises(FileNotFoundError) as exc:
        _task.require("nope")
    assert str(tasks / "nope") in str(exc.value)
    assert "no task at" in str(exc.value)


def test_happy_path_returns_resolved_task_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks = _setup_tasks_dir(tmp_path, monkeypatch)
    (tasks / "foo").mkdir()
    assert _task.require("foo") == tasks / "foo"


def test_required_files_check_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks = _setup_tasks_dir(tmp_path, monkeypatch)
    task = tasks / "foo"
    task.mkdir()
    (task / "PROMPT.md").write_text("x")
    (task / "SPEC.md").write_text("x")
    assert _task.require("foo", ["PROMPT.md", "SPEC.md"]) == task


def test_missing_required_file_names_specific_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tasks = _setup_tasks_dir(tmp_path, monkeypatch)
    task = tasks / "foo"
    task.mkdir()
    (task / "PROMPT.md").write_text("x")
    # SPEC.md missing
    with pytest.raises(FileNotFoundError) as exc:
        _task.require("foo", ["PROMPT.md", "SPEC.md"])
    msg = str(exc.value)
    assert "SPEC.md" in msg
    assert "PROMPT.md" not in msg.replace("SPEC.md", "")
    assert str(task / "SPEC.md") in msg


def test_works_under_default_root_when_env_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPENBENCH_TASKS_DIR", raising=False)
    monkeypatch.setattr(_task._config, "repo_root", lambda: tmp_path)
    (tmp_path / "bench" / "tasks" / "bar").mkdir(parents=True)
    assert _task.require("bar") == tmp_path / "bench" / "tasks" / "bar"
