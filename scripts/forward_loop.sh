#!/bin/sh
# Optional hourly scheduler at minute 6. Starting it remains an explicit operator action.
set -eu
cd "$(dirname "$0")/.."
: "${FORWARD_STATE_DIR:?Set FORWARD_STATE_DIR to an absolute directory outside the checkout}"
case "$FORWARD_STATE_DIR" in /*) ;; *) echo "FORWARD_STATE_DIR must be absolute" >&2; exit 2 ;; esac
FORWARD_STATE_DIR=$(realpath -m -- "$FORWARD_STATE_DIR")
case "$FORWARD_STATE_DIR/" in "$(pwd -P)/"*) echo "Run storage must be outside the checkout" >&2; exit 2 ;; esac
export FORWARD_STATE_DIR
mkdir -p "$FORWARD_STATE_DIR"
exec 8> .forward_loop.lock
flock -n 8 || { echo "Another forward loop owns .forward_loop.lock" >&2; exit 1; }
echo $$ > .forward_loop.pid
while true; do
  now=$(date -u +%s)
  next=$(( (now / 3600 + 1) * 3600 + 360 ))
  sleep $(( next - now ))
  if sh scripts/forward_all.sh; then
    state=SUCCESS
  else
    state=FAILED
  fi
  echo "$(date -u +%FT%TZ) forward_loop $state; inspect per-run status.json" >> "$FORWARD_STATE_DIR/loop.log"
done
