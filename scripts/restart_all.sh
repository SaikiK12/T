#!/bin/sh
# Bring the forward loop, the notice loop and every recorder/forward daemon back after a container or machine restart.
# Idempotent: each daemon's `ensure` does nothing when its journal lock is held by a live process, and the two loops
# refuse to start twice (flock). Paper only; nothing here places an order or reads a key.
#   FORWARD_STATE_DIR=/absolute/path/outside/the/checkout sh scripts/restart_all.sh
# FORWARD_STATE_DIR defaults to ../forward_state next to the checkout. The full forward tick runs once at the end so lanes
# and panels catch up; the hourly loop would do it at minute 15 anyway.
set -u
cd "$(dirname "$0")/.." || exit 1
: "${FORWARD_STATE_DIR:=$(cd .. && pwd -P)/forward_state}"
export FORWARD_STATE_DIR
mkdir -p "$FORWARD_STATE_DIR" data/logs
PY=.venv/bin/python
[ -x "$PY" ] || PY=python3
timeout 90 "$PY" scripts/clock_check.py slew >/dev/null 2>&1 || echo "clock check failed or timed out" >&2

# notice_loop.sh has no lock of its own, so a second copy would double the 5-minute cycle: start each loop only if absent
pgrep -f "sh scripts/forward_loop.sh" >/dev/null || setsid nohup sh scripts/forward_loop.sh >/dev/null 2>&1 &
pgrep -f "sh scripts/notice_loop.sh" >/dev/null || setsid nohup sh scripts/notice_loop.sh >/dev/null 2>&1 &

for s in forward_usopen record_tape record_hft record_raw record_option_expiry record_lighter_trades record_dex_prices \
         record_news record_commodity_perps forward_settlelit forward_settlehop; do
  timeout 40 "$PY" "scripts/$s.py" ensure >/dev/null 2>&1 || echo "ensure failed or timed out: $s" >&2
done

setsid nohup sh scripts/forward_all.sh >"$FORWARD_STATE_DIR/restart_tick.log" 2>&1 &
echo "restarted: loops, ${FORWARD_STATE_DIR} state, daemons ensured, full tick started"
