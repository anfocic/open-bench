#!/usr/bin/env bash
# run-all.sh <task>
#
# End-to-end driver: runs every implementer in bench/config.json with --auto,
# then auto-drives all judges, then aggregates. Single command per task.
#
# Each implementer runs sequentially (worktrees are isolated but opencode
# sessions are not safe to parallelize). Failures in one model do not abort
# the rest; a summary is printed at the end.

set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "usage: $0 <task>" >&2
    exit 2
fi

task="$1"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"
config="${repo_root}/bench/config.json"

if [[ ! -f "${config}" ]]; then
    echo "error: ${config} not found" >&2
    exit 1
fi

implementers=()
while IFS= read -r line; do
    implementers+=("${line}")
done < <(python3 - "${config}" <<'PYEOF'
import json, sys
print('\n'.join(json.load(open(sys.argv[1]))['implementers']))
PYEOF
)

if [[ ${#implementers[@]} -eq 0 ]]; then
    echo "error: no implementers in ${config}" >&2
    exit 1
fi

declare -a ok_models=()
declare -a fail_models=()

echo "==> implementer phase: ${#implementers[@]} model(s)"
for model in "${implementers[@]}"; do
    echo
    echo "--- ${model} ---"
    if "${script_dir}/start-run.sh" --auto "${task}" "${model}"; then
        ok_models+=("${model}")
    else
        echo "WARN: ${model} failed, continuing" >&2
        fail_models+=("${model}")
    fi
done

echo
echo "==> judgment phase"
"${script_dir}/start_judgments.py" --auto "${task}"

echo
echo "==> aggregate phase"
"${script_dir}/aggregate_judges.py" "${task}"

echo
echo "==> done"
echo "ok:     ${ok_models[*]:-none}"
echo "failed: ${fail_models[*]:-none}"
[[ ${#fail_models[@]} -eq 0 ]]
