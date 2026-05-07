"""OPENBENCH_TASKS_DIR env override resolves task locations from arbitrary paths."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from . import conftest  # noqa: F401

from bench.scripts import _task


def test_tasks_dir_default_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENBENCH_TASKS_DIR", raising=False)
    monkeypatch.setattr(_task._config, "repo_root", lambda: Path("/fake/root"))
    assert _task.tasks_dir() == Path("/fake/root/bench/tasks")


def test_task_dir_composes_with_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENBENCH_TASKS_DIR", raising=False)
    monkeypatch.setattr(_task._config, "repo_root", lambda: Path("/fake/root"))
    assert _task.task_dir("foo") == Path("/fake/root/bench/tasks/foo")


def test_env_override_absolute_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENBENCH_TASKS_DIR", str(tmp_path))
    assert _task.tasks_dir() == tmp_path
    assert _task.task_dir("foo") == tmp_path / "foo"


def test_env_override_expanduser(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENBENCH_TASKS_DIR", "~/custom/tasks")
    resolved = _task.tasks_dir()
    assert "~" not in str(resolved)
    assert str(resolved).endswith("/custom/tasks")


def test_load_reads_task_json_from_overridden_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = tmp_path / "mytask"
    task.mkdir()
    (task / "task.json").write_text(json.dumps({
        "entrypoint": "main.go",
        "language": "go",
    }))
    monkeypatch.setenv("OPENBENCH_TASKS_DIR", str(tmp_path))
    cfg = _task.load("mytask")
    assert cfg["entrypoint"] == "main.go"
    assert cfg["language"] == "go"
    # Defaults still present for unspecified keys.
    assert cfg["loc_method"] == "non_blank_non_comment_lines"


def test_env_override_takes_precedence_over_repo_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENBENCH_TASKS_DIR", str(tmp_path))
    monkeypatch.setattr(_task._config, "repo_root", lambda: Path("/should/not/be/used"))
    assert _task.tasks_dir() == tmp_path
