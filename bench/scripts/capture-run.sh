#!/usr/bin/env bash
# capture-run.sh <task> <model>
#
# Captures artifacts from a finished run:
#   - copies hidden tests into the worktree (ephemerally)
#   - runs them, saves output
#   - removes test files (so diff stays clean)
#   - saves diff.patch, edited files, transcript, meta.json
#
# Run AFTER the model has finished its session in the worktree.

set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "usage: $0 <task> <model>" >&2
    exit 2
fi

task="$1"
model="$2"

repo_root="$(git rev-parse --show-toplevel)"
task_dir="${repo_root}/bench/tasks/${task}"

# Find the most recent run dir for this task+model under builds/<model>/rounds/.
model_dir="${repo_root}/builds/${model}"
run_dir="$(ls -1d "${model_dir}/rounds/${task}-"* 2>/dev/null | sort | tail -n1 || true)"
if [[ -z "${run_dir}" || ! -d "${run_dir}" ]]; then
    echo "error: no run dir for ${task}-* under ${model_dir}/" >&2
    echo "       did you call start-run.sh first?" >&2
    exit 1
fi

run_basename="$(basename "${run_dir}")"
run_date="${run_basename#${task}-}"
slug="${task}-${model}-${run_date}"
worktree_dir="${repo_root}/../sandbox-eval-${slug}"
if [[ ! -d "${worktree_dir}" ]]; then
    echo "error: worktree not found at ${worktree_dir}" >&2
    exit 1
fi

# Refuse if the model didn't produce sandbox.py — the most common failure
# mode is running capture-run.sh before the opencode session has actually
# happened. Catch it loudly instead of producing an empty run dir.
if [[ ! -f "${worktree_dir}/sandbox.py" ]]; then
    if [[ "${ALLOW_EMPTY_IMPL:-0}" != "1" ]]; then
        echo "error: ${worktree_dir}/sandbox.py is missing" >&2
        echo "       the model has not produced an implementation yet" >&2
        echo "       did you run the opencode session in the worktree?" >&2
        echo "       if you intended an empty run (e.g. dry-run validation)," >&2
        echo "       set ALLOW_EMPTY_IMPL=1 and re-run." >&2
        exit 1
    fi
    echo "  note: sandbox.py missing; ALLOW_EMPTY_IMPL=1, continuing" >&2
fi

started_at_file="${run_dir}/.started_at"
started_at="$(cat "${started_at_file}" 2>/dev/null || echo "unknown")"
ended_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

mkdir -p "${run_dir}"

# 1. diff against base — three layers, since the model may commit, leave
#    files staged/unstaged, or leave them entirely untracked.
base_branch="${BASE_BRANCH:-}"
if [[ -z "${base_branch}" ]]; then
    base_branch="$(git -C "${repo_root}" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@')" || base_branch=""
fi
if [[ -z "${base_branch}" ]]; then
    for cand in main master; do
        if git -C "${repo_root}" rev-parse --verify "${cand}" >/dev/null 2>&1; then
            base_branch="${cand}"; break
        fi
    done
fi
base="$(git -C "${worktree_dir}" merge-base HEAD "${base_branch}" 2>/dev/null || git -C "${repo_root}" rev-parse "${base_branch}")"
: > "${run_dir}/diff.patch"

# (a) committed changes
git -C "${worktree_dir}" diff "${base}"...HEAD -- . ':!PROMPT.md' ':!SPEC.md' >> "${run_dir}/diff.patch" || true

# (b) tracked-but-uncommitted changes
git -C "${worktree_dir}" diff HEAD -- . ':!PROMPT.md' ':!SPEC.md' >> "${run_dir}/diff.patch" 2>/dev/null || true

