"""Code task kind: entrypoint + pytest + LOC.

`extract_artifact` is the per-task code-specific subset of capture: it
computes the diff against the base branch, copies modified source files
into the run dir, promotes the entrypoint to the model dir, runs the
hidden test suite, and counts LOC. The orchestrator (`capture_run.py`)
remains responsible for run-dir lifecycle, meta.json, transcript
handling, and operator-facing UX.

`assemble_packet` and `score` are the per-judge code-specific subset of
the judgment phase: packet assembly (the four task files +
blinded `implementations/<label><suffix>` layout) and the per-judge
opencode invocation. The orchestrator (`start_judgments.py`) remains
responsible for run discovery, label assignment, pairings/runs_index/
judgment_meta.json, and the threadpool fanout across judges.

`aggregate` is the code-rubric-specific report renderer: it loads each
judge's structured scores, splits them by tier (expert / peer / self),
medians them, lays out the scoreboard / per-judge / per-impl / inter-
judge / self-bias / cost tables, and returns the markdown. The
orchestrator (`aggregate_judges.py`) only resolves the judgment dir,
reads the three top-level meta files, and writes the rendered review
to disk.
"""

from __future__ import annotations

import functools
import json
import os
import pathlib
import shutil
import statistics
import subprocess
import time
from typing import Any

from .. import _config
from .. import _git
from .. import _logging
from .. import _opencode_run
from .. import _pytest_parse
from .. import _stats
from .. import _task

log = _logging.get_logger(__name__)
_run_git = _git.run_git


