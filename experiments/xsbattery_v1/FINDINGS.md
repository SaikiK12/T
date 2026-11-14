# FINDINGS: xsbattery_v1 (R238). Eight cross-sectional features as one-week spread books

**Verdict: NULL.** None of the 16 books reached t 2 in discovery (2021-2023), so validation was not computed. The
holdout was not read.

- **Registry row:** R238 (trials 16). Program trials after it: 9,471,921.
- **Gate:** 0 (screen).
- **Reproduce:** prereg sha 045de11e, frozen in commit 284f0fc before the run. Run `python scripts/run_xsbattery.py`
  (about 3 minutes).
- **Origin:** queue M034 (weekly momentum and reversal), M180 (MAX, IVOL, skew), M182 (52-week high), M171 (funding
  slope), M178 (OHLC spread proxy). The owner's brute-force pass.

## Numbers (discovery 2021-01..2023-12, 1,095 days; 168 h hold)

H longs bin 7 of the feature and shorts bin 0. L is the reverse, so its gross is the H gross with the sign flipped and
its net is lower by twice the cost.

| Book | Net bp/day 1x / 2x / 3x | NW t (1x) | Gross / cost (1x) | Trimmed (1x) | K | Coverage |
|---|---|---|---|---|---|---|
| mom7/H | +9.0 / +7.3 / +5.5 | **1.77** | 10.8 / 1.75 | +6.5 | 12.9 | 99.6% |
| rev28/H | +8.5 / +7.4 / +6.3 | 1.27 | 9.5 / 1.08 | +7.4 | 12.2 | 95.2% |
| hi52/H | +6.4 / +5.8 / +5.3 | 0.98 | 6.9 / 0.55 | +6.1 | 5.1 | 48.0% |
| maxd/H | +6.0 / +5.3 / +4.5 | 1.08 | 6.7 / 0.72 | +4.4 | 11.8 | 93.0% |
| skew/H | +5.5 / +4.6 / +3.7 | 1.16 | 6.5 / 0.93 | +3.6 | 11.8 | 93.3% |
| arspread/H | +5.0 / +3.9 / +2.7 | 0.88 | 6.2 / 1.18 | +3.9 | 5.5 | 93.3% |
| ivol/H | +3.7 / +3.0 / +2.4 | 0.63 | 4.4 / 0.68 | +1.4 | 11.7 | 92.9% |
| fslope/L | +2.0 / +0.5 / -0.9 | 0.47 | 3.4 / 1.41 | +2.2 | 11.9 | 94.2% |

The other eight books (mom7/L, rev28/L, ...) are the mirrors and lost: mom7/L -12.5 bp/day (t -2.46) was the largest.

Per year at 1x (bp/day):

| Book | 2021 | 2022 | 2023 |
|---|---|---|---|
| mom7/H | +23.3 | +2.4 | +1.5 |
| rev28/H | +23.8 | -3.5 | +5.1 |
| maxd/H | +11.2 | -2.9 | +9.6 |
| ivol/H | +19.9 | -11.8 | +3.0 |
| skew/H | +13.9 | +3.2 | -0.5 |
| hi52/H | 0.0 (no positions) | -7.4 | +26.5 |
| fslope/H | -10.2 | -2.5 | -1.6 |
| arspread/H | +14.4 | -1.4 | +2.2 |

## Cost sensitivity
Costs are 0.6-1.8 bp/day at 1x on a one-week hold. No verdict changes between 1x and 3x: no book reaches t 2 at any
multiple. fslope/L turns negative at 3x; the other seven positive books stay positive.

## Reading
- **One bet, not eight.** The H books of rev28, maxd, ivol and skew have pairwise discovery correlations of 0.49-0.84
  (maxd with ivol 0.84); mom7 correlates 0.57 with rev28 and 0.22-0.32 with the rest. They all long the coins that
  recently ran and swing most, and short the quiet ones.
  - That bet earned in 2021, the alt-season year (+11 to +24 bp/day), and roughly nothing in 2022-2023.
  - It is the same 2021 tilt seen in R222 and R236.
- **The 28-day "reversal" is momentum.** rev28/H, long the 28-day winners, earned +8.5 bp/day. There is no
  one-month reversal in this universe at a one-week hold.
- **Each feature alone:**
  - **hi52 (52-week-high nearness)** needs a full year of history: 48% coverage and no positions in 2021. It made
    +26.5 bp/day in 2023 and -7.4 in 2022, so it rests on one year.
  - **fslope (funding slope)** is the only feature uncorrelated with the cluster (-0.21 to +0.01). Neither side
    earned.
  - **arspread (Abdi-Ranaldo spread)** is uncorrelated with the others (at most 0.11) and was flat after 2021.
- **What the multiplicity note expected:** about 0.4 false discovery passes under the null. There were none. The
  closest, mom7/H at t 1.77, would also have had to clear validation in 2024-25, where R236 showed the small-coin
  and high-volatility tilt reversing.

## Not checked
- Other holds (24 h, 72 h) and lookbacks (the atlas covered horizons up to 72 h).
- One-sided books.
- Residuals of each feature against the momentum/volatility cluster.
- The holdout.
