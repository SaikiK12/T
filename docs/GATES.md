# Gates: from an idea to the owner's money

Written 2026-10-20 from `docs/CAPITAL_GATE_REVIEW.md` and the critics in `docs/CRITIQUE.md`. It replaces "go_real
passed" as the meaning of "ready". `lab.gate.go_real()` stays as one step inside gate 2; it is not the decision.

Nothing here changes a frozen PREREG. Lanes frozen before today keep their own rules. This file says how their results
are read and what a new lane must pre-register.

## The funnel

| Gate | Question | Evidence that counts | Who decides |
|---|---|---|---|
| 0. Screen | Is there anything here at all? | Any archive window, including the spent holdout. Labelled **exploratory**. | the loop |
| 1. Research | Does the signal predict, net of costs, on days nobody had seen? | Only on-time forward days after the freeze, or an archive window never read by anyone (another venue, held-back history). | frozen PREREG |
| 2. Execution | Can the owner's venue fill it at the owner's size? | Paper fills at fixed notionals on MEXC contract rules: delay, depth, partials, funding events. `go_real()` runs here. | frozen PREREG |
| 3. Account risk | Can it blow up the account? | Replay on MEXC margin tiers, fair-price liquidation, squeezes and gaps, failed hedges, with gross and per-contract caps set first. | frozen PREREG |
| 4. Owner | Does the owner accept a small, bounded stake? | Gates 1-3 written up, with the max loss stated. | **the owner only** |

A result is named by the highest gate it passed. "In-sample", "holdout" and "replay" are all gate 0. The registry's
`CONFIRMED` on R181, R185, R190, R192, R195 and R197 means in-sample (gate 0). R191 carry passed a single holdout test
at 1x costs, which is also gate 0 now that the holdout is spent.

## Rules for gate 1 (new lanes from 2026-10-20)
- **One decision per signal.** Lanes that share cells (R200, R214, R215, R218, R225 all use the same flow cells) are
  diagnostics of one signal, not separate chances. A new lane names which decision it feeds.
- **Days counted:** strict on-time days only (every hour computed within 60 minutes, `scripts/forward_lag.py`).
  Replayed days are reported, never counted.
- **Test:** a one-sided test whose threshold is calibrated by simulation under a dependent null (block bootstrap of
  the lane's own archive returns with the mean removed), not a hit rate. Report the trimmed mean (top and bottom 10
  days removed) and a leave-two-coins-out mean next to the plain mean.
- **Power:** the PREREG states the days needed for 80% power at the Sharpe it expects. If that is longer than the
  decision date below, the lane says so and is labelled a futility screen.

## Rules for gate 2
- `go_real()` at the PREREG's day count, never earlier. `forward_tick.py` now writes `verdict: PENDING` until day 90.
- Costs at 1x, 2x and 3x of MEXC's measured cost (R224), plus the API fee of 6 / 8 bp in force since 2026-06-01.
- A book the owner cannot place by hand (50 coins, hourly slices) needs a daily-netted version of 15 orders or fewer,
  frozen as its own lane before it is scored.

## Rules for gate 3
To be set before any result is read, in the lane's PREREG:
- max gross exposure and max per-contract notional (per MEXC risk tier);
- daily stop and account drawdown stop;
- the replay of margin and liquidation on fair price for every day of the paper record.

## Gate 4: what the owner sets (proposals, not decisions)
The owner fills these in; the lab proposes, it does not decide.
- **Small stakes**: proposed at most 2% of the account's trading capital per book, and no single contract above its
  MEXC base risk tier.
- **Max loss**: proposed hard stop at 25% of the stake; the book is switched off and re-registered after that.
- **Calibration orders**: the strategy critic proposes 20-30 tiny live orders to measure real fills against paper.
  That would be a carve-out from rule 6 of `AGENTS.md` and only the owner can grant it.

## Dates
- **2027-01-18**: first 90-on-time-day looks for R215, R218 and R220 (R221's futility look). A book with t <= -2 stops.
- **2027-01-31**: lane count frozen. No new forward lane on the flow cells after this date unless one passes gate 1.
- **2027-04-20**: review of the whole program against this file. If nothing has passed gate 1, the search is
  re-budgeted towards event lanes and other markets, and the review is written up for the owner.
- **2027-10-20**: R221's last look (365 days).
