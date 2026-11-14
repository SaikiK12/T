# PREREG: flow72_fwd3 (R214), the R200 forward books entered one bar late

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R214
- **Owner (single writer):** the session that froze it; it writes only `experiments/flow72_fwd3/journal/`
- **Code:** `scripts/forward_delayed.py` (reads R200's journal and price cache; never writes them)
- **Source:** Codex review, `docs/IMPLEMENTATION_INTEGRITY_REVIEW.md` finding 2.

## Why
R200 (flow72_fwd2) credits a slice with the return from the close of its signal bar, 12 minutes or more before the
signal exists. Its journal and spec are frozen and stay untouched. This twin keeps R200's signals and changes only
the entry: one bar later, a price that is always available after the signal is computed on time.

## What the author had seen
R200's 18 replayed days (2026-10-01..18, all backfilled from endpoint history, tagged `late`): A +22.2%, B +9.7% at
1x. No delayed book has been computed on forward data.

## Rules
- Signals: R200's `signals.csv` rows (bins of top_vs_crowd, taker[24], taker[4], eligibility, liquidity rank),
  unchanged.
- Entry: a slice whose signal is at row t opens at row t + 1 (position set at the close of the bar after the signal
  bar), if the symbol has a signal row (is eligible) at t + 1; held 72 h; size 1 / (72 x 9.316); universe hedge; tier
  costs; funding as R200.
- Books: **A** (three cells summed, primary) and **B** (top_vs_crowd alone).
- Days: **on-time days** are 2026-10-20 and later (UTC). Days 2026-10-01..10-19 are computed for warm-up and reported
  as `replay`, never counted in the decision.

## Decision (same gate as R200, applied to on-time days only)
At 90 on-time days (2027-01-17 at the earliest): `lab.gate.go_real()` on book A's daily 1x net. 30- and 60-day
checkpoints are monitoring only; no retuning, no early pass. Book B is reported, never promoted.

## Reported, not decided on
2x and 3x costs; gross, cost, hedge per day; the replay days next to R200's own tickets (the delay's effect on the
same days); the lag between each signal hour's bar close and R200's `run_at` (median, 90th percentile, max), and a
diagnostic book A_rt that opens each slice at the first bar closing after `run_at` (on-time days only).

## Multiplicity
Trials = 3 (A, B, A_rt). Program trials before: 9,471,709 (after R213).

## Expectations
A one-bar delay costs a few percent of a 72 h slice's edge; the forward numbers are noisy at 90 days either way
(R200's own expectations apply: t near 0.5-1 for a Sharpe near 1).