class CodeTask:
    def extract_artifact(
        self,
        *,
        worktree: pathlib.Path,
        run_dir: pathlib.Path,
        model_dir: pathlib.Path,
        task_dir: pathlib.Path,
        task_cfg: dict[str, Any],
        base_branch: str,
    ) -> dict[str, Any]:
        """Capture the code-specific artifacts of a finished run.

        Side effects (filesystem):
          - writes <run_dir>/diff.patch
          - copies each modified source file matching the entrypoint
            extension/basename into <run_dir>/<rel>
          - promotes <run_dir>/<entrypoint> to <model_dir>/<entrypoint>
          - writes <run_dir>/test-output.txt
          - ephemerally copies task tests into <worktree>/_eval_tests/,
            runs them, removes the dir on the way out

        Returns the subset of meta.json fields owned by the code-task:
        base_commit, entrypoint, impl_loc, test_exit_code.
        """
        entrypoint = task_cfg["entrypoint"]
        test_invocation = task_cfg["test_invocation"]
        loc_method = task_cfg["loc_method"]

        base = _run_git("merge-base", "HEAD", base_branch,
                         cwd=worktree, check=False).strip()
        if not base:
            base = _run_git("rev-parse", base_branch, cwd=worktree).strip()

        diff_lines: list[str] = []
        diff_lines.append(_run_git(
            "diff", f"{base}...HEAD", "--", ".", ":!PROMPT.md", ":!SPEC.md",
            cwd=worktree, check=False))
        diff_lines.append(_run_git(
            "diff", "HEAD", "--", ".", ":!PROMPT.md", ":!SPEC.md",
            cwd=worktree, check=False))

        untracked = _run_git(
            "ls-files", "--others", "--exclude-standard",
            cwd=worktree).strip().splitlines()
        for f in untracked:
            f = f.strip()
            if not f or f in ("PROMPT.md", "SPEC.md", "transcript.md"):
                continue
            if f.startswith("_eval_tests/"):
                continue
            fpath = worktree / f
            if not fpath.exists():
                continue
            try:
                result = subprocess.run(
                    ["git", "diff", "--no-index", "--no-color",
                     "/dev/null", str(fpath)],
                    cwd=worktree, capture_output=True, text=True, check=False,
                )
                diff_lines.append(result.stdout)
            except OSError:
                # git binary missing or fpath unreadable — skip; the rest
                # of the diff still captures.
                pass

        (run_dir / "diff.patch").write_text("\n".join(diff_lines))

        suffix = pathlib.Path(entrypoint).suffix
        # Empty suffix → fall back to entrypoint basename. Otherwise `*""`
        # expands to `*` and matches every path in the worktree.
        pathspec = f"*{suffix}" if suffix else pathlib.Path(entrypoint).name
        modified_ext = _run_git(
            "diff", "--name-only", base, "--", pathspec,
            cwd=worktree, check=False).strip().splitlines()
        modified_ext += _run_git(
            "diff", "--name-only", "HEAD", "--", pathspec,
            cwd=worktree, check=False).strip().splitlines()
        untracked_ext = _run_git(
            "ls-files", "--others", "--exclude-standard", pathspec,
            cwd=worktree).strip().splitlines()

        all_modified = sorted(set(
            f.strip() for f in modified_ext + untracked_ext
            if f.strip() and not f.strip().startswith("_eval_tests/")
        ))

        for rel in all_modified:
            src = worktree / rel
            if not src.is_file():
                continue
            dest = run_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

        if (run_dir / entrypoint).exists():
            shutil.copy2(run_dir / entrypoint, model_dir / entrypoint)

        eval_dir = worktree / "_eval_tests"
        if eval_dir.exists():
            shutil.rmtree(eval_dir)
        eval_dir.mkdir()

        tests_src = task_dir / "tests"
        if not tests_src.is_dir():
            shutil.rmtree(eval_dir, ignore_errors=True)
            raise FileNotFoundError(f"no tests dir at {tests_src}")

        shutil.copytree(tests_src, eval_dir, dirs_exist_ok=True)

        test_timeout = int(os.environ.get("CAPTURE_TEST_TIMEOUT", "300"))
        try:
            proc = subprocess.run(
                test_invocation,
                cwd=str(worktree),
                capture_output=True,
                text=True,
                timeout=test_timeout,
            )
            test_exit = proc.returncode
            test_stdout = proc.stdout
            test_stderr = proc.stderr
        except subprocess.TimeoutExpired as e:
            log.error("hidden tests timed out after %ds — recording exit 124. "
                      "Override with CAPTURE_TEST_TIMEOUT=<seconds>.",
                      test_timeout)
            test_exit = 124
            test_stdout = (e.stdout.decode(errors="replace")
                           if isinstance(e.stdout, bytes)
                           else (e.stdout or ""))
            test_stderr = (e.stderr.decode(errors="replace")
                           if isinstance(e.stderr, bytes)
                           else (e.stderr or ""))
        (run_dir / "test-output.txt").write_text(
            test_stdout + "\n--- stderr ---\n" + test_stderr)

        shutil.rmtree(eval_dir, ignore_errors=True)

        impl_path = worktree / entrypoint
        loc = _task.loc_count(impl_path, loc_method) if impl_path.exists() else 0

        return {
            "base_commit": base,
            "entrypoint": entrypoint,
            "impl_loc": loc,
            "test_exit_code": test_exit,
        }

    def assemble_packet(
        self,
        *,
        task_dir: pathlib.Path,
        judge_dir: pathlib.Path,
        impls: list[dict],
        mapping: dict[str, str],
        entrypoint: str,
    ) -> None:
        """Write one judge's packet at judge_dir.

        Side effects (filesystem):
          - <judge_dir>/packet/{PROMPT.md, SPEC.md, JUDGE_PROMPT.md,
            JUDGE_RUBRIC.md} (each copied from task_dir if present)
          - <judge_dir>/packet/implementations/<label><suffix> per impl
            in mapping, blinded
          - <judge_dir>/packet/README.md cover note
          - <judge_dir>/output/ (empty — judge fills it)
        """
        packet = judge_dir / "packet"
        impl_dir = packet / "implementations"
        output = judge_dir / "output"
        impl_dir.mkdir(parents=True, exist_ok=True)
        output.mkdir(parents=True, exist_ok=True)

        for fname in ["PROMPT.md", "SPEC.md", "JUDGE_PROMPT.md", "JUDGE_RUBRIC.md"]:
            src = task_dir / fname
            if src.exists():
                shutil.copy2(src, packet / fname)

        suffix = pathlib.Path(entrypoint).suffix
        for impl in impls:
            if impl["model"] not in mapping:
                continue
            label = mapping[impl["model"]]
            shutil.copy2(impl["impl_path"], impl_dir / f"{label}{suffix}")

        labels = sorted(mapping.values())
        cover = packet / "README.md"
        cover.write_text(
            f"# Judgment packet\n\n"
            f"Implementations to review (blinded labels): {', '.join(labels)}\n\n"
            f"Read PROMPT.md and SPEC.md first to understand what was asked.\n"
            f"Then read JUDGE_PROMPT.md for your task and the output format.\n"
            f"Score each implementation independently. Write outputs to ../output/.\n"
        )

    def score(
        self,
        *,
        judge: str,
        judge_dir: pathlib.Path,
        slug: str,
        message: str,
        log_path: pathlib.Path | None,
        out_root_name: str,
    ) -> tuple[int, float]:
        """Drive a single judge through `opencode run`.

        Returns (rc, elapsed_seconds). Caller is responsible for skipping
        judges whose slug isn't in config — this helper assumes the slug
        exists. With log_path=None, opencode inherits stdout (sequential
        mode); with log_path set, output is redirected so concurrent
        judges' streams don't interleave.
        """
        title = f"{out_root_name}-{judge}"
        started = time.monotonic()
        rc = _opencode_run.run(
            directory=judge_dir,
            model=slug,
            message=message,
            title=title,
            log_path=log_path,
        )
        return rc, time.monotonic() - started

    def aggregate(
        self,
        *,
        judgment_dir: pathlib.Path,
        judgment_meta: dict[str, Any],
        pairings: dict[str, dict[str, str]],
        runs_index: dict[str, dict[str, Any]],
        repo_root: pathlib.Path,
    ) -> str:
        """Render the code-rubric review as markdown.

        Loads each judge's `<label>_scores.json`, parses each impl's
        `test-output.txt` from its run dir under `repo_root`, and
        assembles the multi-section markdown report. Returns the report
        as a string; caller is responsible for writing it to disk.
        """
        scores_by_judge: dict[str, dict[str, dict[str, Any] | None]] = {}
        for judge, mapping in pairings.items():
            scores_by_judge[judge] = _load_judge_scores(
                judgment_dir / judge, mapping
            )

        test_results: dict[str, dict] = {}
        for model, entry in runs_index.items():
            rel_run = entry["path"]
            run_dir = repo_root / rel_run
            out = run_dir / "test-output.txt"
            if not out.exists():
                log.warning("%s/test-output.txt missing — tests=0/0", rel_run)
                test_results[model] = {"passed": 0, "failed": 0,
                                       "skipped": 0, "errors": 0,
                                       "per_test": {}}
                continue
            test_results[model] = _pytest_parse.parse_pytest_output(
                out.read_text()
            )

        return _render_review(
            task=judgment_meta["task"],
            date_stamp=judgment_meta["date_stamp"],
            judgment_dir=judgment_dir,
            pairings=pairings,
            runs_index=runs_index,
            scores_by_judge=scores_by_judge,
            test_results=test_results,
        )


