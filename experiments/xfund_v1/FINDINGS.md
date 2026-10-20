# FINDINGS: xfund_v1 (R275). Cross-venue funding carry passes at gate 0: about 9-10%/yr on capital, every year positive

**Verdict: PARTIAL (gate 0). 212 of 560 books clear every gate.** This is the first family in the program to pass
with t far above its reality-check null. Gate 0 cannot confirm it. Confirmation comes from the venue replication
(R277, venues this family never read), forward paper days and the first reserved batch.

- **Window:** 2021-01..2026-09. Each set starts when its venues' funding histories allow: Hyperliquid 2023-05,
  MEXC 2025-05.
- **Costs:** 7 / 14 / 21 bp per leg per side.
- **Registry:** R275, 560 trials. Program trials become 9,478,301.
- **Reproduce:**
  - prereg sha fca2c619, frozen in commit b44b526 before any spread or return was read;
  - `python scripts/qx_run.py experiments/xfund_v1` at that commit;
  - the symbol table rebuilds byte for byte, and the family takes about 40 s on qx.
- **Universe:** 867 coins on at least 2 venues: Binance 867, Gate 860, Hyperliquid 216, MEXC 520.

## The rule (from the PREREG)
- **Signal:** each day at 00:00 UTC, for each coin and venue pair, take the funding each venue settled over the last
  L days. The spread is the difference between the two, annualized.
- **Entries:** coins whose spread is at least th, widest first, into K free slots.
- **Position:** long the coin on the venue that paid less, short it on the venue that paid more, 1x on each leg.
- **Exits:** when the spread falls below th / 2.
- **Identity guard:** a pair is used only when the two venues' daily returns correlated at least 0.9 over the last
  30 days.
- **Returns** are on total capital, both venues' collateral included.

## Best book per venue set (by 1x t)
| Book | Days | 1x %/yr | 2x | 3x | Sharpe | t | NW t | RC p | Halves bp/day | 2025+ bp/day | Max DD | Top-10-day share | Pairs held | Pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gate+hyperliquid L14d th5% K20 | 1225 | +9.73 | +8.51 | +7.28 | 6.93 | 12.70 | 8.63 | 0.0005 | +3.57 / +1.77 | +1.77 | -2.1% | 11% | 19.9 | yes |
| binance+hyperliquid L14d th10% K20 | 1225 | +8.63 | +7.02 | +5.40 | 6.92 | 12.67 | 8.95 | 0.0005 | +2.99 / +1.74 | +1.73 | -1.1% | 14% | 19.9 | yes |
| binance+mexc L14d th10% K20 | 507 | +6.33 | +4.96 | +3.60 | 6.99 | 8.24 | 4.80 | 0.0005 | +2.25 / +1.22 | +1.73 | -0.4% | 26% | 13.2 | yes |
| all four L14d th10% K20 | 2078 | +13.21 | +11.68 | +10.16 | 3.07 | 7.33 | 7.68 | 0.0015 | +2.66 / +4.58 | +5.43 | -4.7% | 26% | 19.0 | yes |
| gate+mexc L7d th10% K20 | 514 | +16.29 | +12.99 | +9.69 | 5.98 | 7.10 | 7.38 | 0.0015 | +3.71 / +5.22 | +4.46 | -0.9% | 28% | 20.0 | yes |
| binance+gate L14d th10% K20 | 2078 | +10.05 | +8.33 | +6.60 | 2.40 | 5.73 | 5.96 | 0.0055 | +1.98 / +3.53 | +4.80 | -5.1% | 31% | 18.6 | yes |
| hyperliquid+mexc L3d th5% K20 | 518 | +7.98 | +3.02 | -1.94 | 4.20 | 5.00 | 4.02 | 0.018 | +1.90 / +2.48 | +2.19 | -1.1% | 36% | 20.0 | yes |

- **Pass count by set:**

  | Set | Passing books |
  |---|---|
  | binance+hyperliquid | 57 |
  | gate+hyperliquid | 53 |
  | binance+mexc | 43 |
  | gate+mexc | 27 |
  | all four | 19 |
  | hyperliquid+mexc | 8 |
  | binance+gate | 5 |

  All 212 passing books are listed in `results/strategies.csv`. The reality-check null's 95th percentile is t 4.27.
- **Neighbors pass too.** The passing books form broad regions, not isolated cells. Gate+Hyperliquid passes at every
  lookback from 1 to 14 days, at thresholds from 5% to 80%, and at K from 3 to 20.

## By year (1x / 2x / 3x, %/yr on capital)
| Book | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (to Sep) |
|---|---|---|---|---|---|---|
| gate+hyperliquid L14d th5% K20 | | | +18.6 / +17.8 / +17.1 (from May) | +10.1 / +9.1 / +8.0 | +5.0 / +3.6 / +2.2 | +8.4 / +6.8 / +5.3 |
| binance+hyperliquid L14d th10% K20 | | | +16.5 / +15.7 / +14.9 | +7.9 / +6.3 / +4.7 | +5.2 / +3.3 / +1.4 | +7.9 / +6.0 / +4.2 |
| binance+mexc L14d th10% K20 | | | | | +8.2 / +6.4 / +4.7 (from May) | +4.7 / +3.7 / +2.7 |
| gate+mexc L7d th10% K20 | | | | | +13.1 / +9.9 / +6.7 (from May) | +19.1 / +15.7 / +12.3 |
| binance+gate L14d th10% K20 | +11.6 / +9.8 / +7.9 | +8.3 / +7.0 / +5.7 | +2.3 / +0.5 / -1.4 | +5.1 / +3.3 / +1.6 | +24.3 / +22.6 / +20.9 | +8.4 / +6.5 / +4.5 |

