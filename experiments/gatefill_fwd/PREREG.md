# PREREG: gatefill_fwd, a resting order on Gate's leg of C14, hedged on Binance, forward on paper

Freeze with `lab.prereg.freeze()` before the first tick. After that this file is never edited.

- **Registry id:** R498
- **Owner (single writer):** Claude (session claude/yo-9a1k5w); the only writer of the journal is the GitHub workflow
  `.github/workflows/claude-gatefill.yml`.
- **Date registered (UTC):** 2026-11-16
- **Method:** M546, lever 2 of `research/intake/fee_map_20261116.md`. Earned by R497 `gatemaker_v1` (LEVER_HOLDS).

## Question
For R390's C14 book (Binance + Gate carry) at $5k a leg, is it cheaper to:
- rest the Gate leg as a limit order, take the Binance leg 5 seconds after each Gate fill, and cross whatever is still
  unfilled after 60 minutes;
- than to cross both legs at once?

It is measured forward on paper from the first tick after this freeze until 2026-12-01 00:00 UTC.

This lane measures cost and tests no return: **0 trials**. It never changes R390's decision.

## Why
- **R497** found the lever holds in every volume band on Gate's tape, at a 2 bp and at a 4 bp maker fee. But it let
  every trade at the touch fill the resting order.
- **What this lane adds:**
  - the displayed queue ahead at placement;
  - fills only by trade-through, or by volume at the price beyond that queue;
  - the time to fill;
  - the chase when the price leaves;
  - the Binance hedge's own move, which is where adverse selection shows up for a hedged leg.

## Universe and placement
- **Contracts:** each tick, the Gate contract of every position that R390's book A holds, read from
  `experiments/xfund_bg_fwd/journal/tickets.csv` at the tick and mapped by `experiments/xfund_v1/symbols.csv`.
- **Ticks:** every 2 hours, at minute 47, by the workflow.
  - GitHub may start a tick late or drop it. Orders are placed whenever a tick runs, never chosen on outcomes.
- **Live reads at placement, per contract:**
  - Gate's `order_book` (100 levels) and contract fields (quanto, tick size, listed maker fee);
  - Binance's `depth` (100 levels) on www.binance.com.
  - t0 is the Gate book's server time (`current`).
- **Paper orders, per contract and tick:** a bid and an ask, each of $1k and $5k notional.
  - **touch:** at Gate's best price, behind the size displayed there.
  - **inside:** one tick inside the spread, first in its queue. Only when the spread is at least 2 ticks.
  - **primary:** inside when it exists, else touch. This is what a resting order would do when there is room.
- **Recorded before settlement, in `journal/orders.csv` (append-only):**
  - the order, its queue ahead;
  - the Gate and Binance mids at t0;
  - the taker cost of each venue for the same side and size, walked through its shown book (bp from the mid,
    without fee).

## Settlement (at the first tick at least 70 minutes after t0)
- **Tapes:**
  - Gate's public trade tape over [t0 − 300 s, t0 + 3,900 s], with R497's frozen pager (`scripts/run_gatemaker.py`).
  - Binance's public aggTrades over [t0 − 300 s, t0 + 3,606 s].
