#!/usr/bin/env bash
# new-task.sh — shim, see new_task.py
exec python3 "$(dirname "$0")/new_task.py" "$@"