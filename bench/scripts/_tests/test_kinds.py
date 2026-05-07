"""Registry + resolver behaviour for the task-kind plugin scaffolding."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from . import conftest  # noqa: F401

from bench.scripts import _kinds, _task
from bench.scripts._kinds.code import CodeTask


def test_get_code_returns_code_task() -> None:
    assert isinstance(_kinds.get("code"), CodeTask)


def test_get_unknown_raises_with_known_kinds() -> None:
    with pytest.raises(ValueError) as exc:
        _kinds.get("nonexistent")
    msg = str(exc.value)
    assert "nonexistent" in msg
    assert "code" in msg


def test_get_returns_fresh_instance_each_call() -> None:
    a = _kinds.get("code")
    b = _kinds.get("code")
    assert a is not b
    assert type(a) is type(b) is CodeTask


def test_load_defaults_task_kind_to_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENBENCH_TASKS_DIR", raising=False)
    # Tasks dir doesn't need to exist for load() — when task.json is absent,
    # DEFAULTS is returned verbatim.
    monkeypatch.setattr(_task._config, "repo_root", lambda: Path("/nonexistent"))
    cfg = _task.load("anything")
    assert cfg["task_kind"] == "code"


def _setup_task(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    task_json: dict | None,
) -> None:
    tasks = tmp_path / "tasks"
    task = tasks / "foo"
    task.mkdir(parents=True)
    if task_json is not None:
        (task / "task.json").write_text(json.dumps(task_json))
    monkeypatch.setenv("OPENBENCH_TASKS_DIR", str(tasks))


def test_kind_for_default_when_task_json_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_task(tmp_path, monkeypatch, task_json=None)
    assert isinstance(_task.kind_for("foo"), CodeTask)


def test_kind_for_explicit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_task(tmp_path, monkeypatch, task_json={"task_kind": "code"})
    assert isinstance(_task.kind_for("foo"), CodeTask)


def test_kind_for_unknown_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_task(tmp_path, monkeypatch, task_json={"task_kind": "bogus"})
    with pytest.raises(ValueError) as exc:
        _task.kind_for("foo")
    assert "bogus" in str(exc.value)
