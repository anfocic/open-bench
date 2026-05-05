#!/usr/bin/env bash
# run-all.sh — shim, see run_all.py
exec python3 "$(dirname "$0")/run_all.py" "$@"