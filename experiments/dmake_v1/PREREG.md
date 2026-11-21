# PREREG: dmake_v1 (R522). Make on Deribit's thin new perps, hedge on Hyperliquid: a simulation from full trade history

Freeze with `lab.prereg.freeze()` before the trades are fetched. Never edited afterwards.

- **Registry id:** R522
- **Owner (single writer):** the Claude session that froze it. `scripts/fetch_deribit_trades.py` is the only writer
  of `data/deribit_trades/`, and `scripts/run_dmake.py` the only writer of `experiments/dmake_v1/results/`.
- **Date registered (UTC):** 2026-11-21

**Methods:** M561 (new: cross-venue market making, make on the thin venue, take the hedge on the liquid one).
Liquidity provision (family P4).
- **Paper only:** public data; nothing can place an order.

## Why
- **The breakthrough review** (`docs/reviews/breakthrough_20261121.md`), Bet 2: turn the cost into income.
- **Who pays:** impatient takers on thin new books.
  - Deribit opened about 130 linear USDC perps in 2026-08..11. 67 of those created 2026-08..10 are also on
    Hyperliquid.
  - They printed 40 to 2,200 trades on 2026-11-10 (8 coins counted; trade counts only).
- **R513:** a resting Kraken order saved about 8 bp a side at a 1-hour fallback.
- **The data.** Deribit's history server serves every trade with the index at that moment, so this can be read on
  history.

## How it loses money (written first)
- **Adverse selection.** A taker who trades through our quote often knows the index is moving. The fill then comes
  just before the index moves against us, and the hedge is worse.
- **Latency.** Our quote uses the index 2 seconds old. A real quoter is slower or faster than that.
- **Queue.** We assume a fill only when a trade prints strictly through the quote. That misses fills at the quote
  (conservative) and ignores queue position ahead of us at better prices.
- **Hedge basis.** We hedge at Deribit's index. Hyperliquid's price can differ by a few bp, and that is not modelled.
- **One-sided flow.** Inventory piles up on one side until the cap stops it, and units left at the end pay full taker
  costs.

## Break-even, written before the freeze
- **Cost per fill:** 1.5 bp maker fee on Deribit, plus 4.5 bp taker fee and 2 bp half-spread on Hyperliquid, so 8 bp.
- **The bar.** At k = 15 bp from the index, the fill earns 15 bp less the move of the index between the quote and
  the fill. So the book pays only if adverse selection is under about 7 bp a fill.

## Supply and power
- **Universe:** the 67 coins (`scripts/fetch_deribit_trades.py universe`), from creation + 3 days to 2026-11-20,
  about 20-110 days a coin.
- **Supply:** a median coin printed about 550 trades a day on 2026-11-10. With at most one fill per side per minute,
  fills are expected in the thousands.
- **Power.** The decision is a day-clustered NW t on the daily dollar PnL over about 80 days. A mean edge of ±1 bp
  across thousands of fills gives |t| well above 3. A null near 0 is clear.

## Rule (`scripts/run_dmake.py`)
- **Quotes.** bid = I(t − 2 s)(1 − k) and ask = I(t − 2 s)(1 + k). I is the index on the last trade at or before
  t − 2 s.
- **Fill.**
  - A taker sell strictly below the bid fills it; a taker buy strictly above the ask fills it.
  - At most one fill per side per coin per 60 s. One unit is $500.
  - Inventory is capped at ±10 units per coin.
- **Edge of a fill:** see the runner docstring. Hedge at the fill trade's index with h = 6.5 bp; Deribit maker 1.5 bp.
- **End of window.** Units left are closed at Deribit taker (3.5 bp) plus h.
- **Primary:** k = 15 bp.
- **Secondary (reported):** k = 5, 10, 25 and 40 bp.
- **Costs at 2x and 3x:** every fee and h doubled or tripled.
- **Not counted:** funding on inventory, the Deribit-Hyperliquid basis, and venue points.

## Decision (primary, k = 15 bp)
- **UNREADABLE:** fewer than 30 days with fills.
- **PASS:** all of these hold:
  - the NW t (lag 5) of daily dollar PnL is at least 3.0;
  - the dollar PnL per day at 2x costs is above 0;
  - the PnL per day without the two best coins is above 0;
  - both halves of the days are positive.
- **FAIL:** otherwise.
- **Also reported:**
  - mean, median and share-positive edge per fill;
  - fills per coin per day;
  - 3x costs;
  - the secondaries.
- **What a PASS earns:** a forward paper lane that quotes on live books (a new id), with Hyperliquid's live hedge
  price.

## What the author has seen
- Trade counts for 8 coins on 2026-11-10, and the history server's fields (names only).
- Deribit's daily funding and prices for these coins (R519).
- No trade-level price was examined.

## Trials
- **This round:** 5 (the primary and four reported k values).
- **Program trials:** 9,785,765 before, 9,785,770 after.

## Inputs
| File | sha256 |
|---|---|
| `scripts/fetch_deribit_trades.py` | 66a00945bd7720356050580b896d839c27b9f5022790085b41287c684737fb58 |
| `scripts/run_dmake.py` | 38ee9ccce043ea336a47115f67f6f8fed59bdf8a0a28ab491cf40747daed61fc |
| `tests/test_dmake.py` | 7c5e9ff94459c3ba6b32618a6f7ac88182268f67360ea59fc6d051e4c19ea759 |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 |
| `scripts/run_xfund_bfx.py` | 62c1c214856c80b5006527824778815069cf341b740bb5d48c4d646364d30b79 |
| `data/deribit_perps/instruments.json` | 113acd9629e53914ccfc7612c9ccd8ad23954fa049d588c29d1e4e2a1c4aaeab |
| `experiments/deribitgap_v1/results/symbols.csv` | 8809f6ccc93191b9244623f209647637d72b802ec35cfdd680475e9409d2fe98 |
