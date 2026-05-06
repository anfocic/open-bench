#!/usr/bin/env bash
# run-all.sh — shim, see run_all.py
cd "$(git rev-parse --show-toplevel)"
exec python3 -m bench.scripts.run_all "$@"
