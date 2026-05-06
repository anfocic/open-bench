#!/usr/bin/env bash
# new-task.sh — shim, see new_task.py
cd "$(git rev-parse --show-toplevel)"
exec python3 -m bench.scripts.new_task "$@"
