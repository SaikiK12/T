# PREREG: ltroll_v1 (R481). Did Lighter's funding on its futures-priced commodity perps exceed the roll it paid for?

- **Registry id:** R481
- **Owner (single writer):** Claude, this session (cloud container, 2026-11-12)
- **Date registered (UTC):** 2026-11-12

Method M532 on a second venue. This file is frozen by `lab.prereg.freeze()` and pushed before the fetch
(`scripts/fetch_ltroll.py`) and before any Lighter funding or price value of the window is read. After the freeze it is
never edited; a changed idea is a new lane.

## Question
Lighter prices WTI, NATGAS, BRENTOIL and XCU (copper) from futures. Over business days 5-9 of a roll month its oracle
moves from one contract to the next in 20% steps. In contango that lifts the perp, which perp longs keep. The question is
whether their funding to shorts was larger. On trade.xyz it was: R478's post hoc measured NATGAS funding minus roll at
+1.29% of notional a cycle (sd 1.34, 7 of 8 positive), and R480 now runs it forward.

**The test:** a NATGAS short on Lighter hedged with the futures its oracle references, from listing to the October 2026
roll. Did it earn more than the 13-week bill after costs? NATGAS decides; WTI, BRENTOIL and XCU are reported.

**Arbitrage predicts NULL:** funding ≈ roll-up, so the excess is about minus costs and minus the bill on the idle
margin.

## Why on Lighter, and why this window
- Lighter's roll page (https://docs.lighter.xyz/trading/real-world-assets-rwas/futures-contract-price-rolling-mechanism,
  read 2026-11-12) gives the published 2026 schedule:
  - WTI, NATGAS and XCU at 5:30 PM ET. Each window runs from business day 5 to business day 9; e.g. July 07-08..07-14,
    October 10-07..10-13.
  - WTI and NATGAS move from the next month's contract to the one after (July: Q26 to U26).
  - XCU uses the next of H/K/N/U/Z (August U26 to Z26, November Z26 to H27; no roll in July, September, October or
    December).
  - BRENTOIL is two months ahead (July: U26 to V26), at 7:00 PM ET in the table and 23:59 London in the current
    configuration.
  - This is the same schedule and the same contracts as trade.xyz.
- **"As of 2026-10-22, WTI, NATGAS and XCU use RedStone prices rather than Lighter's rolling source."** RedStone's
  roll is not documented. So the window ends with the October roll's business day 10 (2026-10-14) for every market,
  BRENTOIL included, to keep one window.
- The page's tables start in July 2026. The schedule before July is not documented. That is a risk to the measure
  below, and it is reported, not repaired.
- Lighter's funding (https://docs.lighter.xyz/trading/funding, read 2026-11-12):
  - Hourly.
  - Premium multiplier 1/2 for RWA markets.
  - A small clamp of 0.05% that pulls the premium toward a base interest rate of 0.0032% per 8 h for many RWA markets
    (about 3.5%/yr to shorts when the premium sits inside the clamp).
  - A big clamp of 4% per 8 h.
- Not the same mechanics as xyz, so a second venue is a real replication.
- Fees: Lighter's Standard account is 0/0 (orderBooks lists maker and taker fee 0.0000 for all four markets).

## The measure (`scripts/run_ltroll.py`)
R478's post hoc identity, on Lighter.
- **Marks:** 20:00 UTC on NYSE business days (R478's calendar, `run_rollcarry.bdays`).
  - The perp: the close of Lighter's 1-hour candle ending at the mark.
  - The future: the close of Yahoo's 60-minute bar of the continuous front ending at the mark (NG=F, CL=F, BZ=F,
    HG=F).
  - If either bar is missing, the latest common bar end within 3 hours before the mark is used. Lagged marks are
    counted.
- `r(day) = perp / front − 1`.
  - Before the roll (business day 4), perp and front reference the same contract, so r is the perp's premium.
  - After it (business day 10), the oracle is on the next contract. The front stays on the old one until it expires
    later in the month: NG about 3 business days before month end, CL around the 20th, BZ on the last business day,
    HG 3 business days before month end.
  - So `roll_M = r(BD10) − r(BD4)` is the roll-up the oracle passed to longs in month M.
  - Reported: `roll_wide_M = r(BD12) − r(BD3)`, a wider bracket in case a step fell a day outside business days 5-9.
