# PREREG: mexc_fwd_sq (R218), the agreement-squared flow book traded on MEXC, forward

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R218
- **Owner (single writer):** the session that froze it; it writes only `experiments/mexc_fwd_sq/journal/`
- **Code:** `scripts/forward_mexc_sq.py` (uses `scripts/forward_mexc.py`'s loader and scorer; reads R200's journal)

## Why
R217 (sizing_v1) found that sizing a coin by the square of the number of agreeing flow cells beat linear sizing in
every window: Sharpe 1.96 / 1.68 / 1.49 vs 1.81 / 1.39 / 1.05. It missed the frozen bar in discovery (+0.15 against
+0.3), so it is not a pass. This lane is the clean test: a forward period no one has seen, on the owner's venue.

## What the author had seen
- All of R217 (archive 2021-01..2026-09), including X2's known holdout.
- R215's 18 replayed days for books A and B on MEXC.
- No X2 number on forward or MEXC data has been computed.

## Rules
- Everything as R215: R200's signals, one bar late, MEXC closes and funding, MEXC-mapped crypto contracts only,
  universe hedge over them, tier costs 1x/2x/3x.
- The only change is the book. **X2**: a coin flagged by k of the three cells (top_vs_crowd, taker[24], taker[4]; xs8
  bin 0; short) holds k² slices of size 0.7056 / (72 x 9.316). 0.7056 = 0.997 / 1.413 is R217's frozen ratio that
  matches X2's mean gross exposure to book A's on 2021-23.
- Days: on-time from 2026-10-20 (UTC); replay days 2026-10-01..19 are reported separately and never decide.

## Decision
At 90 on-time days (2027-01-17 at the earliest): `lab.gate.go_real()` on X2's daily 1x net.

Reported next to R215's book A on the same days:
- the difference of daily nets (mean, NW t);
- per-coin contributions.

30- and 60-day checkpoints are monitoring only.

## Multiplicity
Trials = 1. Program trials before: 9,471,728.

## Expectations
X2 tracks R215's A closely (same signals) with more concentration. Over 90 days the difference between them is noise
unless the archive gap (+4 to +6 bp/day) holds.
