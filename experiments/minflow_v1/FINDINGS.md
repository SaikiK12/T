# FINDINGS: minflow_v1 (R349). Extreme 5-minute order flow on BTC, ETH and SOL reverses over the next 5 minutes, by enough to pay on a zero-fee venue; the effect has shrunk since mid-2025

**Verdict: PASS (gate 0, on seen years), 57 trials.** M426 has a pick. M306 (absorption and exhaustion) is NULL.
- **The pick:** `flow_fade_k5_h5`.
  - When the signed taker volume of the last 5 minutes reaches its trailing-week 99.5th percentile, it takes the
    other side at the next minute's open and exits 5 minutes later.
  - It trades BTC, ETH and SOL, about 8 trades a day across the three.
- **All four frozen checks pass:**
  1. The reality check over all 57 rules gives p < 0.0005. No bootstrap maximum of 2,000 reached the pick's
     studentized discovery mean of 4.80; the null's 95th percentile is 3.28.
  2. The validation t at 1x is 3.48 (bar 2.0).
  3. Validation 2x is +5.7 bp a day.
  4. Both validation halves are positive: +11.8 and +1.5 bp a day.
- **What it is worth:** at Lighter's zero fee and measured book cost, +2.7 bp a trade net in 2024-01..2026-09.
  - It is only +0.6 bp a trade since 2025-07 (t 0.7 per trade), and about 0 in 2026.
  - At MEXC's web cost (3 bp a side) it loses in every validation window.
- **What the pass earns** (frozen in the PREREG):
  - a forward paper lane on Lighter's own recorded quotes, with a new id frozen before its first day;
  - a place in a reserved 2020 batch.
  - Nothing trades with money.

## The pick, window by window
Units: the book holds a third of capital per coin. bp a day is of capital, and bp a trade is of the trade's notional.
1x is Lighter's measured $1k book walk (BTC 0.27, ETH 0.23, SOL 0.30 bp a side, no fee).

| Window | Trades a day | Hit | Gross / trade | 1x net / trade | 1x / 2x / 3x bp a day | MEXC web bp a day | NW t (1x) |
|---|---|---|---|---|---|---|---|
| Discovery 2021-04..2023 | 8.0 | 57.4% | +6.22 | +5.70 | +15.25 / +13.82 / +12.38 | +0.62 | 4.67 |
| **Validation 2024-01..2026-09** | **7.9** | **56.5%** | **+3.22** | **+2.69** | **+7.11 / +5.69 / +4.28** | **−7.33** | **3.48** |
| 2024-01..2025-06 | 8.2 | 56.5% | +4.85 | +4.32 | +11.81 / +10.34 / +8.88 | −3.15 | 4.23 |
| 2025-07..2026-09 (spent holdout) | 7.6 | 56.5% | +1.12 | +0.59 | +1.48 / +0.13 / −1.22 | −12.34 | 0.54 |

- **By calendar year (1x, bp a day):** 2021 +34.4, 2022 +7.6, 2023 +6.7, 2024 +12.2, 2025 +7.7, 2026 (to September)
  −0.5.
- **By coin (1x net per trade):**

  | Coin | 2021-23 | 2024-25H1 | 2025H2-26 |
  |---|---|---|---|
  | BTC | +1.95 (t 1.5) | +3.60 (t 2.9) | +1.60 (t 1.5) |
  | ETH | +5.77 (t 2.9) | +2.79 (t 1.4) | +0.71 (t 0.5) |
  | SOL | +10.07 (t 4.6) | +6.47 (t 3.3) | −0.55 (t −0.3) |

  - Each cell holds 1,100-3,100 trades.
  - BTC's tick is under 0.03 bp, so its result is not a bid-ask bounce. SOL's coarser tick in 2022-23 may inflate
    its early numbers (Known limits in the PREREG).
- **By side (validation):** longs (fading heavy selling) +4.53 bp a trade, shorts +0.22. 57% of trades are longs.
- **Trade spread:** a trade's net has a standard deviation of 62 bp in validation (51 since 2025-07). The median is
  +5.0 bp, the 5th percentile −81 and the 95th +81.
- **Concentration:**
  - the 10 best validation days carry 37% of the net;
  - without them, validation is +4.5 bp a day;
  - the 5% trimmed mean of the days with a trade is +8.4.
- **One minute late** (reported only): entering at the close of the minute after the signal still grosses +5.60
  (discovery) and +2.42 (validation) bp a trade. Its 1x net is +13.2 and +4.8 bp a day. The effect is not confined to
  the first seconds.
- **Funding** is negligible at a 5-minute hold: −0.001 bp a trade.

## The whole family
- **Fade versus follow:**
  - Every fade rule on returns or signed flow grosses positive per trade in discovery.
  - In validation, 17 of the 18 do. The exception is ret fade, k5, 60 minutes.
  - Every follow rule grosses negative in validation.
  - Extreme minutes in these perps partly reverse within 5-15 minutes. The 60-minute holds keep less of it.
