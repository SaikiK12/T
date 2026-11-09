# Edge loop state

This is the loop's working memory for `docs/loop/PROMPT.md`. The live queue stays `registry/methods.csv`. This file
holds only the current focus, the lenses last used and one line per tick.

## Current focus
- **Tick 2: the M321/M188 weekend-reopen test on held data.**
  - **Data:** Binance TradFi perps, 1-minute klines in `data/tradfi_perps/klines_1m`.
    - QQQUSDT and SPYUSDT from 2026-04-06.
    - XAUUSDT from 2025-12-11 and XAGUSDT from 2026-01-07.
    - CLUSDT, BZUSDT and NATGASUSDT from 2026-04-01.
  - **The question:** at the CME reopen (Sunday 22:00 UTC in summer, 23:00 UTC in winter), does the perp continue or
    reverse its weekend move over the next 15-60 minutes and into the cash open?
  - **Who pays:** weekend traders on thin perp books, before the reference market reopens.
  - **Why the fast firms might leave it:** the weekend books are small, and the payoff needs a hedge-less hold of
    minutes to hours.
  - **Priors against:** an unread paper reported in M442 found negative out-of-sample Sharpe after costs. R244 (BTC's
    weekend move into QQQ and SPY) is a different question and was NULL.
  - **Before freezing:**
    - Check coverage and the Binance TradFi taker fee.
    - Cluster by weekend; seven assets share each one.
    - Split commodities at the 2026-05 EWMA mark change (M188 note); count the split as trials.
    - State power: about 30-47 weekends.
- **Standing duties** (`docs/OPERATIONS.md`): the R392 freeze before 11-17 (check-in fires 11-16 11:20 UTC), R404's
  close on 11-18, and the R406/R413 successors after 11-19.

## Lenses last used
1, 2, 3+4 (tick 1). Next: 5 (red team on R391, R300 and R265/R266), 6 (forced and scheduled flow), 7 (cross-market
gaps reachable from France).

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
