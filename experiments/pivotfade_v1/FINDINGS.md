# FINDINGS: pivotfade_v1 (R248). Fade a close beyond the prior day's floor pivot R1/S1

**Verdict: NULL.** The mirror of PIVOT_BREAK, chosen after it lost in every discovery window, failed on all four of
its first unseen windows. The holdout was not read, because nothing passed validation.
- **Indices 2013-19:** alpha -0.57 bp/day, t -0.62.
- **Forex 2013-19:** alpha +0.46, t 0.98, and negative at 2x.
- **Crypto 2024-01..2025-06:** 4 h net -9.9 bp/day (t -1.36); 1 d -8.3 (t -1.00).
- The pivot family is closed at 8 trials: R243's 2 pivot books, R247's 2 and this lane's 4.

- **Registry row:** R248 (trials 4). Program trials after it: 9,471,983.
- **Gate:** 1 for forex and indices (failed at validation); 0 for crypto.
- **Reproduce:** prereg sha 7d51d6aa, frozen in commit 844cb11 before the run. Run `python scripts/run_pivotfade.py`
  (about 3 minutes).
- **Origin:** queue M231 (from R247), M203.

## Numbers

**Forex and indices, validation 2013-2019** (alpha against the group's equal-weight buy-and-hold):

| Book | Net bp/day 1x / 2x / 3x | Gross / cost (1x) | Turnover /yr | Alpha bp/day (t) | Alpha 2x / 3x |
|---|---|---|---|---|---|
| PIVOT_FADE/FX | +0.46 / -0.24 / -0.95 | +1.16 / 0.70 | 177 | +0.46 (0.98) | -0.24 / -0.94 |
| PIVOT_FADE/IDX | -0.30 / -1.05 / -1.79 | +0.44 / 0.74 | 188 | -0.57 (-0.62) | -1.32 / -2.06 |
| *Control* REV1D/FX | +0.80 / -0.24 / -1.27 | +1.83 / 1.04 | 261 | +0.80 (1.25) | — |
| *Control* REV1D/IDX | -0.92 / -1.89 / -2.86 | +0.05 / 0.97 | 245 | -1.13 (-0.98) | — |

Alpha per year at 1x (bp/day):

| Book | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 |
|---|---|---|---|---|---|---|---|
| PIVOT_FADE/IDX | +1.1 | -0.8 | -2.6 | +0.9 | +0.0 | -0.9 | -1.7 |
| PIVOT_FADE/FX | +2.5 | +1.0 | -0.7 | -0.3 | +1.5 | +0.2 | -1.0 |

**Crypto, validation 2024-01..2025-06** (directional; alpha against the equal-weight market):

| Book | Net bp/day 1x / 2x / 3x | NW t (1x) | Gross / cost (1x) | Gross exposure | Alpha (t) |
|---|---|---|---|---|---|
| PIVOT_FADE/CRYPTO-4h | -9.9 / -18.8 / -27.6 | -1.36 | -1.0 / 8.9 | 0.25 | -9.4 (-1.27) |
| PIVOT_FADE/CRYPTO-1d | -8.3 / -12.8 / -17.4 | -1.00 | -3.7 / 4.6 | 0.39 | -7.2 (-0.86) |
| *Control* REV1D/CRYPTO-4h | -33.3 / -78.2 / -123.1 | -2.48 | +11.5 / 44.9 | 0.99 | -32.6 (-2.49) |
| *Control* REV1D/CRYPTO-1d | -1.1 / -8.6 / -16.2 | -0.09 | +6.4 / 7.5 | 1.00 | +1.1 (0.09) |

**Pivot fade minus one-bar reversal** (control; 1x daily alpha or net):
- FX: -0.34 bp/day, t -0.92.
- Indices: +0.55, t 0.98.
- Crypto 4 h: +23.5, t 1.85. This is mostly the control's 45 bp/day of cost.
- Crypto 1 d: -7.2, t -1.23.

## Cost sensitivity
- **Forex and indices:** 1 bp one-way at 1x and about 180 round trips a year cost 0.7 bp/day. That is more than the
  index fade's gross, and 60% of the forex gross. No book is positive at 2x.
- **Crypto:** gross is already negative, so cost does not decide.

## Reading
- **The discovery pattern did not carry forward.**
  - In 2001-12, index closes beyond R1/S1 reversed: the break lost 3.81 bp/day of alpha, t -4.16. Much of it came in
    2008 (-17.0 that year).
  - In 2013-19 the fade earned +0.44 gross and lost after cost. Plain one-day index reversal also went to zero
    (REV1D/IDX gross +0.05).
  - This matches the literature's finding that daily index reversal faded after the 2000s.
- **Forex is the closest:** +1.16 bp/day gross, t 0.98 at 1x. But it is no better than plain one-day reversal
  (difference -0.34), and the cost of trading it daily takes most of it.
- **In crypto the sign flipped between eras.**
  - Breaks lost in 2021-23 (R243).
  - The fade lost before costs in 2024-25, gross -1.0 (4 h) and -3.7 (1 d).
  - Taking a lost book's mirror bought nothing here: the 2021-23 losses did not predict 2024-25.
- **Lesson for the lab:** a post-hoc mirror of a strongly losing book is worth one cheap lane on unseen windows (this
  one cost 4 trials), but its prior should be low. Here it failed in all three markets.

## Not checked
- The 2020-26 holdout (forex and indices). It was not read, because nothing passed validation.
- R2/S2 levels, ATR bands beyond R1/S1, intraday fades at the level itself (needs intraday forex and index bars:
  Dukascopy phase 2, the owner's yes).
- Maker execution in crypto.
