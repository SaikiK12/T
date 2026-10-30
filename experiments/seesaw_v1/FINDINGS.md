# FINDINGS: seesaw_v1 (R219), the big coins' last hour does predict alts, by about 1.5 bp per hour; costs eat it

PREREG sha 52b33054. Run 2026-10-19 by `scripts/run_seesaw.py`. Results in `results/` (`spreads.csv` holds the next-hour
quintile spreads).

## Verdict: NULL. No variant passed discovery; validation and holdout books were not run
A one-hour-delay check was planned only for variants that reached validation, so it was never computed. The holdout
stays unread for this family.

| Variant | Net 1x (bp/day, t) | Gross | Cost | Long-leg gross | Short-leg gross | Next-hour quintile spread (disc / val, bp per hour) |
|---|---|---|---|---|---|---|
| F1 lead-lag, H 1 h | -334.3, t -30.7 | **+35.3** | 369.6 | +36.0 | +0.1 | **+1.45 / +0.93** |
| F1 lead-lag, H 4 h | -77.8, t -16.5 | +14.7 | 92.5 | +23.9 | -8.5 | +1.45 / +0.93 |
| F2 catch-up L 1, H 4 | -109.9, t -16.0 | +24.2 | 134.1 | +30.8 | -5.8 | +4.87 / +0.00 |
| F2 catch-up L 4, H 4 | -135.7, t -15.0 | -0.7 | 135.0 | +18.3 | -18.2 | +2.37 / -0.65 |
| F2 catch-up L 24, H 24 | -29.7, t -3.9 | -7.1 | 22.6 | +10.6 | -16.9 | +0.84 / -0.02 |

Discovery is 2021-01..2023-12, crypto contracts only, alts of liquidity rank 6-50, and leaders are ranks 1-5. Net at
2x/3x is in `results/results.csv`; it is only worse.

## Reading
- **The lead-lag (F1) exists at the hourly scale and holds out of sample before costs.** The alts whose fitted reaction
  to the leaders' last hour predicts a rise beat those predicted to fall by +1.45 bp in the next hour in 2021-23 and
  +0.93 bp in 2024-25H1. It is small and steady: about 22-35 bp per day if captured every hour, carried by the long side.
- **It cannot pay a taker.** Opening and closing 1 h slices at 8-12 bp one-way costs about 370 bp per day. Holding 4 h
  costs 92 bp/day and keeps 15 bp/day of gross.
- **Catch-up (F2) decays:** +4.9 bp per hour in 2021-23, 0.0 in 2024-25H1.
- The lead is at minute scale in the literature (Guo et al. 2024). What survives an hour is a remnant.

## What could make it pay (each needs a new lane)
- **Maker entries on MEXC.** MEXC lists maker fee 0 on most contracts (`docs/RESEARCH_FRONTIER.md`; the contract list
  shows makerFeeRate 0 for BTC_USDT). A limit-order version of F1 pays no fee, but fills are adverse-selected: R193
  showed maker fills on directional cells turn into market exposure. It needs a paper test with queue-aware fills,
  not an OHLC trade-through.
- **Overlay rather than standalone.** F1's score can tilt the entry hour of slices that the flow books open anyway, at
  no extra turnover.
- Trials 5. Program trials after this lane: 9,471,734.
