# FINDINGS: xsalt_v1 (R222), slow altcoin cross-sections: none pays

PREREG sha 6b78b640. Run 2026-10-19 by `scripts/run_xsalt.py`. Results are in `results/`:
- `results.csv`: every variant at 1x/2x/3x;
- `spreads.csv`: next-24 h quintile spreads;
- `verdict.json`: stages, beta persistence, RESMOM - MOM.

## Verdict: NULL. All six variants failed discovery; validation and holdout books were not run
The holdout stays unread for this family.

Discovery is 2021-01..2023-12: 1,095 days, crypto contracts only, top-50 eligible, quintiles of about 8-10 coins. Units
are bp/day. Alpha t is the NW t of the net after removing its BTC beta (the decision statistic).

| Variant | Net 1x | Alpha t | Beta to BTC | Gross | Cost | Long leg / short leg gross | Net 2x / 3x | Max DD |
|---|---|---|---|---|---|---|---|---|
| BETA (long low beta, 7 d) | +2.5 | +0.48 | -0.22 | +3.4 | 1.0 | +10.6 / -7.3 | +1.5 / +0.5 | 79% |
| RESMOM (30 d) | -3.3 | -0.58 | +0.03 | -2.4 | 0.9 | +0.1 / -2.3 | -4.2 / -5.1 | 78% |
| MOM, the control (30 d) | **+7.7** | **+1.23** | -0.01 | +8.3 | 0.6 | +4.5 / +4.3 | +7.2 / +6.6 | 64% |
| MAX_POS (long high MAX, 7 d) | +3.0 | +0.27 | +0.13 | +5.7 | 2.7 | +18.2 / -11.9 | +0.2 / -2.5 | 52% |
| MAX_NEG (long low MAX, 7 d) | -8.4 | -0.95 | -0.13 | -5.7 | 2.7 | +11.9 / -18.2 | -11.2 / -13.9 | 127% |
| PREM (long high premium net of funding, 7 d) | -5.5 | -0.91 | +0.06 | -2.6 | 2.9 | +14.5 / -16.0 | -8.3 / -11.2 | 113% |

## Reading
- **Slow books cost little (0.6-2.9 bp/day), but the cross-sections earn almost nothing gross.** The best,
  plain 30-day momentum, makes +8 bp/day gross at t 1.2 over three years. These are equity-style factors and they do
  not carry over to the top-50 crypto perps.
- **Low beta:** long low-beta coins and short high-beta coins is gross positive (+3.4 bp/day), with t 0.5 after the
  BTC correction. Beta persists moderately: the rank correlation of beta 90 days apart is 0.38 in 2021-23 and 0.52 in
  2024-25H1. This is Sila et al.'s finding that past beta predicts future beta only partly.
- **Residual momentum lost to plain momentum:** RESMOM - MOM = -11.0 bp/day, t -1.61, in discovery. The brief's
  premise (residual beats plain) fails here.
- **MAX:** the high-MAX coins earned slightly more than the low-MAX coins. That is the sign Ozdamar et al. report for
  crypto, not the equity lottery effect, but t 0.27.
- **PREM:** long high premium-net-of-funding lost.

## Next-24 h quintile spreads, top minus bottom (reported, not decided)

| Score | 2021-23 | 2024-25H1 |
|---|---|---|
| BETA | +1.7 | +10.7 |
| RESMOM | -16.1 | -19.9 |
| MOM | +6.1 | -35.9 |
| MAX | -0.6 | -16.0 |
| PREM | -6.5 | -47.4 |

- A negative spread means the top quintile did worse the next day.
- Two scores have the same sign in both windows: **RESMOM's residual reverses at 24 h**, and **high premium net of
  funding underperforms over the next 24 h** (-6.5 / -47.4).
- These spreads are not tests: daily quintile spreads of about 8 coins have a standard error of roughly 8-10 bp/day
  before autocorrelation.
- A 24 h contrarian lane on either score would be chosen after seeing these numbers. Its only clean test is the
  unread holdout, and it needs its own registration.

## Costs
Net at 2x/3x is in the table. Costs are not what failed these books; the gross is.

## Multiplicity
Trials 6. Program trials after this lane: 9,471,745.
