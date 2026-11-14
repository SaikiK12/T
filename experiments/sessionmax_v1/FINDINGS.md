# FINDINGS: sessionmax_v1 (R490, M539) — session-decomposed MAX on crypto perps

**Verdict: NULL.** The session decomposition (M539) adds no net edge over the plain 24 h MAX (M144) on 24/7 crypto
perps, and no book clears its gate. This reproduces R222's M144 null on a longer, wider sample and extends it to the
intraday/overnight split the source paper proposes. Frozen PREREG `df357d4084ea`; one run, no search.

## What was run
`scripts/run_sessionmax.py` on `data/klines_1h` (50 USDT-margined Binance perps, 2021-01-01..2026-09-30, manifest sha
`16e6434c8fcd`). Three dollar-neutral top/bottom-quintile books, 7-day (168 h) hold, daily signal at the 14:00 UTC
close, costs from `engine.cost_matrix` (liquidity tiers): **S-INTRA** (max of last 7 intraday session returns
14:00-20:59 UTC), **S-OVER** (max of last 7 overnight returns 21:00-13:59 UTC), **CONTROL** (max of last 7 plain 24 h
returns, the M144 book). Discovery day < 2024-01-01 (1,095 days); validation 2024-01-01..2025-06-30. 18 scored cells.

## Result (1x cost, discovery)

| Book | net bp/day | NW t | alpha t (vs BTC) | gross bp/day | cost bp/day |
|---|---|---|---|---|---|
| S-INTRA | -3.23 | -0.52 | -0.61 | -0.46 | 2.77 |
| S-OVER | +2.13 | +0.29 | +0.24 | +4.98 | 2.84 |
| CONTROL (24 h MAX) | -2.74 | -0.41 | -0.48 | +0.05 | 2.79 |

No book passes the discovery gate (mean > 0 **and** alpha t >= 2.0). Only S-OVER is positive at 1x, and it fails
twice over: alpha t 0.24 (<< 2.0) and, on the PREREG's own M539 claim, it beats CONTROL by only +4.87 bp/day at
t 1.33 (< the stated bar), on 1,095 days.

## Cost sensitivity (discovery)

| Book | 1x | 2x | 3x |
|---|---|---|---|
| S-INTRA | -3.23 | -5.99 | -8.76 |
| S-OVER | +2.13 | -0.71 | -3.55 |
| CONTROL | -2.74 | -5.53 | -8.31 |

S-OVER's +2.13 bp/day gross-of-nothing is entirely inside the cost band: at 2x cost it is -0.71, at 3x -3.55. The
signal's gross edge (~5 bp/day) is smaller than realistic round-trip cost on a 7-day hold in this liquidity tier.

## Validation (read only because a book was positive at 1x discovery, as the PREREG allows)
S-OVER 2024-01..2025-06: **-5.97 bp/day**, alpha t -0.67. The one positive discovery cell does not survive out of
sample; it changes sign. S-INTRA -1.40, CONTROL -3.26. The holdout was never touched (no book passed validation).

## Null and robustness
- **Block bootstrap** (block 10 d, 2,000 replicas, seed 20261114) on the best book's own 1x daily net: the 95th
  percentile of the mean-removed null is alpha t **1.61**; the observed S-OVER alpha t is **0.24**. No rejection.
- **Session-label permutation** (swap which window is intraday vs overnight per day, 200 replicas): S-OVER's real
  edge over CONTROL (+4.87 bp/day) sits at the 97.5th percentile of the label-shuffled distribution — i.e. it is
  **not** distinguishable from what the same 14:00 signal produces under a random session label. The "session" is not
  doing the work; the sign split is noise.
- **Trimmed mean (10%, 1x discovery):** S-INTRA -9.28, S-OVER -5.24, CONTROL -9.21 bp/day. Every book is negative
  after trimming the tails — the thin positive S-OVER mean is tail-driven.
- **Leave-two-coins-out (1,225 pairs, 1x discovery):** S-OVER min -1.41, mean +1.96, 96.6% of pairs positive;
  S-INTRA 0.2%, CONTROL 1.4% positive. S-OVER's sign is broad across coin pairs, but its magnitude is inside the
  cost band and its alpha t is 0.24, so breadth does not rescue significance.

## Reading against the program, not just this null
- **Reproduces R222 (M144 NULL).** CONTROL here (24 h MAX, longer sample) is -2.74 bp/day, t -0.41 — the same null.
- **Extends R435 (M492 NULL).** The overnight/intraday split on MEXC stock perps was null; here on crypto perps it is
  null too. Two venues, two session definitions, one answer.
- **M539's distinctive claim fails.** The paper's "positive same-session sign" is not present net of cost, and the
  permutation test shows the apparent S-OVER edge is not a session effect.

## Honest limits
- **Universe survivorship:** the 50 symbols are a large-cap set chosen in 2026, not the 2021 universe. Stated in the
  PREREG; it biases toward coins that survived, which if anything flatters a momentum signal — and it is still null.
- **Hold deviation:** the paper holds only within a session; this lane holds 7 days continuously (the lab's slice
  engine prices a continuous hold). A session-restricted hold is a successor lane, not tested here.
- **No funding on the control's benchmark leg:** the BTC benchmark is price-only, matching R222's convention.
- **One run.** No feature, split or parameter was varied after seeing results. A second read needs a new frozen PREREG.
- **Not checked:** paid-vs-recorded funding for this venue, and a full coverage-survival comparison (the fixed major
  universe makes it moot).

## What this authorizes
Nothing. A NULL is a result: M539 is closed as tested-and-null. It does not open a forward lane, does not move
`go_real()`, and authorizes no order, key or money.

## Reproduction
```
.venv/bin/python -m lab.data build klines 1h --symbols "$(cat /tmp/syms.txt)"   # data/klines_1h, manifest 16e6434c8fcd
python -c "import lab.prereg as p; p.freeze('experiments/sessionmax_v1/PREREG.md')"   # df357d4084ea
python scripts/run_sessionmax.py                                                  # writes results/report.json
```
