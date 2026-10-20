# Critique of the program (2026-10-20)

On 2026-10-20 the owner asked for critics of how the project is run: how bad it is, how unserious, what to turn over.
Five subagents reported:
- an outsider;
- a strategist;
- a statistical referee;
- a docs planner;
- a scout for untried axes.

Three more were cut off by a rate limit: execution realism, engineering, and alternative data. They will be added
when they finish.

Every critic read the repository only. None placed orders or downloaded anything. Their numbers are their own and come
with their caveats; where this file acts on one, it says so.

## Verdict in one line
The process is serious and the decisions are not. The lab registers, freezes and counts well. But the only edge
that passed out of sample is carry at about 1%/yr, below a T-bill. The forward lanes cannot decide anything within
a year, and nothing defined a stop, a budget or a loss limit.

## The problems, worst first

| # | Problem | Source | What we do | State |
|---|---|---|---|---|
| 1 | **In-sample t 3.25 of the flow book is selection-contaminated.** The cells were picked on the same years from 338k atlas cells. R197 changed the construction after R196 failed. | referee | Every in-sample number is labelled gate 0 (exploratory). Read against program trials. | done (GATES, MAP, EDGE_SCOREBOARD) |
| 2 | **The holdout is spent.** More than ten lanes read it, and what they saw chose X2, book B and R218. | referee, outsider | Declared spent at program level today. Holdout numbers are exploratory. New evidence comes only from on-time days or never-read windows. | done (EDGE_SCOREBOARD) |
| 3 | **Holdout PnL is a few days and two coins.** Ten of 457 days are 113% of book A's PnL. BEAT and LAB are about 68% of gross. | referee | Trimmed mean and leave-two-coins-out become required in gate-1 tests. | rule in GATES |
| 4 | **go_real is close to a coin flip.** With zero edge it passes 16% of the time at 90 days. Its -40% tail check never binds. Six correlated lanes give a 37-58% chance that one passes by luck. | referee, outsider | go_real moved to gate 2 (execution), not the decision. `forward_tick.py` now writes `verdict: PENDING` until day 90. | done (GATES, `scripts/forward_tick.py`) |
| 5 | **Forward lanes cannot decide in useful time.** A Sharpe-1 book needs about 2,000 days for 80% power. R221's boundaries were frozen with a simulated size of 4.24% against 2.31% nominal. | referee, strategist | Lanes are futility screens. Decision dates are set. Faster evidence comes from event lanes (about 130 events for t 2) and, if the owner allows, tiny live calibration orders. | dates in GATES; owner ask |
| 6 | **Replay days counted as evidence.** R200 counts 18 replayed days, and lanes R214-R218 were designed after seeing them. | referee | Only strict on-time days count (`scripts/forward_lag.py`). The panel shows replay and on-time apart. | done |
| 7 | **One signal, many lanes.** R200, R214, R215, R218 and R225 share cells (correlation 0.4-0.99). | referee, outsider | They are one decision. No new lane on these cells after 2027-01-31. | rule in GATES |
| 8 | **The backtest is not the traded book.** It uses an ideal universe hedge, gross exposure drifting from 1.31 to 1.93, Binance costs on MEXC, no margin or squeeze model, and 50 coins in hourly slices that nobody can place by hand. | referee, strategist | Gate 3 needs a margin and liquidation replay. Gate 2 needs a daily-netted version of 15 orders or fewer. | rules in GATES |
| 9 | **Coin identity is not controlled.** The placebo is two time shifts. Effective sample = coin episodes. | referee | Coin-block permutation and listing-age controls go into the next flow test. | queued |
| 10 | **Positioning data covers 10-13% of coin-hours in 2021-22.** Book B's "5/5 years" is mostly taker. | referee | Stated in MAP. B's discovery is effectively 2023. | note |
| 11 | **Carry "confirmed" is about 1%/yr.** Its holdout t is 1.14 at 2x costs, and 0.80% of its 1.45% is basis. Funding has compressed from 11% (2024) to 2.2% (2026). | referee, strategist | Reworded. Kept running as a forward lane. Stock-perp carry (funding 14-17% on stock perps) is a new queue item. | done; queued |
| 12 | **Trial ledger.** It has 6 blank trial rows (e.g. R181), and R202 shows 0 trials although it took the best of 10 sizes. 88% of trials are correlated atlas cells. DSR and SPA exist but are unused on the headline books. | outsider, referee | Append-only adjustment rows for the missing counts. DSR/SPA over the real lineage goes into the next flow write-up. | queued |
| 13 | **Effort off goal.** R229-R232 were six-coin spot, there were claims from reels, and the AI loop acts as a data collector. | strategist, outsider | The owner widened the goal on 2026-10-20 (any market), so spot is in scope. Every lane must name the gate it can reach. | done (objective) |
| 14 | **The strongest old edge is parked.** The unlock short (R179: 414 events, +2.5% per event, p 0.002) needs the DefiLlama calendar. | strategist | Owner ask, repeated on the panel. | waiting on owner |
| 15 | **Docs bloat.** There are 38 docs, one book has four names, and some pointers dangle. | outsider, docs plan | Reorganise into audits/, notes/, sources/ and archive/ with "moved from" headers. PREREG links stay valid. | queued |
| 16 | **No stop, no budget, no loss limit.** | outsider, strategist | Dates and proposed stake and max loss in GATES. The owner sets the numbers. | proposal |

