# Deviations and fixes: flow72_fwd3 (R214)

R214 reads R200's signals, so R200's `DEVIATIONS.md` applies here too.

## 2026-10-19
**`run_at` was read in seconds, not milliseconds.** Pandas 3 parses the run-time strings to microseconds, and
the code divided by 10^6 as if they were nanoseconds.
- **Effect:** every realized lag was clamped to one bar, so the reported `A_rt` book equalled `A`, and
  `run_at_lag_min` would have been wrong.
- **Fix:** milliseconds are now computed whatever unit pandas parses to.
- **Tickets affected:** none. `A_rt` is reported, not decided, and no on-time day (from 2026-10-20) had been
  ticketed.

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