# ---------------------------------------------------------------------------
# Code-rubric helpers (private to the kind). Module-level functions, not
# methods, because they're stateless and were lifted wholesale from
# aggregate_judges.py during the v0.2 carve.
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=1)
def _expert_judges() -> frozenset[str]:
    return frozenset(_config.load().expert_judges)


def _is_score(x: Any) -> bool:
    """Return True if x is a numeric score. Excludes bool: a judge writing
    `"spec_compliance": true` is a malformed score, not a 1."""
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _fmt_int(v: float | int | None) -> str:
    if v is None:
        return "—"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, float):
        return f"{v:.1f}"
    return str(v)


def quality_total(q: dict[str, Any] | None) -> int | None:
    if not q:
        return None
    keys = ("clarity", "conciseness", "error_handling", "comments")
    parts = [q.get(k) for k in keys if _is_score(q.get(k))]
    if len(parts) != 4:
        return None
    return sum(parts)


def _load_judge_scores(judge_dir: pathlib.Path,
                       mapping: dict[str, str]) -> dict[str, dict[str, Any] | None]:
    out_dir = judge_dir / "output"
    by_model: dict[str, dict[str, Any] | None] = {}
    for model, label in mapping.items():
        f = out_dir / f"{label}_scores.json"
        if not f.exists():
            by_model[model] = None
            continue
        try:
            by_model[model] = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            log.warning("%s not valid JSON: %s", f, e)
            by_model[model] = None
    return by_model


def _load_run_meta(repo_root: pathlib.Path, run_dir_rel: str) -> dict[str, Any]:
    p = repo_root / run_dir_rel / "meta.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return {}


def _get_impl_loc(meta: dict[str, Any]) -> int | str:
    if "impl_loc" in meta:
        return meta["impl_loc"]
    if "sandbox_py_loc" in meta:
        return meta["sandbox_py_loc"]
    return "—"


