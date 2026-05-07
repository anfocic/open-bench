"""opencode session helpers for capture_run.py.

opencode stores every session it has ever run; `opencode session list
--format json` exposes them with their working directory. Given a
worktree path we can find the matching session, then `opencode export
<id>` returns full JSON with per-message cost + tokens + model slug.

This eliminates the "open three provider dashboards and hand-edit
meta.json" step that was the single biggest fork-friction point.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from . import _stats


class OpencodeNotAvailable(Exception):
    pass


def available() -> bool:
    return shutil.which("opencode") is not None


def find_session_for_directory(directory: str | Path) -> str | None:
    """Return the most recently-updated session whose `directory` matches.

    Returns None if opencode isn't installed, has no sessions, or none of
    its sessions point at this directory. Caller is expected to fall
    back to the legacy transcript.md flow.
    """
    if not available():
        return None
    try:
        out = subprocess.check_output(
            ["opencode", "session", "list", "--format", "json"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return None

    try:
        sessions = json.loads(out)
    except json.JSONDecodeError:
        return None

    target = str(Path(directory).resolve())
    matching = [
        s for s in sessions
        if s.get("directory") and str(Path(s["directory"]).resolve()) == target
    ]
    if not matching:
        return None
    matching.sort(key=lambda s: s.get("updated") or 0, reverse=True)
    return matching[0]["id"]


def export_session(session_id: str) -> dict[str, Any] | None:
    """Return parsed export JSON for `session_id`, or None on failure.

    `opencode export` prints a leading "Exporting session: <id>" line
    before the JSON payload, so we strip everything before the first {.
    """
    if not available():
        return None
    # opencode export truncates stdout to 64KB when piped, so route through
    # a temp file. See: large sessions silently lose payload via subprocess
    # pipes despite exit 0.
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=True) as tmp:
        try:
            subprocess.check_call(
                ["opencode", "export", session_id],
                stdout=tmp,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            return None
        tmp.seek(0)
        raw = tmp.read()

    brace = raw.find("{")
    if brace < 0:
        return None
    try:
        return json.loads(raw[brace:])
    except json.JSONDecodeError:
        return None


def summarize(session: dict[str, Any]) -> dict[str, Any]:
    """Sum per-message cost + tokens. Picks the modal model+provider
    across assistant messages, since a session may contain multiple
    models if the user switched mid-session."""
    cost_usd = 0.0
    tokens_total = 0
    tokens_input = 0
    tokens_output = 0
    tokens_reasoning = 0
    cache_read = 0
    cache_write = 0
    model_counts: dict[tuple[str, str], int] = {}
    started_ms: int | None = None
    ended_ms: int | None = None
    assistant_msgs = 0

    for msg in session.get("messages", []):
        info = msg.get("info", {})
        if info.get("role") != "assistant":
            continue
        assistant_msgs += 1

        cost_usd += float(info.get("cost") or 0)
        toks = info.get("tokens") or {}
        tokens_total += int(toks.get("total") or 0)
        tokens_input += int(toks.get("input") or 0)
        tokens_output += int(toks.get("output") or 0)
        tokens_reasoning += int(toks.get("reasoning") or 0)
        cache = toks.get("cache") or {}
        cache_read += int(cache.get("read") or 0)
        cache_write += int(cache.get("write") or 0)

        provider = info.get("providerID") or ""
        model = info.get("modelID") or info.get("model", {}).get("modelID") or ""
        if provider or model:
            key = (provider, model)
            model_counts[key] = model_counts.get(key, 0) + 1

        time = info.get("time") or {}
        created = time.get("created")
        completed = time.get("completed")
        if isinstance(created, (int, float)) and not isinstance(created, bool):
            started_ms = int(created) if started_ms is None else min(started_ms, int(created))
        if isinstance(completed, (int, float)) and not isinstance(completed, bool):
            ended_ms = int(completed) if ended_ms is None else max(ended_ms, int(completed))

    top = _stats.mode_of_counts(model_counts)
    if top is not None:
        provider, model = top
        model_slug = f"{provider}/{model}" if provider else model
    else:
        model_slug = None

    wall_clock_seconds: float | None = None
    if started_ms is not None and ended_ms is not None and ended_ms >= started_ms:
        wall_clock_seconds = round((ended_ms - started_ms) / 1000.0, 1)

    return {
        "model_slug": model_slug,
        "cost_usd": round(cost_usd, 6),
        "tokens_total": tokens_total,
        "input_tokens": tokens_input,
        "output_tokens": tokens_output,
        "reasoning_tokens": tokens_reasoning,
        "cache_read_tokens": cache_read,
        "cache_write_tokens": cache_write,
        "assistant_message_count": assistant_msgs,
        "model_wall_clock_seconds": wall_clock_seconds,
        "harness": "opencode",
        "harness_version": session.get("info", {}).get("version"),
        "session_id": session.get("info", {}).get("id"),
    }


def render_transcript(session: dict[str, Any]) -> str:
    """Render the session as the same markdown shape as opencode's TUI
    export, so existing transcripts and auto-captured ones look alike.

    We keep this lean — the canonical artifact is the JSON export; the
    markdown is for human reading.
    """
    info = session.get("info", {})
    lines: list[str] = []
    title = info.get("title") or "(untitled)"
    sid = info.get("id") or ""
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"**Session ID:** {sid}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for msg in session.get("messages", []):
        minfo = msg.get("info", {})
        role = minfo.get("role", "unknown")
        if role == "user":
            lines.append("## User")
        elif role == "assistant":
            model = minfo.get("modelID") or ""
            provider = minfo.get("providerID") or ""
            slug = f"{provider}/{model}" if provider else model
            lines.append(f"## Assistant ({slug})" if slug else "## Assistant")
        else:
            lines.append(f"## {role.capitalize()}")
        lines.append("")
        for part in msg.get("parts", []):
            ptype = part.get("type")
            if ptype == "text":
                lines.append(part.get("text", ""))
                lines.append("")
            elif ptype == "reasoning":
                lines.append("_Thinking:_")
                lines.append("")
                lines.append(part.get("text", ""))
                lines.append("")
            elif ptype == "tool":
                tool = part.get("tool") or part.get("name") or "tool"
                lines.append(f"_Tool call: {tool}_")
                lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)
