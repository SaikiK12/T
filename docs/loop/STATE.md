# Edge loop state

This is the loop's working memory for `docs/loop/PROMPT.md`. The live queue stays `registry/methods.csv`. This file
holds only the current focus, the lenses last used and one line per tick.

## Current focus
**Hunt mode (owner, 2026-11-09 ~22:45 UTC):** "work continuously, not every 3 hours; the subscription ends soon; hunt
for breakthroughs at 100% of compute".

**How the hunt runs:**
- Parallel forks, one lane each. R-ids and folders are pre-assigned.
- Two-phase protocol: the fork freezes and registers, then replies FROZEN. The orchestrator commits and pushes, then
  sends GO. The fork runs once and writes FINDINGS. The orchestrator closes the registry row, updates methods.csv,
  commits and posts on #7.
- Forks never run git and never touch shared files.
- Haiku helpers generate ideas in between.
- The scheduled task is an hourly safety net only.

**State on 2026-11-12 08:15 UTC** (the 11-09 wave tables are in the tick log below and in `registry/rounds.csv`):
- **Forward on GitHub Actions** (`docs/HANDOVER.md`): R441-R459 books, R463 and R467 (weekend fades, from 11-13).
- **Dated reads:** R469 (Asian closure fade on unseen openings) on 2027-02-01; R446's EARNED look on 2027-02-08;
  R474 (hedged TLT carry) futility on 2027-02-13 and final on 2027-05-15, by `claude-tltcarry.yml`; R479 (HIP-3
  funding carry) on the same two dates, by `claude-hip3carry.yml`.
- **Pattern:** R462, R465 and R468 found large effects on stock perps in spring-summer 2026 that were flat afterwards.
  Prefer structural trades (carry, inventory, fees) over price-pattern lanes.
- **Closed:** R470 `xvfund_v1` (M527) NULL: the xyz-vs-Lighter funding carry is too thin even before costs.
  R471 `cryptomon_v1` (M521) NULL: Bitcoin-linked stocks open with the weekend priced and do not drift after.
  R473 `tlteom_v1` (M528) PARTIAL: the Treasury month-end rally survives on TLT before costs, but not net of
  xyz:TLT's cost and funding (longs paid about 20%/yr since listing).
- **Closed 11-12 (morning):** R472 `rebalfront_v1` (M522) NULL: the rebalancing front-run earned in its paper's
  span, not after 2023 (+0.05 bp a day net). R475 `hip3stock_v1` (M530) frozen PASS recorded PARTIAL: xyz stock
  funding carry +11.2 points over the bill in A, half from one BIRD liquidation day; carry alone below the bill in B.
- **Closed 11-12 (late morning), all recorded PARTIAL:** R476 `hip3other_v1` (R475's rule on the other HIP-3
  deployers) +3.12 points in A (t 2.14), pure carry with a weekly sd of 0.09%, but only 9 trades on venues that have
  since closed. R477 `xyztwin_v1` (xyz index/ETF/metal perps hedged with London twins) +1.62 (t 0.50): carry
  +2.48, drowned by hedge noise. R478 `rollcarry_v1` (M532) NATGAS short hedged with UNG +10.52 in A (t 1.68),
  -0.09 in B: funding beat the contango roll-up in A only. The R475-R477 identity check drops markets with under 60
  marks through a NaN; a post hoc rerun moves no verdict (`experiments/hip3stock_v1/posthoc/`).
- **Running:** R479 `hip3carry_fwd` (M530/M531 forward from 2026-11-16): book S on every live HIP-3 dex's US-stock
  perps (16:00 New York marks, $150k/day capacity floor), book T on R477's twin pairs; decides carry, with the
  total positive at assumed and measured costs. Paragon and EntropyIO books are now recorded (`hip3/`).
- **Open queue rows:** M523's negative-gamma regime is nearly absent since 2024-11 (18 of 504 sessions). M296 has
  too few events. M532's forward lane needs a hedge a French account can hold (CME micro futures or LSE ETCs).

**Test choice after the 2026-11-10 false-null audit:** compute the detectable edge before registering. Pool
directional ideas into one family or run them forward; prefer structural, high-Sharpe trades on held data.

**Standing duties** (`docs/OPERATIONS.md`): R404's close on 11-18, and the R406/R413 successors after 11-19.
R392 is being done now.

## Lenses last used
1, 2, 3+4 (tick 1); 5, 6+7 (hunt wave, 2026-11-09); 8 and 1 (wave 2, 2026-11-10); 2 and 3+4 (wave 3,
2026-11-10). Next: 5, then 6+7. Three waves in a row produced no new testable row: run a wave only when a lane is
waiting, and pick tests from our own measurements first.

## Tick log
- **2026-11-09, tick 1 (by hand).**
  - **Lenses and ideas:** lenses 1, 2 and 3+4. About 25 ideas gave 1 new row (M491) and notes on M188, M292, M296 and
    M474. Two Binance pages were verified.
  - **Killed by arithmetic before any data:**
    - USDC making with a rebate: needs 1.5% of maker volume.
    - A Standard maker behind Lighter's speed bump: its 300 ms cancel loses to the 140 ms Premium taker.
    - An unlock short 30 days ahead: duplicate of M072, already NULL.
  - **Written:** `docs/INFRA_GAP.md`. With Jane Street's infrastructure alone, none of our five rows flips. Two
    would flip with scale or a venue tier.
  - **No registered test this tick.** Building the loop took the tick, which counts as a failed act step under the
    prompt.
  - **The deduction that changes the next choice:** look for payers who are not racing (capacity, long holds, rule
    clocks), not for speed.
- **2026-11-09 to 11-10, hunt wave 1.**
  - **R432 NULL.** Its only lead, an oil fade held to the cash open, cannot be checked on fresh pre-April weekends:
    MEXC traded only 3 of them. It is forward-only.
  - **R433 NULL as a trade.** Informed Lighter accounts stay informed out of sample (Spearman 0.42 at 60 s), but a
    follower 1.3 s late keeps less than the touch. The open use is the maker side (M474).
  - **YouTube @losingloonies:** blocked by YouTube's bot wall from this container. A script was left for the owner.
