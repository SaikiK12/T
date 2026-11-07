# PREREG: flow72_v1 (R196), short the coins sold by takers and shorted by top traders, 72 h, market-neutral

Freeze with `lab.prereg.freeze()` before the first real-data statistic. After that this file is never edited; a changed
idea is a new lane.

- **Registry id:** R196
- **Owner (single writer):** the session that froze it
- **Code:** `lab/pack.py` (universe hedge, hedge_col = -2), `scripts/run_flow72.py`

## What the author had seen
atlas_v1 flow results in full (discovery and validation): three excess cells at h 72 replicated, all on the short side:
top_vs_crowd/xs8 bin 0 (top traders' long/short ratio lowest relative to the crowd's), -54 bp discovery / -40 bp
validation; taker[24]/xs8 bin 0 (most taker selling over 24 h), -57 / -37 bp; taker[4]/xs8 bin 0, -32 / -16 bp; validation
edge/cost 2.8, 2.6, 1.1 (day-weighted). maker_v1 and pack_v1 in full (raw cells are beta; limit entries do not help
shorts). Context-atlas lists not read.

## Question
These are the only replicated edges that are cross-sectional (hedged by construction), slow (72 h, so one round trip is
spread over three days) and large next to costs. Does a book that shorts the coins entering those bins, hedged with the
tradable universe, earn after costs over 2021-01-01 to 2025-06-30, consistently by year? This is an in-sample design
check (the cells were chosen with both periods); a pass earns one holdout shot.

## Book (lab/pack.py)
- Cells in priority order: top_vs_crowd/xs8 bin 0, taker[24]/xs8 bin 0, taker[4]/xs8 bin 0; side short; hold 72 h;
  episode starts (the hour a tradable coin enters the bin); one position per coin; each position 1/slots of capital.
- Entry: market at the close (tier cost) or a sell limit 0.5 sigma above the close (trade-through 2 bp, maker fee 2 bp).
  Exit: market at the close 72 h later (tier cost). Funding paid/received hourly at settlements.
- Hedge: long the equal-weighted basket of the coins tradable at each close for the book's net short exposure (its
  return is the basket's mean next-bar return; tier cost on each change of size; the basket's internal rebalancing is
  not charged), or long BTC for the same amount, or none.
- Grid: entry {market, limit}, hedge {universe, BTC, none}, slots {10, 20}, cost multiple {1, 2, 3}. Primary: market
  entry, universe hedge, slots 20, 1x.

## Decision
**PASS** (earns a one-shot holdout lane, frozen before it is read) if the primary's daily net has Newey-West t (lag 10)
>= 3, is positive in at least 4 of the 5 calendar years 2021-2025H1, and stays positive at 2x costs. Otherwise NULL.

## Reported
Every grid point: net per year, Sharpe, t, max drawdown, gross, costs, hedge PnL and cost, mean exposure and open
positions, fills per day, beta to BTC.

## Multiplicity
Trials = 2 x 3 x 2 x 3 = 36 books (the three cells come from atlas_v1's 338,240).

## Expectations (written before running)
Positive in most years with the universe hedge, weaker with BTC (alts against BTC adds noise). Per position about
-40 bp of excess over 72 h against a round trip of about 15 bp: a thin but real margin at 1x, gone at 3x.
