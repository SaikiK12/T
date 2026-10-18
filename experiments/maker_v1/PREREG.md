# PREREG: maker_v1 (R193), limit-order entries on the replicated gross edges

Freeze with `lab.prereg.freeze()` before the first real-data statistic. After that this file is never edited; a changed
idea is a new lane.

- **Registry id:** R193
- **Owner (single writer):** the session that froze it
- **Code:** `lab/maker.py`, `scripts/run_maker.py`

## What the author had seen
atlas_v1 (main+clock) discovery and validation: 431 distinct raw cells (view, bin, horizon) are confident gross edges in
discovery that replicated in validation, mostly short-horizon mean reversion (bbz, rsi, ret, ema_ratio, struct, fvg,
sweep), with day-weighted edge/cost median 3.8. The merge lanes found that per-trade edges are much smaller than the
day-weighted ones and that no merge pays after taker costs. No fill-based (high/low) statistic has been computed.

## Question
"If there were no fees these signals would pay" is the recurring answer. A resting limit order removes most of the
cost of an entry (no spread or slippage, a maker fee of 0 to 2 bp) but fills mostly when the price moves through it,
against the trade. For the replicated gross edges, how much survives when the entry is a limit order under a strict
fill rule, compared with a market entry, and does a book of the cells selected on discovery pay on validation?

## Data and periods
Research universe of atlas_v1 (top 50 by trailing 30-day quote volume; 499 columns). Hourly close, high, low and funding
settlements from the panel. Discovery 2021-01-01 to 2023-12-31; validation 2024-01-01 to 2025-06-30; holdout
(from 2025-07-01) not read.

## Signals
The 413 replicated CGE(all) raw cells of atlas_v1 on the main tensor that are not time-only (deduplicated by view, bin,
horizon), side = sign of the discovery mean. A cell fires at an episode start (the hour a tradable symbol enters the bin).
h in {1, 4, 12, 24, 72} as the cell says.

## Execution (lab/maker.py)
- Taker entry (baseline): at close[t], tier cost (6/8/12/20 bp one-way by liquidity rank).
- Maker entry: limit at close[t] x (1 - side x kappa x vol), vol = std of the last 168 hourly returns; valid during bar
  t + 1; filled only if that bar trades through it by eps = 2 bp (low below for a buy, high above for a sell).
  kappa in {0, 0.25, 0.5, 1.0}. The fill price is the limit.
- Exit mode 0: market at close[t + h] (tier cost). Exit mode 1: limit at close[t + h] resting during bar t + h + 1 (maker
  fee if traded through), else market at close[t + h + 1] (tier cost).
- Funding settled while open is paid by longs and received by shorts.
- Maker fee in {0, 2 bp} (0: MEXC web/app maker; 2 bp: Binance regular maker). Taker costs x cmult in {1, 2, 3}.

## Statistics
Per cell and configuration: posted orders, fill rate, per-trade mean gross and net (sum over trades / trades), and the
daily sum of trade net returns (a fixed stake per trade, zero on days without trades) with its Newey-West t (lag
ceil(h/24) + 2), per period. Unconditional baseline: every tradable symbol and hour as a "cell", long and short, for each
horizon and kappa (the adverse selection of a limit order with no signal).

## Primary configuration and decision
- Primary: kappa 0.5, exit mode 0, maker fee 2 bp, cmult 1.
- Selection on discovery only: cells with primary net daily-sum t >= 3 and positive mean.
- Book: the selected cells in order of discovery t, one position per symbol, at most 10 at a time, 1/10 of capital each,
  opposite signals on a symbol cancel; run on validation with the primary configuration and, for comparison, with
  taker entries on the same cells.
- **SIGNAL** if the validation book's daily net has t >= 2 and a positive mean at cmult 1, fee 2 bp. A SIGNAL earns a
  one-shot holdout lane with the same cells and configuration. Otherwise NULL.
- Reported regardless: for the 413 cells, the share with positive per-trade net mean under taker vs maker entry in each
  period; fill rates; per-trade gross of filled vs all signals (the adverse selection); the unconditional baseline; book
  net at cmult 1, 2, 3 and fee 0 and 2 bp, per year.

## Multiplicity
Trials = 413 cells x 5 entry modes x 2 exit modes x 2 fees x 3 cost multiples = 24,780, plus the 2 books.

## Expectations (written before running)
Fill rates of 30-60% at kappa 0.5; filled trades will have a much lower gross than the signal's average (adverse
selection), but the saved entry cost (6-20 bp) and the price improvement (kappa x vol, 25-50 bp) are large next to the
short-horizon edges. More cells will be net positive with maker entries than with taker entries. Whether a book of
discovery-selected cells holds on validation is open: the merge lanes say per-trade edges are fragile.
