# PREREG: pack_v1 (R194), many confident signals in one hedged maker book (in-sample design check)

Freeze with `lab.prereg.freeze()` before the first real-data statistic. After that this file is never edited; a changed
idea is a new lane.

- **Registry id:** R194
- **Owner (single writer):** the session that froze it
- **Code:** `lab/pack.py`, `scripts/run_pack.py`

## What the author had seen
maker_v1 (R193) in full: per trade, limit entries 1 sigma below the close turn the replicated gross edges positive
(median +23.5 bp discovery, +11.4 bp validation at fee 0), 61% of cells positive in both periods at fee 2 bp; the frozen
4-cell long-only book was NULL with drawdowns over 100% from market beta. atlas_v1, merges, listings, carry as recorded.
The context atlas (R192) is running; none of its results have been read.

## Question
The single-cell books fail on beta and on too few trades. Does a pack of every cell that pays per trade with limit
entries in both periods, traded together in one book with a BTC hedge, give a net return with a usable t over
2021-01-01 to 2025-06-30? This is a design check on data the cells were chosen on; only a pass earns a one-shot holdout.

## Cells
From maker_v1 (kappa 1, exit at market, fee 2 bp, 1x): the cells with per-trade net > 0 and >= 30 trades in both
discovery and validation, in order of min(discovery, validation) per-trade net (best first).

## Book (lab/pack.py)
Limit entries 1 sigma below (above for shorts) the close, trade-through by 2 bp in the next bar; exit at the close of
t + h at the tier cost; maker fee 2 bp; one position per symbol; each position 1/slots of capital; hourly marking with
funding. Hedge: short (long) BTCUSDT for beta x the book's net long (short) exposure at each close, paying its tier cost
on every change.

Grid: slots in {10, 20, 40}; hedge in {none, BTC beta 1}; cost multiple in {1, 2, 3} (fee fixed).
Primary: slots 20, BTC hedge, 1x. Period: 2021-01-01 to 2025-06-30 (rows of the research universe), reported per
calendar year.

## Decision
**PASS** (earns a one-shot holdout lane, frozen before it is read) if the primary's daily net has Newey-West t (lag 10)
>= 3, is positive in at least 4 of the 5 calendar years 2021-2025H1, and stays positive at 2x costs. Otherwise NULL.

## Reported
Net per year, Sharpe, t, max drawdown, gross / entry cost / exit cost / hedge PnL / hedge cost per year, mean exposure
and open positions, fills per day, and the beta of the daily net to BTC's daily return, for every grid point.

## Multiplicity
Trials = 3 x 2 x 3 = 18 books (on top of the maker_v1 trials the cells came from).

## Expectations (written before running)
The hedge removes most of the drawdown. Net positive in 2021 and 2023-2024, weak in 2022. t near 3 is possible because
the pack trades often; costs at 2x will hurt but per-trade nets of 10-20 bp leave room.
