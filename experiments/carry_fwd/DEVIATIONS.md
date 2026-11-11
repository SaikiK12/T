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

## 2026-11-11, MEXC requests paced on GitHub's runners (no ticket affected)
- On GitHub's shared runners MEXC refused part of R220's burst of requests with code 510 ("Endpoint rate limit
  exceeded ... scope: IP"), after R215 and R218 had used the same IP. `lab/mexc.py` raises at once on such a reply
  and R220 wrote nothing (runs 42933784241 and 42939724639; the last ticket stayed 2026-11-05).
- The workflow, now hourly at :17, runs the script through `scripts/run_paced_mexc.py`: MEXC requests at most every
  0.25 s, and each 510 retried after 5, 15 and 45 s. `scripts/forward_carry.py` and `lab/mexc.py` are unchanged; a
  fetch that succeeds returns the same data as before, so the rule and every value are unchanged.
