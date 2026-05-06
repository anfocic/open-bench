#!/usr/bin/env bash
# capture-run.sh — shim, see capture_run.py
cd "$(git rev-parse --show-toplevel)"
exec python3 -m bench.scripts.capture_run "$@"