- **Sub-family reality checks** (reported only): ret p 0.007, flow < 0.0005, absorb 0.80, exhaust 1.00, lead 0.72.
  Hansen's SPA over all 57 in discovery: p 0.001.
- **The fade rules, by studentized discovery mean** (gross bp a trade, and 1x bp a day and t in validation):

  | Rule | Discovery stat | Gross disc / valid | Valid 1x bp a day (t) |
  |---|---|---|---|
  | flow fade k5 h5 (pick) | 4.80 | +6.22 / +3.22 | +7.11 (3.48) |
  | ret fade k5 h5 | 3.52 | +4.26 / +1.87 | +4.99 (1.86) |
  | flow fade k15 h5 | 3.03 | +3.94 / +2.18 | +3.82 (1.84) |
  | ret fade k15 h5 | 2.99 | +3.99 / +2.90 | +6.75 (2.58) |
  | flow fade k15 h15 | 2.47 | +6.72 / +3.11 | +3.04 (1.47) |
  | ret fade k15 h15 | 2.44 | +6.29 / +2.74 | +3.73 (1.38) |
  | flow fade k1 h15 | 2.04 | +2.38 / +1.47 | +4.93 (1.53) |
  | flow fade k1 h5 | 1.90 | +1.70 / +1.24 | +4.37 (1.41) |

- **M306, absorption and exhaustion (12 rules):** nothing.
  - Absorption's "book" read (trade against the absorbed side) is the best of them, at a discovery stat of 0.75. It
    loses 7.3 bp a day in validation at 15 minutes.
  - Exhaustion's book read is −9 to −13 bp a day in discovery.
  - Their "anti" reads lose more, because they trade 10-45 times a day for under 1 bp of gross.
- **BTC's lead into ETH and SOL (9 rules):** nothing that clears the family's null. The best is lead k15 h15 (stat
  0.67).

## Costs (1x, 2x, 3x)
- **1x:** Lighter Standard, no fee.
  - Each side pays the coin's median $1k book walk from R348: BTC 0.27, ETH 0.23 and SOL 0.30 bp.
  - Prices are moved half a tick against each fill.
- **2x and 3x:** +5.69 and +4.28 bp a day in validation, and +0.13 and −1.22 since 2025-07.
- **The pick breaks even at 1.6 bp a side in validation,** and at 0.56 since 2025-07. That is why it needs a fee-free
  venue:
  - MEXC web (3 bp a side) loses −7.3 bp a day in validation;
  - MEXC or Binance API (8.5 bp) loses far more.

## What this does and does not show
**It shows,** on 2021-2026 Binance 1-minute bars for the three most liquid perps:
- After the most extreme 0.5% of 5-minute order-flow windows, the next 5 minutes reverse about 56% of the time.
- The reversal is worth a few basis points a trade, mostly after heavy selling.
- It holds in every year to 2025, on each coin, and in a whole family of related rules. It survives a one-minute-late
  entry.

**It does not show:**
- **That it still pays.** Since 2025-07 it earns +0.6 bp a trade (t 0.7), and 2026 to date is about 0. The decline
  from 2021 is steady, so the forward test, not this table, decides.
- **That Lighter fills match.**
  - The fills here are Binance prints with half a tick against the trade, at Lighter's October 2026 book walk.
  - Lighter's own quotes one second after each signal are the forward lane's first measurement. Its paired gap to
    these prints should be measurable within days.
- **Capacity.** At $1k a trade the walk is about 0.25 bp a side. Larger trades walk further, and the edge is a few
  bp.
- **Speed of proof.** At 62 bp of noise a trade, an edge of +2.7 bp needs about 4,000 trades (about 500 days at 8 a
  day) for 80% power at t 2. At +0.6 bp, forward days alone cannot confirm it in a useful time. The reserved 2020
  minutes (BTC and ETH from 2020-01, SOL from 2020-09) are the faster test of whether the effect exists outside the
  years it was found in.

## Lane details
- **Registry row:** R349, 57 trials.
  - PREREG sha256 `0c75a8c4…0a14`, frozen and pushed in `0974be4` before the run.
  - It was claimed on #7 (comment 6444858325).
  - All 15 inputs matched.
- **Reproduce:** `python scripts/run_minflow.py` (about 80 s). It writes `results/variants.csv`,
  `results/daily.csv.gz`, `results/trades_best.csv.gz` and `results/summary.json`. The log is `run.log`.
- **Gate:** 0. Every year was read before, by many lanes at hourly resolution and by R289-R293 on these 1-minute
  files for other rules.
- **Read against the program:** trials go from 9,479,011 to 9,479,068 on this branch, or 9,479,085 counting #56's
  R338-R346.
  - The pick's reality check accounts for this family's 57 rules, not for the program's search.
  - Its validation read is a single test on years other lanes have read.
- **The tables above** (by coin and half, by side, the trade spread) come from `results/trades_best.csv.gz` after the
  run. They are reported and not decided on.
