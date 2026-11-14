# FINDINGS: llpstake_v1 (R447), gate 0

**CONTINUE to gate 1, by the frozen rule (1x excess not below 0).** Gate 0 can only stop this lane, and it does not.
It decides nothing in favour: LLP's own return over the window was seen in R446. Gate 1 runs forward from
2026-11-11. `.github/workflows/claude-xperp-reads.yml` writes weekly status reads, then the frozen decisions once
2027-02-08 and 2027-05-09 have passed.

- **Frozen:** PREREG sha256 `e4340b8d…`, after R446's gate 0 and before any LIT funding figure was read.
- **Data:** commit `cb048a9130ad656500f4eacbfea5cdc1651ff132` of `claude/okx-xperp-data` (the first with `lit/`).
- **Run:** `python scripts/run_llpstake.py --data <worktree at that commit> --window gate0`. Output is in
  `results/gate0/` (daily.csv, report.json).

## Gate 0: 2026-01-15..2026-11-10, 300 days, one unit rebalanced daily
| Cost | Net on capital, %/yr | Excess over 4.0%, points | NW t (lag 10) |
|---|---|---|---|
| 1x | +10.04 | +6.04 | 3.94 |
| 2x | +9.91 | +5.91 | 3.86 |
| 3x | +9.78 | +5.78 | 3.77 |

- **Parts of the 1x net, on the whole capital:**
  - LLP: +7.65%/yr;
  - staking: +0.85%/yr;
  - funding received by the short: +1.65%/yr;
  - basis between the spot stake and the perp short: +0.02%/yr;
  - costs: −0.13%/yr.
- **Capital:**
  - LLP held 72% of capital on average: 84% in April, when LIT was cheap, and 53% in September.
  - The unit's capital ran from 11.6 to 20.6 USDC, so LIT traded between about $0.8 and $5.3.
- **Risk:**
  - worst day −0.32% of capital (2026-03-09, an LLP loss);
  - maximum drawdown −0.35%;
  - no liquidation of the short; one missing day (2026-11-10, the last bar was not finished).
- **By month, net %/yr at 1x:** Jan +12.8 (17 days), Feb +9.4, Mar +0.7, Apr +10.3, May +9.9, Jun +12.0, Jul +10.1,
  Aug +17.9, Sep +9.1, Oct +9.9, Nov +9.1 (10 days). Only March, when LLP itself was flat, fell below the hurdle.
- **The stake without the short (reported, not deciding):** +22.9%/yr, with a daily sd of 1.15%, nineteen times the
  hedged book's. That figure is LIT's price path, not a return a depositor can count on.

## Funding sign: checked
- Lighter's funding page (read 2026-11-10): "When the funding rate is positive, users with long positions pay a
  funding fee to users with short positions." Its formula adds an interest rate of 0.01% per 8 hours, about 11%/yr
  paid by longs when the premium is zero.
- Under the recorder's reading of the API's `direction` field, funding was positive on 90% of days. It came to about
  12.3%/yr on the short's notional, close to that interest baseline. The opposite reading would make shorts pay on
  most days, against the documented formula.
- The signed rate also moves with the perp's premium over spot (correlation +0.18 by day).

## Power: can gate 1 decide?
- Daily sd of the excess: 0.061%. The detectable excess (t 2.5, 80% power) is +7.9 points at 90 days and +5.6 at
  180.
- At gate 0's level (excess +6.0), the expected t is about 2.6 at 90 days and 3.6 at 180. EARNED at 90 days then has
  about seven chances in ten, and CONFIRMED at 180 nearly nine in ten, **if no crash day falls in the window**.
- The window holds no day like LLP's 2025-10-11 (−5.35% of the pool):
  - In this book, such a day would cost about 3.8% of capital, because LLP is about 72% of it. That stays inside
    gate 1's −5% drawdown limit.
  - Over 180 days, it would still cut the annualized excess by about 7.8 points, enough to end the lane.

## Against R446
- R446's LLP book (per USDC in the pool) made +10.80%/yr in 2026.
- Held as a depositor must hold it, with the stake and the short, the same pool makes +10.04%/yr on all the capital.
  - The stake and the margin dilute LLP's return.
  - The staking reward and the short's funding (+2.5 points together) make most of it back.
  - The hedge keeps LIT's price out: the basis part is +0.02%/yr.
- So the stake requirement costs about 0.8 points a year and removes about a quarter of LLP's tail per unit of
  capital.

## Program
- One trial; program total 9,784,991 (`registry.program_trials()`).
- Gate 0 is a seen read for LLP's part (R446). Its t of 3.94 is not evidence on its own.

## Limits
- **LLP's tail:** the window starts after the 2025-10-11 crash. The forward window may hold none, or one that ends
  the lane.
- **LIT's tail:**
  - LIT is Lighter's own token, so a venue failure hits the pool, the stake and the hedge at once.
  - The liquidation check uses daily highs and an assumed 20% maintenance margin. No day came near the trigger.
    Lighter's LIT margin tiers were not read.
- **Staking:** the 6% "currently" fixed rate is assumed for the whole window, paid daily. Its history and payment
  schedule were not read.
- **Requirement date:** the start date rests on a secondary source.
- **Funding:** it is the short's main extra. If LIT's longs stop paying the interest baseline, about 1.6 points go.
- **Clocks:** LLP's stamps fall near 20:00 UTC; funding and bars run by UTC day.
- **Jurisdiction:** Lighter's terms, as read, do not exclude France. That is not legal advice, and the owner checks.
- **Forward reads:**
  - A look reads every calendar day to the look date. A day with no data is booked at 0 and counted as missing,
    which pulls the excess toward −4 points.
  - The default end is the last day every input covers.
