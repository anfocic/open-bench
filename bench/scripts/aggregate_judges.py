#!/usr/bin/env python3
"""aggregate_judges.py <task>

Reads the latest judgment phase under results/judgments/<task>-<date>/ and
produces an aggregated review at results/reviews/<task>-<date>.md.

Inputs:
- pairings.json — judge → {model: blinded_label} per judge
- runs_index.json — model → builds/<model>/rounds/<run_dir> path (relative to repo root)
- <judge>/output/<label>_scores.json — judge's structured scores per impl

Hidden test results are pulled from
builds/<model>/rounds/<task>-<date>/test-output.txt — the objective signal.
Judges did not see them.

Output: per-implementation table with all judges' scores + median,
hidden-test pass count, and a recommendation skeleton for the human to
fill in.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _config  # noqa: E402

REPO_ROOT = _config.REPO_ROOT

# Loaded once at startup from bench/config.json. Both start_judgments.py
# and this aggregator read from the same source so the expert/peer split
# is consistent across the round.
CFG = _config.load()
EXPERT_JUDGES = set(CFG.expert_judges)


def latest_judgment_dir(task: str) -> pathlib.Path | None:
    base = REPO_ROOT / "results" / "judgments"
    if not base.is_dir():
        return None
    candidates = sorted(
        d for d in base.iterdir() if d.is_dir() and d.name.startswith(f"{task}-")
    )
    return candidates[-1] if candidates else None


def parse_pytest_output(text: str) -> dict:
    """Extract pass/fail counts and per-test status from pytest -v output.

    Pytest summary lines vary in ordering (e.g. `7 failed, 2 passed in 3.79s`
    when failures exist; `9 passed in 3.28s` when all pass), so we anchor on
    the `===` summary border lines and grep each label independently."""
    summary_text = "\n".join(
        line for line in text.splitlines()
        if line.startswith("=")
        and any(k in line for k in ("passed", "failed", "skipped", "error"))
    )

    def count(label: str) -> int:
        m = re.search(rf"(\d+)\s+{label}", summary_text)
        return int(m.group(1)) if m else 0

    passed = count("passed")
    failed = count("failed")
    skipped = count("skipped")
    errors = count("error")

    per_test = {}
    line_re = re.compile(
        r"^(?P<path>_eval_tests/[^:]+)::(?P<name>[\w\[\]\-]+)\s+(?P<verdict>PASSED|FAILED|SKIPPED|ERROR)",
        re.MULTILINE,
    )
    for m in line_re.finditer(text):
        per_test[m.group("name")] = m.group("verdict")

    return {
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "errors": errors,
        "per_test": per_test,
    }


def load_judge_scores(judge_dir: pathlib.Path,
                      mapping: dict[str, str]) -> dict[str, dict | None]:
    """Return {model: scores_dict | None} for one judge."""
    out_dir = judge_dir / "output"
    by_model: dict[str, dict | None] = {}
    for model, label in mapping.items():
        f = out_dir / f"{label}_scores.json"
        if not f.exists():
            by_model[model] = None
            continue
        try:
            by_model[model] = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            print(f"  warn: {f.relative_to(REPO_ROOT)} not valid JSON: {e}",
                  file=sys.stderr)
            by_model[model] = None
    return by_model


def compute_median(values: list[float]) -> float | None:
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return statistics.median(clean)


def fmt_int(v: float | int | None) -> str:
    if v is None:
        return "—"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, float):
        return f"{v:.1f}"
    return str(v)


def quality_total(q: dict | None) -> int | None:
    if not q:
        return None
    keys = ("clarity", "conciseness", "error_handling", "comments")
    parts = [q.get(k) for k in keys if isinstance(q.get(k), (int, float))]
    if len(parts) != 4:
        return None
    return sum(parts)


def load_run_meta(run_dir_rel: str) -> dict:
    """Read meta.json from a run dir; return empty dict if missing/malformed."""
    p = REPO_ROOT / run_dir_rel / "meta.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return {}


def get_impl_loc(meta: dict) -> int | str:
    """Return impl_loc from meta.json, falling back to sandbox_py_loc."""
    if "impl_loc" in meta:
        return meta["impl_loc"]
    if "sandbox_py_loc" in meta:
        return meta["sandbox_py_loc"]
    return "—"


def get_entrypoint(meta: dict) -> str:
    """Return entrypoint from meta.json, falling back to 'sandbox.py'."""
    return meta.get("entrypoint", "sandbox.py")


def split_judge_scores(judges: list[str],
                       scores_by_judge: dict[str, dict[str, dict | None]],
                       model: str) -> dict:
    """Return spec/quality/verdict/hard_fail scores split by judge tier.

    Self-judgments (judge == impl model) are tracked separately in
    self_spec / self_qual and excluded from the expert/peer/all medians,
    so the scoreboard is not self-inflated. The self-bias section reads
    self_* directly to compute deltas vs peer median.
    """
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
        is_expert = judge in EXPERT_JUDGES
        is_self = judge == model
        if isinstance(spec, (int, float)):
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
        # Verdict/hard_fail aggregation: include self too — these are
        # categorical, not medians, so self contributes to the modal
        # verdict without pulling a numeric average.
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


def render_scoreboard(impl_models: list[str], judges: list[str],
                      scores_by_judge: dict, test_results: dict) -> list[str]:
    """Top-level scoreboard with all-judge / expert / peer median splits."""
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
        sp = split_judge_scores(judges, scores_by_judge, model)

        hf_summary = "pass"
        if any(h == "fail" for h in sp["hard_fails"]):
            fails = sum(1 for h in sp["hard_fails"] if h == "fail")
            hf_summary = f"fail ({fails}/{len(sp['hard_fails'])})"

        verdict_mode = "—"
        if sp["verdicts"]:
            counter: dict[str, int] = {}
            for v in sp["verdicts"]:
                counter[v] = counter.get(v, 0) + 1
            verdict_mode = max(counter.items(), key=lambda kv: kv[1])[0]

        tests = test_results.get(model, {})
        total_tests = sum(tests.get(k, 0) for k in ("passed", "failed", "skipped", "errors"))
        tests_str = f"{tests.get('passed', 0)}/{total_tests}" if total_tests else "—"

        lines.append(
            f"| {model} | {hf_summary} | "
            f"{fmt_int(compute_median(sp['all_specs']))} | "
            f"{fmt_int(compute_median(sp['expert_specs']))} | "
            f"{fmt_int(compute_median(sp['peer_specs']))} | "
            f"{fmt_int(compute_median(sp['all_quals']))} | "
            f"{fmt_int(compute_median(sp['expert_quals']))} | "
            f"{fmt_int(compute_median(sp['peer_quals']))} | "
            f"{tests_str} | {verdict_mode} |"
        )
    lines.append("")
    return lines


def render_per_judge_ranking(impl_models: list[str], judges: list[str],
                             scores_by_judge: dict) -> list[str]:
    """For each judge, sort impls they scored by spec_compliance descending."""
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
            if isinstance(spec, (int, float)):
                ranked.append((spec, model))
        ranked.sort(key=lambda x: (-x[0], x[1]))
        cols = []
        for i in range(3):
            if i < len(ranked):
                spec, model = ranked[i]
                cols.append(f"{model} ({fmt_int(spec)})")
            else:
                cols.append("—")
        lines.append(f"| {judge} | " + " | ".join(cols) + " |")
    lines.append("")
    return lines


def render_per_implementation(impl_models: list[str], judges: list[str],
                              scores_by_judge: dict, runs_index: dict,
                              test_results: dict) -> list[str]:
    """One section per impl with every judge's row + objective tests."""
    lines = ["## Per-implementation detail", ""]
    for model in impl_models:
        lines.append(f"### {model}")
        lines.append("")
        run_dir = runs_index.get(model, "—")
        lines.append(f"Run: `{run_dir}`")
        lines.append("")
        lines.append("| Judge | Tier | Hard-fail | Spec /10 | Quality /20 | Verdict | Note |")
        lines.append("|---|---|---|---|---|---|---|")
        for judge in judges:
            s = scores_by_judge.get(judge, {}).get(model)
            if judge == model:
                tier = "self"
            elif judge in EXPERT_JUDGES:
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
                f"{fmt_int(s.get('spec_compliance'))} | "
                f"{fmt_int(qt)} | "
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


