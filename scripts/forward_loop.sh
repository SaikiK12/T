#!/bin/sh
# Optional scheduler: the full tick at minute 15 of every hour, and R200 alone at minute 45. Starting it remains an
# explicit operator action, for example:
#   FORWARD_STATE_DIR=/home/user/forward_state setsid nohup sh scripts/forward_loop.sh >/dev/null 2>&1 &
# Why these minutes: R200 computes an hour 12 minutes after its bar closes (forward_tick.MARGIN) and defers it until
# 95% of its coins have all twelve 5-minute rows; forward_lag.py counts an hour computed more than 60 minutes after
# its close as late. At minute 6 the bar that had just closed was not yet due, so every hour waited for the next tick
# (66 minutes): late by construction. Minute 15 computes it about 15 minutes after the close; minute 45 picks up an
# hour deferred at minute 15, still inside 60.
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
  hour=$(( now / 3600 * 3600 ))
  if [ "$now" -lt $(( hour + 900 )) ]; then
    next=$(( hour + 900 )); args=""
  elif [ "$now" -lt $(( hour + 2700 )) ]; then
    next=$(( hour + 2700 )); args="--task R200"
  else
    next=$(( hour + 4500 )); args=""
  fi
  sleep $(( next - now ))
  # $args is unquoted on purpose: empty for the full tick, two words for R200 alone
  if sh scripts/forward_all.sh $args; then
    state=SUCCESS
  else
    state=FAILED
  fi
  echo "$(date -u +%FT%TZ) forward_loop ${args:-full tick} $state; inspect per-run status.json" >> "$FORWARD_STATE_DIR/loop.log"
done
