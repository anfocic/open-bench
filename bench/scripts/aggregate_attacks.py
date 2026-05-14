#!/usr/bin/env python3
"""aggregate_attacks.py — render the round-2 ("Break") review.

Reads results/attacks/break-sandbox-<date>/matrix.json (written by
run_attacks) and renders results/reviews/break-sandbox-<date>.md.

Scoring is objective and **defense-weighted**: a model is ranked first
by how few breaches its sandbox took, then by how many it landed as an
attacker. The score unit is a distinct `(model, attack-class)` breach,
not a raw exploit count, so a model that writes five redundant exploits
in one class doesn't out-score one that writes one effective exploit
each across five classes.

`render_review(matrix)` is pure (matrix dict in, markdown str out) so the
snapshot test can pin it without touching disk.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

from . import _config
from . import _logging
from .run_attacks import ATTACK_CLASSES, class_of

log = _logging.get_logger(__name__)


def _bogus_by_attacker(matrix: dict[str, Any]) -> dict[str, set[str]]:
    """Per attacker: the exploit names that escaped the reference oracle.

    The reference sandbox has no vulnerabilities, so any per-test escape
    against it is bogus (cheese or mis-asserted), not a real escape. Empty
    when the matrix has no reference section (pre-oracle run)."""
    ref = matrix.get("reference", {})
    return {atk: set(pair.get("escaped", [])) for atk, pair in ref.items()}


def _filter_reference_bogus(matrix: dict[str, Any]) -> dict[str, Any]:
    """A copy of `matrix` with reference-escaping (bogus) exploits removed
    from every pair's `escaped`, and `by_class` / `n_escaped` recomputed.

    No-op — returns the input object unchanged — when nothing was flagged
    bogus, so a matrix with no reference section renders byte-identically
    to the pre-oracle behaviour."""
    bogus = _bogus_by_attacker(matrix)
    if not any(bogus.values()):
        return matrix
    out = dict(matrix)
    new_pairs = []
    for p in matrix.get("pairs", []):
        b = bogus.get(p["attacker"], set())
        kept = [n for n in p.get("escaped", []) if n not in b]
        if len(kept) == len(p.get("escaped", [])):
            new_pairs.append(p)
            continue
        q = dict(p)
        q["escaped"] = kept
        q["by_class"] = {c: any(class_of(n) == c for n in kept)
                         for c in ATTACK_CLASSES}
        q["n_escaped"] = len(kept)
        new_pairs.append(q)
    out["pairs"] = new_pairs
    return out


def _reference_section(matrix: dict[str, Any],
                       bogus: dict[str, set[str]]) -> list[str]:
    """The `## Reference oracle` block — emitted only when the matrix has a
    reference section. `matrix` here is the raw (unfiltered) matrix."""
    ref = matrix.get("reference", {})
    out = ["## Reference oracle\n"]
    out.append(
        "Every exploit suite was also run against a known-correct reference "
        "sandbox (`bench/tasks/break-sandbox/reference/sandbox.py`). An "
        "exploit that \"escapes\" the reference cannot be demonstrating a "
        "real vulnerability — it is cheese or mis-asserted, and is excluded "
        "from the scoring below.\n")
    out.append("| Attacker | Exploits run vs reference | "
               "Escaped reference (excluded) |")
    out.append("|---|---|---|")
    for atk in sorted(ref):
        p = ref[atk]
        n_run = (p.get("n_escaped", 0) + p.get("n_held", 0)
                 + p.get("n_errored", 0))
        excl = sorted(bogus.get(atk, set()))
        cell = ", ".join(f"`{n}`" for n in excl) if excl else "—"
        out.append(f"| {atk} | {n_run} | {cell} |")
    out.append("")
    return out


def _model_scores(matrix: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Per-model aggregates derived purely from matrix.json's per-pair
    `by_class` rollup. Score unit = distinct (model, class) breach."""
    models = sorted(set(matrix.get("attackers", [])) |
                    set(matrix.get("targets", [])))
    s = {m: {
        "attacker_score": 0,      # distinct (target, class) breaches landed
        "defender_score": 0,      # distinct (attacker, class) breaches taken
        "attacker_classes": set(),
        "defender_classes": set(),
        "targets_breached": set(),
        "raw_landed": 0,
        "raw_suffered": 0,
    } for m in models}

    for p in matrix.get("pairs", []):
        atk, tgt = p["attacker"], p["target"]
        breached = sorted(c for c in ATTACK_CLASSES
                          if p.get("by_class", {}).get(c))
        s[atk]["attacker_score"] += len(breached)
        s[tgt]["defender_score"] += len(breached)
        s[atk]["attacker_classes"].update(breached)
        s[tgt]["defender_classes"].update(breached)
        if breached:
            s[atk]["targets_breached"].add(tgt)
        s[atk]["raw_landed"] += p.get("n_escaped", 0)
        s[tgt]["raw_suffered"] += p.get("n_escaped", 0)
    return s


