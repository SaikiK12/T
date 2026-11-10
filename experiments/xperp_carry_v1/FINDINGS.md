# FINDINGS: xperp_carry_v1 (R441), gate 0

**Gate 0 is reported and decides nothing.** The lane runs on to gate 1, which is forward from 2026-11-11. It is
read by `.github/workflows/claude-xperp-reads.yml`: weekly status reads, then the frozen decision once 2027-02-08
and 2027-05-09 have passed.

- **Frozen:** PREREG sha256 `437fc80d…`, before any statistic.
- **Data:** commit `013dc728946cc5cf7c3177050a01ae7167049826` of `claude/okx-xperp-data`, the recorder's first run
  (2026-11-10 17:58 UTC, 0 failures, 263 X-Perps, 129 spot pairs).
- **Run:** `python scripts/run_xperp_carry.py --data <worktree at that commit> --window gate0`. Output is in
  `results/gate0/` (daily.csv, trades.csv, report.json).

## Gate 0: 2026-08-20..2026-11-10, 83 days, survivor universe, seen cross-section
| Cost | Net on capital, %/yr | Excess over 4.0%, points | NW t (lag 10) |
|---|---|---|---|
| 1x | +5.37 | +1.37 | 0.62 |
| 2x | +3.75 | −0.25 | −0.09 |
| 3x | +2.14 | −1.86 | −0.52 |

- **Parts, at 1x on capital:**
  - funding received: +7.90%/yr;
  - price (−Δmark + Δspot): −0.92%/yr;
  - costs: −1.61%/yr.
  - Funding on capital is about +11.9%/yr on notional (capital is 1.5 × notional), in line with R430's seen median
    of about 10.4%.
- **Book:**
  - 10 slots full from day 1;
  - 16 entries, 6 exits, 0 forced;
  - mean hold of the closed positions 11.5 days;
  - worst day −0.32% of capital; maximum drawdown −0.34%.
- **Halves:** +4.29 and +6.42%/yr net at 1x. Both are positive, but only the second clears the hurdle.
- **Top-10-day share: 205%.** The ten best days carry more than the whole net. This is noise around a small mean, not
  a steady accrual.
- **Read:** before the hurdle, the book earns roughly what the funding median promised, less costs. After the 4%
  T-bill hurdle it is barely positive at 1x and gone at 2x. This is the same picture as R430's BTC/ETH null, on a
  wider universe. The window and the universe were seen, so this decides nothing.

## Power: can gate 1 decide?
- **Frozen statistic** (daily sd of the excess, no autocorrelation adjustment): sd 0.138% a day. The detectable annual
  excess at t 2.5 with 80% power is +17.7 points at 90 days and +12.5 points at 180.
- **Why that overstates it:** the daily noise is almost all price, i.e. mark-versus-spot basis at the 00:00 close.
  - sd of price 0.137% against sd of funding 0.011%;
  - the price part has lag-1 autocorrelation −0.59, so it mean-reverts.
- **Long-run sd implied by gate 0's NW t:** about 0.055% a day. With it:
  - t 2.0 at 90 days needs about +4.2 points;
  - t 2.5 at 180 days needs about +3.7 points, or about +5.0 points with 80% power.
  - This is a reported diagnostic, not a frozen number.
- **So:** gate 1 can decide only if the forward excess is about three times gate 0's +1.4 points. At gate 0's level,
  the likely path is CONTINUE at 90 days and NULL at 180. That NULL would mean "not shown at this power", not "no
  edge".

## Program
- One trial; program total 9,784,985 with R442 (`registry.program_trials()`).
- At t 0.62, nothing here survives any multiplicity reading.

## Limits
- **Survivor universe:** the 2026-11-10 listing only.
- **Seen cross-section:** R430's report, the reason this gate decides nothing.
- **No measured costs:** books start 2026-11-10, so gate 0 charged 5 bp impact per leg.
- **Fills:** at daily closes (mark and spot last trade). No live fills.
- **Venue access:** OKX's own guide says X-Perps are open in all 30 EEA countries (France included) with KYC and an
  appropriateness test, but no register entry for a French passport was reached (`docs/reviews/venue_access_fr_20261110.md`).
- **Not checked:**
  - whether the X-Perp funding-like payment stays as recorded;
  - transfer and custody costs;
  - EUR/USD on EUR-quoted spot legs.
