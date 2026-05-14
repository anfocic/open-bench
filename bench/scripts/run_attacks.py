#!/usr/bin/env python3
"""run_attacks.py — round-2 ("Break") attack matrix.

Discovers every model's round-2 exploit suite (the `break-sandbox` task's
`exploit.py`) and every model's round-1 `sandbox.py`, then runs each
exploit suite against every other model's sandbox — self-pairs excluded.

Scoring is objective: with the exploit suite's inverted polarity, a
per-test PASS means the exploit escaped that sandbox; a FAIL means the
sandbox held. No judge, no human.

Per pair (in a throwaway tmp dir, mirroring perf_bench.run_once):
  <work>/sandbox.py             the target
  <work>/_eval_tests/exploit.py the attacker's suite
  <work>/_eval_tests/conftest.py  the matrix conftest (sandbox fixture)
then `pytest _eval_tests/exploit.py -v`, parsed with _pytest_parse.

Output:
  results/attacks/break-sandbox-<date>/matrix.json              (committed)
  results/attacks/break-sandbox-<date>/pair-<atk>-vs-<tgt>.txt   (raw, gitignored)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from . import _config
from . import _logging
from . import _pytest_parse
from . import _runs
from . import _task

log = _logging.get_logger(__name__)

ATTACK_CLASSES = ("network", "fs", "resource", "privesc", "shellinj")
_CLASS_RE = re.compile(r"^test_escape_(network|fs|resource|privesc|shellinj)__")


def _has(binary: str) -> bool:
    return shutil.which(binary) is not None


def class_of(test_name: str) -> str | None:
    """Attack class from a `test_escape_<class>__<name>` test name."""
    m = _CLASS_RE.match(test_name)
    return m.group(1) if m else None


def read_exploit_catalog(attacker: dict[str, Any]) -> list[dict[str, str]]:
    """Dump an attacker's `EXPLOITS` list by importing exploit.py in a
    subprocess. The capture gate already proved exploit.py imports cleanly
    without a target present. Returns [] on any failure (flagged later)."""
    impl = attacker["impl_path"]
    code = (
        "import json, exploit; "
        "print(json.dumps([{'name': n, 'class': c, 'description': d} "
        "for (n, c, d) in exploit.EXPLOITS]))"
    )
    try:
        out = subprocess.check_output(
            [sys.executable, "-c", code],
            cwd=impl.parent, text=True, stderr=subprocess.DEVNULL, timeout=30,
        )
        parsed = json.loads(out)
        return parsed if isinstance(parsed, list) else []
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            json.JSONDecodeError, OSError):
        return []


def run_pair(
    attacker: dict[str, Any],
    target: dict[str, Any],
    conftest_src: Path,
    timeout: int,
) -> tuple[dict[str, Any], str]:
    """Run one attacker's suite against one target sandbox.

    Returns (pair_result, raw_output). The work dir is removed in
    `finally` so a timeout or exception can't leak it into /tmp.
    """
    work = Path(tempfile.mkdtemp(
        prefix=f"attack-{attacker['model']}-vs-{target['model']}-"))
    try:
        shutil.copy2(target["impl_path"], work / "sandbox.py")
        eval_dir = work / "_eval_tests"
        eval_dir.mkdir()
        shutil.copy2(attacker["impl_path"], eval_dir / "exploit.py")
        shutil.copy2(conftest_src, eval_dir / "conftest.py")

        timed_out = False
        try:
            proc = subprocess.run(
                # point pytest at the file, not the dir: `exploit.py` doesn't
                # match the default `python_files` glob, so a dir target
                # collects 0 tests; an explicit path bypasses that filter
                [sys.executable, "-m", "pytest", "_eval_tests/exploit.py",
                 "-v", "--tb=line", "-p", "no:cacheprovider"],
                cwd=work, capture_output=True, text=True, timeout=timeout,
            )
            stdout, stderr = proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as e:
            timed_out = True
            stdout = e.stdout or ""
            stderr = e.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", "replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", "replace")

        per_test = _pytest_parse.parse_pytest_output(stdout)["per_test"]
        escaped, held, errored = [], [], []
        for name, verdict in per_test.items():
            if verdict == "PASSED":
                escaped.append(name)
            elif verdict == "FAILED":
                held.append(name)
            else:  # SKIPPED, ERROR — exploit was inconclusive
                errored.append(name)

        by_class = {c: False for c in ATTACK_CLASSES}
        for name in escaped:
            cls = class_of(name)
            if cls in by_class:
                by_class[cls] = True

        result = {
            "attacker": attacker["model"],
            "target": target["model"],
            "escaped": sorted(escaped),
            "held": sorted(held),
            "errored": sorted(errored),
            "timed_out": timed_out,
            "by_class": by_class,
            "n_escaped": len(escaped),
            "n_held": len(held),
            "n_errored": len(errored),
        }
        return result, stdout + ("\n--- stderr ---\n" + stderr if stderr else "")
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="round date stamp (default: today UTC)")
    ap.add_argument("--models",
                    help="comma-separated subset of models to include "
                         "(both as attacker and target)")
    ap.add_argument("--no-reference", action="store_true",
                    help="skip the reference-oracle control pass "
                         "(bogus exploits then can't be excluded from scoring)")
    ap.add_argument("--quiet", "-q", action="store_true",
                    help="warnings + errors only")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="debug output")
    args = ap.parse_args()
    _logging.setup_logging(quiet=args.quiet, verbose=args.verbose)

    repo_root = _config.repo_root()

    if not (_has("podman") or _has("docker")):
        log.error("no container runtime on PATH (need podman or docker) — "
                  "the attack matrix has no real escape signal without one")
        return 1
    runtime = "podman" if _has("podman") else "docker"

    try:
        task_dir = _task.require("break-sandbox")
    except FileNotFoundError as e:
        log.error("%s", e)
        return 1
    conftest_src = task_dir / "conftest_runner.py"
    if not conftest_src.exists():
        log.error("missing %s", conftest_src)
        return 1

    only: set[str] | None = None
    if args.models:
        only = {m.strip() for m in args.models.split(",") if m.strip()}

    attackers = []
    for a in _runs.find_latest_runs("break-sandbox", "exploit.py",
                                    repo_root=repo_root):
        rc = a["meta"].get("test_exit_code", 0)
        if rc != 0:
            log.warning("%s failed the capture gate (test_exit_code=%s) — "
                        "excluded as attacker", a["model"], rc)
            continue
        attackers.append(a)
    targets = _runs.find_latest_runs("sandbox", "sandbox.py",
                                     repo_root=repo_root)

    if only is not None:
        attackers = [a for a in attackers if a["model"] in only]
        targets = [t for t in targets if t["model"] in only]

    if len(attackers) < 2:
        log.error("need >= 2 valid attackers, found %d", len(attackers))
        return 1
    if len(targets) < 2:
        log.error("need >= 2 targets, found %d", len(targets))
        return 1

    attackers.sort(key=lambda r: r["model"])
    targets.sort(key=lambda r: r["model"])

    date_stamp = args.date or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    out_dir = repo_root / "results" / "attacks" / f"break-sandbox-{date_stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    pair_timeout = int(os.environ.get("ATTACK_PAIR_TIMEOUT", "600"))

    log.info("==> attack matrix: %d attackers x %d targets (runtime=%s)",
             len(attackers), len(targets), runtime)
    log.info("    out: %s", out_dir.relative_to(repo_root))

    catalog = {a["model"]: read_exploit_catalog(a) for a in attackers}

    pairs: list[dict[str, Any]] = []
    for a in attackers:
        for t in targets:
            if a["model"] == t["model"]:
                continue
            log.info("--- %s vs %s ---", a["model"], t["model"])
            try:
                pair, raw = run_pair(a, t, conftest_src, pair_timeout)
            except OSError as e:
                log.error("pair %s vs %s failed: %s",
                          a["model"], t["model"], e)
                continue
            pairs.append(pair)
            (out_dir / f"pair-{a['model']}-vs-{t['model']}.txt").write_text(raw)
            log.info("escaped=%d held=%d errored=%d%s",
                     pair["n_escaped"], pair["n_held"], pair["n_errored"],
                     " TIMEOUT" if pair["timed_out"] else "")

    # --- reference-oracle control pass -----------------------------------
    # Every exploit suite also runs against a known-correct reference
    # sandbox. An exploit that "escapes" the reference can't be a real
    # escape — aggregate_attacks excludes it from scoring.
    reference: dict[str, Any] = {}
    ref_path = task_dir / "reference" / "sandbox.py"
    if args.no_reference:
        log.info("--no-reference: skipping the reference-oracle control pass")
    elif not ref_path.exists():
        log.warning("no reference sandbox at %s — exploits won't be checked "
                    "against the oracle; bogus exploits can't be excluded "
                    "from scoring", ref_path)
    else:
        log.info("--- reference-oracle control pass (%d attackers) ---",
                 len(attackers))
        ref_target = {"model": "reference", "impl_path": ref_path}
        for a in attackers:
            try:
                pair, raw = run_pair(a, ref_target, conftest_src, pair_timeout)
            except OSError as e:
                log.error("reference pair %s failed: %s", a["model"], e)
                continue
            reference[a["model"]] = pair
            (out_dir / f"pair-{a['model']}-vs-reference.txt").write_text(raw)
            log.info("%s vs reference: escaped=%d held=%d errored=%d",
                     a["model"], pair["n_escaped"], pair["n_held"],
                     pair["n_errored"])

    matrix = {
        "task": "break-sandbox",
        "date": date_stamp,
        "runtime": runtime,
        "attackers": [a["model"] for a in attackers],
        "targets": [t["model"] for t in targets],
        "pairs": pairs,
        "exploit_catalog": catalog,
    }
    if reference:
        matrix["reference"] = reference
    (out_dir / "matrix.json").write_text(json.dumps(matrix, indent=2) + "\n")
    log.info("==> wrote %s", (out_dir / "matrix.json").relative_to(repo_root))
    return 0


if __name__ == "__main__":
    sys.exit(main())
