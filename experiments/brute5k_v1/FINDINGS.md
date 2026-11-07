# FINDINGS: brute5k_v1 (R263). 5,472 chart strategies: nothing survives costs and selection

**Verdict: NULL (gate 0).**
- **Primary:** the walk-forward "pick what worked in the last 6 months" stream earns +1.18 bp a day at 1x over
  2021-07..2025-06 (NW t 0.96). Its mean at 2x is still positive (+0.29 bp/day), but its t is far below 2.
- **The selection does carry information.** The stream beats 99.9% of random monthly picks from the same 5,472.
  But the strategies it picks from lose on average (-1.02 bp/day equal-weighted), so beating random still nets
  about zero.
- **Secondary:** the best single strategy in discovery fails White's reality check (p 0.334) and earns nothing in
  validation.
- **Registry:** R263, 5,475 trials (5,472 strategies + 3 lookbacks). Program trials become 9,477,556.
- **Reproduce:** prereg sha in `PREREG.sha256` (frozen before any statistic). Then run
  `python scripts/run_brute5k.py`.
  - It takes about 45 min at nice 10.
  - It has a per-timeframe resume checkpoint in `cache/`, added after a container restart killed the first run.
    The killed and stopped logs are kept.
- **Execution mode:** API. The 1 h and 4 h rules trade too often for manual orders. A daily (24 h) subset would fit
  manual-web, but none passes.
- **Universe:** the top-20 perps by daily rank, 242 coins ever members, about 19.2 a row. 29 member cells had a
  missing next return (legacy zero, disclosed in the PREREG).

## Primary: walk-forward selection, K = 20 strategies, monthly
| Lookback | Window | 1x bp/day (t) | 2x bp/day (t) | 3x bp/day (t) | Sharpe 1x |
|---|---|---|---|---|---|
| **6 months (decided)** | **2021-07..2025-06** | **+1.18 (0.96)** | +0.29 (0.23) | -0.61 (-0.49) | 0.42 |
| 3 months | 2021-07..2025-06 | +2.02 (1.51) | +0.92 (0.69) | -0.18 (-0.13) | 0.66 |
| 12 months | 2022-01..2025-06 | +0.31 (0.22) | -0.71 (-0.51) | -1.73 (-1.25) | 0.11 |
| 6 months, exploratory | 2025-07..2026-09 (spent) | +1.01 (0.54) | +0.17 | -0.67 | 0.48 |

- **Gates:**

  | Gate | Rule | Result |
  |---|---|---|
  | 1 | 1x NW t >= 2 | 0.96, fail |
  | 2 | 2x mean > 0 | +0.29 bp/day, pass |
  | 3 | 1x mean above the random-selection null's 95th percentile | pass. Null mean -1.11 bp/day, 95th percentile -0.04, share of nulls above the stream 0.001 |

- **Decay by year (6-month lookback, 1x, bp/day):**

  | 2021 H2 | 2022 | 2023 | 2024 | 2025 H1 | 2025 H2 (spent) | 2026 (spent) |
  |---|---|---|---|---|---|---|
  | +5.76 | +1.55 | +0.65 | +0.42 | -1.60 | -3.39 | +3.97 |

  The edge was in 2021's trend and has been near zero since.

## Secondary: the best single strategy
- **The strategy:** RSI(14) with thresholds 10/90, 1 h bars, long-only, no filter, no stop (id 330).
- **Discovery (2021-07..2023-12):** +0.89 bp/day, NW t 3.11.
- **Reality check over all 5,472:** statistic 3.21, null 95th percentile 4.11, **p 0.334**. Its discovery t is what the
  best of 5,472 shows by luck.
- **Validation (2024-01..2025-06):** +0.01 bp/day (t 0.02); 2x -0.01; 3x -0.03. Fail.

## The landscape (1x, discovery 2021-07..2023-12 vs validation 2024-01..2025-06)
- **Discovery:** 41% of strategies have a positive net mean, against 53% gross, so costs flip about a fifth of them.
- **t >= 2:** 0.6% of strategies in discovery and 1.0% in validation. That is below the 2.3% a one-sided t >= 2
  gives by chance.
- **The top 100 by discovery t** average a validation t of 1.11. That is weak persistence, in line with the IC below.
- **Persistence IC:** trailing 6-month Sharpe vs next month's net, across strategies, has mean 0.044 (NW t 1.30). It is
  positive in 54% of months, and 0.073 in the exploratory window.

