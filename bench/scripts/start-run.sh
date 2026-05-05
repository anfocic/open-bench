#!/usr/bin/env bash
# start-run.sh — shim, see start_run.py
exec python3 "$(dirname "$0")/start_run.py" "$@"