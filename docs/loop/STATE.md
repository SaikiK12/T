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

**Standing duties** (`docs/OPERATIONS.md`): R404's close on 11-18, and the R406/R413 successors after 11-19.
R392 is being done now.

## Lenses last used
1, 2, 3+4 (tick 1); 5, 6+7 (hunt wave, 2026-11-09). Next: 8 (market making for the slow), then 1.

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

