# FINDINGS: ictlevels_v1 (R246). Round numbers, SMT divergence and the 8 AM New York range on hourly bars

**Verdict: NULL.** None of the 8 books passed discovery (2021-2023). Validation was not computed and the holdout was
not read.
- The round-number books lost heavily (t below -9). Most of the loss is cost: these books turn over all day.
- **SMT_FADE/24 is the only book with real gross** (+11.3 bp/day). Its 9.4 bp/day of cost leaves +2.0 net (t 0.29).
- The 8 AM range books lost both ways.

- **Registry row:** R246 (trials 8). Program trials after it: 9,471,965.
- **Gate:** 0.
- **Reproduce:** prereg sha 55e6f756, frozen in commit 446b744 before the run. Run `python scripts/run_ictlevels.py`
  (about 1.5 minutes).
- **Origin:** queue M010, M011, M012.

## Numbers (discovery 2021-01..2023-12; directional; alpha and beta against the equal-weight market)

| Book | Net bp/day 1x / 2x / 3x | NW t (1x) | Gross / cost (1x) | Gross exposure | Alpha bp/day (t) | Triggers |
|---|---|---|---|---|---|---|
| RN_CROSS (follow) | -84.8 / -151.8 / -218.9 | -9.93 | -17.7 / 67.1 | 0.90 | -83.4 (-10.31) | 382,066 |
| RN_REJECT (fade) | -40.2 / -71.0 / -101.7 | -9.66 | -9.5 / 30.7 | 0.91 | -41.1 (-9.84) | 286,895 |
| SMT_FADE/24 | **+2.0** / -7.4 / -16.8 | 0.29 | **+11.3** / 9.4 | 0.79 | +2.2 (0.33) | 125,088 |
| SMT_FOLLOW/24 | -20.7 / -30.0 / -39.4 | -3.07 | -11.3 / 9.4 | 0.79 | -20.9 (-3.13) | 125,088 |
| SMT_FADE/168 | -4.5 / -7.4 / -10.2 | -0.86 | -1.6 / 2.9 | 0.28 | -5.1 (-0.97) | 41,045 |
| SMT_FOLLOW/168 | -1.2 / -4.1 / -7.0 | -0.24 | +1.6 / 2.9 | 0.28 | -0.6 (-0.12) | 41,045 |
| AM8_FADE | -7.0 / -16.4 / -25.8 | -1.56 | +2.5 / 9.4 | 0.14 | -7.2 (-1.60) | 35,685 trades |
| AM8_FOLLOW | -11.9 / -21.3 / -30.8 | -2.66 | -2.5 / 9.4 | 0.14 | -11.7 (-2.62) | 35,685 trades |

Triggers are coin-hours with a trigger on an eligible coin; for AM8, they are trades. Betas are all within 0.1 of
zero.

Per year at 1x (bp/day):

| Book | 2021 | 2022 | 2023 |
|---|---|---|---|
| RN_CROSS | -123.8 | -63.0 | -67.5 |
| RN_REJECT | -54.6 | -35.2 | -30.9 |
| SMT_FADE/24 | -1.4 | +15.0 | -7.7 |
| SMT_FOLLOW/24 | -16.1 | -34.1 | -11.9 |
| AM8_FADE | +6.5 | -21.1 | -6.3 |
| AM8_FOLLOW | -25.4 | +2.5 | -12.7 |

## Cost sensitivity
- **The round-number grid (two significant figures, 1-10% apart) is crossed or touched about 7 times per coin per
  day.** Each trigger restarts a 24 h position, so the books cost 31-67 bp/day at 1x.
- SMT/24 and AM8 cost about 9.4 bp/day; SMT/168 costs 2.9.
- No book is positive at 2x.

## Reading
- **Round numbers: crossings reverse, they do not run.**
  - RN_CROSS's gross is -17.7 bp/day, so after a close through a level, price comes back.
  - RN_REJECT's gross is -9.5, so after a wick through a level that closes back, price goes on through it later.
  - Both fit short-horizon reversal of the trigger bar's own move.
- **Part of it is specific to round numbers.** This check was post hoc and descriptive; it was not pre-registered and
  no decision rests on it.
  - The same crossing book on a grid shifted by half a step (levels at 61,500, 62,500 ...) grosses -6.9 bp/day.
  - Round levels minus shifted levels: **-10.8 bp/day, NW t -3.30**, negative every year (2021 -17.5, 2022 -7.5,
    2023 -7.3).
  - So a close through a round number fails more often than a close through an arbitrary level. That fits the ICT
    "liquidity sweep" story, and Osler's take-profit clustering more than her stop-loss cascade.
  - It is a gross effect inside a book that loses 85 bp/day net. A tradeable version needs far fewer trades. It is
    queued as M230 (below), with the shifted grid as its pre-registered control.
- **SMT divergence:**
  - At 24 h, fading the divergence earns +11.3 bp/day gross. That is the reversal side, as ICT reads it, but cost
    takes almost all of it, and 2022 carries the sum.
  - At 168 h (weekly extremes) nothing is there.
- **8 AM New York range:**
  - Fading the first break of the 08:00 bar's range grosses +2.5 bp/day; following it grosses -2.5.
  - Both lose net, as R152 found on 1-minute data.

## New queue row
- **M230: round-number sweep fade with low turnover.** The one-significant-figure grid (BTC 60k, 70k ...) and the
  two-figure grid. Fade a close through a level, at most one trade per coin per level per day, and hold 4-24 h.
  - The control is the half-step-shifted grid, pre-registered, and the test is the difference.
  - Maker entry at the level is a variant.
  - Post-hoc origin: R246's descriptive check above.

## Not checked
- Maker execution (R193 found simple maker fills adverse-selected).
- Shorter holds (1-4 h); one-significant-figure levels only; a fade of SMT on 4 h bars.
- SMT against ETH instead of BTC; pairs within sectors.
- Opening ranges at other session opens (M206 covers 00/08/13:30 UTC).
- Validation and the holdout.
