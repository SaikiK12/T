# PREREG: carry_v1 (R190), funding carry on liquid perpetuals

Freeze with `lab.prereg.freeze()` before the first real-data statistic. Never edited afterwards.

- **Registry id:** R190
- **Code:** `lab/carry.py`, `scripts/run_carry.py`
- **What the author had seen:** funding appeared in atlas_v1 only as a cross-sectional predictor of returns (strong in
  2021-2023, not replicated in 2024-2025H1). No carry PnL has been computed on this data. The idea is structural and
  published (longs pay for leverage; the carry is earned by holding the other side), not mined.

## Question
How much does a hedged funding carry (short perp, long the same coin spot) earn after costs on Binance's liquid
perpetuals, in which years, and is it consistent enough to be called an edge? This is the textbook case of a strategy
that works without fees; here fees and basis risk are charged.

## Data and universe
Panel as in the other lanes (all 900 USDT perps, hourly, funding at its settlement bars, premium index klines as the
basis). Tradable: top 50 by trailing 30-day quote volume at that hour AND a Binance spot pair (same coin, or the coin
without its 1000x prefix) with spot klines in that month (data/spot_pairs.json).
Splits: discovery 2021-01-01..2023-12-31, validation 2024-01-01..2025-06-30, holdout from 2025-07-01 not read.

## Strategy
- Signal: trailing funding = sum of settled rates over the last 72 hours, annualized (x 365/3).
- Enter (short perp + long spot) when trailing funding > theta_in; exit when < theta_in / 2 or the symbol stops being
  tradable. At most 10 positions get full weight: each position holds 1/max(open, 10) of capital per leg.
- PnL per hour: funding received at settlement + minus the basis change (premium index) - costs. Costs per weight
  change: perp tier cost (6/8/12/20 bp one-way by liquidity rank) + spot taker cost, on entry and exit.
- Grid: theta_in in 10%, 20%, 40% APR; spot cost 10 bp (Binance taker) or 5 bp (cheaper venue); cost multiplier 1x and 2x.
- Primary: theta_in 20%, spot 10 bp, 1x.

## Reported
Annual net return on capital per leg, Sharpe, Newey-West t (lag 10, daily), max drawdown, funding and basis parts,
cost, average open positions, per-year net, and the share of time invested.

## Decision
- **SIGNAL** if the primary's discovery net has t >= 3 and at least 2 of 3 discovery years positive.
- **VALIDATED** if also positive on validation with t >= 2. A validated primary earns a one-shot holdout lane.
- Otherwise NULL (still reported: the size of the carry by year is useful on its own).

## Multiplicity
Trials = 3 x 2 x 2 = 12 configurations.

## Expectations (written before running)
Positive and large in 2021, small or near zero in 2022-2023 when funding was low, positive again in 2024. Discovery t
may pass; whether it is consistent enough is the open question. Basis blowouts in squeezes are the main risk.
