#!/bin/sh
# One forward tick: R200's journal first (scripts/forward_tick.py), then the lanes that read it:
# R214 flow72_fwd3 (one bar late, Binance), R215 mexc_fwd (MEXC), R218 mexc_fwd_sq (agreement-squared on MEXC),
# R220 carry_fwd (funding carry on Binance and MEXC), R221 mexc_seq (sequential decision on the MEXC books).
cd "$(dirname "$0")/.." || exit 1
PY=.venv/bin/python
timeout 1500 $PY scripts/forward_tick.py >> experiments/flow72_fwd2/tick.log 2>&1
timeout 900 $PY scripts/forward_delayed.py >> experiments/flow72_fwd3/tick.log 2>&1
timeout 900 $PY scripts/forward_mexc.py >> experiments/mexc_fwd/tick.log 2>&1
timeout 900 $PY scripts/forward_mexc_sq.py >> experiments/mexc_fwd_sq/tick.log 2>&1
timeout 900 $PY scripts/forward_carry.py >> experiments/carry_fwd/tick.log 2>&1
timeout 300 $PY scripts/forward_seq.py >> experiments/mexc_seq/tick.log 2>&1