def _split_judge_scores(judges: list[str],
                        scores_by_judge: dict[str, dict[str, dict[str, Any] | None]],
                        model: str) -> dict[str, Any]:
    expert_specs: list[float] = []
    expert_quals: list[float] = []
    peer_specs: list[float] = []
    peer_quals: list[float] = []
    all_specs: list[float] = []
    all_quals: list[float] = []
    self_spec: float | None = None
    self_qual: float | None = None
    verdicts: list[str] = []
    hard_fails: list[str] = []

    for judge in judges:
        s = scores_by_judge.get(judge, {}).get(model)
        if s is None:
            continue
        spec = s.get("spec_compliance")
        qt = quality_total(s.get("code_quality"))
        is_expert = judge in _expert_judges()
        is_self = judge == model
        if _is_score(spec):
            if is_self:
                self_spec = spec
            else:
                all_specs.append(spec)
                (expert_specs if is_expert else peer_specs).append(spec)
        if qt is not None:
            if is_self:
                self_qual = qt
            else:
                all_quals.append(qt)
                (expert_quals if is_expert else peer_quals).append(qt)
        if s.get("verdict"):
            verdicts.append(s["verdict"])
        if s.get("hard_fail"):
            hard_fails.append(s["hard_fail"])

    return {
        "expert_specs": expert_specs,
        "expert_quals": expert_quals,
        "peer_specs": peer_specs,
        "peer_quals": peer_quals,
        "all_specs": all_specs,
        "all_quals": all_quals,
        "self_spec": self_spec,
        "self_qual": self_qual,
        "verdicts": verdicts,
        "hard_fails": hard_fails,
    }


def _render_scoreboard(impl_models: list[str], judges: list[str],
                       scores_by_judge: dict[str, Any],
                       test_results: dict[str, Any]) -> list[str]:
    lines = ["## Scoreboard", ""]
    lines.append(
        "Three medians shown so reader can compare expert vs peer consensus. "
        "Hidden test results are objective (pulled from each run's "
        "`test-output.txt`) and shown alongside for triangulation."
    )
    lines.append("")
    lines.append("| Impl | Hard-fail | Spec — all | Spec — expert | Spec — peer | "
                 "Quality — all | Quality — expert | Quality — peer | "
                 "Tests | Verdict (mode) |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")

    for model in impl_models:
        sp = _split_judge_scores(judges, scores_by_judge, model)

        hf_summary = "pass"
        if any(h == "fail" for h in sp["hard_fails"]):
            fails = sum(1 for h in sp["hard_fails"] if h == "fail")
            hf_summary = f"fail ({fails}/{len(sp['hard_fails'])})"

        verdict_mode = _stats.mode(sp["verdicts"]) or "—"

        tests = test_results.get(model, {})
        total_tests = sum(tests.get(k, 0) for k in ("passed", "failed", "skipped", "errors"))
        tests_str = f"{tests.get('passed', 0)}/{total_tests}" if total_tests else "—"

        lines.append(
            f"| {model} | {hf_summary} | "
            f"{_fmt_int(_stats.median(sp['all_specs']))} | "
            f"{_fmt_int(_stats.median(sp['expert_specs']))} | "
            f"{_fmt_int(_stats.median(sp['peer_specs']))} | "
            f"{_fmt_int(_stats.median(sp['all_quals']))} | "
            f"{_fmt_int(_stats.median(sp['expert_quals']))} | "
            f"{_fmt_int(_stats.median(sp['peer_quals']))} | "
            f"{tests_str} | {verdict_mode} |"
        )
    lines.append("")
    return lines


def _render_per_judge_ranking(impl_models: list[str], judges: list[str],
                              scores_by_judge: dict[str, Any]) -> list[str]:
    lines = ["## Per-judge ranking by spec compliance", ""]
    lines.append("How each judge ranked the implementations (highest spec score first). "
                 "If a judge gave equal scores, ordering is alphabetical.")
    lines.append("")
    lines.append("| Judge | 1st | 2nd | 3rd |")
    lines.append("|---|---|---|---|")

    for judge in judges:
        ranked: list[tuple[float, str]] = []
        for model in impl_models:
            s = scores_by_judge.get(judge, {}).get(model)
            if s is None:
                continue
            spec = s.get("spec_compliance")
            if _is_score(spec):
                ranked.append((spec, model))
        ranked.sort(key=lambda x: (-x[0], x[1]))
        cols = []
        for i in range(3):
            if i < len(ranked):
                spec, model = ranked[i]
                cols.append(f"{model} ({_fmt_int(spec)})")
            else:
                cols.append("—")
        lines.append(f"| {judge} | " + " | ".join(cols) + " |")
    lines.append("")
    return lines


