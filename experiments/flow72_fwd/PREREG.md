# PREREG: flow72_fwd (R199), forward paper test of the 72 h flow slice book and of top-vs-crowd alone

Freeze with `lab.prereg.freeze()` before the first forward mark is computed. Never edited afterwards; a change is a new
lane. Paper only: no orders, no keys, no money.

- **Registry id:** R199
- **Owner (single writer):** the session that froze it; the journal is written only by `scripts/forward_tick.py`
- **Code:** `lab/live.py`, `lab/flowfeat.py`, `lab/slices.py`, `lab/gate.py`, `scripts/live_parity.py`,
  `scripts/forward_tick.py`

## What the author had seen
flow72_v2 (R197, in-sample PASS, +42.6%/yr net, t 3.25) and flow72_holdout (R198, 2025-07-01..2026-09-30: +104% over
457 days, t 1.22, NOT CONFIRMED; top_vs_crowd alone t 2.72, max DD 16%, reported only). The archive ends 2026-09-30.
**No return, price path or flow value after 2026-09-30 has been looked at for these cells** (the live endpoints were
only probed for format on 2026-10-19: a handful of BTCUSDT rows). `scripts/live_parity.py` was written and started
before this file was frozen; its output had not been read.

## Data gate (before any mark)
`scripts/live_parity.py` rebuilds, from the live public endpoints, the hourly metrics and the xs8 bins of
top_vs_crowd, taker[4] and taker[24] on archive rows 2026-09-24..2026-09-30 (archive eligibility). **Gate: for each of
the three specs, the live bin equals the archive bin in >= 99% of the eligible cells the archive binned.** If any spec
is below 99%, the forward test does not start; the cause is reported and a fix is a new lane. The rank rebuilt from
live klines is reported, not gated (the live list lacks coins delisted since).

## Frozen rules (R197's construction on live data)
- Universe: USDT perpetuals trading on Binance USD-M (exchangeInfo now); rank by the sum of the last 720 hourly quote
  volumes; tradable = rank <= 50 with a close in the hour. Tier costs 6/8/12/20 bp one way by rank (`engine.cost_matrix`).
- Hour t = the bar [t, t + 1 h). Live 5-minute rows reduced to hours as `lab/flow.reduce_metrics` (ratios averaged over
  the hour, keyed by the hour that contains the row; taker rows aligned by the shift the parity check selects).
  Features and xs8 bins by `lab/flowfeat.py` on the tradable set at t. An hour is computed once the bar has closed and
  at least 6 minutes have passed.
- **Book A (primary):** cells top_vs_crowd/xs8 bin 0, taker[24]/xs8 bin 0, taker[4]/xs8 bin 0; side short; a slice of
  1 / (72 x 9.316) per (hour, coin, cell) in the cell, closed 72 h later; position set at the close of t, earns
  close[t+1] / close[t] - 1 and pays/receives funding settled in the next bar; tier cost on every change of position;
  hedge: long the equal-weighted basket of tradable coins for the book's net short exposure (idealized, as R197/R198).
- **Book B:** top_vs_crowd/xs8 bin 0 alone, same construction.
- Forward period: **from 2026-10-01 00:00 UTC** (the first hour after the archive; not read before), starting flat.
  Hours before this file's freeze date are computed from the live endpoints' history (they keep about 28 days) and
  flagged `late`; they are as unseen as later hours. Hours the tick misses are filled on the next run from the same
  endpoints (also flagged) as long as the data are still available; hours that can no longer be computed are recorded
  as missing, never invented.

## Tickets and scoring
- One ticket per book per complete UTC day: the day's net return (sum of the hourly book returns at 1x costs), as an
  unlevered fraction of capital. Journals (append-only, committed): `journal/signals.csv` (every tradable coin each
  hour: rank, close, raw hourly metrics, the three bins), `journal/ticks.csv` (one row per computed hour),
  `journal/tickets.csv` (one row per book per day).
- Checkpoints at 30, 60 and 90 scored days: `lab.gate.go_real` on each book's daily tickets, NW t (lag 10), annualized
  mean, max drawdown, hit rate, 2x and 3x costs, and the top-10 and BTC hedges.

## Decision (at 90 scored days, 2026-12-29 at the earliest)
- A book **PASSES** when `lab.gate.go_real` passes on its 90 daily tickets (>= 20 scored, mean > 0, hit >= 0.55, worst
  day >= -40%) **and** its NW t (lag 10) >= 2. Book A is the primary; book B is the second of two trials.
- A pass makes a small real stake *possible*; the owner decides and places any order (AGENTS.md rules 5 and 6).
- Stop rule: if book A's cumulative daily net falls 50% below its running peak, the test stops and is recorded NULL.

## Multiplicity
Trials = 2 (books A and B). Program trials (507,088 before this lane) are read alongside; this is the first lane
whose data were not available when its rule was chosen.

## Expectations (written before any forward data)
In-sample +42.6%/yr, holdout +83%/yr with far higher variance (t 1.22). Ninety days of a book with a daily Sharpe near
1 give a t near 0.5 to 1 on average, so a PASS at 90 days is unlikely even if the edge is real; book B (smoother on
the holdout) has the better chance. The likely outcome at 90 days is "positive or negative, not decided", and the
test should continue as a monitor beyond it under a new id if it is promising.
