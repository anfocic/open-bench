#!/usr/bin/env bash
# start-run.sh [--auto] <task> <model>
#
# Creates an isolated git worktree on a fresh branch, drops PROMPT.md +
# SPEC.md at the worktree root, and prints the next steps.
#
# The worktree branches off the current main HEAD, so the model starts from
# the same baseline regardless of in-flight work on main.
#
# With --auto, drives `opencode run` non-interactively against the
# worktree using the model slug from bench/config.json, then chains to
# capture-run.sh on success. Uses --dangerously-skip-permissions; see
# README warning before using.

set -euo pipefail

auto_drive=0
positional=()
for arg in "$@"; do
    case "${arg}" in
        --auto) auto_drive=1 ;;
        --) ;;
        --*) echo "error: unknown flag '${arg}'" >&2; exit 2 ;;
        *)  positional+=("${arg}") ;;
    esac
done

if [[ ${#positional[@]} -ne 2 ]]; then
    echo "usage: $0 [--auto] <task> <model>" >&2
    echo "  task:   directory name under bench/tasks/" >&2
    echo "  model:  short slug (kimi, deepseek, minimax, ...)" >&2
    echo "  --auto: drive opencode non-interactively, then capture" >&2
    exit 2
fi

task="${positional[0]}"
model="${positional[1]}"

repo_root="$(git rev-parse --show-toplevel)"
task_dir="${repo_root}/bench/tasks/${task}"

if [[ ! -d "${task_dir}" ]]; then
    echo "error: no task at ${task_dir}" >&2
    exit 1
fi

# Soft-validate model against config. Warning only — experimentation with
# an extra slot is allowed, but the warning makes typos loud.
config_path="${repo_root}/bench/config.json"
if [[ -f "${config_path}" ]]; then
    if ! python3 - "${config_path}" "${model}" <<'PYEOF' 2>/dev/null
import json, sys
config_path, model = sys.argv[1], sys.argv[2]
with open(config_path) as f:
    cfg = json.load(f)
sys.exit(0 if model in cfg.get('implementers', []) else 1)
PYEOF
    then
        echo "  warn: '${model}' not in bench/config.json implementers" >&2
        echo "        proceeding anyway — add it to config if this is intentional" >&2
    fi
fi

if [[ ! -f "${task_dir}/PROMPT.md" || ! -f "${task_dir}/SPEC.md" ]]; then
    echo "error: task missing PROMPT.md or SPEC.md" >&2
    exit 1
fi

date_stamp="${RUN_STAMP:-$(date +%Y-%m-%d)}"
slug="${task}-${model}-${date_stamp}"
branch="eval/${slug}"
worktree_dir="${repo_root}/../sandbox-eval-${slug}"

if git -C "${repo_root}" worktree list --porcelain | grep -q "^worktree ${worktree_dir}$"; then
    echo "error: worktree already exists at ${worktree_dir}" >&2
    echo "       remove with: git worktree remove ${worktree_dir}" >&2
    exit 1
fi

if git -C "${repo_root}" rev-parse --verify "${branch}" >/dev/null 2>&1; then
    echo "error: branch ${branch} already exists" >&2
    echo "       delete with: git branch -D ${branch}" >&2
    exit 1
fi

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
if [[ -z "${base_branch}" ]]; then
    echo "error: cannot determine base branch (tried origin/HEAD, main, master)" >&2
    echo "       set BASE_BRANCH=<your-default-branch>" >&2
    exit 1
fi
base="$(git -C "${repo_root}" rev-parse "${base_branch}")"
git -C "${repo_root}" worktree add -b "${branch}" "${worktree_dir}" "${base}"

cp "${task_dir}/PROMPT.md" "${worktree_dir}/PROMPT.md"
cp "${task_dir}/SPEC.md" "${worktree_dir}/SPEC.md"

# Record the run start time for wall-clock measurement at capture.
# Layout: builds/<model>/rounds/<task>-<date>/ — per-model rounds archive
# alongside the current builds/<model>/sandbox.py pointer.
run_dir="${repo_root}/builds/${model}/rounds/${task}-${date_stamp}"
mkdir -p "${run_dir}"
date -u +%Y-%m-%dT%H:%M:%SZ > "${run_dir}/.started_at"

cat <<EOF

✓ worktree ready
  path:    ${worktree_dir}
  branch:  ${branch}
  base:    ${base}
EOF

if [[ "${auto_drive}" -eq 1 ]]; then
    echo
    echo "▶ --auto: driving opencode against ${worktree_dir}"
    echo

    # Resolve slug from config and run opencode via the shared wrapper.
    # On success, chain to capture-run.sh; on failure, leave worktree
    # intact so the user can inspect what happened.
    python3 - "${repo_root}/bench/scripts" "${worktree_dir}" "${model}" "${task}-${model}-${date_stamp}" <<'PYEOF'
import sys
scripts_dir, worktree_dir, model, title = sys.argv[1:]
sys.path.insert(0, scripts_dir)
import _config
import _opencode_run

cfg = _config.load()
slug = cfg.slug_for(model)

message = (
    "Read PROMPT.md and SPEC.md at the worktree root, then implement "
    "sandbox.py per the spec. Stop when sandbox.py exists at the worktree "
    "root and your own quick smoke check passes."
)

rc = _opencode_run.run(
    directory=worktree_dir,
    model=slug,
    message=message,
    title=title,
)
sys.exit(rc)
PYEOF
    rc=$?

    if [[ ${rc} -ne 0 ]]; then
        echo
        echo "✗ opencode run exited ${rc}; not capturing"
        echo "  worktree preserved at: ${worktree_dir}"
        echo "  inspect, then either retry or run capture-run.sh manually"
        exit "${rc}"
    fi

    echo
    echo "▶ --auto: chaining to capture-run.sh"
    exec "${repo_root}/bench/scripts/capture-run.sh" "${task}" "${model}"
fi

cat <<EOF

next steps
  1. cd ${worktree_dir}
  2. open opencode, set model: ${model}
  3. paste PROMPT.md into the session and let it run
  4. when finished, drop the session export at: ${worktree_dir}/transcript.md
  5. capture artifacts:
     ${repo_root}/bench/scripts/capture-run.sh ${task} ${model}

EOF
