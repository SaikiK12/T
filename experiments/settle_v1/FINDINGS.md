# FINDINGS: settle_v1 (R223), funding capture across a settlement: the price moves against you by more than the payment

PREREG sha e1f380f4. Run 2026-10-19 by `scripts/run_settle.py`. Results are in `results/`:
- `results.csv`;
- `events_disc_val.csv`: one row per event, discovery and validation only;
- `verdict.json`.

## Verdict: NULL. Both directions failed discovery; validation and holdout were not run
The holdout stays unread for this family.

Discovery is 2021-01..2023-12, crypto contracts. A position is held from 1 h before an expected settlement to 1 h
after, when the last settled rate is at or beyond ±0.20%. Units are bp per event, and t is clustered by event month.

| Variant | Universe | Events (months) | Net 1x, t | Funding collected | Price part | Cost | Net 2x / 3x | Pass-through | Off-cycle net |
|---|---|---|---|---|---|---|---|---|---|
| LONG_NEG (rate <= -0.20%) | rank <= 50 | 1,339 (36) | **-38.5, t -0.69** | +47.6 | -72.3 | 13.9 | -52.4 / -66.3 | 1.52 | -26.6 |
| LONG_NEG | rank 51-100 | 823 (36) | -83.8, t -0.95 | +35.1 | -95.0 | 23.9 | -107.8 / -131.7 | 2.71 | -34.8 |
| SHORT_POS (rate >= +0.20%) | rank <= 50 | 1,980 (9) | **-43.4, t -1.93** | +22.9 | -51.7 | 14.6 | -58.0 / -72.7 | 2.26 | -8.4 |
| SHORT_POS | rank 51-100 | 1,786 (9) | -38.4, t -2.39 | +24.5 | -38.9 | 24.0 | -62.4 / -86.4 | 1.59 | -23.7 |

- Hit rate is 0.47-0.50.
- On 4 h contracts LONG_NEG nets -8.6 bp (280 events); on 8 h contracts, -46.4.
- Excess over the equal-weight universe is +3.8 (LONG_NEG) and -3.5 (SHORT_POS) bp net. The extreme-rate windows are
  market-wide moves.

## Reading
- **The payment is real, but the price more than pays it back.** Pass-through is 1.5-2.3 for the top 50: the price
  moves against the holder by one and a half to two times the funding collected. The dividend analogy predicted a
  pass-through of 1. The market over-adjusts.
- **Part of this is the state, part is the settlement.**
  - **State:** the off-cycle window (the same events two to four hours earlier, with no settlement) loses 26.6 bp
    net, or about -13 bp gross. Extreme negative funding comes with falling prices.
  - **Settlement:** the window around the settlement loses about -72 bp in price, so roughly -60 bp is specific to
    the settlement hours.
- **Squeezes are rare and clustered:** positive rates at +0.20% occur in only 9 months, so SHORT_POS is a few
  episodes.
- **For MEXC:** its settled rates match Binance's, so collecting an extreme rate on MEXC across settlement is not a
  free payment either. Rule 2 in `docs/MEXC_EDGES.md` is closed.
- The reverse trade (fade the payment) would have earned roughly 72 - 48 = +25 bp gross per LONG_NEG event, about
  +11 net, with t well under 1. It would be a new lane chosen after seeing this. Not worth registering.

## Multiplicity
Trials 2. Program trials after this lane: 9,471,747.
