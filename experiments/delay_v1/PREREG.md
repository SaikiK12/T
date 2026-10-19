# PREREG: delay_v1 (R213), how much does a late entry cost the flow books?

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R213
- **Owner (single writer):** the session that froze it
- **Code:** `scripts/run_delay.py`, `lab/slices.py`
- **Source:** Codex review, `docs/IMPLEMENTATION_INTEGRITY_REVIEW.md` finding 2.

## Why
The archive books (R197, R198) and the forward paper books (R200) set a position at the close of the signal's own bar
(row t) and credit it with ret[t] = close[t+1] / close[t] - 1. Live, the signal for row t is ready 12 minutes after
that close at best; R200's journal shows hours computed 10 minutes to several hours after it (`run_at`). This lane
measures how fast the edge decays with entry delay, on data the author has already seen at zero delay.

## What the author had seen
All R197/R198 results at zero delay (combined book in-sample +42.6%/yr t 3.25; holdout +103.8% t 1.22; top_vs_crowd
alone holdout +89.3% t 2.72). No delayed variant of any flow book has been computed. Both windows' outcomes are known,
so nothing here is a confirmation; it is a sensitivity measurement.

## Books (as R198: 72 h slices, size 1 / (72 x 9.316), universe hedge, tier costs, funding)
- **A:** the three cells summed: top_vs_crowd, taker[24], taker[4], xs8 bin 0, short.
- **B:** top_vs_crowd bin 0 short alone, same unit (as R200's book B).
- Delay d hours: a slice whose signal is at row t opens at row t + d, if the symbol is eligible at t + d. d = 0 is the
  known reference; **d = 1 and d = 2 are the trials**.

## Windows
In-sample 2021-01-01..2025-06-30 and holdout 2025-07-01..2026-09-30, each run with 72 h warm-up so live slices carry in.

## Reported
For each book, window, d in (0, 1, 2) and costs 1x/2x/3x: mean bp/day, NW t (lag 10), total, max DD, gross and cost
per day. The share of the d = 0 net lost per hour of delay, (net_0 - net_1) / net_0.

## Reading rule (fixed now)
- If book A's in-sample 1x net loses **25% or more** at d = 1, R200's paper result is flagged optimistic in MAP and the
  delayed twin R214 is the operational read of the forward test.
- The 12-minute loss is **not measured** here (hourly data); a linear-decay guess of 0.2 x the 1 h loss may be quoted
  only with that label.

## Multiplicity
Trials = 4 (A and B at d = 1, 2). Program trials before: 9,471,705.

## Expectations
72 h slices are long relative to one hour, so the loss should be small unless the edge is front-loaded in the first
hours after the signal. Guess: A loses 5-15% of its net at d = 1.
