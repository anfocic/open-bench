"""OPENBENCH_CONFIG env override resolves config.json from arbitrary paths."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from . import conftest  # noqa: F401

from bench.scripts import _config


def test_default_path_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENBENCH_CONFIG", raising=False)
    monkeypatch.setattr(_config, "repo_root", lambda: Path("/fake/root"))
    assert _config.config_path() == Path("/fake/root/bench/config.json")


def test_env_override_absolute_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "elsewhere" / "config.json"
    cfg.parent.mkdir()
    cfg.write_text(json.dumps({
        "implementers": ["a"],
        "expert_judges": [],
        "slugs": {"a": "opencode-go/a"},
    }))
    monkeypatch.setenv("OPENBENCH_CONFIG", str(cfg))
    assert _config.config_path() == cfg
    loaded = _config.load()
    assert loaded.implementers == ["a"]


def test_env_override_expanduser(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENBENCH_CONFIG", "~/custom/config.json")
    resolved = _config.config_path()
    assert "~" not in str(resolved)
    assert str(resolved).endswith("/custom/config.json")


def test_env_override_takes_precedence_over_repo_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "override.json"
    cfg.write_text(json.dumps({
        "implementers": ["override-only"],
        "expert_judges": [],
        "slugs": {"override-only": "opencode-go/x"},
    }))
    monkeypatch.setenv("OPENBENCH_CONFIG", str(cfg))
    monkeypatch.setattr(_config, "repo_root", lambda: Path("/should/not/be/used"))
    assert _config.load().implementers == ["override-only"]