# (c) untracked files — render each as a /dev/null → file diff with
#     paths relative to the worktree root.
pushd "${worktree_dir}" >/dev/null
while IFS= read -r f; do
    [[ -z "${f}" || "${f}" == "PROMPT.md" || "${f}" == "SPEC.md" || "${f}" == "transcript.md" ]] && continue
    [[ "${f}" == _eval_tests/* ]] && continue
    git --no-pager diff --no-index --no-color /dev/null "${f}" 2>/dev/null \
        >> "${run_dir}/diff.patch" || true
done < <(git ls-files --others --exclude-standard)
popd >/dev/null

# 2. snapshot model-modified files only — anything that differs from the base
#    commit (committed, staged, unstaged, or untracked). Limited to .py files
#    so the run dir doesn't accumulate unrelated artifacts. Restricted to
#    files outside the worktree-prep set (PROMPT.md / SPEC.md / tests).
modified_py="$(
    cd "${worktree_dir}" && {
        git diff --name-only "${base}" -- '*.py' 2>/dev/null
        git diff --name-only HEAD -- '*.py' 2>/dev/null
        git ls-files --others --exclude-standard -- '*.py'
    } | sort -u | grep -vE '^_eval_tests/' || true
)"
if [[ -n "${modified_py}" ]]; then
    while IFS= read -r rel; do
        [[ -z "${rel}" ]] && continue
        [[ ! -f "${worktree_dir}/${rel}" ]] && continue
        dest="${run_dir}/${rel}"
        mkdir -p "$(dirname "${dest}")"
        cp "${worktree_dir}/${rel}" "${dest}"
    done <<< "${modified_py}"
fi

# Promote sandbox.py to <model>/sandbox.py — the "current" copy at the
# model dir root, alongside the dated archives.
if [[ -f "${run_dir}/sandbox.py" ]]; then
    cp "${run_dir}/sandbox.py" "${model_dir}/sandbox.py"
fi

# 3. copy hidden tests into worktree, run pytest, then remove
eval_dir="${worktree_dir}/_eval_tests"
rm -rf "${eval_dir}"
mkdir -p "${eval_dir}"
if [[ ! -d "${task_dir}/tests" ]]; then
    echo "error: no tests dir at ${task_dir}/tests" >&2
    exit 1
fi
cp -R "${task_dir}/tests/." "${eval_dir}/"

if ! python3 -m pytest --version >/dev/null 2>&1; then
    echo "error: pytest not available for $(python3 -c 'import sys; print(sys.executable)')" >&2
    echo "       install with: python3 -m pip install pytest" >&2
    echo "       (the model's score is meaningless without a working test runner)" >&2
    rm -rf "${eval_dir}"
    exit 1
fi

pushd "${worktree_dir}" >/dev/null
set +e
python3 -m pytest _eval_tests/ -v --tb=short 2>&1 | tee "${run_dir}/test-output.txt"
test_exit=$?
set -e
popd >/dev/null

rm -rf "${eval_dir}"

# 4. transcript + opencode session capture
#
# Try, in order:
#   (a) auto-locate the opencode session whose directory == worktree, export
#       it as JSON (canonical artifact) + render its markdown transcript
#   (b) fall back to a hand-saved worktree/transcript.md if (a) finds nothing
#   (c) write a placeholder explaining what to do
#
# (a) is the path that makes meta.json's cost / tokens / model_slug fields
# auto-populate without a provider-dashboard round-trip.
opencode_session_json="${run_dir}/opencode_session.json"
opencode_summary_json="${run_dir}/.opencode_summary.json"
rm -f "${opencode_session_json}" "${opencode_summary_json}"

python3 - "${worktree_dir}" "${opencode_session_json}" "${opencode_summary_json}" "${run_dir}/transcript.md" "${repo_root}/bench/scripts" <<'PYEOF'
import json
import pathlib
import sys

worktree_dir, session_out, summary_out, transcript_out, scripts_dir = sys.argv[1:]
sys.path.insert(0, scripts_dir)

try:
    import _opencode
except Exception as e:
    print(f"  warn: could not load _opencode helper ({e}); skipping auto-capture",
          file=sys.stderr)
    sys.exit(0)

if not _opencode.available():
    sys.exit(0)

session_id = _opencode.find_session_for_directory(worktree_dir)
if not session_id:
    print("  note: no opencode session found for worktree — "
          "falling back to transcript.md", file=sys.stderr)
    sys.exit(0)

session = _opencode.export_session(session_id)
if not session:
    print(f"  warn: opencode export failed for session {session_id}",
          file=sys.stderr)
    sys.exit(0)

pathlib.Path(session_out).write_text(json.dumps(session, indent=2) + "\n")

summary = _opencode.summarize(session)
pathlib.Path(summary_out).write_text(json.dumps(summary, indent=2) + "\n")

# Only write transcript.md if user did not save one themselves.
transcript_path = pathlib.Path(transcript_out)
worktree_transcript = pathlib.Path(worktree_dir) / "transcript.md"
if not worktree_transcript.exists():
    transcript_path.write_text(_opencode.render_transcript(session))

print(f"  ✓ opencode session captured: {session_id}", file=sys.stderr)
print(f"    cost ${summary['cost_usd']:.4f}, "
      f"{summary['tokens_total']} tokens, "
      f"model {summary['model_slug']}", file=sys.stderr)
PYEOF

# If user provided a hand-saved transcript.md, prefer it over our render.
if [[ -f "${worktree_dir}/transcript.md" ]]; then
    cp "${worktree_dir}/transcript.md" "${run_dir}/transcript.md"
elif [[ ! -f "${run_dir}/transcript.md" ]]; then
    cat > "${run_dir}/transcript.md" <<EOF
# transcript missing

No \`transcript.md\` found at worktree root and no opencode session
matching this worktree. To capture the session manually, either:
  - export the session via \`opencode export <sessionID> > ${worktree_dir}/session.json\`
  - or copy the terminal scrollback to ${worktree_dir}/transcript.md
then re-run capture-run.sh.
EOF
fi

# 5. count LOC of model's sandbox.py (rough quality signal)
loc="0"
if [[ -f "${worktree_dir}/sandbox.py" ]]; then
    loc="$(grep -cvE '^\s*(#|$)' "${worktree_dir}/sandbox.py" || echo 0)"
fi

# 6. meta — auto-fields go in a temp file, then merged with any
#    hand-edited meta.json so re-capture doesn't clobber things like
#    cost_usd / model_slug / notes.
opencode_version="$(opencode --version 2>/dev/null || echo unknown)"
python_version="$(python3 --version 2>&1)"

auto_meta="${run_dir}/meta-auto.json"
cat > "${auto_meta}" <<EOF
{
  "task": "${task}",
  "model": "${model}",
  "slug": "${slug}",
  "started_at": "${started_at}",
  "ended_at": "${ended_at}",
  "base_commit": "${base}",
  "worktree": "${worktree_dir}",
  "test_exit_code": ${test_exit},
  "sandbox_py_loc": ${loc},
  "opencode_version": "${opencode_version}",
  "python_version": "${python_version}"
}
EOF

python3 - "${run_dir}/meta.json" "${auto_meta}" "${opencode_summary_json}" <<'PYEOF'
import json, os, sys
meta_path, auto_path, summary_path = sys.argv[1], sys.argv[2], sys.argv[3]
existing = {}
if os.path.exists(meta_path):
    try:
        with open(meta_path) as f:
            existing = json.load(f)
    except json.JSONDecodeError:
        existing = {}
with open(auto_path) as f:
    auto = json.load(f)
existing.update(auto)  # auto-fields win for keys they own; hand-edited keys preserved
# opencode summary, if present, populates cost/tokens/model_slug. These
# fields are auto-derived from the session export, so they overwrite any
# stale hand-edits — captured-from-source wins over remembered.
if os.path.exists(summary_path):
    with open(summary_path) as f:
        summary = json.load(f)
    existing.update({k: v for k, v in summary.items() if v is not None})
    os.unlink(summary_path)
with open(meta_path, "w") as f:
    json.dump(existing, f, indent=2)
    f.write("\n")
os.unlink(auto_path)
PYEOF

cat <<EOF

✓ captured
  run dir:     ${run_dir}
  test exit:   ${test_exit}  (0 = all passed)
  sandbox.py:  ${loc} LOC

artifacts (in ${run_dir})
  - sandbox.py            (also copied to ${model_dir}/sandbox.py = current)
  - diff.patch
  - test-output.txt
  - transcript.md
  - meta.json

next: review with results/reviews/TEMPLATE.md → results/reviews/${task}-$(date +%Y-%m-%d).md
EOF
