# FINDINGS: dexvault_v1 (R446), gate 0

**Both books CONTINUE to gate 1, by the frozen rule (1x excess not below 0).** Gate 0 can only stop a book, and it
stops neither. It decides nothing in favour: both vaults' public APRs were known in general before the freeze.
Gate 1 runs forward from 2026-11-11, book by book. `.github/workflows/claude-xperp-reads.yml` writes weekly status
reads, then the frozen decisions once 2027-02-08 and 2027-05-09 have passed.

- **Frozen:** PREREG sha256 `11334fdc…`, before any figure of either vault's return series was read.
- **Data:** commit `55a0b58ef5b8d388ff86e7fcc2f58239591b93e2` of `claude/okx-xperp-data`: one HLP snapshot (fetched
  2026-11-10) and LLP's daily share prices from 2025-01-16.
- **Run:** `python scripts/run_dexvault.py --data <worktree at that commit> --window gate0`. Output is in
  `results/gate0/` (hlp_periods.csv, llp_periods.csv, report.json).

## Gate 0: 2025-01-01..2026-11-10
| Book | Periods | Cost | Net on capital, %/yr | Excess over 4.0%, points | NW t |
|---|---|---|---|---|---|
| HLP (lag 4) | 52, median 14 days | 1x | +14.30 | +10.30 | 1.87 |
| | | 2x | +14.20 | +10.20 | 1.85 |
| | | 3x | +14.10 | +10.10 | 1.83 |
| LLP (lag 10) | 662 days | 1x | +73.26 | +69.26 | 3.16 |
| | | 2x | +73.16 | +69.16 | 3.16 |
| | | 3x | +73.06 | +69.06 | 3.15 |

Costs barely matter here: one round trip a year is 10 bp of capital at 1x.

## The headline is not the level to expect. Read this first
- **LLP's +73%/yr comes from its first months.** Net %/yr by quarter (1x):

  | | Q1 | Q2 | Q3 | Q4 |
  |---|---|---|---|---|
  | 2025 | +441.7 | +82.3 | +54.6 | −0.7 |
  | 2026 | +6.5 | +10.6 | +15.2 | +10.8 (40 days) |

  - 2025: +129.3%/yr (NW t 3.22). 2026: +10.80%/yr, an excess of +6.80 points (NW t 3.27 at lag 10).
  - Last 365 days: +10.65%/yr; last 180: +12.83; last 90: +15.79.
- **HLP is lower and noisier in 2026.**
  - 2025: +17.45%/yr (NW t 1.73). 2026: +10.65%/yr, an excess of +6.65 points (NW t 0.89).
  - By quarter: +11.7, +10.6, +10.2, +35.9 in 2025; +32.4, −1.5, +2.9, +13.6 in 2026 (the last quarter is 4 periods).
  - Last 365 days: +8.38%/yr; last 180: +4.81; last 90: +8.69.
- These splits are reported, not deciding, and they are read on the window that also gave the headline.

## Tail
- **LLP:**
  - Worst day −6.73% (2025-03-03). Maximum drawdown −9.11% (2025-03-02 to 2025-03-05).
  - 13 days below −1%, all but one before 2025-06.
  - That one is 2025-10-11: −5.35%. Its stamp (about 20:00 UTC) covers the crash of 2025-10-10. Since 2025-04, it is
    the largest drawdown. That quarter netted −0.7%/yr.
  - LLP backstops liquidations. A crash day turns its steady gain into a loss of several months' return.
- **HLP:**
  - Worst period −0.80% (14 days to 2025-11-12). Maximum drawdown −0.80% (2025-10-29 to 2025-11-12).
  - At two-week resolution, losses inside a period net against its gains. Gate 0 sees neither the 2025-03 loss
    events nor intraday swings at their size.
- **Gate 1's drawdown condition** (1x cumulative drawdown above −5%) fails if one day like LLP's 2025-10-11 falls in
  the forward window.

## Power: can gate 1 decide?
- **LLP:**
  - Daily sd: 1.02% on the whole window, 0.080% in 2026.
  - Detectable excess (t 2.5, 80% power) at 2026's sd: +10.3 points at 90 days and +7.3 at 180. On the whole
    window's sd: +131 and +93.
  - At 2026's level (excess +6.8, sd 0.080%), the expected t is about 2.2 at 90 days and 3.1 at 180. EARNED at 90
    days then has roughly an even chance, and CONFIRMED at 180 about seven in ten, if no crash day falls in the
    window.
  - This is the first France-reachable vault return in this program that gate 1 can plausibly confirm at its recent
    level. It is not yet a book a depositor can hold as measured (next section).