## By family and timeframe (mean of the family's strategies, bp/day)
| Family | 1 h disc / val | 4 h disc / val | 12 h disc / val | 24 h disc / val |
|---|---|---|---|---|
| MACD | -8.86 / -10.34 | +1.52 / +0.07 | +3.74 / +1.44 | +5.11 / +1.27 |
| Supertrend | -4.52 / -2.23 | +1.35 / +1.66 | +3.77 / -1.00 | +2.74 / -0.92 |
| EMA cross | +0.89 / +0.16 | +2.00 / +1.12 | +1.86 / -0.88 | +1.15 / -0.76 |
| TS momentum | -8.12 / -8.76 | +1.55 / -0.24 | +1.98 / +0.60 | +0.58 / -1.98 |
| Donchian | -3.00 / -1.74 | +0.71 / -0.77 | +1.05 / -1.63 | +0.22 / -1.58 |
| RSI | -8.37 / -6.70 | -2.66 / -2.28 | -1.60 / -1.39 | -1.82 / -0.19 |
| Bollinger | -3.81 / -3.53 | -1.06 / -1.52 | -0.20 / -0.58 | -0.08 / -0.07 |
| VWAP band | -3.01 / -2.90 | -1.08 / -1.08 | -0.41 / -0.59 | -0.14 / -0.05 |
| Fibonacci | -1.41 / -2.09 | -0.61 / -1.02 | -0.68 / -0.56 | -0.82 / -1.25 |

- **Costs kill the 1 h trend rules.** For example, MACD 1 h is +3.2 bp/day gross against 12.1 bp/day of cost.
- **Slower trend rules** (MACD, Supertrend and EMA on 12 h and 1 d) earn in discovery, mostly from 2021-22 H1. They
  fall to about 0 or below in validation.
- **Mean-reversion families** (RSI, Bollinger fade, VWAP fade) lose at every timeframe.
- **Fibonacci retracements (queue M204)** lose at every timeframe, and in 10 of 12 half-years. Yet the walk-forward
  picked them most (77% of picks in 2021, 56% in 2026). Their low turnover gives a smooth trailing Sharpe on small
  means.

## "Why now and not before" (reported, not decided)
- **Trend families earn in trending half-years and give it back in chop:**

  | Family | 2021 H2 | 2022 H1 | 2022 H2 | 2023 H1 | 2023 H2 | 2026 H1 |
  |---|---|---|---|---|---|---|
  | Supertrend | +2.9 | +7.0 | -5.3 | -4.1 | +3.7 | +9.3 |
  | MACD | +0.0 | +8.5 | -5.0 | -2.5 | +1.0 | +8.4 |

  TS momentum has the same pattern.
- **Regime:** the trend families' monthly means correlate with the size of BTC's monthly move (abs return), not its
  sign:

  | Family | Corr with abs BTC return | Corr with signed BTC return |
  |---|---|---|
  | Donchian | 0.36 | 0.12 |
  | TS momentum | 0.34 | 0.02 |
  | EMA | 0.28 | -0.01 |
  | Supertrend | 0.28 | 0.04 |

  - RSI is the reverse: -0.14 with the size of BTC's move.
  - So "it works now" means "BTC is moving a lot now". That is not predictable from the trailing 6 months
    (IC t 1.30).
- **2026 H1:** the trend families' strongest half-year. It is as strong as 2022 H1, or stronger. That is in the spent
  window, so it is exploratory only.

## Monte Carlo on leverage (reported; daily bootstrap, no intraday liquidation)
| Leverage | Median 1-year wealth | 5th percentile | P(drawdown >= 50%) | P(losing year) |
|---|---|---|---|---|
| 1x | 1.037 | 0.897 | 0.0% | 34% |
| 3x | 1.081 | 0.694 | 1.2% | 39% |
| 5x | 1.083 | 0.505 | 20% | 43% |
| 10x | 0.889 | 0.167 | 81% | 55% |

- These are for the walk-forward stream. Its growth-optimal leverage is 4x, on an edge that is not significant.
- **Leverage does not create an edge.** Above 3x it mostly buys drawdown.
- The best single strategy's MC uses its in-sample discovery stream. It is meaningless after its validation of about
  0, and is reported only because the PREREG required it.

## Reading
- **Against program trials (9,477,556):** nothing here is close to any bar. The secondary's discovery t of 3.11 is the
  expected maximum of 5,472 tries.
- **Answer to the owner's question:**
  - Brute-forcing chart strategies does not produce an edge on the top-20 perps after costs.
  - Picking recent winners beats picking at random, but not by enough to pay.
  - Leverage only scales the noise.
- **Pre-committed (docs/GATES.md):** the best single strategy (id 330) and the 6-month walk-forward stream enter the
  first reserved 2020 batch whatever they scored here.
  - In 2020 the walk-forward has only July-December after its 6-month warm-up.
- **Methods:**
  - M204 (Fibonacci) is now TESTED and NULL.
  - M228 (stops by regime) is PARTIAL: the 2 x ATR stop overlay is in the grammar, but this lane does not split its
    effect by book type.
  - M205 (trendline breaks) is not covered. Donchian breakouts are the nearest rule.
