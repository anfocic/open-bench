"""Shared config loader for bench/ scripts.

Single source of truth for which models compete and which judges are
expert tier. Both Python scripts and bash scripts read from
`bench/config.json` so adding a model / swapping the expert panel
is one edit, not a grep across the repo.
"""

from __future__ import annotations

import json
import pathlib
import subprocess


REPO_ROOT = pathlib.Path(
    subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True
    ).strip()
)

CONFIG_PATH = REPO_ROOT / "bench" / "config.json"


class Config:
    def __init__(self, data: dict) -> None:
        self.implementers: list[str] = list(data.get("implementers", []))
        self.expert_judges: list[str] = list(data.get("expert_judges", []))
        self.harness: str = str(data.get("harness", "opencode"))
        slugs_raw = data.get("slugs", {}) or {}
        self.slugs: dict[str, str] = {str(k): str(v) for k, v in slugs_raw.items()}

        if not self.implementers:
            raise ValueError(f"{CONFIG_PATH}: implementers list is empty")
        # expert_judges may be empty — that means peer-only judging, with
        # no peer-vs-expert delta available in the review. Allowed.

        overlap = set(self.implementers) & set(self.expert_judges)
        if overlap:
            raise ValueError(
                f"{CONFIG_PATH}: {sorted(overlap)} appear in both implementers "
                f"and expert_judges — a model cannot judge its own family"
            )

    def is_expert(self, judge: str) -> bool:
        return judge in self.expert_judges

    def slug_for(self, name: str) -> str:
        """Return the harness model slug (e.g. opencode-go/kimi-k2.6) for an
        implementer label. Raises with a pointer to config.json when missing."""
        if name not in self.slugs:
            raise KeyError(
                f"no slug for '{name}' in {CONFIG_PATH}. "
                f"Add it under the 'slugs' map, e.g.\n"
                f'  "{name}": "opencode-go/<model-id>"'
            )
        return self.slugs[name]


def load() -> Config:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"{CONFIG_PATH} not found. Create it with at minimum:\n"
            f'  {{"implementers": ["..."], "expert_judges": ["..."]}}'
        )
    with open(CONFIG_PATH) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise SystemExit(f"malformed JSON in {CONFIG_PATH}: {e}")
    return Config(data)