def _ranked(scores: dict[str, dict[str, Any]]) -> list[str]:
    """Models best -> worst. Defense-weighted: fewest breaches taken first,
    ties broken by most breaches landed, then model name for determinism."""
    return sorted(
        scores,
        key=lambda m: (scores[m]["defender_score"],
                       -scores[m]["attacker_score"],
                       m),
    )


def render_review(matrix: dict[str, Any]) -> str:
    raw_matrix = matrix
    bogus = _bogus_by_attacker(raw_matrix)
    matrix = _filter_reference_bogus(matrix)

    date = matrix.get("date", "unknown")
    runtime = matrix.get("runtime", "unknown")
    attackers = list(matrix.get("attackers", []))
    targets = list(matrix.get("targets", []))
    pairs = matrix.get("pairs", [])
    catalog = matrix.get("exploit_catalog", {})

    scores = _model_scores(matrix)
    ranked = _ranked(scores)
    pair_by = {(p["attacker"], p["target"]): p for p in pairs}

    total_breaches = sum(s["attacker_score"] for s in scores.values())
    out: list[str] = []

    out.append(f"# Break round — break-sandbox ({date})\n")
    out.append("## Summary\n")
    out.append(
        f"{len(attackers)} attacker(s) x {len(targets)} target(s), "
        f"{len(pairs)} ordered pairs (self-attack excluded), runtime "
        f"`{runtime}`. Objective scoring: a per-test PASS is an escape. "
        f"Score unit is a distinct (model, attack-class) breach; "
        f"{total_breaches} landed in total.\n")

    if raw_matrix.get("reference"):
        out.extend(_reference_section(raw_matrix, bogus))

    # --- Attack matrix -----------------------------------------------------
    out.append("## Attack matrix\n")
    out.append("Cell = distinct attack classes breached (0-5). Rows attack, "
               "columns defend; row sum = attacker score, column sum = "
               "defender score.\n")
    header = "| atk \\ def | " + " | ".join(targets) + " |"
    out.append(header)
    out.append("|" + "---|" * (len(targets) + 1))
    for a in attackers:
        cells = []
        for t in targets:
            if a == t:
                cells.append("—")
                continue
            p = pair_by.get((a, t))
            if p is None:
                cells.append("·")
                continue
            n = sum(1 for c in ATTACK_CLASSES if p.get("by_class", {}).get(c))
            cells.append(str(n))
        out.append(f"| {a} | " + " | ".join(cells) + " |")
    out.append("")

    # --- Attacker scoreboard ----------------------------------------------
    out.append("## Attacker scoreboard\n")
    out.append("| Attacker | Score (class breaches) | Targets breached | "
               "Distinct classes | Raw exploits landed |")
    out.append("|---|---|---|---|---|")
    for m in sorted(attackers,
                    key=lambda x: (-scores[x]["attacker_score"], x)):
        s = scores[m]
        out.append(
            f"| {m} | {s['attacker_score']} | "
            f"{len(s['targets_breached'])} | "
            f"{len(s['attacker_classes'])} | {s['raw_landed']} |")
    out.append("")

    # --- Defender scoreboard ----------------------------------------------
    out.append("## Defender scoreboard\n")
    out.append("Lower is better — breaches taken.\n")
    out.append("| Defender | Score (breaches taken) | Distinct classes "
               "breached | Raw exploits suffered |")
    out.append("|---|---|---|---|")
    for m in sorted(targets,
                    key=lambda x: (scores[x]["defender_score"], x)):
        s = scores[m]
        out.append(
            f"| {m} | {s['defender_score']} | "
            f"{len(s['defender_classes'])} | {s['raw_suffered']} |")
    out.append("")

    # --- Breach detail -----------------------------------------------------
    out.append("## Breach detail\n")
    breached_pairs = [p for p in pairs if p.get("n_escaped", 0) > 0]
    if not breached_pairs:
        out.append("No exploit escaped any target sandbox.\n")
    else:
        for p in sorted(breached_pairs,
                        key=lambda x: (x["attacker"], x["target"])):
            desc = {e["name"]: e.get("description", "")
                    for e in catalog.get(p["attacker"], [])}
            out.append(f"### {p['attacker']} vs {p['target']}\n")
            for name in p["escaped"]:
                cls = name.split("__")[0].replace("test_escape_", "")
                d = desc.get(name, "")
                out.append(f"- `{name}` ({cls})"
                           + (f" — {d}" if d else ""))
            out.append("")

    # --- Attack-class coverage --------------------------------------------
    out.append("## Attack-class coverage\n")
    out.append("| Class | Targets breached | Attackers who landed it |")
    out.append("|---|---|---|")
    for c in ATTACK_CLASSES:
        tgts = sorted({p["target"] for p in pairs
                       if p.get("by_class", {}).get(c)})
        atks = sorted({p["attacker"] for p in pairs
                       if p.get("by_class", {}).get(c)})
        out.append(f"| {c} | {len(tgts)} | "
                   + (", ".join(atks) if atks else "—") + " |")
    out.append("")

    # --- Round ranking -----------------------------------------------------
    out.append("## Round ranking\n")
    out.append("Defense-weighted: ranked by breaches taken (asc), then "
               "breaches landed (desc). Models with identical records share "
               "a rank. This is a per-round ranking only — not a tournament "
               "standing, and it carries no elimination.\n")
    out.append("| Rank | Model | Defender score | Attacker score |")
    out.append("|---|---|---|---|")
    prev_key: tuple[int, int] | None = None
    rank = 0
    for i, m in enumerate(ranked, 1):
        s = scores[m]
        key = (s["defender_score"], -s["attacker_score"])
        if key != prev_key:
            rank, prev_key = i, key
        out.append(f"| {rank} | {m} | {s['defender_score']} | "
                   f"{s['attacker_score']} |")
    out.append("")
    if total_breaches == 0:
        out.append("No exploit landed against any sandbox — every model is "
                   "tied. This round did not separate the lineup.\n")

    # --- Data-quality notes -----------------------------------------------
    out.append("## Data-quality notes\n")
    notes: list[str] = []
    timed = sorted(f"{p['attacker']} vs {p['target']}"
                   for p in pairs if p.get("timed_out"))
    if timed:
        notes.append(f"Timed-out pairs (partial results): {', '.join(timed)}.")
    errored = sorted(f"{p['attacker']} vs {p['target']} ({p['n_errored']})"
                     for p in pairs if p.get("n_errored", 0) > 0)
    if errored:
        notes.append("Pairs with inconclusive (errored/skipped) exploits: "
                     + ", ".join(errored) + ".")
    empty_cat = sorted(m for m in attackers if not catalog.get(m))
    if empty_cat:
        notes.append("Attackers with no readable EXPLOITS catalog: "
                     + ", ".join(empty_cat) + ".")
    flagged = {a: sorted(names) for a, names in bogus.items() if names}
    if flagged:
        parts = []
        for a in sorted(flagged):
            marked = []
            for n in flagged[a]:
                a_pairs = [p for p in raw_matrix.get("pairs", [])
                           if p["attacker"] == a]
                # also escaping every real target = pure-cheese signature
                universal = (a_pairs and
                             all(n in p.get("escaped", []) for p in a_pairs))
                marked.append(f"`{n}`" + (" (universal)" if universal else ""))
            parts.append(f"{a}: {', '.join(marked)}")
        notes.append("Exploits excluded as bogus (escaped the reference "
                     "oracle): " + "; ".join(parts) + ".")
    if not notes:
        notes.append("None.")
    for n in notes:
        out.append(f"- {n}")
    out.append("")

    return "\n".join(out)


