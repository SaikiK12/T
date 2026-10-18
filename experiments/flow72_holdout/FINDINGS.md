# FINDINGS: flow72_holdout (R198)

**Verdict: NOT CONFIRMED by the frozen rule (t 1.22 < 2), with a large positive mean.** The 72 h flow slice book earned
+104% (sum of daily returns) over 457 holdout days, but with far more volatility than in-sample, so the holdout cannot
tell it from luck at the agreed bar. The holdout is spent for these cells.

- **Registry row:** R198 (trials: 1)
- **Reproduce:** prereg sha 6e510b1e; `python scripts/run_flow72_holdout.py` (run 2026-10-18; a first attempt crashed on
  an array length in the BTC-beta line before any statistic was computed or printed, then ran once after the fix).

## Numbers (2025-07-01 to 2026-09-30, 457 days, 1x costs unless said)
| book | hedge | total | per year | Sharpe | NW t | max DD | beta BTC | gross exposure |
|---|---|---|---|---|---|---|---|---|
| combined | universe (primary) | +103.8% | +82.9% | 1.05 | 1.22 | 47% | 0.10 | 1.93 |
| combined | top 10 basket | +167.3% | +133.6% | 1.08 | 1.11 | 82% | 0.17 | 1.93 |
| combined | BTC | +117.9% | +94.2% | 0.69 | 0.85 | 85% | -0.13 | 1.93 |
| combined | none | +156.4% | +124.9% | 0.77 | 0.94 | 76% | -2.05 | 1.93 |
| top_vs_crowd alone | universe | +89.3% | +71.4% | 2.49 | 2.72 | 16% | -0.02 | 0.64 |
| taker[24] alone | universe | +20.3% | +16.2% | 0.31 | 0.36 | 41% | 0.08 | 0.64 |
| taker[4] alone | universe | -5.9% | -4.7% | -0.21 | -0.29 | 18% | 0.04 | 0.64 |

Primary by month: Jul +17%, Aug +7%, Sep -17%, Oct -1%, Nov +22%, Dec -10%, Jan +9%, Feb -17%, Mar +7%, Apr +14%,
May +7%, Jun -19%, Jul +33%, Aug +51%, Sep +2% (10 of 15 positive).

In-sample reference for the practical hedges (2021-2025H1): top 10 basket +66%/yr (t 2.53, max DD 72%), BTC +100%/yr
(t 2.46, max DD 111%), against the idealized universe hedge's +42.6% (t 3.25, max DD 27%).

## Cost sensitivity
Primary: +82.9%/yr (1x), +61.8% (2x, t 0.91), +40.7% (3x, t 0.60). Costs are not what decides this book; its variance is.

## Reading
- The sign held out of sample at every cost level and with every hedge; the size went up, and so did the risk: the
  book carried 1.93 of gross short exposure against 1.31 in-sample (more coins sat in the bins with K frozen), and the
  monthly swings reached +-20 to 50%.
- top_vs_crowd alone (top traders positioned short against the crowd) is the cleanest part: t 2.72 on the holdout,
  max drawdown 16%. It was reported, not decided on, so it is a lead for a forward test, not a confirmed edge.
- taker[4] adds nothing out of sample, as its in-sample cost sensitivity already suggested.

## What this does not show
- The universe hedge is idealized; the top-10 basket and BTC hedges are practical and riskier.
- No borrow, margin or liquidation modeling for a book short 1.3-1.9x of capital in alts; squeezes are in the returns
  but not forced exits.
- Program multiplicity: the cells came out of a 338,240-cell atlas and two book designs.

## Next
A forward paper monitor of the frozen primary and of top_vs_crowd alone (pre-registered forward tickets, scored with
`lab.gate.go_real`); no real money before that gate.