- **Every year is positive at 1x and 2x for every book in the table.** Only binance+gate 2023 turns negative, and
  only at 3x.
- **The Hyperliquid books decay.** They made 17-19%/yr in 2023, the year Hyperliquid's funding was new and
  thinly arbitraged. In 2025-26 they make 5-8%/yr.

## Audit (done after the run, before writing this)
- **Funding recomputed from the raw files.** I took 4 Gate+Hyperliquid trades: GMX, BNB, MAV and YGG, 2023-2026.
  - Each trade's funding PnL, summed from the venues' raw parquet files, equals the engine's to the 5th decimal.
  - Their price PnL is within 0.1% of a buy-and-hold of the two legs.
- **Units:** Hyperliquid's hourly rate has its median at 1.25e-5 every year from 2023 to 2025, which is its
  0.01%-per-8h baseline. So hourly and 8-hourly venues add up in the same units.
  - BTC funding averaged 11.9%/yr on Binance, 8.8% on Gate and 24.1% on Hyperliquid in 2024.
  - The gap is real (Hyperliquid's funding ran above the CEXs' through 2024), not a units error.
- **Concentration:** Gate+Hyperliquid L14 th5% K20 traded 181 coins in 587 trades. The top 5 coins make 18% of
  the gross and the top 10 make 29%. The same holds in the other sets: top 10 coins 29-47%.
- **Price legs:** the price legs net to about zero, and funding is 96-105% of the gross. The book earns the funding
  difference, as designed.
- **Forced exits** (one venue stops trading the coin):
  - About 5% of the passing books' gross (median), with a range of -7% to 42%.
  - Removing every forced trade leaves all 212 passing books positive. The best book goes from 9.73 to 9.27%/yr.
  - **An accounting flaw, found in this audit:** when one venue stops trading a coin, its close is carried forward
    for a day while the other leg still moves. That unhedged day made the largest losses in the family:
    - NEIROETH, Hyperliquid delisted on 2025-09-26, -83% on one leg;
    - A2Z and YALA on Gate in 2026, -140% and -114%.
  - **How to fix it:** a live trader closes both legs when a venue announces a delisting. The fix (exit both legs
    at the last common fresh close) goes into the next spread lane's engine version. This lane's frozen engine is
    not changed.
- **Survivorship is smaller than the PREREG feared.** The PREREG said Hyperliquid's history holds only live
  coins. It holds 234 coins, and 56 of them ended before 2026-10-01 (STRAX, FRIEND, RNDR, MATIC and others).
  MEXC's history is still live contracts only.
- **Capacity:** the Gate+Hyperliquid L14 set has 74 coins a day above 5%/yr and 22 above 20%/yr. Gate+MEXC has
  219 and 73. K = 20 at the owner's size ($10k means $250 per leg) is far below any book's depth. It was not
  checked against order books.

## Reading
- **Against program trials (9,478,301):**
  - The best t (12.70 plain, 8.63 Newey-West) is far beyond any family-wise null in the program.
  - The reality-check null for these 560 books is 4.27, and a Bonferroni bar over 9.5M trials is about 5.9.
  - The result is not a selection artifact. It is a known, structural carry: venues with different trader
    populations pay different funding on the same coin.
  - What is not known is whether it survives the frictions the backtest omits.
- **What the backtest does not model** (from the PREREG):
  - liquidation of one leg at leverage above 1x;
  - moving collateral between venues;
  - intraday rebalancing;
  - the actual fill price at 00:00 UTC on two venues at once.
  - Returns are on 1x legs. At 2-3x per leg the return on capital scales up, and so does liquidation risk on a
    one-sided squeeze.
- **For the owner:**
  - Gate+Hyperliquid needs a Gate account and a Hyperliquid wallet (USDC on Arbitrum).
  - The MEXC books need MEXC plus Binance or Gate.
  - The MEXC sets have only 17 months of history, mostly inside the RECENT gate.

## Pre-committed actions (from the PREREG, now executed)
1. **Forward paper:**
   - The best passing book by 1x t, **gate+hyperliquid L14d th5% K20**, gets a frozen forward paper lane with a
     new id.
   - The best passing book with a MEXC leg, **binance+mexc L14d th10% K20** (t 8.24), goes forward in the same lane.
2. **Reserved batch:** the best passing binance+gate book, **binance+gate L14d th10% K20**, joins the first reserved
   batch (Binance and Gate 2020 rows).
3. **Venue replication (R277):** L14, th 5%, K20, unchanged, on binance+kucoin, binance+dydx, gate+kucoin and
   kucoin+dydx. A set replicates at NW t > 2.50 with HALVES and a positive 2x mean. It runs once the KuCoin and dYdX
   downloads finish.

## Post hoc (not decided by this lane)
- **gate+mexc L7d th10% K20** has the highest annual net of any MEXC book: +16.3 / +13.0 / +9.7 %/yr at
  1x / 2x / 3x, t 7.10.
  - It was not the pre-committed MEXC pick (that rule chose by t).
  - The forward lane may carry it only as a book labelled post hoc, with the multiplicity counted there.
- **Method M059 is TESTED: PARTIAL.** The next spread lane should:
  - use the delisting fix above;
  - add the leg-liquidation check at 2x and 3x;
  - add venues as they arrive (KuCoin, dYdX, Kraken).