def render_inter_judge_agreement(impl_models: list[str], judges: list[str],
                                 scores_by_judge: dict) -> list[str]:
    """Surface where judges agreed/disagreed sharply on spec scores per impl."""
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
            if isinstance(spec, (int, float)):
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
        lines.append(f"| {model} | {fmt_int(mn)} | {fmt_int(mx)} | {fmt_int(mx - mn)} | "
                     f"{sd:.2f} | {', '.join(j for j, _ in scores)} |")
    lines.append("")

    # Did all judges rank the same impl best?
    best_per_judge: dict[str, str | None] = {}
    for judge in judges:
        candidates: list[tuple[float, str]] = []
        for model in impl_models:
            s = scores_by_judge.get(judge, {}).get(model)
            if s is None:
                continue
            spec = s.get("spec_compliance")
            if isinstance(spec, (int, float)):
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


def render_self_bias_check(impl_models: list[str], judges: list[str],
                           scores_by_judge: dict) -> list[str]:
    """How much each model overrates its own work vs peer consensus.

    Δ = self_score − peer_median. Positive = the model scored its own
    code higher than peers did. Useful as a per-model bias signal and as
    a sanity check that peer-blind judging is meaningfully harder than
    self-judging would be.
    """
    lines = ["## Self-bias check", ""]
    has_self_data = any(
        split_judge_scores(judges, scores_by_judge, m)["self_spec"] is not None
        or split_judge_scores(judges, scores_by_judge, m)["self_qual"] is not None
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
    if EXPERT_JUDGES:
        peer_label = "Peer (excl. self) med"
    else:
        peer_label = "Peer med"
    lines.append(
        f"| Impl | Self spec | {peer_label} spec | Δ spec | "
        f"Self qual | {peer_label} qual | Δ qual |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for model in impl_models:
        sp = split_judge_scores(judges, scores_by_judge, model)
        s_spec = sp["self_spec"]
        s_qual = sp["self_qual"]
        # Use peer median as the comparator (peers, excluding self and
        # excluding experts). If experts are configured, swap to the
        # all-non-self median for a wider sample — but currently
        # bench/config has no expert judges so `peer_specs` already is
        # "everyone except self".
        comp_spec = compute_median(sp["peer_specs"])
        comp_qual = compute_median(sp["peer_quals"])
        d_spec = (s_spec - comp_spec) if (s_spec is not None and comp_spec is not None) else None
        d_qual = (s_qual - comp_qual) if (s_qual is not None and comp_qual is not None) else None
        lines.append(
            f"| {model} | {fmt_int(s_spec)} | {fmt_int(comp_spec)} | "
            f"{fmt_int(d_spec)} | {fmt_int(s_qual)} | "
            f"{fmt_int(comp_qual)} | {fmt_int(d_qual)} |"
        )
    lines.append("")
    return lines


def render_judge_cost(judges: list[str], judgment_dir: pathlib.Path) -> list[str]:
    """Per-judge wall-clock + cost data, pulled from each judge dir's
    judge_meta.json (hand-edited)."""
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
            tier = "expert" if judge in EXPERT_JUDGES else "peer"
            lines.append(f"| {judge} | {tier} | — | — | — | — | — |")
            continue
        try:
            meta = json.loads(meta_path.read_text())
        except json.JSONDecodeError:
            meta = {}
        tier = "expert" if judge in EXPERT_JUDGES else "peer"
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


def render_cost_efficiency(impl_models: list[str], runs_index: dict,
                           test_results: dict) -> list[str]:
    """Cost / wall-clock / cost-per-passing-test, pulled from each run's meta.json."""
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
        meta = load_run_meta(runs_index.get(model, ""))
        slug = meta.get("model_slug", "—")
        loc = get_impl_loc(meta)
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


def render_review(task: str,
                  judgment_dir: pathlib.Path,
                  pairings: dict[str, dict[str, str]],
                  runs_index: dict[str, str],
                  scores_by_judge: dict[str, dict[str, dict | None]],
                  test_results: dict[str, dict]) -> str:
    impl_models = sorted(runs_index.keys())
    judges = list(pairings.keys())
    date_stamp = judgment_dir.name[len(task) + 1:]
    expert_judges = [j for j in judges if j in EXPERT_JUDGES]
    peer_judges = [j for j in judges if j not in EXPERT_JUDGES]

    # Count how many judges actually filed scores (rough completion check).
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

    lines.extend(render_scoreboard(impl_models, judges, scores_by_judge, test_results))
    lines.extend(render_per_judge_ranking(impl_models, judges, scores_by_judge))
    lines.extend(render_self_bias_check(impl_models, judges, scores_by_judge))
    lines.extend(render_inter_judge_agreement(impl_models, judges, scores_by_judge))
    lines.extend(render_per_implementation(
        impl_models, judges, scores_by_judge, runs_index, test_results
    ))
    lines.extend(render_cost_efficiency(impl_models, runs_index, test_results))
    lines.extend(render_judge_cost(judges, judgment_dir))

    # Human-fill sections at the bottom — these are the blog-post centerpieces.
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


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("task", help="task name under bench/tasks/")
    p.add_argument("--judgment-dir",
                   help="explicit judgment dir under results/judgments/ "
                        "(default: latest matching task)")
    args = p.parse_args()

    if args.judgment_dir:
        judgment_dir = pathlib.Path(args.judgment_dir)
        if not judgment_dir.is_absolute():
            judgment_dir = REPO_ROOT / args.judgment_dir
    else:
        judgment_dir = latest_judgment_dir(args.task)
    if judgment_dir is None or not judgment_dir.is_dir():
        print(f"error: no judgment dir found for task '{args.task}'",
              file=sys.stderr)
        return 1

    pairings_file = judgment_dir / "pairings.json"
    if not pairings_file.exists():
        print(f"error: {pairings_file} missing", file=sys.stderr)
        return 1
    pairings = json.loads(pairings_file.read_text())

    runs_index_file = judgment_dir / "runs_index.json"
    if not runs_index_file.exists():
        print(f"error: {runs_index_file} missing", file=sys.stderr)
        return 1
    runs_index = json.loads(runs_index_file.read_text())

    print(f"aggregating from {judgment_dir.relative_to(REPO_ROOT)}")
    print(f"  judges: {', '.join(pairings.keys())}")
    print(f"  impls:  {', '.join(runs_index.keys())}")

    # Per-judge scores keyed by model
    scores_by_judge: dict[str, dict[str, dict | None]] = {}
    for judge, mapping in pairings.items():
        scores_by_judge[judge] = load_judge_scores(judgment_dir / judge, mapping)

    # Hidden test results from each model's run dir (objective)
    test_results: dict[str, dict] = {}
    for model, rel_run in runs_index.items():
        run_dir = REPO_ROOT / rel_run
        out = run_dir / "test-output.txt"
        if not out.exists():
            print(f"  warn: {rel_run}/test-output.txt missing — tests=0/0",
                  file=sys.stderr)
            test_results[model] = {"passed": 0, "failed": 0, "skipped": 0,
                                   "errors": 0, "per_test": {}}
            continue
        test_results[model] = parse_pytest_output(out.read_text())

    review_md = render_review(
        task=args.task,
        judgment_dir=judgment_dir,
        pairings=pairings,
        runs_index=runs_index,
        scores_by_judge=scores_by_judge,
        test_results=test_results,
    )

    date_stamp = judgment_dir.name[len(args.task) + 1:]
    review_path = REPO_ROOT / "results" / "reviews" / f"{args.task}-{date_stamp}.md"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(review_md)
    print()
    print(f"✓ wrote {review_path.relative_to(REPO_ROOT)}")
    print(f"  ({sum(1 for _ in review_md.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
