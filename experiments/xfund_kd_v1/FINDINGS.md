# FINDINGS: xfund_kd_v1 (R277). R275's carry replicates on KuCoin, which R275 never read; the dYdX sets do not

**Verdict: PARTIAL (venue replication, gate 0): 2 of 4 sets replicate.** Under the frozen rule, CONFIRMED needed 3
of 4.

- **Registry:** R277, 4 trials. Program trials become 9,478,326.
- **Reproduce:**
  - prereg sha d399c923, frozen in commit 0ab0a98 before any KuCoin or dYdX return or rate was read;
  - `python scripts/qx_run.py experiments/xfund_kd_v1` (11 inputs match; the symbol table rebuilds byte for byte;
    the run takes 2 s).
- **The book:** R275's best, unchanged: L14d, th 5%/yr, K20, R275's engine, costs 7 / 14 / 21 bp per leg per side.

## The four sets
| Set | From | Days | 1x %/yr | 2x | 3x | t | NW t | Halves bp/day | 2025+ bp/day | Max DD | Top-10-day share | Funding share | Trades | Replicates |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gate+kucoin | 2021-01-22 | 2078 | +11.76 | +10.34 | +8.92 | 14.51 | 11.41 | +1.64 / +4.80 | +5.93 | -0.7% | 12% | 1.02 | 1153 | **yes** |
| binance+kucoin | 2021-01-22 | 2078 | +10.80 | +9.36 | +7.92 | 12.56 | 11.17 | +1.40 / +4.52 | +5.68 | -2.3% | 13% | 1.04 | 1168 | **yes** |
| kucoin+dydx | 2023-12-06 | 1030 | +6.78 | +5.61 | +4.44 | 1.16 | 2.13 | +1.67 / +2.05 | +1.87 | -6.9% | 97% | 0.64 | 471 | no (NW t) |
| binance+dydx | 2023-12-06 | 1030 | +8.34 | +7.44 | +6.53 | 0.83 | 1.44 | +1.32 / +3.24 | +2.75 | -11.2% | 127% | 0.41 | 364 | no (NW t) |

- **Rule:** a set replicates when NW t > 2.50 (Bonferroni over 4), both halves > 0 and the 2x mean > 0.
- **The engine's own family gates** (reality check over the 4 books, null 95th percentile t 2.11, plus RECENT, TRIM
  and HURDLE) pass the same two KuCoin sets. They are reported, not decided on.

## By year (1x / 2x / 3x, %/yr on capital)
| Set | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (to Sep) |
|---|---|---|---|---|---|---|
| gate+kucoin | +10.0 / +8.3 / +6.6 | +5.5 / +4.1 / +2.7 | +4.7 / +3.0 / +1.3 | +9.5 / +8.4 / +7.3 | +20.0 / +18.8 / +17.6 | +23.7 / +22.2 / +20.8 |
| binance+kucoin | +9.5 / +7.9 / +6.4 | +2.4 / +0.7 / -1.1 | +5.3 / +3.5 / +1.8 | +8.5 / +7.5 / +6.4 | +20.0 / +18.9 / +17.8 | +21.8 / +20.4 / +18.9 |
| kucoin+dydx | | | +9.2 / +7.4 / +5.7 (25 d) | +6.4 / +4.9 / +3.5 | +11.8 / +10.5 / +9.2 | +0.4 / -0.1 / -0.7 |
| binance+dydx | | | +2.9 / +1.2 / -0.6 (25 d) | +5.5 / +4.7 / +3.8 | +17.4 / +16.2 / +15.0 | +0.4 / -0.0 / -0.5 |

- **The KuCoin sets are positive every year at 1x and 2x.** Only binance+kucoin 2022 turns negative, and only at 3x.
- **The KuCoin carry grows in 2025-26 (+20-24%/yr).** The Hyperliquid books of R275 decayed to 5-8%/yr over the
  same years.

## Audit (done after the run, before writing this)
- **Units:** per settlement, BTC's median in 2024 was:
  - Binance, Gate and KuCoin: about 1e-4 every 8 h;
  - dYdX: 1.7e-5 every hour.

  Annualized BTC funding in 2024: Binance 12.0%, Gate 8.8%, KuCoin 17.5%, dYdX 22.3%. ETH is similar. Rates add up
  in the same units.
- **Funding recomputed from the raw files** for 12 random trades (3 per set). Each equals the engine's to 5e-9.
- **The KuCoin sets are not concentrated:**
  - gate+kucoin traded 316 coins in 1,153 trades; the top 5 coins make 11% of the gross and the top 10 make 19%;
  - binance+kucoin: 297 coins, 12% and 19%.
- **Funding is 102-104% of the gross,** and the price legs net to about zero.
- **KuCoin is the long leg in 44-51% of trades,** so the result does not rest on one venue always paying more.
- **The dYdX sets fail because of one event, the crash of 2025-10-10:**
  - dYdX's hourly closes at 00:00 on 2025-10-11 printed crash prices far from Binance's and KuCoin's. The next day
    they recovered.
  - The engine books each day's price return on a constant notional. A -60% then +150% round trip on one leg
    therefore adds up to about +90%, as if the book had topped up the leg at the bottom.
  - binance+dydx booked -10.9% of capital on 2025-10-11 and +26.1% on 2025-10-12; kucoin+dydx booked -6.9% and
    +14.7%.
  - The trades with the largest price PnL (TON +117%, ORDI +112%, WLD -116% of one leg) all span those days.
  - **Without the two days (post hoc, not a decision):**

    | Set | %/yr | NW t |
    |---|---|---|
    | kucoin+dydx | +4.0 | 5.67 |
    | binance+dydx | +3.0 | 4.88 |

    This is a smaller carry than KuCoin's.
  - R275's books and the KuCoin sets moved less than 0.6% of capital on each of those days.
- **Forced exits:** 0-2 per set. The stale-leg flaw R275 documented does not drive any of these results.

## Reading
- **Against program trials (9,478,326):**
  - This lane is a confirmation of R275, with 4 trials and a Bonferroni bar, not a search.
  - Two sets built on a venue nobody had read clear it with NW t above 11.
- **Cross-venue funding carry is a property of venues whose traders differ, not of the four venues R275 read.**
  - It is not a T-bill-like yield: it varies by year, from +2.4% to +24%.
- **What the backtest still does not model** (as R275):
  - liquidation above 1x (M265, next);
  - moving collateral between venues;
  - fills at the close on two venues at once.
- **dYdX:** its trade prices are not a usable mark in a crash. A live book there would need oracle (index) prices for
  its daily marks, which the downloaded candles do not hold.

## Pre-committed actions (from the PREREG)
- **A replicating set with a venue the owner can trade may get its own forward lane (a new id).**
  - gate+kucoin and binance+kucoin L14d th5% K20 go forward on paper in a new lane, frozen before its first live day.
  - Whether the owner can open a KuCoin account where they live is for the owner to check.
- **R278 keeps its frozen books.**
