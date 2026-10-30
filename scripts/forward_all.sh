#!/bin/sh
# Compatibility entry point: task graph/locks/timeouts live in lab/operations.py.
# This does not install or start a scheduler. Configure external run storage explicitly.
set -eu
cd "$(dirname "$0")/.."
: "${FORWARD_STATE_DIR:?Set FORWARD_STATE_DIR to an absolute directory outside the checkout}"
PY=${FORWARD_PYTHON:-.venv/bin/python}
exec "$PY" scripts/orchestrate_forward.py --execute --state-dir "$FORWARD_STATE_DIR" \
  --run-id "$(date -u +%Y%m%dT%H%M%S)_$$" --python "$PY" "$@"
