# PREREG: flow72_v2 (R197), the same three flow cells as overlapping 72 h slices

Freeze with `lab.prereg.freeze()` before the first real-data statistic. After that this file is never edited; a changed
idea is a new lane.

- **Registry id:** R197
- **Owner (single writer):** the session that froze it
- **Code:** `lab/slices.py`, `scripts/run_flow72_slices.py`

## What the author had seen
flow72_v1 (R196) in full, including its post-verdict diagnostic: per entry the three cells earn 5-13 bp over 72 h on
validation, over all hours in the bin 16-40 bp (excess, day-weighted and trade-weighted alike). atlas_v1 flow results.
This lane exists because of that diagnostic; it is chosen after seeing data and is judged accordingly (in-sample check,
then a one-shot holdout only on a pass).

## Question
The atlas mean of a cell is what a book earns if it opens a slice every hour a coin is in the cell and closes it 72 h
later. Each slice pays one round trip (about 15 bp). Does that construction earn, after costs and hedged with the
universe, over 2021-01-01 to 2025-06-30, consistently by year?

## Book (lab/slices.py)
- Cells: top_vs_crowd/xs8 bin 0, taker[24]/xs8 bin 0, taker[4]/xs8 bin 0 (flow tensor), side short. A slice opens at
  every (hour, coin) where the coin is tradable (top 50) and in the cell; it closes 72 h later. "Combined" opens one
  slice per cell the coin is in (stacking).
- Slice size: 1 / (72 x K), K = the mean number of slices opened per hour over 2021-01-01..2023-12-31 for that book, so
  that gross exposure is about 1 on average. Position = sum of live slices; costs = tier cost x |change of position| x
  cmult; returns include funding.
- Hedge: long the equal-weighted basket of tradable coins for the book's net short exposure (idealized: the basket's
  internal rebalancing is free; tier cost on changes of its size), or none.
- Grid: book in {each cell alone, combined}; hedge in {universe, none}; cmult in {1, 2, 3}. Primary: combined, universe
  hedge, 1x.

## Decision
**PASS** (earns a one-shot holdout lane, frozen before it is read) if the primary's daily net has Newey-West t (lag 10)
>= 3, is positive in at least 4 of the 5 calendar years 2021-2025H1, and stays positive at 2x costs. Otherwise NULL.

## Reported
Every grid point: net per year and per split (discovery, validation), Sharpe, t, max drawdown, gross, costs, hedge PnL
and cost, mean gross and net exposure, turnover, beta to BTC.

## Multiplicity
Trials = 4 x 2 x 3 = 24 books, on top of flow72_v1's 36 and atlas_v1's cells.

## Expectations (written before running)
Gross excess of about 20-40 bp per slice over 72 h against 15 bp of cost: positive at 1x in discovery, thin in
validation, negative at 3x. The t over 4.5 years may reach 3 for the combined book; 2024-2025 will be the weak years.
