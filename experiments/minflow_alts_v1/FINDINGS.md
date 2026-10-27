# FINDINGS: minflow_alts_v1 (R351). R349's pick on nine new coins: the reversal is there gross, but under each coin's Lighter cost, and gone since 2025-07

**Verdict: NULL by the frozen rule, 1 trial.** R349's `flow_fade_k5_h5`, unchanged, on BNB, XRP, TRX, AVAX, LINK,
DOGE, SUI, ADA and LTC (2021-04..2026-09). Nobody had read these coins' 1-minute bars before this run.
- **Gross:** the fade earns on 8 of the 9 coins (all but TRX). It averages +1.68 bp a trade, about half of R349's
  validation gross on BTC, ETH and SOL (+3.22).
- **Net:**
  - These coins cost 0.77-4.10 bp a side to fill $1k on Lighter. The book loses 5.54 bp a day at 1x (t −2.88), or
    −2.14 bp a trade.
  - Both halves lose: −5.12 and −5.97 bp a day.
- **Since 2025-07, even the gross is negative:** −0.57 bp a trade, and −11.18 bp a day at 1x (t −2.49).
- **Checks** (REPLICATES needs all four; LIVE needs REPLICATES and the Recent t):

  | Check | Bar | Result | Pass |
  |---|---|---|---|
  | 1. NW t at 1x, All | ≥ 2.0 | −2.88 | no |
  | 2. Mean at 2x, All | > 0 | −15.41 bp a day | no |
  | 3. 1x mean in each half | > 0 | −5.12 / −5.97 bp a day | no |
  | 4. Coins with positive gross | ≥ 6 of 9 | 8 | yes |
  | LIVE: NW t at 1x, Recent | ≥ 2.0 | −2.49 | no |
- **What it means for R349:**
  - The reversal is general: it appears on coins nobody chose.
  - But it is small. Off the three most liquid perps it does not cover a zero-fee venue's book cost.
  - On these coins it has disappeared since mid-2025, which matches R349's own decline (+0.59 bp a trade since
    2025-07, t 0.54).

## Windows
Units: the book gives each coin a ninth of capital. bp a day is of capital, and bp a trade is of the trade's notional.
1x is each coin's Lighter $1k walk from R348, with no fee.

| Window | Trades a day | Hit | Gross / trade | 1x net / trade | 1x / 2x / 3x bp a day | NW t (1x) | Break-even bp a side | Late twin, 1x bp a day | Full tick, 1x bp a day |
|---|---|---|---|---|---|---|---|---|---|
| **All 2021-04..2026-09** | **23.3** | **54%** | **+1.68** | **−2.14** | **−5.54 / −15.41 / −25.29** | **−2.88** | **0.84** | −5.28 | −8.26 |
| Early 2021-04..2023 | 22.7 | 55% | +1.80 | −2.03 | −5.12 / −14.74 / −24.37 | −1.89 | 0.89 | −3.39 | −8.11 |
| Late 2024-01..2026-09 | 23.8 | 53% | +1.57 | −2.25 | −5.97 / −16.09 / −26.21 | −2.18 | 0.78 | −7.17 | −8.40 |
| **Recent 2025-07..2026-09** | **23.0** | **53%** | **−0.57** | **−4.38** | **−11.18 / −20.92 / −30.66** | **−2.49** | **−0.28** | −8.41 | −13.79 |

- **MEXC web** (3 bp a side): −11.18 bp a day over All. **API** (8.5 bp): −39.63.
- **By calendar year** (gross per trade; then 1x bp a day):

  | | 2021 (from April) | 2022 | 2023 | 2024 | 2025 | 2026 (to September) |
  |---|---|---|---|---|---|---|
  | Gross per trade | +7.03 | +0.45 | −0.82 | +3.33 | +0.82 | +0.06 |
  | 1x bp a day | +8.12 | −8.47 | −11.74 | −1.27 | −8.19 | −9.30 |

  2021 is the only year the book earns. 2024 nearly breaks even.

## By coin (All, per trade, bp)

| Coin | Cost a side | Trades | Gross | 1x net | t (per trade) | Gross since 2025-07 |
|---|---|---|---|---|---|---|
| BNB | 0.81 | 5,271 | +1.91 | +0.29 | 0.29 | −0.47 |
| XRP | 0.77 | 5,486 | +1.60 | +0.05 | 0.03 | +1.39 |
| AVAX | 1.63 | 5,499 | +3.56 | +0.29 | 0.20 | −2.52 |
| LINK | 1.65 | 5,425 | +2.95 | −0.35 | −0.23 | −0.52 |
| DOGE | 1.95 | 5,815 | +1.99 | −1.91 | −1.05 | +2.99 |
| SUI (from 2023-05) | 2.00 | 3,296 | +1.36 | −2.64 | −1.10 | +0.54 |
| ADA | 2.72 | 5,357 | +2.00 | −3.45 | −2.28 | +0.43 |
| LTC | 4.10 | 5,369 | +0.33 | −7.87 | −5.32 | −4.37 |
| TRX | 1.59 | 5,233 | −0.84 | −4.05 | −3.57 | −2.76 |

