# PREREG: ctxslice_v1 (R201), the replicated market-neutral context edges as one slice book

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R201
- **Owner (single writer):** the session that froze it
- **Code:** `scripts/run_ctxslice.py`, `lab/slices.py`, `scripts/run_context_atlas.py` (context loaders)

## What the author had seen
atlas_ctx (R192) and atlas_mtf (R195) discovery and validation tables, including the counts and a dozen examples of
replicated excess conditional edges (CCE) with their validation means; flow72_v1/v2 (an entry book loses where a slice
book of the same state earns); the flow72 holdout. No book of these cells has been run on any period, and **no data
from 2025-07-01 on has been read for them**.

## Cells (fixed list, written and hashed by `run_ctxslice.py list` before any book is computed)
Every row of `experiments/atlas_ctx/results/replication.csv` and `experiments/atlas_mtf/results/replication.csv` with
kind = real, measure = excess and cce_rep_2x = True (315 + 232 = 547 cells): a base view and bin, a context and code, a
horizon h, and the sign of the discovery conditional mean. State of cell c at (t, s): the coin's view is in the bin,
the context has the code, and the coin is tradable (top 50).

## Book
- Every hour a coin is in a cell's state, open a slice in the sign's direction, closed h hours later (slices from all
  cells summed; opposite slices net out). Slice size 1 / (h_c x M), where M = the sum over cells of the mean number of
  coins in the cell's state per hour on 2021-01-01..2025-06-30, so the mean gross exposure before netting is 1.
- Position set at the close of t, earns ret[t] (funding included); tier cost (6/8/12/20 bp one way) on every change of
  the net position per coin; universe hedge: the equal-weighted tradable basket offsets the book's net exposure
  (idealized, as R197), so the book earns the excess return it was selected on.

## Stage 1: in-sample (2021-01-01..2025-06-30), selection-biased
The cells were chosen on these years, so this is a filter, not evidence: it shows whether held states survive costs and
netting. **Gate to stage 2: daily net mean > 0 and NW t (lag 10) >= 2 at 1x.** If it fails, the holdout is not read
and the lane is NULL.

## Stage 2: holdout (2025-07-01..2026-09-30), one shot
**CONFIRMED if the daily net at 1x has a positive mean and NW t (lag 10) >= 2.** Otherwise NULL. The holdout is spent
for these cells whatever the outcome.

## Reported (not decided on)
2x and 3x costs; top-10 and BTC hedges; sub-books: atlas_ctx cells only, atlas_mtf cells only, by horizon (1-4 h,
12-24 h, 72 h); per year; per month on the holdout; max drawdown; beta to BTC; mean gross and net exposure; turnover.

## Multiplicity
Trials = 1 (the primary book). Program trials (9,471,634 before this lane) are read alongside; the cells came out of
about 9 million context cells.

## Expectations (written before running)
Day-weighted atlas means overstate what entries earn, and the states are rare and correlated (many share a context),
so the book is thin and lumpy. Turnover is high for 1-4 h cells. Guess: in-sample positive at 1x (the cells were picked
there), holdout around zero to modestly positive with t below 2.