- **HLP:**
  - Daily sd from the snapshot's last 30 days (`month` window, gate 1's measure): 0.21%.
  - Detectable excess: +27 points at 90 days and +19 at 180.
  - At 2026's excess (+6.7) the expected t at 180 days is about 1.1. Gate 1 will most likely read CONTINUE at 90 days
    and NULL at 180. A NULL would not rule out a true excess of several points.

## LLP needs staked LIT: what a real deposit would hold
Read after the gate-0 run, from Lighter's docs (fetched 2026-11-10):
- "the Lighter Liquidity Pool (LLP) is now exclusively accessible to LIT stakers."
- "For every 1 LIT staked, participants may deposit up to 10 USDC into the LLP."
- "Staking participants currently earn a fixed 6% APR through staking rewards."
- "Unstaking is subject to a 3-day lockup period."
- The LLP withdrawal cooldown is 5 minutes (`liquidity_pool_cooldown_period = 300000` ms).
- A news report (The Block, 2026-01-14, secondary) dates the requirement to 2026-01-14 for new depositors. It gives
  existing ones a grace period to 2026-01-28.

Consequences:
- R446's LLP book is the vault's return per USDC deposited. A real deposit of D USDC also holds D/10 LIT, staked.
  The capital is D plus the stake's value, and the stake carries LIT's price unless it is hedged.
- The frozen rule does not model this, and it stays as frozen. Its gate-1 reads remain the vault's own return, with
  the stake outside the book.
- A book that holds the stake, hedged or not, is a new idea. It needs its own lane, frozen before any LIT price or
  funding series is read.
- HLP has no such requirement in the docs read; its deposit caps and minimum were not confirmed.

## What the PREREG got wrong, without changing the rule
- It describes HLP's `allTime` points as "about a week apart". In the gate-0 snapshot the median step is 336 hours
  (14 days): 103 points from 2023-05-10. The rule uses consecutive points whatever their spacing, so nothing changes.
  Lag 4 then spans about eight weeks rather than four.

## Program
- Two trials (two books); program total 9,784,990 (`registry.program_trials()`).
- Gate 0 is a seen read in the sense that the vaults' public APRs were known in general. Its t values are not evidence
  on their own.

## Against the other France-reachable books
- R441-R445 and R288 earn about the hurdle at 2026's level. The best, R445 (HYPE/BTC spot-perp under portfolio
  margin), made +4.15%/yr in 2026.
- LLP made +10.80%/yr in 2026 and HLP +10.65%/yr, both with no trading by the depositor.
- That is not a free return: the depositor is short the venue's tail, and LLP also needs a LIT stake (above). LLP
  gave back about six months of its 2026 rate on 2025-10-11, and HLP's history holds loss events the gate-0
  resolution hides.

## Limits
- **Tail risk:** a vault's loss days are rare and large. Gate 0 holds one crash for LLP after its first months; the
  forward window may hold none, or one that ends the book.
- **Venue risk:**
  - Both are smart-contract venues, authorised nowhere.
  - HLP has a 4-day lock-up, and withdrawals from either can be delayed or halted.
  - LLP takes deposits only against staked LIT (section above). Pool-wide caps and minimum deposits were not
    confirmed for either vault.
- **HLP's measure:**
  - The parent vault's own account value and pnl, as the app shows them.
  - Flows are assumed to fall at period ends.
  - Gate 0 has two-week resolution.
- **LLP's early months:** the share price rose fastest while the pool was small. That level is not available to a
  new deposit.
- **Different clocks:** HLP's days run 00:00-00:00 UTC; LLP's stamps fall near 20:00 UTC.
- **Jurisdiction:** neither venue's terms, as read, exclude France. That is not legal advice, and the owner checks.
- **Forward reads:**
  - A look reads every calendar day to the look date. A day with no data is booked at 0 and counted as missing,
    which pulls the excess toward −4 points.
  - The default end of a read is the last day both books cover.
