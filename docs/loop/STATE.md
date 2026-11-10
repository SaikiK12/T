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

**Wave 1, launched about 22:50 UTC:**
| Round | Lane | Method | What it tests |
|---|---|---|---|
| R432 | weekend_reopen_v1 | M321/M188 | Binance TradFi 1-minute perps at the CME reopen: **NULL** (gate-0 screen) |
| R433 | lighter_flow_v1 | M441 | Lighter public account flow, follow the informed accounts: **NULL** as a trade; the information persists |
| R434 | wti_residual_v1 | M443 | Cross-venue commodity residual, CME open vs closed |
| R435 | stock_tugofwar_v1 | M492, new | Overnight vs intraday cross-section on MEXC stock perps |
| R436 | stock_carry_v1 | M493, new | Stock-perp funding carry hedged with the cash stock |
| R392 | reserved_batch3 | C17 on 2020 + Gate long-tail carry | The owner approved reading it today, not 11-17 |

**Wave 2 candidates:**
- The unlock-short red-team checks: skipped tickets against their outcomes, and margin per event at $10k.
- M494, once a dated history of index changes exists.
- The M296 HIP-3 convergence event study.

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