- **Cycles:** from the business-day-10 mark of M−1 to that of M, for roll months February to October 2026.
  - A cycle starts at the first Lighter candle close if that is later. It is kept only if that start precedes M's
    business-day-4 mark.
  - Expected: NATGAS and BRENTOIL April (from 2026-03-24) to October, 7 cycles; WTI March (from 02-18) to October,
    8; XCU March to October, 8 (its February roll precedes the data).
  - `fund_c` = the sum of Lighter's hourly funding prints in (start, end], signed so that + means longs paid (what
    the short received), on a constant notional.
  - `net_c = fund_c − roll_M` (fraction of notional).
- **Costs, fraction of notional, assumed:**
  - 8 bp when the hedge rolls (4 bp a leg on the weight moved; every month for WTI, NATGAS and BRENTOIL; XCU in
    February, April, June, August and November).
  - 2 bp a cycle for margin re-splits.
  - 9 bp entry in the first cycle and 9 bp exit in the last (perp 5 bp half-spread at 0 fee, futures 4 bp).
  - No measured cost is read: the lab's Lighter book recordings stay with their own runners.
- **Capital:** notional is 3/4 of capital, as in R478 and R480.
  - The hedge is a fully collateralised futures position, so it earns the bill on its 3/4.
  - The perp margin (1/4, USDC) earns nothing.
  - `excess_c(k) = 0.75 × (net_c − k × cost_c) − 0.25 × bill_c`, with the bill from ^IRX (the latest close on or
    before each day) accrued over the cycle.
- **Statistics:**
  - Annualized excess = the sum of `excess_c` / years spanned × 100 (points of capital a year).
  - t = mean / (sd / √n) over cycles, which are about monthly and do not overlap.
  - Reported at 1x, 2x and 3x costs.

## Decision (NATGAS, all its cycles)
- **PASS:** annualized excess ≥ 2 points a year, t ≥ 2.0 and the 2x-cost excess > 0.
- **PARTIAL:** excess > 0.
- **NULL:** otherwise.

These are R478's and R480's thresholds.

**Reported, not decided:**
- WTI, BRENTOIL and XCU.
- For each market, the cycles in Lighter's documented months (July-October) and the wide-bracket measure.
- Per cycle: funding, roll, r(BD4) and r(BD10), lagged marks, missing funding prints, the share of hours shorts paid,
  the bill, and `max_up` (the perp's highest 1-hour close over the cycle's starting close).
  - `max_up` stands in for a margin check. At M = 1/3 a rise of about 25% within a cycle needs a re-split before
    liquidation; re-splits are only charged as the 2 bp allowance.

## What a result earns
- **PASS:** M532 replicated on a second venue (historical, identity measure).
  - It earns no forward lane on Lighter NATGAS, WTI or XCU while RedStone's roll is undocumented.
  - A Lighter BRENTOIL forward lane, which still uses Lighter's own documented roll, may be proposed under a new id.
    That needs BRENTOIL's reported 2x excess > 0 here, and it would be a new test.
- **PARTIAL:** an evidence note on M532, nothing more.
- **NULL:** M532 did not replicate on Lighter.
- **R480 is untouched either way:** its verdict is its own.

## Power (before any Lighter value)
- **At R478's post hoc NATGAS effect:**
  - Funding − roll +1.29% of notional a cycle (sd 1.34). Less about 0.13% of costs, times 0.75, less 0.25 × a bill of
    about 0.30% a cycle: about +0.8% of capital a cycle (sd about 1.0).
  - That is about +10 points a year, with t ≈ 2.1 over 7 cycles: roughly an even chance of t ≥ 2.0.
- **Under arbitrage:** about −0.17% a cycle (−2 points a year), NULL.
- Seven cycles cannot separate a small edge from zero. A PARTIAL is the likely outcome of a real but halved effect.