def _render_per_implementation(impl_models: list[str], judges: list[str],
                               scores_by_judge: dict[str, Any],
                               runs_index: dict[str, dict[str, Any]],
                               test_results: dict[str, Any]) -> list[str]:
    lines = ["## Per-implementation detail", ""]
    for model in impl_models:
        lines.append(f"### {model}")
        lines.append("")
        run_dir = runs_index.get(model, {}).get("path", "—")
        lines.append(f"Run: `{run_dir}`")
        lines.append("")
        lines.append("| Judge | Tier | Hard-fail | Spec /10 | Quality /20 | Verdict | Note |")
        lines.append("|---|---|---|---|---|---|---|")
        for judge in judges:
            s = scores_by_judge.get(judge, {}).get(model)
            if judge == model:
                tier = "self"
            elif judge in _expert_judges():
                tier = "expert"
            else:
                tier = "peer"
            if s is None:
                lines.append(f"| {judge} | {tier} | (no scores file) | — | — | — | — |")
                continue
            qt = quality_total(s.get("code_quality"))
            note = s.get("one_line_summary", "").replace("|", "\\|")
            if len(note) > 80:
                note = note[:77] + "..."
            lines.append(
                f"| {judge} | {tier} | {s.get('hard_fail', '—')} | "
                f"{_fmt_int(s.get('spec_compliance'))} | "
                f"{_fmt_int(qt)} | "
                f"{s.get('verdict', '—')} | {note} |"
            )
        lines.append("")

        tests = test_results.get(model, {})
        if tests.get("per_test"):
            lines.append("**Hidden test results** (objective):")
            lines.append("")
            for name, verdict in sorted(tests["per_test"].items()):
                lines.append(f"- `{name}` — {verdict}")
            lines.append("")
    return lines


def _render_inter_judge_agreement(impl_models: list[str], judges: list[str],
                                  scores_by_judge: dict[str, Any]) -> list[str]:
    lines = ["## Inter-judge agreement", ""]
    lines.append("Spec-score variance across judges per implementation. High range "
                 "= judges disagreed on the same code. Worth investigating.")
    lines.append("")
    lines.append("| Impl | Min spec | Max spec | Range | Stdev | Judges who scored |")
    lines.append("|---|---|---|---|---|---|")
    for model in impl_models:
        scores: list[tuple[str, float]] = []
        for judge in judges:
            s = scores_by_judge.get(judge, {}).get(model)
            if s is None:
                continue
            spec = s.get("spec_compliance")
            if _is_score(spec):
                scores.append((judge, float(spec)))
        if len(scores) < 2:
            lines.append(f"| {model} | — | — | — | — | "
                         f"{', '.join(j for j, _ in scores) or '—'} |")
            continue
        vals = [v for _, v in scores]
        mn, mx = min(vals), max(vals)
        try:
            sd = statistics.stdev(vals)
        except statistics.StatisticsError:
            sd = 0.0
        lines.append(f"| {model} | {_fmt_int(mn)} | {_fmt_int(mx)} | {_fmt_int(mx - mn)} | "
                     f"{sd:.2f} | {', '.join(j for j, _ in scores)} |")
    lines.append("")

    best_per_judge: dict[str, str | None] = {}
    for judge in judges:
        candidates: list[tuple[float, str]] = []
        for model in impl_models:
            s = scores_by_judge.get(judge, {}).get(model)
            if s is None:
                continue
            spec = s.get("spec_compliance")
            if _is_score(spec):
                candidates.append((spec, model))
        candidates.sort(key=lambda x: (-x[0], x[1]))
        best_per_judge[judge] = candidates[0][1] if candidates else None

    chose: dict[str, list[str]] = {}
    for judge, m in best_per_judge.items():
        if m is None:
            continue
        chose.setdefault(m, []).append(judge)

    lines.append("**Best impl per judge:**")
    lines.append("")
    for m in impl_models:
        if m in chose:
            lines.append(f"- **{m}** — chosen best by: {', '.join(chose[m])}")
    lines.append("")
    return lines


