# PREREG: mexc_costs (R224), what a taker order costs on MEXC for the coins the forward books trade

Freeze with `lab.prereg.freeze()` before the first snapshot. Never edited afterwards; a change is a new lane.

- **Registry id:** R224
- **Owner (single writer):** the session that froze it
- **Code:** `scripts/record_mexc_depth.py`, `lab/mexc.py`, `lab/engine.py` (`cost_matrix`)
- **Why:** every forward book on MEXC charges Binance's tier costs:
  - R215, R218, R220 and R221 all use them;
  - the tiers are 6/8/12/20 bp one way by liquidity rank <= 20 / <= 50 / <= 100 / beyond, and cover fee plus
    slippage.
  - The model has never been checked against MEXC's own order book. The owner trades on MEXC, so the cost a real order
    pays there decides how much of a paper edge is achievable.
- **Trials:** 0. This lane measures a cost and tests no strategy.

## What the author had seen
- `docs/MEXC_EDGES.md`:
  - spreads of 0.9-2.3 bp on a handful of zero-fee contracts, from one look by a subagent;
  - thin depth within 0.5% on small names.
- MEXC web taker fees from the 2026-10-19 contract snapshot: 2 bp on most crypto contracts, 0 on zero-fee contracts,
  4-10 bp on a few. API orders pay 8 bp taker since 2026-06-01 (MEXC notice).
- One depth call for BEAT_USDT (2026-10-19, while writing the code): about 0.3 bp spread.
- No cost has been computed from MEXC depth in this lab.

## Snapshots (forward only)
- **When:** each forward tick (`scripts/forward_all.sh`, about twice an hour, at minutes 13 and 43), after R215.
- **Universe:** the symbols R200 lists as eligible at its latest journaled hour (its top 50).
  - Each maps to a MEXC crypto contract with `mexc.map_symbols`.
  - Binance TradFi contracts are excluded (the R216 list plus today's `live.tradfi()`), as in R215.
- **Data:** `depth/{contract}?limit=50` from MEXC's public contract API, plus today's contract snapshot for fees and
  contract size.
- **Per contract and snapshot:**
  - best bid and ask;
  - mid = (bid + ask) / 2;
  - half-spread in bp;
  - for notionals of $1k, $10k and $50k on each side, the impact: the VWAP distance from mid in bp, walking the book
    shown. It is NaN when the 50 levels shown cannot fill the order.
  - USDT depth within 0.5% of mid on each side, and how far the 50 levels reach. When they reach less than 0.5%, the
    depth is a lower bound.
  - the contract's web taker and maker fee.
- Rows are appended to `journal/depth.csv`, never rewritten. A failed request skips that contract for that snapshot
  and is logged.

## Measures (written to `journal/status.json` at every snapshot)
- **One-way taker cost of a $10k order** = fee + mean of buy and sell impact.
  - **Web:** fee = the contract's web taker fee.
  - **API:** fee = 8 bp.
- **Assumed cost:** the tier cost (`engine.cost_matrix`) at the coin's median R200 rank over the snapshots.
- **Per coin:** the medians over snapshots of half-spread, impact at each size, and web and API cost at $10k and $50k.
- **Summary over coins:**
  - the median of each per-coin median;
  - the share of coins whose median web cost at $10k exceeds the assumed cost, and the same share for the API cost;
  - the number of coins where a $50k order could not be filled from the levels shown in more than half of the
    snapshots.

## Report
- **When:** first at 2026-11-03, after 14 days of snapshots. It is updated at each snapshot after that.
- **Reading, fixed now:**
  - If the median coin's API cost at $10k exceeds its assumed cost, the forward books' 1x column is optimistic for
    API trading, and their 2x column is the one to read.
  - If the median coin's web cost at $10k is below half its assumed cost, the 1x column is conservative for manual
    trading.
- **Report only.** No frozen lane changes its cost model or decision because of this lane.

## Known limits, stated in advance
- **Timing.** Snapshots fall at minutes 13 and 43, not at the hour close when the books trade. Spreads around the close
  may differ.
- **The book shown is not the book filled.** Hidden or fleeting orders, and the book's reaction to a large order, are
  not seen. Impact at $50k is a lower bound on what such an order would pay.
- **Contract sizes come from the day's snapshot.** A size change during the day is not seen until the next day.