## What the author had seen before the freeze
- **Lighter values: none of funding or price.**
  - A spans-only probe on 2026-11-12 (`lab.carrylane.lighter_prices` and `lighter_funding`, 2026-01-01..11-12)
    printed only counts, first and last times and the largest gap: NATGAS candles from 2026-03-24 13:00, funding
    from 03-23 20:00; WTI from 02-18; BRENTOIL from 03-24; XCU from 02-09. No gaps above 2 hours.
  - The orderBooks list (market ids, status, 0/0 fees).
  - R459's plumbing fetched a few WTI funding rows for a status check, not analysed.
  - R433/M441's trade recorder saw Lighter WTI, NATGAS and BRENTOIL trades in late October; that was about trader
    identity, not funding or the roll.
- **The roll side is largely seen.**
  - R478's post hoc (`experiments/rollcarry_v1/posthoc/front_roll_months.csv`) printed xyz's monthly r(BD4),
    r(BD10) and roll against NG=F, CL=F and BZ=F for January-November 2026.
  - Lighter's oracle referenced the same contracts on the same days (documented from July), so Lighter's roll should
    be within premium noise of those numbers.
  - The unseen part is Lighter's funding.
  - HG=F (copper) has not been read.
- **xyz numbers:** R478 in full and xyz NATGAS funding by 4-week block (M532's note: 28.7, 59.8, 123 and 141%/yr from
  2026-07-23). These are xyz values, not Lighter's.
- **Choices fixed before the fetch:** NATGAS decides, matching R478 and R480 (named before any data). The window is
  forced by Lighter's RedStone change, and the costs are R480's.

## Risks
- **The identity measure:**
  - It assumes Yahoo's continuous front does not switch between business days 3 and 12, and that Lighter's roll fell
    between the business-day-4 and business-day-10 marks.
  - A roll outside that bracket would vanish from `roll` and flatter the net. The documented-month subset and the wide
    bracket are the checks.
  - Mark noise (the perp's premium at two instants) adds variance, not bias.
- **Pre-July schedule:** undocumented. If Lighter rolled at expiry rather than on business days 5-9 before July, those
  cycles' rolls are mismeasured.
- **Partial first cycles** (NATGAS and BRENTOIL from 03-24, WTI from 02-18) hold less funding and include launch-week
  premia.
- **Funding on a constant notional**, not on the drifting value of a fixed position: a second-order error of about
  the price change times the funding.
- **Costs are assumed**, and liquidation is not modelled (`max_up` is reported). Venue risks: Lighter's zk-rollup,
  LLP and auto-deleveraging, and oracle changes like the RedStone switch itself.
- **The hedge is notional:**
  - A French account would use CME micro futures (QG for natural gas, MCL for WTI) at a futures broker, rolled on
    Lighter's days, or HG/MHG for copper.
  - Brent has no CME micro contract that was checked here.
  - None of this was checked for this lane.

## Trials
4 (four markets computed). Program total after this round: 9,785,271.

## Inputs (sha256)
```inputs
dd6ed7fa39276b4858d3db95d7807d2fa7b12968d763593f7255a315ff5d2050  scripts/run_ltroll.py
bd5c5970ad0aa54f98b597015fdf09765225296b61dff67442f47569fea539e7  scripts/fetch_ltroll.py
c4af390ee73e4b9b5eb4e98a4c3b7b238d637258f90da4664888caac87ebc56a  tests/test_ltroll.py
f8ce0b423e975a4c228bb9dc72820da96c5e698fbdb7947c267479155634659a  scripts/run_rollcarry.py
14c57f1aed3a392a3cdae5a906512cb68cf60e9d3ca0458f6192cf608519e3ee  scripts/run_xyzwknd.py
04c45090be4113b9d9cf7d3c21c534ae8200363da3e5d4d55fe5a528801fdb9b  scripts/fetch_hip3stock.py
982455215c58232fda91a3193222f6afb268a87612685ab86848f1773d26dd1a  scripts/fetch_hip3carry.py
214ff732638a0ec29a1be56d54fb2ee1d341067cd01a8cf2f73196b8542b2d47  scripts/fetch_cryptomon.py
12efdca302dfdbc1312dc7499a53de23af9276406e1934c547b9e8642622e895  lab/carrylane.py
```
