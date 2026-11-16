# gatemaker_v1 (R497): what a resting order earns or loses on Gate

Measurement, 0 trials, frozen 2026-11-16 ([PREREG](PREREG.md)). It prices lever 2 of the
[fee method](../../research/intake/fee_map_20261116.md): rest on Gate's wide leg of R390's C14 carry book and hedge
on Binance at once.

- **What it measures:** from Gate's public trade tape (60 sampled USDT perps, 28 one-hour windows, 2026-11-02..15):
  - a resting order's 1/5/60/300 s markout;
  - a taker's effective half-spread.
- **The rule:** the lever holds in a volume band if the hedged-maker cost is at most half the taker cost.
  - Hedged-maker cost = 2 bp fee − 5 s markout.
  - Taker cost = effective half-spread + 7.5 bp fee.
- **Run:** `python scripts/run_gatemaker.py`, once. Results go in `results/`, and the reading in FINDINGS.md.

**Result (2026-11-16):** LEVER_HOLDS in all four volume bands, at a 2 bp and at a 4 bp maker fee, under the
touch-fill assumption ([FINDINGS](FINDINGS.md)). Queue position, time to fill and the chase cost are not measured
here; they are the job of the forward execution lane this result earns.
