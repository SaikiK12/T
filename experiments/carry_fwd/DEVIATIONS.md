# Deviations and fixes: carry_fwd (R220)

## 2026-10-19 (no ticket affected)
- **MEXC last prices are fetched uncached.** R215 is the single writer of `data/mexc/klines_1h` (AGENTS rule 4).
  Index prices stay in this lane's own cache, `data/mexc/index_price_1h`.
- **Binance TradFi contracts are excluded** before mapping to MEXC. No TradFi contract had a spot pair on either
  venue, so no position changes.

## 2026-11-11, writer change: GitHub Actions
- The local loop ticked this lane until 2026-11-06 13:00 UTC (last journaled hour), when the container stopped. From
  2026-11-11 the only writer is `.github/workflows/claude-flow-paper.yml` (every 2 hours at :41 UTC). It runs the
  frozen scripts unchanged, in the task order of `lab/operations.py`: R200, R214, R215, R218, R221, R225, then R220.
- The hours and days from 2026-11-06 14:00 UTC were computed late, on the first run, from the same public endpoints:
  Binance 5-minute ratio history (kept 30 days), klines and funding, and MEXC klines and funding. Every row still uses
  only data stamped at or before its hour. The frozen code labels these days on-time (`ms >= ON_TIME`). They are
  flagged here as written after the fact.
- The caches `data/live` and `data/mexc` (gitignored) live in the Actions cache. The first run refetches them from the
  public APIs. MEXC contracts are mapped with that day's snapshot, as before.