## Claims withdrawn or reworded (referee list)
- "The holdout was read once per family": it was read by more than ten lanes. Reworded in EDGE_SCOREBOARD.
- "Carry confirmed" and "the only edge confirmed on a holdout": carry passed a single test at 1x and fails at 2x.
  Reworded in EDGE_SCOREBOARD and MAP.
- "Best holdout t" (crypto-only top-vs-crowd): it is the best of 7 series, it falls to t 1.6 without its top 10 days,
  and its MEXC replay is -0.6 bp/day. Reworded in both files.
- "+42.6%/yr, t 3.25, positive all 5 years": this is selection-contaminated, and B has almost no positioning data in
  2021-22. Annotated in both files.
- Prop-challenge payouts (R202): scenario illustrations on an unconfirmed stream. Annotated in MAP.
- Frozen PREREGs say "a forward period no one has seen" (R218) and "nothing after 2026-09-30 looked at" (R199/R200).
  Both are wrong now that the replay was seen. **These files are frozen and are not edited.** This list is the
  correction.

## Where the critics and the owner disagree
- **The critics want focus:** one primary book, a kill date, stop mining.
- **The owner wants breadth:** brute force every method in every market, even the bad-looking ones.
- **This program does both, kept apart by the gates:**
  - **Search is wide and cheap.** Every queued method gets tested, in any market we hold data for: perps, spot, forex,
    index futures, prop-challenge economics. Every result is gate 0, counted in the trial ledger, and a null is
    recorded.
  - **Evidence is narrow and slow.** Only gates 1-3 can move money, and gates 1-3 accept only unseen days. A screen
    that looks good becomes one frozen forward lane under a new id. It does not become a claim.
  - **Breadth is budgeted.** One method is in test at a time, finished before the next (one-piece flow). Forward lanes
    are capped by the 2027-01-31 freeze.

## Untried axes (scout, added to the queue as M170-M199)
The scout's top picks are now in the queue:
- weekly momentum and reversal split by OHLC-liquidity tier (M034, M178, M181);
- next-funding revision (M172);
- daily MAX, IVOL and skew (M180);
- the MEXC-vs-Binance gap (M187, blocked on the MEXC history download);
- the listing-announcement ladder (M190);
- dated-futures basis (M170);
- TradFi perps over the weekend (M188);
- the USDT peg (M189).

The owner's breadth request adds forex and cross-asset rows:
- G10 forex (M193);
- cross-asset time-series momentum (M194);
- NASDAQ overnight vs intraday (M195), turn-of-month (M196), VIX spikes (M197);
- BTC weekend to the NQ Monday gap (M198);
- prop-challenge EV on index futures (M199).

The daily data for these comes from `lab/markets.py` (Yahoo, a few MB).

Dead ends the scout found:
- Binance liquidation snapshots stopped in 2024.
- `allForceOrders` returns 404.
- MEXC insurance-fund history covers only about 7 days, so it needs a recorder.

## Asks for the owner (also on the panel)
1. Yes or no: download the DefiLlama unlock calendar to replicate E01, the strongest old edge.
2. Yes or no: download the MEXC public history (about 9.4k requests) for MEXC-only coins and the MEXC price gap.
3. Yes or no: 20-30 tiny live MEXC orders, placed by the owner, to measure fills against paper. This is a rule-6
   carve-out.
4. Set the stake and max loss in `docs/GATES.md` gate 4.
5. Rotate the two Coinalyze keys pasted into the old chat.
