#!/usr/bin/env bash
# Thin wrapper around main.py so the demo command is short.
#   ./run.sh          -> full chain (bench -> program -> ladder -> figures)
#   ./run.sh bench    -> one stage, extra flags are forwarded
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
if [ $# -eq 0 ]; then
  exec "$PY" main.py all
fi
exec "$PY" main.py "$@"