def _render_self_bias_check(impl_models: list[str], judges: list[str],
                            scores_by_judge: dict[str, Any]) -> list[str]:
    lines = ["## Self-bias check", ""]
    has_self_data = any(
        _split_judge_scores(judges, scores_by_judge, m)["self_spec"] is not None
        or _split_judge_scores(judges, scores_by_judge, m)["self_qual"] is not None
        for m in impl_models
    )
    if not has_self_data:
        lines.append(
            "No self-judgments found. Self-judging is enabled in "
            "`start_judgments.py` (every judge scores every impl, "
            "including its own); if this section is empty, judges may "
            "have skipped self-rows or scores files are missing."
        )
        lines.append("")
        return lines

    lines.append(
        "Δ = `self − peer median`. Positive = the model scored its own "
        "code higher than peers did (overrating itself). Self-judgments "
        "are excluded from the headline scoreboard above so the medians "
        "there are not self-inflated."
    )
    lines.append("")
    if _expert_judges():
        peer_label = "Peer (excl. self) med"
    else:
        peer_label = "Peer med"
    lines.append(
        f"| Impl | Self spec | {peer_label} spec | Δ spec | "
        f"Self qual | {peer_label} qual | Δ qual |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for model in impl_models:
        sp = _split_judge_scores(judges, scores_by_judge, model)
        s_spec = sp["self_spec"]
        s_qual = sp["self_qual"]
        comp_spec = _stats.median(sp["peer_specs"])
        comp_qual = _stats.median(sp["peer_quals"])
        d_spec = (s_spec - comp_spec) if (s_spec is not None and comp_spec is not None) else None
        d_qual = (s_qual - comp_qual) if (s_qual is not None and comp_qual is not None) else None
        lines.append(
            f"| {model} | {_fmt_int(s_spec)} | {_fmt_int(comp_spec)} | "
            f"{_fmt_int(d_spec)} | {_fmt_int(s_qual)} | "
            f"{_fmt_int(comp_qual)} | {_fmt_int(d_qual)} |"
        )
    lines.append("")
    return lines


def _render_judge_cost(judges: list[str], judgment_dir: pathlib.Path) -> list[str]:
    lines = ["## Judging cost & efficiency", ""]
    lines.append("Per-judge wall-clock and cost. Hand-edit each "
                 "`results/judgments/<task>-<date>/<judge>/judge_meta.json` "
                 "to fill in tokens / cost / model slug from dashboards.")
    lines.append("")
    lines.append("| Judge | Tier | Harness | Model | Wall-clock | Tokens | Cost USD |")
    lines.append("|---|---|---|---|---|---|---|")
    for judge in judges:
        meta_path = judgment_dir / judge / "judge_meta.json"
        if not meta_path.exists():
            tier = "expert" if judge in _expert_judges() else "peer"
            lines.append(f"| {judge} | {tier} | — | — | — | — | — |")
            continue
        try:
            meta = json.loads(meta_path.read_text())
        except json.JSONDecodeError:
            meta = {}
        tier = "expert" if judge in _expert_judges() else "peer"
        harness = meta.get("harness", "—")
        slug = meta.get("model_slug", "—")
        wc = meta.get("wall_clock_seconds")
        wc_str = "—"
        if isinstance(wc, (int, float)):
            mins, secs = divmod(int(wc), 60)
            wc_str = f"{mins}m{secs:02d}s"
        tokens = meta.get("tokens_total") or "—"
        cost = meta.get("cost_usd")
        cost_str = f"${cost:.2f}" if isinstance(cost, (int, float)) else "—"
        lines.append(
            f"| {judge} | {tier} | {harness} | `{slug}` | {wc_str} | {tokens} | {cost_str} |"
        )
    lines.append("")
    return lines


def _render_cost_efficiency(impl_models: list[str],
                            runs_index: dict[str, dict[str, Any]],
                            test_results: dict[str, Any],
                            repo_root: pathlib.Path) -> list[str]:
    lines = ["## Cost & efficiency", ""]
    lines.append("Per-implementation cost data, pulled from `builds/<model>/rounds/<task>-<date>/meta.json`. "
                 "Hand-edit those files after capture to fill in input/output token splits "
                 "and exact model slugs from each provider's dashboard.")
    lines.append("")
    lines.append("Wall-clock is *model-only* (sum of opencode turn durations from the session "
                 "export), not the human-perceived envelope. Single-shot, expect ~25% run-to-run "
                 "variance.")
    lines.append("")
    lines.append("| Impl | Model slug | LOC | Wall-clock (model) | Tokens | Cost USD | Tests passed | Cost / passing test |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for model in impl_models:
        meta = _load_run_meta(repo_root, runs_index.get(model, {}).get("path", ""))
        slug = meta.get("model_slug", "—")
        loc = _get_impl_loc(meta)
        wc_seconds = meta.get("model_wall_clock_seconds")
        wc_str = "—"
        if isinstance(wc_seconds, (int, float)):
            mins, secs = divmod(int(wc_seconds), 60)
            wc_str = f"{mins}m{secs:02d}s"
        tokens = meta.get("tokens_total", "—")
        cost = meta.get("cost_usd")
        cost_str = f"${cost:.2f}" if isinstance(cost, (int, float)) else "—"
        tests = test_results.get(model, {})
        passed = tests.get("passed", 0)
        cppt = "—"
        if isinstance(cost, (int, float)) and passed > 0:
            cppt = f"${cost / passed:.4f}"
        lines.append(
            f"| {model} | `{slug}` | {loc} | {wc_str} | {tokens} | {cost_str} | "
            f"{passed} | {cppt} |"
        )
    lines.append("")
    return lines


def _render_review(task: str,
                   date_stamp: str,
                   judgment_dir: pathlib.Path,
                   pairings: dict[str, dict[str, str]],
                   runs_index: dict[str, dict[str, Any]],
                   scores_by_judge: dict[str, dict[str, dict[str, Any] | None]],
                   test_results: dict[str, dict[str, Any]]) -> str:
    impl_models = sorted(runs_index.keys())
    judges = list(pairings.keys())
    expert_judges = [j for j in judges if j in _expert_judges()]
    peer_judges = [j for j in judges if j not in _expert_judges()]

    judges_with_outputs = [
        j for j in judges
        if any(scores_by_judge.get(j, {}).get(m) for m in impl_models)
    ]

    lines: list[str] = []
    lines.append(f"# Review: {task} ({date_stamp})")
    lines.append("")
    lines.append(
        f"Multi-judge blind review of {len(impl_models)} implementation"
        f"{'s' if len(impl_models) != 1 else ''}. Each implementation was scored "
        f"by {len(expert_judges)} expert judge"
        f"{'s' if len(expert_judges) != 1 else ''} "
        f"({', '.join(expert_judges) or '—'}) and "
        f"the {len(peer_judges)} peer model"
        f"{'s' if len(peer_judges) != 1 else ''} "
        f"that didn't produce it. Judges saw only the code + spec, "
        f"not the hidden test results — those come from each run's "
        f"`test-output.txt` and are shown separately as objective signal."
    )
    lines.append("")
    lines.append(f"Judgment dir: `results/judgments/{judgment_dir.name}/`")
    lines.append("")

    if len(judges_with_outputs) < len(judges):
        missing = [j for j in judges if j not in judges_with_outputs]
        lines.append(
            f"> **Note:** {len(missing)} judge"
            f"{'s have' if len(missing) != 1 else ' has'} not yet produced output: "
            f"{', '.join(missing)}. Tables below show partial data; re-run "
            f"`bench/scripts/aggregate_judges.py {task}` once outputs land."
        )
        lines.append("")

    repo_root = _config.repo_root()
    lines.extend(_render_scoreboard(impl_models, judges, scores_by_judge, test_results))
    lines.extend(_render_per_judge_ranking(impl_models, judges, scores_by_judge))
    lines.extend(_render_self_bias_check(impl_models, judges, scores_by_judge))
    lines.extend(_render_inter_judge_agreement(impl_models, judges, scores_by_judge))
    lines.extend(_render_per_implementation(
        impl_models, judges, scores_by_judge, runs_index, test_results
    ))
    lines.extend(_render_cost_efficiency(impl_models, runs_index, test_results, repo_root))
    lines.extend(_render_judge_cost(judges, judgment_dir))

    lines.append("## Cross-model observations")
    lines.append("")
    lines.append("(human reviewer fills — patterns, surprises, where the spec was "
                 "ambiguous, where judges disagreed sharply)")
    lines.append("")

    lines.append("## Recommendation")
    lines.append("")
    lines.append("(human reviewer fills — which implementation to use for the next round, "
                  "or whether to rewrite from the best "
                  "parts of each)")
    lines.append("")

    lines.append("## Spec changes suggested")
    lines.append("")
    lines.append("(human reviewer fills — edits to SPEC.md if reviewing "
                 "surfaced ambiguities)")
    lines.append("")

    return "\n".join(lines)
