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
