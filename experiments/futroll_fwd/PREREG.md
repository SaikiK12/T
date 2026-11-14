# PREREG: futroll_fwd (R480). Does xyz:NATGAS's funding keep paying more than the futures roll, hedged with the contracts its oracle references?

- **Registry id:** R480
- **Owner (single writer):** Claude, this session (cloud container, 2026-11-12); the recordings are written by
  `.github/workflows/claude-futroll-recorder.yml` and the reads are run by `.github/workflows/claude-futroll.yml`
- **Date registered (UTC):** 2026-11-12

Method M532. Earned by R478 (`rollcarry_v1`, PARTIAL with a positive 2x excess), whose PREREG asked for a forward lane
with a hedge a French account can hold. This file is frozen by `lab.prereg.freeze()` before the first forward mark
(2026-11-13, 16:00 New York) and before any data of the forward window exists. After the freeze it is never edited; a
changed idea is a new lane.

## Question
trade.xyz prices NATGAS, CL (WTI) and BRENTOIL from futures. On business days 5-9 of each month the oracle moves from
the designated front contract to the next in 20% steps (switching at 18:00 New York). In contango the roll lifts the
perp; perp longs gain it and pay funding. R478 found that, for NATGAS in January-July 2026, the funding paid was larger
than the roll-up: shorting the perp against UNG kept about +10.5 points a year over the bill (t 1.68). Its B months
were flat with UNG, and UNG is not available to a French account.

R480 asks the same question forward with the hedge an executable book would use: the NYMEX contracts themselves, held
in xyz's weights and rolled on xyz's schedule. Such a hedge does not jump at the roll; the perp does. So the pair keeps
the funding minus the roll-up minus costs, plus small mark noise. **Arbitrage predicts NULL** (funding ≈ roll-up, so
the excess is about minus costs and minus the bill on idle margin).

## What the author had seen before the freeze
- R478 in full (xyz funding and candles to 2026-11-11, UNG/USO/BNO, the per-cycle table).
- R478's post hoc (`experiments/rollcarry_v1/posthoc/`, run 2026-11-12), the roll priced against the continuous
  front future at business day 10:
  - NATGAS funding − roll +1.29% of notional a cycle (sd 1.34), positive in 7 of 8 cycles, B's three included.
  - CL +0.23% (sd 2.33) and BRENTOIL +0.59% (sd 1.19).
- A plumbing run of this lane's code over 2026-11-03..11-11 (before the window): NATGAS's November roll (NGZ26 to
  NGF27) and the funding paid in those days. Over the roll days the funding about matched the roll-up.
- The trade.xyz roll schedule and designated months (`research/intake/m532_hedge_20261112.md`). NATGAS and CL
  reference the next calendar month's contract, BRENTOIL the one after; every month rolls.
- NATGAS decides because R478 named it before any data. Oil is reported only. The post hoc's weaker oil numbers do not
  change which pair decides.

