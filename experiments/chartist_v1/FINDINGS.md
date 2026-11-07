# FINDINGS: chartist_v1 (R243). Seven classic chart rules on 4 h and 1 d bars

**Verdict: NULL.** None of the 14 rules reached t 2 in discovery (2021-2023). Validation was not computed and the
holdout was not read.
- The trend rules on daily bars were positive but weak. Supertrend+RSI was the best at +11.3 bp/day, t 1.23.
- The fades (Stochastic, CCI, Bollinger) and pivot breakouts lost.

- **Registry row:** R243 (trials 14). Program trials after it: 9,471,951.
- **Gate:** 0.
- **Reproduce:** prereg sha 9a06f2c0, frozen in commit 6986397 before the run. Run `python scripts/run_chartist.py`
  (about 3 minutes).
- **Origin:** queue M005, M200, M202, M203. The owner's ask: chartist methods tested even if they look bad.

## Numbers (discovery 2021-01..2023-12; 1x / 2x; alpha and beta against the equal-weight market)

| Rule | Bars | Net bp/day 1x / 2x | NW t (1x) | Gross / cost (1x) | Beta | Alpha bp/day (t) | Long / short share |
|---|---|---|---|---|---|---|---|
| SUPERTREND_RSI | 4h | -0.5 / -6.4 | -0.05 | 5.5 / 5.9 | -0.28 | +3.3 (0.38) | 36% / 42% |
| MACD | 4h | -4.8 / -11.8 | -0.59 | 2.2 / 7.0 | -0.15 | -2.7 (-0.33) | 51% / 49% |
| STOCH (fade) | 4h | -7.6 / -13.5 | -1.75 | -1.8 / 5.8 | +0.08 | -8.8 (**-2.07**) | 16% / 14% |
| CCI (fade) | 4h | -8.7 / -16.6 | -1.55 | -0.7 / 7.9 | +0.17 | -11.0 (-1.90) | 21% / 19% |
| BOLL (fade) | 4h | -5.5 / -10.7 | -1.53 | -0.3 / 5.2 | +0.07 | -6.5 (-1.79) | 6% / 6% |
| ICHIMOKU | 4h | +6.1 / +1.8 | 0.79 | 10.3 / 4.2 | -0.29 | +10.1 (1.26) | 28% / 35% |
| PIVOT_BREAK | 4h | -10.3 / -19.0 | -1.91 | -1.7 / 8.7 | -0.09 | -9.1 (-1.69) | 12% / 13% |
| SUPERTREND_RSI | 1d | **+11.3** / +10.3 | **1.23** | 12.4 / 1.0 | -0.15 | +13.4 (1.39) | 37% / 39% |
| MACD | 1d | +6.6 / +5.4 | 0.74 | 7.8 / 1.2 | -0.16 | +8.8 (0.92) | 47% / 47% |
| STOCH (fade) | 1d | -3.9 / -4.9 | -0.73 | -2.9 / 1.0 | +0.15 | -5.9 (-1.08) | 18% / 12% |
| CCI (fade) | 1d | -9.2 / -10.5 | -1.50 | -7.9 / 1.3 | +0.16 | -11.4 (-1.71) | 19% / 18% |
| BOLL (fade) | 1d | -1.9 / -2.8 | -0.54 | -1.1 / 0.9 | +0.06 | -2.7 (-0.70) | 5% / 7% |
| ICHIMOKU | 1d | -0.5 / -1.2 | -0.07 | 0.2 / 0.7 | -0.11 | +1.1 (0.17) | 25% / 31% |
| PIVOT_BREAK | 1d | -14.5 / -19.0 | -1.99 | -10.0 / 4.5 | -0.11 | -12.9 (-1.72) | 19% / 20% |

Long and short shares are of eligible coin-bars over 2021-2025H1.

Per year at 1x (bp/day):

| Rule | 2021 | 2022 | 2023 |
|---|---|---|---|
| SUPERTREND_RSI/1d | +21.7 | +2.4 | +10.0 |
| MACD/1d | +7.5 | +0.8 | +11.5 |
| ICHIMOKU/4h | -0.2 | +13.0 | +5.4 |
| SUPERTREND_RSI/4h | -12.9 | +7.2 | +4.3 |
| MACD/4h | -25.3 | +9.9 | +1.0 |
| PIVOT_BREAK/4h | -31.0 | +6.4 | -6.4 |
| PIVOT_BREAK/1d | -22.3 | -11.2 | -10.0 |
| CCI/1d | -9.3 | -4.7 | -13.7 |

## Cost sensitivity
- **On 4 h bars, cost decides.** Supertrend, MACD and pivot breaks pay 5.9-8.7 bp/day, more than their gross. Every
  4 h rule is negative at 2x except Ichimoku (+1.8).
- **On daily bars, cost is 0.7-4.5 bp/day.** The two positive trend rules stay positive at 2x and 3x, but neither
  reaches t 2 at 1x.

## Reading
- **Classic chart rules do not beat t 2 on the top-50 perps in 2021-23.**
  - The trend family is right in sign at daily speed: Supertrend+RSI, MACD and R242's 30-day trend all made +6 to +11
    bp/day.
  - It is too weak and too 2021-dependent to pass. This matches the old session's R178, where Supertrend+RSI on 4 h
    looked good in its discovery and lost in its holdout.
- **Overbought/oversold fades lose.** Stochastic, CCI and Bollinger fades had negative alpha in both bar sizes:
  - Stochastic on 4 h had t -2.07 on alpha;
  - CCI was -1.7 to -1.9.

  Coins that are stretched over 1-20 bars keep going. That is the short-term momentum the trend rules earn, seen from
  the other side.
- **Pivot breakouts lose too** (-10 to -14 bp/day, t -1.9 to -2.0): a break of R1 or S1 tends to reverse.
- **No mirror is a result.** Fading pivot breaks, or following overbought coins, was not a pre-registered rule. A
  mirror chosen after seeing its sign would be a new lane, and its trials would add to the count. On daily pivots the
  mirror would gross about +10 bp/day before about 4.5 bp/day of cost.

## Not checked
- Parameter sweeps (M200's n 7-48, thresholds, M202's sweep). One standard setting per rule was tested.
- 1 h bars.
- Bollinger and Keltner squeeze breakouts.
- Pivot bounces.
- Exits other than the next state change (stops, targets, time exits).
- Spot (long-only) versions.
