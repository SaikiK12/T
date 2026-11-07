# Deviations and fixes: carry_fwd (R220)

## 2026-10-19 (no ticket affected)
- **MEXC last prices are fetched uncached.** R215 is the single writer of `data/mexc/klines_1h` (AGENTS rule 4).
  Index prices stay in this lane's own cache, `data/mexc/index_price_1h`.
- **Binance TradFi contracts are excluded** before mapping to MEXC. No TradFi contract had a spot pair on either
  venue, so no position changes.