- **No coin nets more than +0.3 bp a trade over All.** The three cheapest coins (BNB, XRP, AVAX) about break even.
- **Gross by year:** every coin then listed earned in 2021 (+2.6 to +16.2 bp a trade; SUI listed in 2023). Most
  did again in 2024 (+2.2 to +5.3, but not SUI or TRX), and few did in other years.

## By side (All; reported, not decided on)
- **Longs, which fade heavy selling:** 64% of trades, gross +3.49 bp, 1x net −0.34.
- **Shorts, which fade heavy buying:** gross −1.56, net −5.38.
- **Since 2025-07:** longs gross −0.19 and shorts −1.21. Neither side earns.
- This matches R349, where the longs carried the edge (validation +4.53 bp a trade against +0.22 for shorts). It is
  post hoc, so it is not a new rule.

## Noise and tails
- A trade's 1x net has a standard deviation of 109 bp (R349's three coins: 62), and its median is +0.09 bp.
- The 10 best days do not rescue the book: without them All is −7.67 bp a day.

## Costs (1x, 2x, 3x)
- **1x:** Lighter Standard, no fee. Each side pays the coin's R348 median $1k walk, and prices move half a tick
  against each fill.
- **2x / 3x:** −15.41 / −25.29 bp a day over All, and −20.92 / −30.66 over Recent.
- **The pick breaks even at 0.84 bp a side over All, and below zero since 2025-07.** Only BNB and XRP cost less than
  0.84 bp a side.
- **Full tick against each fill:** −8.26 bp a day. The coarse ticks (ADA 2-3.6 bp) add a little bounce to the
  half-tick numbers; they do not hide a profit.

## What this does and does not show
**It shows,** on nine coins' 1-minute bars that nobody had read:
- After the most extreme 0.5% of 5-minute signed-flow windows, the next 5 minutes partly reverse: +1.7 bp a trade
  gross on average, mostly after heavy selling.
- The reversal is too small to pay a zero-fee venue's book cost on any of these coins.
- It was largest in 2021, and since 2025-07 it is gone even before costs.

**It does not show:**
- **That R349's three coins have lost it as well.** That is R349's own recent window: +0.59 bp a trade, t 0.54.
- **Anything about maker entries,** Lighter's own fills, other rules of R349's family, or the reserved 2020 minutes.

## What changes
- **R349's earned forward lane (claimed as R352) is not started.**
  - On nine new coins the reversal's gross is −0.57 bp a trade since 2025-07.
  - On R349's own coins it is +0.59 bp a trade net (t 0.54).
  - A paper lane for an edge that is about zero now would need about 4,000 trades to say anything, so the R352
    claim is released.
- **R349's pick stays recorded for BTC, ETH and SOL** (PARTIAL, gate 0). The reserved 2020 minutes are still the
  cheap test of whether it ever existed outside the years it was found in. It can be named in a later batch.
- **M426** stays PARTIAL: R349's pass, then R351's NULL on new coins.

## Lane details
- **Registry row:** R351, 1 trial.
  - PREREG sha256 `7c82f485…e5e6`, frozen and pushed in `be6dca0` before the run.
  - Claimed on #7 (comment 6445173824). All 32 inputs matched.
  - The runner checked its cost constants against R348's `summary.json`.
- **Data:** `data/klines_1m_tape`, fetched 2026-10-27 with `scripts/fetch_klines_stream.py`.
  - 593 monthly archives, each checked against its published SHA-256 and kept in memory only.
  - 2020 was not fetched.
  - Provenance: `docs/provenance/klines_1m_tape.json`.
- **Reproduce:** `python scripts/run_minflow_alts.py` (about 6 minutes). The log is `run.log`.
  - `results/`: `summary.json`, `windows.csv`, `coins.csv`, `daily.csv.gz` and `trades.csv.gz`.
  - The side, noise and by-year gross tables above were computed from `trades.csv.gz` and `coins.csv` after the run.
    They are reported and not decided on.
- **Read against the program:** trials go from 9,479,068 to 9,479,069 on this branch, or 9,479,086 counting #56's
  R338-R346.
