"""Shared config loader for bench/ scripts.

Single source of truth for which models compete and which judges are
expert tier. Both Python scripts and bash scripts read from
`bench/config.json` so adding a model / swapping the expert panel
is one edit, not a grep across the repo.
"""

from __future__ import annotations

import functools
import json
import os
import pathlib
import subprocess
from typing import Any


@functools.lru_cache(maxsize=1)
def repo_root() -> pathlib.Path:
    return pathlib.Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        ).strip()
    )


def config_path() -> pathlib.Path:
    """Resolve the config.json path. Honours OPENBENCH_CONFIG when set so
    a downstream consumer can run the harness against its own lineup
    without forking. Defaults to <repo_root>/bench/config.json.
    """
    override = os.environ.get("OPENBENCH_CONFIG")
    if override:
        return pathlib.Path(override).expanduser()
    return repo_root() / "bench" / "config.json"


class Config:
    def __init__(self, data: dict[str, Any]) -> None:
        self.implementers: list[str] = list(data.get("implementers", []))
        self.expert_judges: list[str] = list(data.get("expert_judges", []))
        self.harness: str = str(data.get("harness", "opencode"))
        slugs_raw = data.get("slugs", {}) or {}
        self.slugs: dict[str, str] = {str(k): str(v) for k, v in slugs_raw.items()}

        if not self.implementers:
            raise ValueError(f"{config_path()}: implementers list is empty")
        # expert_judges may be empty — that means peer-only judging, with
        # no peer-vs-expert delta available in the review. Allowed.

        overlap = set(self.implementers) & set(self.expert_judges)
        if overlap:
            raise ValueError(
                f"{config_path()}: {sorted(overlap)} appear in both implementers "
                f"and expert_judges — a model cannot judge its own family"
            )

    def is_expert(self, judge: str) -> bool:
        return judge in self.expert_judges

    def slug_for(self, name: str) -> str:
        """Return the harness model slug (e.g. opencode-go/kimi-k2.6) for an
        implementer label. Raises with a pointer to config.json when missing."""
        if name not in self.slugs:
            raise KeyError(
                f"no slug for '{name}' in {config_path()}. "
                f"Add it under the 'slugs' map, e.g.\n"
                f'  "{name}": "opencode-go/<model-id>"'
            )
        return self.slugs[name]


def load() -> Config:
    """Read bench/config.json and return a validated Config.

    Raises FileNotFoundError when the file is missing (with a hint at
    the minimal schema), and SystemExit when the file exists but is
    malformed JSON. Validation errors raised by Config (empty
    implementers, judge/implementer overlap) propagate as ValueError.
    """
    cfg_path = config_path()
    if not cfg_path.exists():
        raise FileNotFoundError(
            f"{cfg_path} not found. Create it with at minimum:\n"
            f'  {{"implementers": ["..."], "expert_judges": ["..."]}}'
        )
    with open(cfg_path) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise SystemExit(f"malformed JSON in {cfg_path}: {e}")
    return Config(data)
