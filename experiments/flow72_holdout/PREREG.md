# PREREG: flow72_holdout (R198), one-shot holdout of the 72 h flow slice book

Freeze with `lab.prereg.freeze()` before the first holdout statistic. Run once. Never edited afterwards.

- **Registry id:** R198
- **Owner (single writer):** the session that froze it
- **Code:** `lab/slices.py`, `scripts/run_flow72_holdout.py`

## What the author had seen
Everything up to flow72_v2 (R197), which passed its in-sample rule: combined book, universe hedge, +42.6%/yr net at 1x
(t 3.25) over 2021-01-01..2025-06-30. No data from 2025-07-01 on has been read for these cells. The holdout period was
read before by listings_holdout (R189) and carry_holdout (R191), for unrelated signals.

## Frozen rule (exactly R197's primary)
- Cells (flow tensor): top_vs_crowd/xs8 bin 0, taker[24]/xs8 bin 0, taker[4]/xs8 bin 0; side short. A slice opens at
  every (hour, coin) where the coin is in the top 50 by trailing 30-day quote volume and in a cell (one slice per cell),
  closes 72 h later. Slice size 1 / (72 x 9.316) (K frozen from 2021-2023).
- Costs: tier cost (6/8/12/20 bp one-way by liquidity rank) on every change of position; funding included.
- Hedge: long the equal-weighted basket of the tradable coins for the book's net short exposure (idealized as in R197).
- Period: 2025-07-01 00:00 UTC to the end of the data (2026-09-30), starting flat.

## Decision
**CONFIRMED** if the daily net has a positive mean and Newey-West t (lag 10) >= 2 at 1x costs. Otherwise NOT CONFIRMED
(registered as NULL). One shot: whatever the outcome, the holdout is spent for these cells.

## Reported (not decided on)
2x and 3x costs; no hedge; a top-10 equal-weighted basket hedge and a BTC hedge (the practical versions), each also on
2021-2025H1 for reference; each cell alone; net per month; max drawdown; beta to BTC.

## Multiplicity
Trials = 1 (the primary). Program trials are read alongside.

## Expectations (written before running)
Smaller than in-sample (edges decay, as validation already showed vs discovery for the atlas cells): perhaps +10 to
+25%/yr with t around 1-2 over 15 months. A NOT CONFIRMED result is the more likely single outcome.
