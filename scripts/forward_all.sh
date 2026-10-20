#!/bin/sh
# One forward tick: R200's journal first (scripts/forward_tick.py), then the lanes that read it:
# R214 flow72_fwd3 (one bar late, Binance), R215 mexc_fwd (MEXC), R218 mexc_fwd_sq (agreement-squared on MEXC),
# R220 carry_fwd (funding carry on Binance and MEXC), R221 mexc_seq (sequential decision on the MEXC books),
# R224 mexc_costs (MEXC order-book cost snapshots), R225 vt_fwd (volatility target on the MEXC books),
# R266 unlocks_fwd (the unlock short on MEXC paper, events from the recorded calendar snapshot). R268 delist_fwd (the
# spot delisting-notice short on MEXC paper) and R270 montag_fwd (the Monitoring Tag short at +24 h) run right after the
# notice recorder, so their tickets precede the next hour.
# Last, the processing-lag report (experiments/forward_lag), the panel (docs/PANEL.md) and the dashboard's datasets
# (dashboard/data/, uploaded to the Control Room artifact by the session's loop tick).
# Before the lanes, the point-in-time recorders (MEXC funding/ticker snapshot, Binance notices, unlock calendar);
# after them, the recorder digest (experiments/recorders/journal/digests.csv).
cd "$(dirname "$0")/.." || exit 1
# one tick at a time: a second run while one is going exits at once
exec 9> .forward.lock
flock -n 9 || { echo "$(date -u +%FT%TZ) another tick is running" >> experiments/flow72_fwd2/tick.log; exit 0; }
PY=.venv/bin/python
STAMP="$(date -u +%FT%TZ) code $(git rev-parse --short HEAD)$(git diff --quiet HEAD -- lab scripts || echo +dirty)"
for d in flow72_fwd2 flow72_fwd3 mexc_fwd mexc_fwd_sq carry_fwd mexc_seq mexc_costs vt_fwd unlocks_fwd delist_fwd montag_fwd recorders; do echo "== tick $STAMP" >> experiments/$d/tick.log; done
# point-in-time recorders first (data/recorders/, gitignored; digests committed by record_digest.py at the end)
timeout 120 $PY scripts/record_mexc_ticker.py >> experiments/recorders/tick.log 2>&1
timeout 300 $PY scripts/record_notices.py >> experiments/recorders/tick.log 2>&1
timeout 300 $PY scripts/record_unlocks.py >> experiments/recorders/tick.log 2>&1
timeout 300 $PY scripts/forward_delist.py >> experiments/delist_fwd/tick.log 2>&1
timeout 300 $PY scripts/forward_montag.py >> experiments/montag_fwd/tick.log 2>&1
timeout 1500 $PY scripts/forward_tick.py >> experiments/flow72_fwd2/tick.log 2>&1
timeout 900 $PY scripts/forward_delayed.py >> experiments/flow72_fwd3/tick.log 2>&1
timeout 900 $PY scripts/forward_mexc.py >> experiments/mexc_fwd/tick.log 2>&1
timeout 300 $PY scripts/record_mexc_depth.py >> experiments/mexc_costs/tick.log 2>&1
timeout 900 $PY scripts/forward_mexc_sq.py >> experiments/mexc_fwd_sq/tick.log 2>&1
timeout 900 $PY scripts/forward_carry.py >> experiments/carry_fwd/tick.log 2>&1
timeout 300 $PY scripts/forward_seq.py >> experiments/mexc_seq/tick.log 2>&1
timeout 300 $PY scripts/forward_vt.py >> experiments/vt_fwd/tick.log 2>&1
timeout 600 $PY scripts/forward_unlocks.py >> experiments/unlocks_fwd/tick.log 2>&1
timeout 120 $PY scripts/forward_lag.py >> experiments/vt_fwd/tick.log 2>&1
timeout 120 $PY scripts/panel.py >> experiments/vt_fwd/tick.log 2>&1
timeout 120 $PY scripts/dashboard_data.py >> experiments/vt_fwd/tick.log 2>&1
timeout 300 $PY scripts/record_digest.py >> experiments/recorders/tick.log 2>&1