- **Fills** (Gate's taker sign: positive size = taker buy):
  - A resting bid is reached only by taker sells after t0.
  - At its price, they first consume the queue displayed ahead of it at placement, then fill it.
  - Any taker sell below its price means the level emptied, so the rest fills at that moment.
  - Asks mirror this.
  - Cancellations ahead are not credited, so fills are slower than reality. Orders joining after it stand behind it.
- **Horizons:** 60 minutes decides; 15 minutes is reported.
- **Mids:** R497's two-sided proxy, the mean of the last taker-buy and last taker-sell prices, each at most 300 s old.
  It is applied to the Gate tape at t0 + horizon and to the Binance tape at each hedge time.
- **Pair cost of the maker route (bp)**, for a Gate order of side D (+1 bid, −1 ask), with fill fractions w_i at times
  τ_i:
  - Gate fills: Σ w_i · D · (P − m_g0) / m_g0;
  - plus the Binance hedge's move: Σ w_i · D · (m_b0 − m_b(τ_i + 5 s)) / m_b0;
  - plus the unfilled share c crossed at t0 + horizon:
    c · [D · (m_g(t0 + h) − m_g0) / m_g0 + the t0 Gate taker cost + 7.5 bp + D · (m_b0 − m_b(t0 + h + 5 s)) / m_b0];
  - plus the Binance taker cost at t0 and 5 bp on the whole notional;
  - plus the maker fee on the filled share: 2 bp decides; 4 bp and the contract's listed rate are reported.
- **Pair cost of the taker route (bp):** Gate taker cost at t0 + 7.5 bp + Binance taker cost at t0 + 5 bp.
- **Saving** = taker route − maker route. A price move common to both venues cancels.
- **A settled row is invalid** (kept, with its reason) when:
  - a tape did not reach its window;
  - a needed mid is missing;
  - a shown book was too thin for the taker cost;
  - or settlement still fails 5 days after t0.

## Reading rule (frozen)
- **Primary sample:** valid settled rows of primary $5k orders at 60 minutes, placed before 2026-12-01 00:00 UTC.
- **Statistics:**
  - mean saving;
  - median saving;
  - a cluster-robust t of the mean, clustered by tick;
  - the leave-two-contracts-out mean: the mean without the two contracts with the largest summed saving.
- **Verdict:**
  - **INSUFFICIENT_DATA** if fewer than 300 orders, or fewer than 10 distinct UTC days.
  - **MAKER_ROUTE** if the mean > 0, t ≥ 2.0, the median > 0 and the leave-two-contracts-out mean > 0.
  - **NO_GAIN** otherwise.
- **When it is read:** `journal/status.json` carries these figures at every tick; before the end they are interim and
  decide nothing. The reading is the first status with `"final": true`. That is the first tick at or after
  2026-12-01 00:00 UTC at which every order placed before then has a settled row.
- **Reported beside, deciding nothing:**
  - the $1k size;
  - touch-only placement;
  - the 15-minute horizon;
  - the maker fee at 4 bp and at the listed rate;
  - fill fractions and times;
  - per-contract figures;
  - C14's net re-priced at the measured pair cost, on R495's linear fit (arithmetic, flagged as such).

**What follows:**
- **MAKER_ROUTE:** the measured maker pair cost becomes C14's execution cost for any later real C14. R390's paper
  verdict and `lab.gate.go_real()` still decide, and real money stays the owner's act.
- **NO_GAIN:** M546 is closed for Gate at a 60-minute rest.

## Known limits (stated before the first tick)
- **These are paper fills.**
  - Hidden or iceberg orders on Gate are not seen.
  - Other traders may react to a real order, for example by stepping ahead of it.
  - Latency between the book read and a real order is not modelled.
- **The Binance hedge is priced from t0's book:** its book at the hedge time is not seen. The chase on Gate is priced
  at the Gate mid at t0 + 60 min plus t0's Gate taker cost, because Gate's book then is not seen either.
- **Exclusions:** orders whose shown book is too thin for a taker are invalid. That leaves out some of the thinnest
  books, where the saving could be largest.
- **Sample:** R390's book changes only by its own frozen decisions. Twenty contracts at a time, about two weeks, ticks
  at GitHub's timing.
- **Scope:** entry and exit cost only. The carry's funding is R390's.

## Costs at 1x / 2x / 3x
- This lane measures cost and tests no return.
- In place of the 1x/2x/3x sensitivity, the saving is reported:
  - with the maker fee at 2 bp (decided), at 4 bp and at the listed rate;
  - at $1k and at $5k.

## Plumbing before the freeze
- On 2026-11-16 around 19:05 UTC, one placement tick wrote into a scratch directory, not this lane's journal. It read
  144 paper orders on R390's 20 contracts; they were not kept.
- One settlement with a backdated t0 read about 70 minutes of the INIT_USDT and UNITREE_USDT tapes on both venues.
  Only validity counts were printed: 16 and 12 valid rows of 16. No cost or saving value was printed.

## Stop rules
- No order is placed at or after 2026-12-01 00:00 UTC. Nothing is retuned, and a changed idea is a new lane.
- The journal is append-only and written only by the workflow. A fix to the workflow file may not change the
  measurement. A fix to the frozen script means a new lane.
- No orders, no money, no credentials.

```inputs
dbaa160fd2fb502fa21322a31ffd0fbe055799223c5af692a5c809759794290f  scripts/forward_gatefill.py
9dd0adada41e94910fdbce9a5f37a1f6e15813e1061c9afd89da7ed2722544a1  tests/test_gatefill.py
d619df0228705122750d01a6ea75d4e66c6163fd68d3e2fa2fa5c98a2a94d837  scripts/run_gatemaker.py
78201a341b9fc498b67f4893f1dd30d67d790d94ca8257a4b1a2ce8f569ab8e0  experiments/xfund_v1/symbols.csv
863e96764478d1da8c03d32cb50c58a638869d3f2bbfb557d1d06a42516d3d3a  experiments/gatemaker_v1/FINDINGS.md
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
```
