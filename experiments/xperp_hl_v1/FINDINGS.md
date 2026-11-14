# FINDINGS: xperp_hl_v1 (R443), gate 0

**Gate 0 is reported and decides nothing.** The lane runs on to gate 1, forward from 2026-11-11. It is read by
`.github/workflows/claude-xperp-reads.yml`: weekly status reads, then the frozen decision once 2027-02-08 and
2027-05-09 have passed.

- **Frozen:** PREREG sha256 `fdfa3131…`, before any OKX-Hyperliquid spread statistic.
- **Data:** commit `8b0116763d2372d9ee54aa31f584edc050261068` of `claude/okx-xperp-data`, the first recorder run with
  `hl/` (2026-11-10 19:06 UTC, 0 failures, 97 Hyperliquid coins matched to OKX crypto X-Perps).
- **Run:** `python scripts/run_xperp_hl.py --data <worktree at that commit> --window gate0`. Output is in
  `results/gate0/` (daily.csv, trades.csv, report.json).

## Gate 0: 2026-08-20..2026-11-10, 83 days, survivor universe, seen funding
| Cost | Net on capital, %/yr | Excess over 4.0%, points | NW t (lag 10) |
|---|---|---|---|
| 1x | +0.95 | −3.05 | −0.55 |
| 2x | −13.63 | −17.63 | −2.45 |
| 3x | −28.21 | −32.21 | −3.60 |

- **Parts, at 1x on capital:**
  - funding spread received: +14.43%/yr;
  - price (the two legs' closes): +1.09%/yr;
  - costs: −14.58%/yr.
- **Why costs eat it: turnover.**
  - Each slot's round trip costs 39 bp of its notional at 1x. That is fees of 5 + 4.5 bp a side, plus 5 bp impact
    per leg and side.
  - The spread between the two venues flips fast, so the book trades about once a day across its 10 slots: 90
    entries, 80 exits, mean hold of the closed positions 7.7 days (median 7).
  - 57 different pairs were held.
  - The 10%/yr entry spread over a week's hold earns about 19 bp, against 39 bp of cost.
- **Direction split:** 48 entries short OKX / long Hyperliquid, and 42 short Hyperliquid / long OKX. No side dominates.
- **Book:**
  - 10 slots full on 68 of 83 days;
  - 0 forced exits;
  - worst day −0.29% of capital; maximum drawdown −1.41%.
- **Halves:** −9.4 and +11.1%/yr net at 1x. The sign flips between halves.
- **Top-10-day share: 1,019%.** The net is a small number made of large, offsetting days.
- **Read:** the spread exists and is large before costs, but it does not persist long enough to pay a taker round trip
  on both venues. This is the same failure as R442 (stock X-Perps): funding above the entry band lasts about a week
  or two. A cheaper execution (maker on both legs) or a wider hold band would be a new lane, read against this one.

## Power: can gate 1 decide?
- **Frozen statistic** (daily sd of the excess): 0.109% a day. The detectable annual excess at t 2.5 with 80% power
  is +14.0 points at 90 days and +9.9 points at 180.
- **Noise:**
  - the price part has sd 0.079% a day with lag-1 autocorrelation −0.53, so it mean-reverts;
  - the funding part has sd 0.066% a day.
- **Long-run sd implied by gate 0's NW t:** 0.138% a day, which makes the detectable excess +17.7 and +12.5 points.
- **So:** gate 1 cannot decide in favour at anything near gate 0's level. At gate 0's level (excess −3), the frozen
  rule reads NULL (stop) at 90 days if the forward excess is still below 0.

## Program
- One trial; program total 9,784,986 (`registry.program_trials()`).
- At t −0.55, nothing here is a result in either direction.

## Limits
- **Survivor universe:** the 2026-11-10 OKX listing and Hyperliquid's coins matched on that day.
- **Seen funding:** on both venues, the reason this gate decides nothing.
- **No measured OKX costs:** books start 2026-11-10, so gate 0 charged 5 bp impact per leg.
- **Fills:** at daily closes (OKX marks, Hyperliquid last trades). No live fills.
- **Margin on two venues:** not modelled; transfers between venues are not costed.
- **Venue status:** Hyperliquid is authorised nowhere; OKX Europe's X-Perp access for a French resident is unconfirmed
  by a register.
