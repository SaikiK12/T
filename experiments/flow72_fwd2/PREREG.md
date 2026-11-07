# PREREG: flow72_fwd2 (R200), forward paper test of the 72 h flow slice book and of top-vs-crowd alone

Freeze with `lab.prereg.freeze()` before the first forward mark is computed. Never edited afterwards; a change is a new
lane. Paper only: no orders, no keys, no money. Supersedes flow72_fwd (R199), abandoned when its data gate failed for
coverage reasons (see experiments/flow72_fwd/FINDINGS.md).

- **Registry id:** R200
- **Owner (single writer):** the session that froze it; the journal is written only by `scripts/forward_tick.py`
- **Code:** `lab/live.py`, `lab/flowfeat.py`, `lab/slices.py`, `lab/gate.py`, `scripts/live_parity.py`,
  `scripts/forward_tick.py`

## What the author had seen
flow72_v2 (R197, in-sample PASS, +42.6%/yr net, t 3.25); flow72_holdout (R198, 2025-07-01..2026-09-30: +104% over
457 days, t 1.22, NOT CONFIRMED; top_vs_crowd alone t 2.72, max DD 16%, reported only); R199's parity diagnosis on
archive rows 2026-09-24..30 (data only). **No return, price path or flow value after 2026-09-30 has been looked at
for these cells**, apart from format probes of a few BTCUSDT rows on 2026-10-19 and the klines cached for the rank
check (prices fetched, not read or summarized).

## Data gate (before any mark)
`scripts/live_parity.py --lane flow72_fwd2` on archive rows 2026-09-24..2026-09-30 with archive eligibility, live rows
put on the archive's clock by the stamp shifts it selects per endpoint. **Gate: for top_vs_crowd, taker[4] and
taker[24] xs8, the live bin equals the archive bin in >= 99% of the eligible cells the archive binned, with live raw
values kept only where the archive has them** (`bins_common`). The comparison with every live coin (`bins`) and the
top-50 overlap of the live rank are reported, not gated. If the gate fails, nothing starts; a fix is a new lane.

## Frozen rules (R197's construction on live data)
- Universe: USDT-margined `PERPETUAL` and `TRADIFI_PERPETUAL` contracts trading on Binance USD-M (exchangeInfo at each
  tick); rank by the sum of the last 720 hourly quote volumes; tradable = rank <= 50 with a close in the hour. Coins
  delisted before a tick are absent from its universe (disclosed). Tier costs 6/8/12/20 bp one way by rank.
- Hour t = the bar [t, t + 1 h). Live 5-minute rows, moved onto the archive's clock by the gate's shifts, reduced to
  hours as `lab/flow.reduce_metrics` (ratios averaged over the hour, OI at its last row). Features and xs8 bins by
  `lab/flowfeat.py` on the tradable set at t, every coin with data included (also non-ASCII names). An hour is
  computed once the bar has closed and at least 12 minutes have passed.
- **Book A (primary):** cells top_vs_crowd/xs8 bin 0, taker[24]/xs8 bin 0, taker[4]/xs8 bin 0; side short; a slice of
  1 / (72 x 9.316) per (hour, coin, cell) in the cell, closed 72 h later; position set at the close of t, earns
  close[t+1] / close[t] - 1 and the funding settled in the next bar; tier cost on every change of position; hedge:
  long the equal-weighted basket of tradable coins for the book's net short exposure (idealized, as R197/R198).
- **Book B:** top_vs_crowd/xs8 bin 0 alone, same construction.
- Forward period: **from 2026-10-01 00:00 UTC**, starting flat. Hours before 2026-10-19 come from the live endpoints'
  history (about 28 days kept) and are flagged `late`; hours a tick misses are filled on the next run while the data
  exist (flagged); hours that can no longer be computed are recorded as missing, never invented.

## Tickets and scoring
- One ticket per book per complete UTC day: the day's net return (sum of hourly book returns at 1x costs), as an
  unlevered fraction of capital. Journals (append-only, committed): `journal/signals.csv`, `journal/ticks.csv`,
  `journal/tickets.csv`; `journal/status.json` is rewritten each tick.
- Checkpoints at 30, 60 and 90 scored days: `lab.gate.go_real` on each book's daily tickets, NW t (lag 10), annualized
  mean, max drawdown, hit rate, 2x and 3x costs, top-10 and BTC hedges.

## Decision (at 90 scored days, 2026-12-29 at the earliest)
- A book **PASSES** when `lab.gate.go_real` passes on its 90 daily tickets (>= 20 scored, mean > 0, hit >= 0.55, worst
  day >= -40%) **and** its NW t (lag 10) >= 2. Book A is the primary; book B is the second of two trials.
- A pass makes a small real stake *possible*; the owner decides and places any order (AGENTS.md rules 5 and 6).
- Stop rule: if book A's cumulative daily net falls 50% below its running peak, the test stops and is recorded NULL.

## Multiplicity
Trials = 2 (books A and B). R199 ran none. Program trials are read alongside.

## Expectations (written before any forward data)
Ninety days of a book with a Sharpe near 1 give a t near 0.5 to 1 on average, so a PASS at 90 days is unlikely even if
the edge is real; book B (smoother on the holdout) has the better chance. The likely outcome is "not decided", and the
monitor should continue past 90 days under a new id if promising.
