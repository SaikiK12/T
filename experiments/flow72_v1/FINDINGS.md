# FINDINGS: flow72_v1 (R196)

**Verdict: NULL.** Shorting coins as they enter the heavy-taker-selling or top-traders-short bins, held 72 h and hedged
with the universe, loses (-20%/yr, t -2.7 at the primary). The atlas edge of these cells lives in the hours a coin
stays in the bin, not at the entry.

- **Registry row:** R196 (trials: 36 books)
- **Reproduce:** prereg sha 717a08b9; `python scripts/run_flow72.py`.

## Numbers (2021-01-01 to 2025-06-30, 1x costs)
| entry | hedge | slots | net / yr | t | max DD | gross | hedge PnL | per year 2021..2025H1 |
|---|---|---|---|---|---|---|---|---|
| market | universe | 20 (primary) | -20.0% | -2.73 | 94% | 4.5% | -10.1% | -2, -26, -26, -4, -32% |
| market | universe | 10 | -4.7% | -0.42 | 88% | 20.2% | -11.5% | +2, +8, +26, -21, -37% |
| market | BTC | 10 | +39.1% | 1.74 | 58% | 20.2% | +32.2% | +2, +32, +45, +40, +56% |
| market | none | 10 | +7.5% | 0.23 | 158% | 20.2% | 0 | +20, +87, -57, -53, +37% |
| limit | universe | 20 | -19.3% | -2.65 | 97% | 5.9% | -7.3% | |

The BTC-hedged rows earn from being long BTC against short alts (alts fell against BTC over the period; beta to BTC
-0.14), not from the cells. 2x and 3x costs: every universe-hedged book is negative.

## Diagnostic (run after the verdict, not pre-registered)
Excess return over 72 h, bin 0, measured over every hour in the bin (as atlas_v1) vs only at episode starts (as the
book trades), day-weighted mean (t) and trade-weighted mean:

| cell | discovery all hours | discovery entries | validation all hours | validation entries |
|---|---|---|---|---|
| top_vs_crowd/xs8 | -53.7 bp (t -3.05) | -56.9 (-2.70), pooled -57.0 | -40.4 (-2.33) | -31.6 (-1.55), pooled -10.1 |
| taker[24]/xs8 | -57.0 (-3.84) | -25.0 (-1.94), pooled -18.7 | -37.1 (-2.11) | -8.9 (-0.52), pooled -5.2 |
| taker[4]/xs8 | -32.1 (-4.45) | -22.5 (-3.73), pooled -20.4 | -15.5 (-2.14) | -14.1 (-2.36), pooled -12.8 |

Per entry, the validation edge is 5-13 bp over 72 h, under one round trip (about 15 bp).

## What this does not show
- The all-hours edge can be traded by a different construction: a slice opened every hour a coin is in the bin and
  closed 72 h later (overlapping portfolios). Its cost per slice is one round trip, its edge the all-hours mean. That is
  a new lane (flow72_v2).
- The universe hedge is idealized (the basket's internal rebalancing is free).

## Next
flow72_v2: overlapping 72 h slices.