- **2026-11-10, wave 1 closed.** R434, R435 and R436 NULL. R392 PARTIAL:
  - GLT carry PASS but +0.73%/yr, below cash.
  - C17 on 2020 at t 3.04 fails α 0.001 by a hair, and its 10 best days carry it.
  - **Owner decision, 2026-11-09:** batch 3 was read on 11-10, not on or after 11-17. The two-week spacing was shortened
    once; the 4-read budget is unchanged. This sat in `docs/GATES.md` until 11-10, when GATES was restored to its
    frozen content (rule 2).
- **2026-11-10, idea wave 2 and forward restart.**
  - **Lenses 8 and 1:** about 8 ideas gave 2 new rows, both BLOCKED (M495 Deribit Block RFQ maker, M496 batch-auction
    maker), and a note on M285 (Lighter LLP). Lens 1 found nothing new; its basis-by-ETF-flow idea is dominated by
    R335/R406 because a locked yield is known at entry.
  - **No registered test.** Nothing new was testable on held data at $10k.
  - **Act instead:** every forward lane had been stopped since 11-06. Restarted as frozen: R371's daemon, then the
    carry ticks (R390 first). Catch-up days are `late` under each PREREG.
  - **Deduction:** the binding constraint is prospective evidence on the carry family, not ideas. Keep the daily
    ticks before 07:00 UTC so days count as `ontime`; the hourly prompt now says so.
- **2026-11-10, R437 carry_v2_audit_v1 (registered test, gate 0): CONFIRMED.**
  - R275's 7 headline carry books re-run on the corrected M468 engine. All 7 survive, including the four forward
    books.
  - The fixes raise %/yr through two effects. The deflated read: R390 A is about +9.7%/yr at 1x (t 8.35) without
    blowout and dead-leg trades, not v2's +13.4.
    - Fixed-quantity funding drift.
    - Blowout exits, about +3.4 pt/yr in the Binance+Gate books.
  - **Deduction:** the carry family is not an accounting artifact on its own venues. The binding question is now
    live execution (fills at 00:00 on two venues, collateral, capacity), which only the forward lanes and the owner's
    eventual small real test can answer.
  - **Ops lesson:** `scripts/catalog.py` rewrites `scripts/README.md`, which the forward orchestrator hashes as
    code. Running it during a batch marked R404 and R278 FAILED, though their ticks completed.