def latest_attacks_dir(repo_root: pathlib.Path,
                       task: str = "break-sandbox") -> pathlib.Path | None:
    base = repo_root / "results" / "attacks"
    if not base.is_dir():
        return None
    cands = sorted(d for d in base.iterdir()
                   if d.is_dir() and d.name.startswith(f"{task}-"))
    return cands[-1] if cands else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--attacks-dir",
                    help="explicit dir under results/attacks/ "
                         "(default: latest break-sandbox-*)")
    ap.add_argument("--quiet", "-q", action="store_true",
                    help="warnings + errors only")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="debug output")
    args = ap.parse_args()
    _logging.setup_logging(quiet=args.quiet, verbose=args.verbose)

    repo_root = _config.repo_root()

    if args.attacks_dir:
        attacks_dir = pathlib.Path(args.attacks_dir)
        if not attacks_dir.is_absolute():
            attacks_dir = repo_root / args.attacks_dir
    else:
        attacks_dir = latest_attacks_dir(repo_root)
    if attacks_dir is None or not attacks_dir.is_dir():
        log.error("no attacks dir found under results/attacks/")
        return 1

    matrix_file = attacks_dir / "matrix.json"
    if not matrix_file.exists():
        log.error("%s missing", matrix_file)
        return 1
    matrix = json.loads(matrix_file.read_text())

    review_md = render_review(matrix)
    date = matrix.get("date", "unknown")
    review_path = repo_root / "results" / "reviews" / f"break-sandbox-{date}.md"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(review_md)
    log.info("wrote %s (%d lines)",
             review_path.relative_to(repo_root),
             sum(1 for _ in review_md.splitlines()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
