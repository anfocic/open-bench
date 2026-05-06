#!/usr/bin/env bash
# start-run.sh — shim, see start_run.py
cd "$(git rev-parse --show-toplevel)"
exec python3 -m bench.scripts.start_run "$@"
