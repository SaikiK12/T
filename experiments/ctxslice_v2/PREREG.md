# PREREG: ctxslice_v2 (R204), the slow (12-24 h) replicated context pairs as a slice book, one-shot holdout

Freeze with `lab.prereg.freeze()` before the first holdout statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R204
- **Owner (single writer):** the session that froze it
- **Code:** `scripts/run_ctxslice.py --lane ctxslice_v2`, `lab/slices.py`

## What the author had seen
ctxslice_v1 (R201) stage 1 in-sample (2021-01..2025-06), including five sub-books: all 547 pairs -32%/yr (t -1.97);
atlas_ctx cells +33.9% (t 3.17); atlas_mtf cells -75.7%; 1-4 h cells -82.5%; **12-24 h cells +39.4%/yr, Sharpe 1.78,
t 3.85, max DD 21%** (at v1's size normalizer); 72 h cells ~0. This lane takes the 12-24 h sub-book because it had
the best in-sample t and the lowest cost per unit of gross, consistent with every earlier lane (slow books pay costs,
fast ones do not). The choice is post hoc among five sub-books on in-sample data: the in-sample numbers are not
evidence. **No data from 2025-07-01 on has been read for these cells.**

## Cells
The rows of `experiments/ctxslice_v1/results/cells.csv` (sha ed59ae0c, verified) with h in {12, 24}: 289 pairs (atlas_ctx
236, atlas_mtf 53). Written to this lane's `results/cells.csv` and hashed before any statistic.

## Book (as R201 otherwise)
Slices in each pair's sign, closed h hours later, summed over pairs (opposite slices net); slice size 1 / (h_c x M2),
M2 = the sum over these 289 pairs of the mean number of coins in each state per hour on 2021-01-01..2025-06-30 (so the
mean gross before netting is 1); position at the close of t earns ret[t] with funding; tier cost on every change of
the net position; universe hedge (idealized).

## Holdout (2025-07-01..2026-09-30), one shot
**CONFIRMED if the daily net at 1x has a positive mean and NW t (lag 10) >= 2.** Otherwise NULL. Spent for these cells
whatever the outcome.

## Reported (not decided on)
2x and 3x; top-10, BTC and no hedge; atlas_ctx-only and atlas_mtf-only parts; 12 h and 24 h parts; per month; max
drawdown; beta to BTC; exposures; turnover.

## Multiplicity
Trials = 1 (primary); the in-sample choice was among 5 sub-books of R201. Program trials 9,471,641 before this lane.

## Expectations (written before running)
In-sample +39%/yr was picked; edges decayed from discovery to validation in every atlas lane, and the flow72 holdout
kept its sign with much more variance. Guess: positive, around +10 to +20%/yr, t near 1-2.
