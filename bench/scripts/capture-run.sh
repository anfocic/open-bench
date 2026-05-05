#!/usr/bin/env bash
# capture-run.sh — shim, see capture_run.py
exec python3 "$(dirname "$0")/capture_run.py" "$@"