## The book (`scripts/run_futroll.py`)
R478's frozen book (`run_rollcarry.simulate`, pinned below) with the US fund replaced by a **rolled-futures
total-return index**, per pair:
- **The hedge index:** a fully collateralised long in the contracts xyz references.
  - Marks at 16:00 New York on business days (weekdays without NYSE full-day closures; 2027's are listed in the runner).
  - Each contract is marked at the close of its latest 60-minute Yahoo bar ending within 3 hours before the mark.
  - At each mark the index takes the return of the weights held since the previous mark, plus the 13-week bill
    (^IRX) on the collateral.
  - It then re-weights to xyz's weights for the next trading day: next-contract weight 0.2, 0.4, 0.6 and 0.8 after
    the marks of business days 5, 6, 7 and 8, and 1.0 from business day 9.
  - Each roll step costs 4 bp per leg on the weight moved (sell the front, buy the next), deducted in the index.
  - The index does not jump at a roll. Its diagnostic `roll_spread` records the jump the oracle's blend makes at the
    same marks: the roll-up passed to perp longs.
  - Why the timing barely matters: if xyz's first step falls one day later than assumed, the hedge is exposed only to
    one day's change in the calendar spread, not to the spread itself.
- **Everything else is R478's:**
  - Notional 3/4 of capital (perp margin M = 1/3 of notional in USDC, earning nothing).
  - Re-splits when the legs drift 5% apart or the margin leaves [M/2, 1.5 M].
  - Liquidation checked on the perp's 1-hour (else 4-hour) highs: the isolated margin is lost, funding up to the
    breach kept, then re-split. Maintenance 5% for NATGAS, 2.5% for CL and BRENTOIL.
  - Funding is every hourly print times the position's notional.
  - Costs: perp 2.9 bp a trade; transfers 10 bp; the futures leg 4 bp a trade at entry, exit and re-splits (patched in
    R478's module for this lane only); roll steps as above.
  - Roll costs are moved into the cost column, so the 2x and 3x lines double them.
- **Window:** from the business-day-10 mark of 2026-11-13 (the first after a completed roll). Cycles run from
  business day 10 to business day 10.

## Data
- **Recorded** (`scripts/record_futroll.py`, twice daily, branch `claude/futroll-data`, single writer):
  - Yahoo 60-minute bars of NG and CL for the next 1-4 calendar months and BZ for the next 2-5.
  - xyz:NATGAS, xyz:CL and xyz:BRENTOIL 1-hour candles and funding.
  - Merged by bar start; each run saves 60 days (Yahoo) and 10 days (venue).
  - Recording is needed because Yahoo drops expired contracts and the venue keeps ~208 days of 1-hour candles.
- **Fetched in each read:** the venue's 4-hour candles and full funding history (merged with the recorded funding by
  time) and ^IRX from Yahoo. Manifest sha256 per file. Each summary also lists the sha256 of every recorded CSV it
  read.
- **The workflows:** `.github/workflows/claude-futroll.yml` (pinned) runs the reads.
  `.github/workflows/claude-futroll-recorder.yml` is not pinned, so its schedule and infrastructure can be repaired
  without stopping the lane. The recorder script itself is pinned.

## Reads and decision (NATGAS; `run_futroll.py --auto`)
Each read is computed once, on R478's weekly statistics: ISO weeks of equity against the bill, Newey-West t with lag 4,
annualized.

| Read | Marks | Runs after | Rule |
|---|---|---|---|
| futility | 2026-11-13 .. 2027-05-14 (cycles 1-6) | 2027-05-15 00:00 UTC | NULL if excess < 0, else CONTINUE |
| final | 2026-11-13 .. 2027-11-12 (cycles 1-12) | 2027-11-13 00:00 UTC | PASS if excess >= 2 points/yr, NW t >= 2.0 and 2x-cost excess > 0; PARTIAL if excess > 0; NULL otherwise |

- **INCONCLUSIVE:** NATGAS has fewer weeks than 18 (futility) or 36 (final), more than 10% of its marks are missing
  (index or perp), or it has no data at all.
- **A futility NULL stands:** the final read still runs and reports, but its verdict is NULL.
- **Reported, not decided:** CL and BRENTOIL by the same rule; the equal-weight pool of the three weekly excess
  series; per-cycle legs with the measured roll-up; liquidations, re-splits and missing marks.
- **Costs:** every read reports excess at 1x, 2x and 3x costs.
- **Trials:** 3 (three pairs computed). Program total after this round: 9,785,267.

## Power (stated before any forward data)
- **What the held data imply.** Post hoc, NATGAS's funding − roll was about +1.29% of notional a cycle (sd 1.34;
  B's three cycles +1.07 on average).
  - In this capital layout, after about 1 point of costs and the bill on idle USDC (a quarter of capital), that is
    roughly +8 to +10 points a year over the bill.
  - The weekly sd is about 0.5% of capital if cycles are independent.
- **The t that implies:**
  - At +9 points: about 1.8 at the futility read (26 weeks) and 2.5 at the final read (52 weeks).
  - At +5 points: about 1.4 at the final read, which would be PARTIAL.
- So the final read can confirm an effect the size of R478's, but not a halved one. The futility read only stops a
  negative carry.
- Arbitrage capital, the half-scaled funding (since 2025-12-19) and R478's flat B months all argue for a smaller
  effect.

## What each verdict earns
- **PASS:** M532 CONFIRMED forward on paper.
  - An executable version (CME Micro Henry Hub MNG or the standard NG, rolled on xyz's days, plus the xyz short) can go
    to the owner through `lab.gate.go_real()` in small stakes.
  - Not before French access to CME energy futures, margins and commissions are checked. None of these are verified
    yet.
- **PARTIAL:** monitoring only; no real money.
- **NULL:** M532 closed on NATGAS.

## Risks and caveats
- **Venue:** trade.xyz and Hyperliquid, USDC, the oracle relayer (17:00-18:00 ET gap), auto-deleveraging, halts,
  deployer exit. Six of nine other HIP-3 deployers delisted everything in 2026.
- **The oracle methodology can change:** roll days, months or funding scale. A change after the freeze is noted in
  the README and read as part of the forward risk, not repaired.
- **Liquidation:** NATGAS can rise 30% in days. The paper margin is isolated and re-split only at marks; a real book
  needs transfers between a futures broker and Hyperliquid (USD to USDC, days), which the 10 bp transfer cost only
  partly prices.
- **Execution:**
  - The paper hedge is fractional. A small real book holds whole contracts (MNG is 1,000 MMBtu, about $3.7k), so it
    would roll in fewer, larger steps.
  - Fully collateralised futures stand in for margin plus T-bills, so margin calls are not modelled.
- **Data:**
  - Yahoo's 60-minute bars of deferred contracts are thin (BZ especially) and can be revised.
  - A recorder outage of more than 10 days leaves the 4-hour fallback for the perp.
  - An outage of more than about 60 days, or past a contract's expiry, loses contract bars: those marks are missing.
- **Costs are assumed:** perp 2.9 bp, futures 4 bp, roll legs 4 bp, transfers 10 bp. The 2x and 3x lines are the
  check.
- **Not in the book:** taxes, EUR/USD and broker interest on margin.

## Inputs (sha256, checked by every read through `run_xyzwknd.frozen_inputs`)
```inputs
b1b2bcf3c392c23f1d9c8ec2767b69e26ea6da1136e57f35471b1c66ddcc4193  scripts/run_futroll.py
1a57429f9ecea80dacdb3722fd74386ff533eb13e99bf3463237da94e8491c29  scripts/record_futroll.py
25ed8c834f0defc2b9481bc3eef30487d5a067f689e495a2b0b119c2d2539e06  tests/test_futroll.py
b54167404e5aebeb80211ea7293d90bc1a74270897053e2b2c69724d781c1abe  .github/workflows/claude-futroll.yml
f8ce0b423e975a4c228bb9dc72820da96c5e698fbdb7947c267479155634659a  scripts/run_rollcarry.py
04c45090be4113b9d9cf7d3c21c534ae8200363da3e5d4d55fe5a528801fdb9b  scripts/fetch_hip3stock.py
982455215c58232fda91a3193222f6afb268a87612685ab86848f1773d26dd1a  scripts/fetch_hip3carry.py
f0cb42452354307bbf5bbbc4e6abad60b7ac2a41149118867fc4d487195ea79f  scripts/fetch_xyztwin.py
214ff732638a0ec29a1be56d54fb2ee1d341067cd01a8cf2f73196b8542b2d47  scripts/fetch_cryptomon.py
14c57f1aed3a392a3cdae5a906512cb68cf60e9d3ca0458f6192cf608519e3ee  scripts/run_xyzwknd.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
```
