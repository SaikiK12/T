# PREREG: itsm_v1 (R203), intraday time-series momentum: does the day's first hour predict its last?

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R203
- **Owner (single writer):** the session that froze it
- **Code:** `scripts/run_itsm.py`
- **Source claim:** `docs/CLAIMS.md` C13 (Shen, Urquhart, Wang 2022, *Financial Review*: with a volume-defined day, the
  first half-hour return predicts the last half-hour return of Bitcoin).

## What the author had seen
The claim and its paper's abstract; the lab's atlas (R185): "day open" views (price vs today's open) replicate as mean
reversion over the next hours, and market clocks alone predict nothing. No statistic of this rule has been computed.

## Rule
- Day = 00:00-24:00 UTC (primary) or a volume clock: the day starts at the coin's hour of lowest mean quote volume over
  the previous 30 days (recomputed daily from past data only).
- Signal: the sign of the day's first hourly return (bar 1 of the day, known at its close).
- Trade: at the close of bar 23, take that sign in the coin; close at the close of bar 24 (the day's last hour).
  Return = the next-bar return as in the lab (funding included); cost = two tier one-way costs (6/8/12/20 bp by rank).
- Universes: BTCUSDT (primary), ETHUSDT, and the 10 most liquid coins at the day's start (equal weight).

## Periods and decision
Discovery 2021-01-01..2023-12-31, validation 2024-01-01..2025-06-30, holdout 2025-07-01..2026-09-30.
- **Gate 1:** primary (BTC, UTC day) gross daily mean > 0 with NW t (lag 5) >= 2 on discovery, **and** the same on
  validation. If gate 1 fails, the lane is NULL and the holdout is not read.
- **Holdout (one shot, only after gate 1):** CONFIRMED if the primary's net daily mean at 1x costs is > 0 with NW t
  >= 2. Otherwise NULL.

## Reported (not decided on)
ETH and top-10; the volume clock; net at 1x/2x/3x; hit rate; per year; the "opposite" reading (does the first hour
predict a reversal in the last hour, as the lab's day-open mean reversion would suggest).

## Multiplicity
Trials = 6 (2 day definitions x 3 universes). Primary = 1.

## Expectations (written before running)
Hourly bars are coarser than the paper's half-hours; the last-hour return of BTC is a few bp in magnitude while a round
trip costs 12 bp, so even a real gross effect is unlikely to survive costs. Gate 1 more likely fails than passes.