- **2026-11-10, wave 3 and R438 carry_v2_audit_kc_v1 (registered test, gate 0): CONFIRMED.**
  - **Forward batch:** R294, R285 and R415 completed. All forward journals are committed.
  - **Lenses 2 and 3+4:** about 9 ideas, no new row (all duplicates or dead by arithmetic). Two carry regime
    variables were logged against M136: the floor share and cross-venue dispersion.
  - **R438:** R279's KuCoin books on the M468 engine. Both survive: gate+kucoin +14.98%/yr, t 9.63; binance+kucoin
    +11.28%/yr, t 8.50.
  - **Measured post hoc:** v2's funding gain is notional drift, mostly a price-funding covariance rather than leverage
    (mean notional/entry 0.91-1.12). This corrects R437's "leverage, not edge" (addendum there). Constant-notional
    figures stay the conservative read.
  - **Deduction:** every forward carry book except R294 is now accounting-clean on held data. R294 waits for M469
    (R404's costs on 11-18). The binding constraint is still forward evidence and execution, not ideas.
- **2026-11-10, false-null audit and R439 carry5_v1 (registered test, gate 0): CONFIRMED.**
  - **Owner's question:** if the engine had accounting errors, why not others that hid edges? Six Haiku auditors
    (Opus ones hit the rate limit) read survivorship, the cross-section engine, cross-asset lanes, NULL power, unused
    data and event timing. Evidence in `docs/reviews/false_null_audit_20261110.md`.
  - **Code:** mostly clean. Two hidden-edge items, neither moves a verdict: the listing cost tier (E1, note on M155)
    and R271's unpriced legs (E2). Delisted exits booked at zero hide short gains (E3, unquantified).
  - **Process (the real error):** most NULLs could detect only 30-190%/yr; they were read as "no edge". Low-Sharpe
    directional ideas were tested one at a time. DIX, SKEW and the index perps were never used (M499, M500 queued).
  - **Ops (mine):** I ran R406/R413 locally while Codex's GitHub runtime owns them; restored in 1ec28d2.
  - **R439:** R275's all-four rule over five venues (adds KuCoin): +18.46%/yr at 1x, NW t 8.71, SURVIVES. Paired vs
    four venues +1.48%/yr, t 0.54; level on constant notional (~+14.7%/yr). KuCoin buys steadiness (t 4.77 -> 8.71,
    top-10-day share 33% -> 18%), not return. The PREREG names a forward lane as the next id.
  - **Deduction:** choose tests by power first. Directional ideas go in pooled registered families or forward, not
    one-by-one on short samples; structural high-Sharpe trades are where held data can decide.
- **2026-11-10, R440 xfund5_fwd armed (forward, gate 1).**
  - R439's frozen next id: the five-venue book forward on paper from 2026-11-11 on `lab/carrylane.py` (v1). Looks at
    90 / 180 scored days (2027-02-09 / 2027-05-10). Run directly: `.venv/bin/python scripts/forward_xfund5.py`
    (not through the orchestrator: `lab/operations.py` is a pinned input of Codex's R429 runtime, and wiring R440
    there broke its `paper` check at 13:50 UTC; reverted).
  - Why it matters: on the archive it has half the daily volatility of the four-venue book, so a forward test decides
    about three times sooner (about 110 days to NW t 2 at the archive rate, against about 365).
  - Forward carry so far (19 days, R278/R279; 6 days R390): small positive means, none significant. Expected at this
    length; no forward book can decide before about 3 months.
  - `REC_CBOE` had stopped with the container restart, and the QQQ/SPY/SPX chains before 2026-11-10 are gone (Cboe
    serves only today's chain). Restarted at 13:40 UTC (pre-open map recorded). It runs only when a batch or a wake
    runs it.
- **2026-11-10, ops: the container is reclaimed while the session is idle.** The VM rebooted at 14:52 UTC (uptime 0)
  and every daemon died with it; files survive. This, not a bug in the lane, is why R371's daemon kept vanishing and
  missed 2026-11-09. Daemons are reliable only while a turn is active. The carry ticks and R440 run at a wake, so they
  are unaffected. R371 decides at 10:00 New York (15:00 UTC in winter): the 14:51 wake starts the daemon and stays
  active until the day's ticket is written.
- **2026-11-10, venue access from France (owner: "rien ne dépend de moi").** Evidence in
  `docs/reviews/venue_access_fr_20261110.md` (one Haiku agent, decisive pages re-read by me).
  - Binance (left France 1 Jul 2026, reported), Gate (clause 2.5), MEXC (terms) and KuCoin (Art. 17(5)) exclude France
    for perps. The MiCA entities of Gate and KuCoin list no derivatives. Hyperliquid and Lighter do not exclude France
    but are authorised nowhere; ESMA treats perps as likely CFDs (24 Feb 2026).
  - **Every forward carry lane has a leg on an excluded venue.** The DEX-only book is below cash on seen rows (R288
    hyperliquid+lighter +3.53%/yr vs 4.13%).
  - **Deduction:** the binding constraint for the owner is venue access, not ideas. France-reachable routes are M490
    (OKX Europe alt X-Perp carry, UNTESTED; its France eligibility is itself unverified), M487/M488 (Kraken, Coinbase
    CDE) and DEX books. Paper lanes keep running as evidence on the edge, not on an executable book.
- **2026-11-10, forward carry lanes move to GitHub Actions (single writer).** The container is reclaimed when idle and
  the session will end, so the lanes now run on `.github/workflows/claude-carry-paper.yml` (hourly 00:29-07:29 UTC):
  R278, R279, R294, R390, R440, then R285 and R415.
  - Probe run 42863150912: every endpoint the lanes use answers from a GitHub runner (Binance through
    www.binance.com; fapi.binance.com returns 451 there and is not used). OKX EEA, Kraken, Coinbase and Cboe answer too.
  - Data roots live in the Actions cache. `scripts/prefetch_carry_data.py` (dispatch input `prefetch_only`) fills it
    without ticking. Journals are committed to the default branch by the workflow. Each lane's NOTES.md records the
    writer change.
  - **The local loop no longer ticks these seven lanes.** It checks that the workflow ran and fixes it with a code
    push if it failed. R371 (10:00 New York daemon) and the Cboe recorder still run locally for now.
- **2026-11-10, R371 and the Cboe recorder also move to GitHub Actions.**
  - `claude-usopen.yml`: the daemon runs from about 30 min before 10:00 New York to 6 min after, and a scoring tick
    runs at 00:47 UTC. It is the sole writer of `experiments/usopen_fwd/journal/` from 2026-11-11. Since 11-02 the
    container left 5 of 8 tickets missed and none scored after 10-30.
  - `claude-cboe-recorder.yml`: 13:12 and 21:33 UTC on weekdays, writing the data branch `claude/cboe-chain-data`
    (seeded with 2026-11-10 pre).
  - `claude-okx-recorder.yml`: 02:37 and 14:37 UTC, writing `claude/okx-xperp-data`.
  - **The local loop now runs no forward lane and no recorder.** It checks the workflows and fixes failures by code
    pushes.
- **2026-11-10, R441 and R442 frozen: the France-reachable carry route on OKX Europe X-Perps.**
  - OKX's own X-Perps guide says they are open in all 30 EEA countries (France included), with KYC, an
    appropriateness test and "availability may vary". No register entry for a French passport was reached (venue
    note, later section).
  - The recorder's first run (data commit 013dc72, 0 failures) is gate 0 for both lanes.
  - R441 (M490): crypto X-Perps against OKX EEA spot. Gate 0 is reported only (R430's cross-section was seen).
  - R442 (M501, new): X-Perps of 62 US-listed stocks against the stock held at an EU broker. No stock X-Perp number
    was read before the freeze, so its gate 0 is unseen data. It decides only a stop.
  - Gate 1 for both is forward from 2026-11-11, with looks on 2027-02-08 and 2027-05-09. `claude-xperp-reads.yml`
    (Mondays 04:23 UTC) writes status reads and, once each look date has passed, the frozen decision. So no session
    is needed for the decision.
  - **Gate 0 results (same day):**
    - **R442 is NULL (stop).** Net −0.50%/yr on capital at 1x, excess −4.5 points, NW t −4.65. The hedge works (price
      part flat). Funding above 10%/yr lasts about two weeks, which is too short to pay a 50 bp round trip, and half
      the slots sit idle.
    - **R441 is reported only.** Net +5.37%/yr at 1x, excess +1.37 points, t 0.62; 2x excess −0.25. Gate 1 needs
      about +4 points to decide (NW-implied power), so the likely path is CONTINUE, then NULL.
    - **Deduction:** the one France-reachable perp route earns about the T-bill plus a point at best on seen data.
      The confirmed carry edge (+10 to +18%/yr) needs Binance, Gate, MEXC or KuCoin legs.
- **2026-11-10, R443 frozen and its gate 0 read: OKX Europe X-Perps against Hyperliquid perps (M502).**
  - `scripts/record_hl_daily.py` now runs in `claude-okx-recorder.yml`. It writes Hyperliquid funding and daily
    candles of the 97 coins that match an OKX crypto X-Perp under `hl/` of the same data branch. Data commit 8b01167
    is R443's gate 0.
  - The rule: short the venue paying more trailing 7-day funding when the spread is at least 10%/yr, long the other.
  - **Gate 0 (reported only; funding on both venues was seen):**
    - net +0.95%/yr at 1x, excess −3.05 points, t −0.55; 2x −13.6%/yr;
    - the funding spread earns +14.4%/yr, but costs take −14.6%/yr.
    - The spread flips within about a week (mean hold 7.7 days), and a 39 bp taker round trip on two venues eats it.
  - Gate 1 is forward from 2026-11-11 through `claude-xperp-reads.yml`.
- **2026-11-10, R444 frozen and NULL (stop) at gate 0: Hyperliquid spot against Hyperliquid perp (M503).**
  - `scripts/record_hl_spot.py` writes `hl_spot/` on the same data branch: 12 pairs (HYPE and Unit coins with a
    same-name perp), funding from 2024-11-01, both legs' daily candles. Data commit 814573b is gate 0.
  - Over 679 days (2025-01-01..2026-11-10) the book nets +2.57%/yr on capital at 1x, an excess of −1.43 points
    (t −3.66). It is steady: both years about +2.5, every held pair positive, worst day −0.42%.
  - It fails on idle cash: 3.8 of 10 slots held. Per held slot it earns about +6.7%/yr on that slot's capital, which
    is +2.7 points over the hurdle and still under the +3-point bar.
  - **Deduction for France:** the Hyperliquid-only cash-and-carry is real but thin. It is a T-bill-plus-a-little
    product, not a breakthrough. The confirmed carry edges remain on venues that exclude France.
  - Correction, same day: R444's portfolio-margin figure (+7.70%/yr at capital N/2) needs a USDC borrow at 5%/yr or
    more. With no borrow (capital N) the book reads +3.85%/yr, excess −0.15.
- **2026-11-10, R445 frozen, gate 0 CONTINUE (seen, stops only): HYPE and BTC carry, fully deployed (M504).**
  - R444's rule on the two pairs whose spot has a listed portfolio-margin LTV, every qualifying pair held, capital
    split across them, spot backing the perp with a 10% USDC buffer (capital N × 1.1).
  - Gate 0 (2025-01-01..2026-11-10): +10.06%/yr at 1x, excess +6.06 points, t 3.67; 2x +3.21, 3x +0.36. Without
    portfolio margin (N × 1.5): excess +3.38.
  - The level is falling: +15.2%/yr in 2025, +4.2%/yr in 2026 (about the hurdle). The pairs were picked after R444,
    so gate 0 is not evidence; gate 1 decides on 2027-02-08 and 2027-05-09 and has about a one-in-four chance of
    passing even at gate 0's full level.
- **2026-11-10, R446 frozen, gate 0 CONTINUE for both books (stops only): deposits in HLP and LLP (M505).**
  - New recorder `scripts/record_dex_vaults.py`, run by `claude-okx-recorder.yml` into `vaults/`. The PREREG was frozen
    before either vault's return series was read.
  - HLP: +14.30%/yr, excess +10.30, t 1.87 on two-week periods; 2026 +10.65%/yr (t 0.89). Gate 1 can detect only
    about +19 points at 180 days, so a NULL there is the likely read.
  - LLP: +73.26%/yr from a small pool's first months; 2026 +10.80%/yr, excess +6.80, t 3.27. It lost 5.35% on
    2025-10-11. At 2026's level, gate 1 has roughly an even chance at 90 days and about seven in ten at 180, if no
    crash day falls in the window.
  - Read after the run: LLP takes deposits only against staked LIT (1 LIT per 10 USDC, 6% staking APR, 3-day
    unstaking). R446 measures the vault per USDC; a book with the stake is a new lane.
- **2026-11-10, R447 frozen, gate 0 CONTINUE (stops only): LLP as a depositor must hold it (M506).**
  - Per LIT staked, 10 USDC in LLP and a 1-LIT short on Lighter's LIT perp with margin equal to its notional. New
    recorder `scripts/record_lit_hedge.py` writes `lit/` (LIT perp hourly funding, perp and spot daily bars).
  - Gate 0 (2026-01-15..2026-11-10): +10.04%/yr on all capital at 1x, excess +6.04, t 3.94; 3x +5.78. Parts: LLP
    +7.65, staking +0.85, funding received +1.65, basis +0.02, costs -0.13. Max drawdown -0.35%, no liquidation.
  - LLP's part was seen in R446, so gate 0 is not evidence. Gate 1 (2027-02-08, 2027-05-09) has about seven chances
    in ten at 90 days if no crash day like 2025-10-11 falls in the window; one such day would end the lane.
- **2026-11-11, the flow-book forward lanes move to GitHub Actions.**
  - R200, R214, R215, R218, R220, R221 and R225 stopped on 2026-11-06 13:00 UTC with the container. They were never
    migrated, so R285's and R415's flow sleeves read stale journals.
  - `.github/workflows/claude-flow-paper.yml` (every 2 hours at :41 UTC) is now their only writer. It runs the frozen
    scripts unchanged, in the order set by `lab/operations.py`.
  - Binance keeps 5-minute ratio history for 30 days, so the first run computes the missed hours from the same public
    data. Each lane's DEVIATIONS.md flags those days as written after the fact.
  - Why now: on the owner's request to rank the methods by PnL, the flow books are the lab's highest-PnL candidates.
    Holdout: A +82.9%/yr (t 1.22), top_vs_crowd alone +71.4%/yr (t 2.72). Neither is confirmed, and only forward days
    can decide them.
- **2026-11-11, R448 flow_hl_v1: the flow books on Hyperliquid, gate 0.**
  - R200's signals on crypto perps only, priced on Hyperliquid's hourly closes and funding (France-reachable). Frozen
    `e87e3aed` before any Hyperliquid return.
  - Gate 0 (2026-04..09, seen on Binance): book A CONTINUE at +4.9 bp/day (t 0.91), book B NULL at -0.7.
  - Hyperliquid equals Binance on the same coins (correlation 0.9996). The gap is coverage: on every crypto coin,
    Binance's books made A +47.1 and B +25.3 bp/day, carried by LAB and BEAT, which neither Hyperliquid nor Lighter
    lists.
  - With R216 (forward gain from stock perps), the flow books' high returns have not come from coins the owner can
    trade from France.
  - `claude-flow-paper.yml` now runs hourly at :17, so R200's hours are on time under docs/GATES.md, and ticks R448
    after R200 from 2026-11-12.
- **2026-11-11, R449 jlphedge_v1: perp-DEX pool tokens hedged on Hyperliquid, gate 0.**
  - Book J holds Jupiter's JLP against SOL/ETH/BTC shorts, and book G holds GMX v2's GM ETH-USDC against an ETH
    short. The ratios come from an ex-ante 60-span regression. Frozen `7ae66e56` before any return.
  - Gate 0 (2024-02..2026-11, public APYs known, so stop only): both CONTINUE. J made +22.1%/yr (t 4.48) and G +12.0%
    (t 4.75).
  - By year, J went +43.9, +16.2, +5.6 and G +19.4, +9.5, +7.2. The return was 2024's; in 2026 both sit below
    HLP/LLP (R446) and HYPE carry (R445).
  - Gate 1 is expected NULL at 180 days. `claude-flow-paper.yml` writes the tickets hourly (once per book and day,
    the day before).
- **2026-11-11, R451 flow_hlstock_v1: R200's stock-perp flow books on Hyperliquid's xyz markets, gate 0.**
  - R216 found R200's forward gain mostly in Binance's TradFi perps (closed to France). xyz (HIP-3, trade.xyz)
    lists 21 of R200's 24 TradFi symbols; its terms do not name France. Frozen `89eceed0` before any xyz return.
  - Gate 0 (2026-10-01..11-10, seen): both CONTINUE. A +13.4% (t 1.81) on xyz vs +13.3% on Binance for the same
    coins, B +7.6% on both; daily correlation 0.9998. Trimmed means about 0: a few days and leveraged-ETF shorts.
  - Forward from 2026-11-12 in `claude-flow-paper.yml` after R448.
- **2026-11-11, R452 litpoolsel_v1: Lighter's operator pools picked by past record, gate 0 decides.**
  - The owner asked for HLP/LLP competitors that a real deposit would match. Lighter publishes every pool's daily
    share price, so the test reads what a deposit earns. Frozen `45627260` before any pool return.
  - NULL: 1x +7.2%/yr (excess +3.2, t 0.33). The mean/sd score picked dormant pools; the equal-weight pool lost
    5.2%/yr after fees; LLP +10.7%/yr and XLP -51%/yr over the same months.
  - Competitor survey: `research/intake/perp_vaults_20261111.md` (only dYdX's MegaVault publishes history; small).
- **2026-11-11, R450 hlvaultsel_v1: Hyperliquid user vaults picked by past record, gate 0 decides.**
  - Top 10 vaults (>=180 days, >=$500k, active in >=80% of periods) by 180-day mean/sd, monthly, net of the
    leader's share. Data branch `claude/hl-vaults-data` at `ed333ff`. Frozen `a329f8cc` before any vault return.
  - NULL: 1x -23.2%/yr net, excess -27.2 (t -2.26). Real blowups: three 2025-09-30 picks lost over 90% in the
    2025-10-10 crash; the 2026-09-30 picks lost 21.5%. In 2026 the equal-weight eligible vault made +8.2%/yr.
  - Both M507 venues are NULL: HLP and LLP (R446) remain the better deposits.
- **2026-11-11, xyz cost recorder and xyz funding.**
  - `claude-xyz-books.yml` (hourly, data branch `claude/xyz-books-data`) records the cost of a $1k-$25k market order
    on every trade.xyz market, so R451's tickets can later be read at measured costs (real equal to paper). Only a
    smoke run's counts were looked at.
  - No xyz funding-carry lane: trade.xyz scales Hyperliquid's funding by 0.5 since 2025-12-19, "lowers baseline
    funding to ~5.5% annualized" (docs.trade.xyz changelog; `perpDexs` lists multiplier 0.5 on 136 of 138 xyz
    markets). Short perp and fully paid stock at 2x perp margin is then about 3.7%/yr on capital before costs, under
    the 4% hurdle, as R442 found on OKX (funding +3.7%/yr).
- **2026-11-11, R453 flow_hlstock_mc_v1: R451's books at measured xyz costs (real money equal to paper).**
  - 117 of 122 xyz markets run in HIP-3 growth mode: taker fee 0.9 bp, not the 9 bp floor R451 charges. R453
    recomputes R451's positions with that fee plus the $1k slippage of the hourly snapshots. Frozen `26a0ed2d` before
    any snapshot value was read; zero trials (it can only fail R451). Weekly in `claude-xperp-reads.yml`.
- **2026-11-11, HLP inventory recorder (M510).** The owner asked to dig into HLP's and LLP's methods. HLP's edge
  (spread capture, liquidation flow) is not open to a depositor, but its positions are public in real time and kept
  nowhere. `scripts/record_hlp_positions.py` (in `claude-xyz-books.yml`, hourly, `hlp/` on `claude/xyz-books-data`)
  records every child vault's positions and every main-dex perp's open interest and funding. A forward PREREG is
  frozen before any snapshot value is read.
- **2026-11-11, R454 hlpinv_v1 (M510) frozen `9df27190` before any HLP value was read.** Each hourly snapshot ranks
  the main-dex perps by HLP's net size over open interest. Book F shorts the eighth where HLP is most net short (the
  crowd long against HLP, the analogue of R197's crowd cells); book R the opposite. 72 h slices, universe hedge,
  9 bp a trade. Counted from 2026-11-15; futility screen at 90 days, decision at 365 against 1,000 random-bin
  placebo books. Two trials (program 9,785,001). Weekly in `claude-xperp-reads.yml`.
- **2026-11-11, R220 on GitHub:** MEXC refused R220's request burst by IP (code 510), so it wrote nothing after
  2026-11-05. `scripts/run_paced_mexc.py` paces MEXC requests and retries 510s around the unchanged script; run
  42942661403 wrote its tickets through 2026-11-10 (`experiments/carry_fwd/DEVIATIONS.md`).
- **2026-11-11, LLP inventory and main-dex book costs recorded (M511).** Lighter's public `account` endpoint lists
  LLP's positions (199 non-zero on the first run) and `orderBookDetails` each market's open interest, with no history
  kept: `scripts/record_llp_positions.py` writes `llp/` hourly on `claude/xyz-books-data`. The same workflow now
  records book costs on Hyperliquid's main-dex perps (`main/`, `record_xyz_books.py --dex ""`, 179 markets) for
  measured-cost reads of R448 and R454. An LLP lane is frozen before any `llp/` value is read.
- **2026-11-11, R455 llpinv_v1 (M511) frozen `ea4f9f26` before any LLP value was read.** R454's rule unchanged on
  Lighter: share = LLP's signed position value over open interest in USD, eligible markets active with $10M volume and
  $2M open interest, books F and R, Lighter's closes and funding, 9 bp a trade, placebo seed 455. Lighter does not
  exclude France. Two trials (program 9,785,003). Weekly in `claude-xperp-reads.yml`, read separately from R454.
- **2026-11-11, Lighter book costs recorded hourly on GitHub.** `scripts/record_lighter_costs.py` (stdlib, the
  arithmetic of `record_lighter_book.py`) writes the cost of a $1k and $10k market order on every active Lighter perp
  to `lighter/books/` on `claude/xyz-books-data`, for a measured-cost read of R455 frozen before any cost is read.
- **2026-11-11, R456 invcost_v1 frozen `ececc01b` (0 trials).** R454's and R455's books recomputed unchanged at
  measured costs: Hyperliquid 4.5 bp + $1k slippage from `main/books/`, Lighter 0 fee + $1k slippage from
  `lighter/books/` (nearest snapshot within 90 minutes, else 9 bp); stops if its 9 bp recomputation differs from a
  parent's tickets. EXECUTABLE AT MEASURED COSTS at 365 counted days only if the parent passed. Weekly reads.
- **2026-11-11, R457 usopen_dex_fwd frozen `dee511b4` (2 trials, program 9,785,005).** R371's US-open picks
  (C17) traded where a French resident can: R371's 50-name table filtered to the names each venue lists, R371's
  pick, one-minute fills 3 minutes after each clock, venue funding, fee + $1k book cost from the nearest
  snapshot. Book L on Lighter (0 fee) decides at R371's 125/500 scored days; book H on Hyperliquid main + xyz is
  reported. Forward from 2026-11-12, daily in `claude-usopen-dex.yml`.
- **2026-11-11, R458 flow_hl_mc_v1 frozen `f938cec8` (0 trials).** R448's crypto flow books recomputed unchanged at
  Hyperliquid's 4.5 bp taker fee + $1k slippage from `main/books/` (nearest snapshot within 90 minutes, else R448's
  6-20 bp tier cost); stops if its recomputation differs from R448's tickets. Book A's gate-0 net fell to +0.1
  bp/day at 3x, so its cost decides it. Weekly in `claude-xperp-reads.yml`. Also: R215 now runs through
  `run_paced_mexc.py` after a MEXC 510 refusal (run 42980224484).
- **2026-11-11, R459 oilwknd_fwd frozen `78454c92` (2 trials, program 9,785,007).** R432's only lead on fresh
  weekends where a French resident can trade: Lighter WTI and BRENTOIL, |W| (Fri 17:00 ET to Sun 17:55 ET) >= 100 bp
  faded from the first one-minute open in [S - 4, S - 1 min] to the Monday 09:30 ET cash open, hourly funding and the
  $1k `lighter/books/` cost charged. Futility at 15 traded weekends, final at 40. Daily in `claude-oilwknd.yml`.
  Lighter's candles return at most 500 bars (the last of the range), so the runner asks three short ranges; R457's
  windows are under 70 minutes and unaffected.
- **2026-11-11, three quick checks; no lane (configuration and size only, no return series read).**
  - **HLP/LLP competitors with no history yet read:** Paradex's largest active vault holds about $2.4M (the next
    ones under $0.2M); Extended's vault holds about $52M at a seen last-30-day APR of 8.28%, below HLP and LLP.
    Neither publishes a share-price history found by the author. Details: `research/intake/perp_vaults_20261111.md`.
  - **Hyperliquid's HIP-3 dexes:** 10 listed; on 2026-11-11 only xyz (122), para (33), io (15) and mkts (1) had live
    markets. 21 underlyings trade on two dexes, mostly small single stocks: too thin for a cross-dex funding book.
  - **Lighter vs xyz on the same stocks:** Lighter's `orderBookDetails` gives each market's funding settings. Its
    TradFi perps use an interest component of 0.0032 (per 8 h, in %) with a premium multiplier of 50, against 0.0100
    and 100 on crypto. That is a baseline of about 3.5%/yr, against xyz's about 5.5% (multiplier 0.5). The structural
    spread is about 2%/yr of notional, under the 4% hurdle at any safe leverage, so no lane. M073 (a resting bid
    ladder in cascades, the depositor's route to HLP's liquidation income) is already a trap at -0.84% per rung.
- **2026-11-11, GitHub skips scheduled runs; guarded catch-up runs added.** `claude-flow-paper.yml`'s 06:17 and 08:17
  UTC runs never fired, so R200 computed hours 02:00 and 05:00 of 11-11 75 and 94 minutes after their close (hour
  07:00 is later still). A day counts for R448/R451 (and R453/R458) only if every hour is computed within 60 minutes,
  so skipped runs would leave few counted days. The workflow now also fires at :32 and :47; a scheduled run ticks
  only when R200's `ticks.csv` lacks the last closed hour, else it stops after the checkout and calls no API. The
  book recorder (`claude-xyz-books.yml`) also fires at :27 and :47 and records only if the data branch has no commit
  in the current UTC hour, so it keeps one snapshot an hour. No frozen script, rule or journal changed.
- **2026-11-11, a clock for the time-bound runs (`claude-clock.yml`).** The catch-up crons were not enough: GitHub
  started no run of `claude-flow-paper.yml` or `claude-xyz-books.yml` from 08:53 to 09:56 UTC, and Codex's hourly
  workflows show scheduled starts 40-90 minutes after their cron minute. Hour 08:00 was computed by a manual dispatch
  at 09:56. A `workflow_dispatch` starts within seconds, so one runner now stays awake for about 5 h 45 min and
  dispatches `claude-xyz-books.yml` at :07/:35 and `claude-flow-paper.yml` at :14/:40 (both with `if_due`, the same
  check as their crons: R200's hour due 12 minutes after its close, one book snapshot an hour) and
  `claude-usopen.yml` at 09:20 New York on weekdays, then dispatches itself; a 3-hourly cron restarts a lost chain.
  Before 2026-11-12 nothing counts for R448/R451, so the clock is in place for their first day. Public repository:
  no minutes are billed. No frozen script, rule or journal changed.
- **2026-11-11, idea wave 4 and R460 (USDT mints).**
  - **The wave.** At the owner's request for wide batched research, eight Haiku lenses read the web. The lenses were:
    DEX funding, options, EU basis, papers, Hyperliquid quirks, vault methods, closed-market price discovery, and
    scheduled events. Every idea and where it sits in the lab is recorded in
    `research/intake/idea_wave4_20261111.md`, with 14 aliases (IW4-*).
  - **What is new.**
    - M512 (USDT mints) was tested.
    - M513 (earnings reaction on 24/7 stock perps) is queued; it needs a power count first.
    - M514 (ETF flows) is blocked: no free flow history.
    - The rest already sits in tested or blocked rows. For example, Hyperliquid-Lighter carry is R288, below the
      hurdle.
  - **R460 `usdtmint_v1`: NULL.** It covers 262 Tether Issue events on Tron and Ethereum from free APIs (TronGrid and
    Blockscout). BTC 24 h: +23 bp per trade against a +6 bp placebo, Holm p 0.40, negative in the holdout, -3.4 bp at
    2x cost. BTC 4 h: p 0.44. 30 trials; program total 9,785,037.
- **2026-11-11, R461 `earnperp_v1` (M513, earnings on 24/7 stock perps): NULL.**
  - 1,735 EDGAR 8-K Item 2.02 filings timed to the second; MEXC hourly stock perps. Sample B (the Q3 season) was
    fetched after the freeze into `data/mexc_stock_post`.
  - After-close filings: the perp's first move does not continue or reverse on average. Next close +22 bp (n 219,
    Holm p 1.0, MDE80 127 bp); next open +1 bp. Both lose at 1x (30 bp).
  - Diagnostic lead only: before-open filings held to the close +80 bp in A, +70 bp in B (raw p 0.03 of 32 cells). It
    needs a new prospective lane on fresh filings (season from 2027-01). 32 trials; program total 9,785,069.
- **2026-11-11, idea wave 5 and R462 `xyzwknd_v1`: gate-0 PASS (recorded PARTIAL).**
  - **The wave.** Eight more Haiku lenses read the web: off-hours stock events, fee levers, Hyperliquid public state,
    the xyz oracle, passive quoting, venue price history, buybacks and macro proxies. The record is
    `research/intake/idea_wave5_20261111.md`, with 12 aliases (IW5-*).
  - **New queue rows:** M515 (tested); M516 (QUEUED, overnight offerings); M517-M519 (BLOCKED).
  - **R462.** On trade.xyz (France-reachable, growth-mode fee 0.9 bp), US-stock perps price themselves on a 30-minute
    EMA from Friday 20:00 to Sunday 20:05 New York. Fading weekend moves of at least 50 bp from Sunday 19:00 to 22:00
    earns +42 bp per market-weekend in A (18 weekends, Holm p 0.004, net 2x +29 bp) and +36 bp in B (6 weekends).
    Held to Monday 10:00 it is NULL (noise).
  - **Caveats:** prices are last trades and costs are assumed.
  - **Next:** the forward lane R463 at recorded xyz book costs. 32 trials; program total 9,785,101.
- **2026-11-11, R463 `xyzwknd_fwd` frozen (RUNNING, PENDING), before the first weekend (Friday 2026-11-13).**
  - **Measure A decides:** R462's frozen rule at that day's taker fee and the $1k book cost recorded on
    `claude/xyz-books-data`.
  - **Measure B must agree:** point-in-time tickets. `claude-xyzwknd-tick.yml` decides at Sunday 19:00 New York from
    the candles then available, walks the live book, and walks it again at 22:00.
  - **Reads:** futility at 15 traded weekends; PASS at 20 (p < 0.01) or 30 (p < 0.04) only if the tickets cover two
    thirds of the weekends with a positive mean. Scored daily by `claude-xyzwknd.yml`.
  - 1 trial; program total 9,785,102.
- **2026-11-11, idea wave 6 (six Haiku web lenses) and R464 `xyzns_wknd_v1` NULL.**
  - **Intake:** `research/intake/idea_wave6_20261111.md`. New rows M520 (tested), M521-M523 (UNTESTED: crypto-linked
    stock perps against BTC's weekend move, month-end rebalancing, end-of-day momentum); notes on M515, M447, M492.
  - **Correction:** the Blockworks/HPC slope of 0.834 has the reopen move as the dependent variable. The perp gives
    back about a sixth of its weekend move, which supports R462's fade rather than contradicting it.
  - **R464.** R462's rule on xyz's 14 index, commodity and FX perps: A +2.7 bp at |W| >= 25 (p 0.86), +1.9 bp at
    |W| >= 50 (p 0.93), net negative from 1x. B (6 weekends) was +75/+102 bp but cannot rescue A. The overshoot is
    at most a stock-perp effect; R463 still decides it forward.
  - 40 trials; program total 9,785,142.
- **2026-11-11, R465 `ltwknd_v1` PARTIAL, R466 `xvwknd_v1` INCONCLUSIVE, idea wave 7.**
  - **R465.** R462's frozen rule on Lighter's 50 shared US-stock perps at 0 fee: A +45.3 bp (p 0.005, net 2x +37.3),
    B +35.6, unseen C (February-April) -1.3 at Sunday 22:00. Lighter and xyz weekend moves correlate 0.96 (a venue
    replication). Post hoc: C gave the overshoot back at Monday 04:00-06:00, consistent with Lighter's equity oracle
    (Pyth Pro) lacking the overnight session before mid-2026. Earns a forward Lighter lane under a new id. 32 trials.
  - **R466 (new M524).** The xyz-versus-Lighter gap at Sunday 19:00: median 7.6 bp, decision cell n 55 < 100 in A;
    the closure looks like last-trade bounce (persistence 0.25). No forward lane. 10 trials.
  - **Wave 7** (`research/intake/idea_wave7_20261111.md`, six lenses): CME crypto is 24/7 since 2026-05-29, so the
    CME gap is gone; pre-IPO perps have too few conversions; M525 (US-holiday closure fade) queued UNTESTED; notes on
    M296, M475, M515.
  - Program total 9,785,184.
- 2026-11-11, R467 `ltwknd_fwd` frozen (`e9fb7621`) before the first weekend, earned by R465's PARTIAL.
  - R465's rule forward on Lighter's 50 US-stock perps from Friday 2026-11-13: A (traded candle closes, listed fee,
    recorded `lighter/books` $1k cost) decides; B (live book-walk tickets at Sunday 19:00 and 22:00 New York) must
    agree on two thirds of weekends. Futility at 15 traded weekends, PASS at 20 (p < 0.01) or 30 (p < 0.04).
  - Power from R465's weekends: PASS 79% at a 10 bp round trip on A + B, 39% if C's flat months recur; 5.4% at zero.
  - `claude-clock.yml` now dispatches R463's and R467's tick workflows at 18:10 and 21:10 New York on Sundays
    (GitHub's crons start 40-90 minutes late). Read R463 and R467 together (weekend moves correlate at 0.96).
  - Program total 9,785,185.
- 2026-11-11, R468 `asiaclose_v1` (M526, new): Asian single-stock perps (xyz 9, Lighter 9) across the weekday-night
  closure of KRX, TSE, HKEX and SSE, frozen (`72983781`) before any price.
  - Frozen verdict PASS, recorded PARTIAL: fade, A +87.8 bp (p 0.034, 65 days), B +9.5 bp (p 0.71, median -0.1).
  - A leans on the Hong Kong AI listings (ZHIPU, MINIMAX); KRX A +54.5 (p 0.12), B -13; TSE negative.
  - Post hoc: W lagged 1 h gives A +94.8 (p 0.015, not entry bounce), B -1.3. Same decay as R465's C.
  - Program total 9,785,237.
- 2026-11-11, R469 `asiaclose_c` frozen (`bcf3a776`) before its first opening: R468's rule and universe read once
  on unseen openings 2026-11-12 .. 2027-01-29 (sample C).
  - Decision: R468's cell, fade, one-sided day-clustered p <= 0.05 and mean > 2 units; 7 trials.
  - `claude-asiaclose-c.yml` runs it on 2027-02-01..04 at 07:41 UTC; the runner refuses earlier and reads once.
  - Power: PASS about 61% if A's +88 bp held, 8% if B's +9.5 bp is the truth. PASS earns a forward lane.
  - Program total 9,785,244.
- 2026-11-11, R470 `xvfund_v1` (M527) NULL. Short the venue (xyz or Lighter) paying more 7-day funding on the same
  US stock perp, long the other; 10 slots, taker costs, 4%/yr hurdle.
  - A (272 days) 1x excess -2.64 pts (t -1.22), 2x -5.55; B (71 days) +7.42 (t 0.71), mostly venue price noise.
  - Before costs A's excess is +0.28 pts (+1.79 after xyz's 2025-12-19 funding change): too thin at any cost.
  - 96 of 241 exits were forced by missing Lighter closes (56 on Sundays); six Lighter markets never traded.
  - Program total 9,785,245.
- 2026-11-12, R471 `cryptomon_v1` (M521) NULL. Wave 8 re-read M521-M523 on the web (owner: no shelving without it).
  Bitcoin's weekend return W against the Monday open-to-close move of MSTR, COIN, MARA and RIOT, 2020-09..2026-11.
  - A (173 sessions) slope +0.057 (t 0.48, detectable ~0.34); follow events +39.1 bp gross (t 0.54); B -30.0 bp.
  - The open gap carries the weekend: slope +0.91 (A) and +0.99 (B). B's negative-W rebound is three crash Mondays.
  - M522 (month-end rebalancing): the authors' sample runs to 2025, so only a forward lane on xyz SP500 is clean.
  - M523 (end-of-day momentum): lives on negative-gamma days, 18 of 504 sessions since 2024-11. Not registered.
  - Program total 9,785,247.
- 2026-11-12, R473 `tlteom_v1` (M528, new) PARTIAL. Found while R472 waited for FRED: Hartley and Schwarz's
  end-of-month Treasury rally (1990-2018) as a long TLT over the last 3 trading days, priced for xyz:TLT.
  - R (197 months, 2002-08..2018-12) +39.1 bp gross (t 4.15). U (94 months, 2019-01..2026-10) +24.7 (t 1.79); net
    1x +13.0 (t 0.95) at 5.8 bp + 5.5%/yr funding; 2x +7.2, 3x +1.4. 2026 -51 bp (10 months). IEF U +22.2 (t 3.26).
  - Post hoc: xyz:TLT longs paid a mean 20%/yr funding since listing (2026-09-17; median 5.5%), about 21 bp a hold.
    No lane on the perp; reopen only on a funded instrument or with month-end funding near base.
  - R472's FINDINGS must read its bond leg against that funding. Program total 9,785,249.
- 2026-11-12, R474 `tltcarry_fwd` (M529, new) frozen `b6d045f8`, forward. R473's funding fact turned around: long
  the UCITS 20+ year Treasury ETF (DTLA, London, USD, accumulating) and short xyz:TLT at 1/3 USDC margin. The perp
  follows TLT's unadjusted price, so the short keeps the coupon (~4.9%/yr) plus the funding longs pay.
  - About +13 points a year over the bill at the listing-mean funding, +4 at base, about 0 at zero funding.
  - Reads: held (after the freeze, reported only); futility 2027-02-13 (NULL if excess < 0); final 2027-05-15
    (PASS at >= 2 points, NW t >= 2.0). Program total 9,785,250.
- 2026-11-12 ~08:15 UTC: R472 and R475 closed; R476 fetching; owner reels read.
  - R472 `rebalfront_v1` (M522) NULL. FRED refused the frozen client from the container and from a GitHub runner,
    so DTB3 came from the Board's H.15 archive, byte-identical to FRED's file (`ce8a96cc`). R's Calendar×week4
    slope t is -1.67 (needs <= -2); U 2023-03..2026-11 +0.05 bp/day net (t 0.05); 2026 -2.11.
  - R475 `hip3stock_v1` (M530) frozen PASS recorded PARTIAL: A +11.18 pts/yr (t 2.03), 2x +9.79; carry only +5.56
    in A, -0.84 in B; one BIRD liquidation day ~5 pts of A; leave-BIRD-out +5.80 (t 1.92); weekly sd 0.72%.
    Earned forward lane to be designed after R476/R477: same-instant marks at the 16:00 New York close, measured
    xyz costs, a stated liquidation policy, honest power (weekly sd ~0.7%).
  - Owner reels: DfnLTPTCILu (Quant Guild model tier list) read, no test; DeoTlhAs0FE and DfnDCP9xLKi behind
    Instagram's login wall, not read. Program total 9,785,259.
- 2026-11-12 ~09:00 UTC: R476-R478 closed PARTIAL; R479 frozen (`61a7db1e`, 2 trials).
  - R479 `hip3carry_fwd` decides R475's rule forward on fresh weeks only, with the identity NaN fixed and costs
    from the hourly book snapshots. A test dispatch of `claude-hip3carry.yml` ran checkout, install and the
    snapshot worktree, and both reads refused before their dates. Program total 9,785,264.
