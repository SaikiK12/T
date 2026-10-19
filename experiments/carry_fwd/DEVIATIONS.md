# Deviations and fixes: carry_fwd (R220)

## 2026-10-19 (no ticket affected)
- **MEXC last prices are fetched uncached.** R215 is the single writer of `data/mexc/klines_1h` (AGENTS rule 4).
  Index prices stay in this lane's own cache, `data/mexc/index_price_1h`.
- **Binance TradFi contracts are excluded** before mapping to MEXC. No TradFi contract had a spot pair on either
  venue, so no position changes.

## 2026-10-19 (forward-code integrity fixes; no tickets recomputed)
- **Failed feed handling:** all requested funding and price streams must return successfully before this script writes
  tickets. A successful empty funding response remains distinct from a failed request, since funding is sparse between
  settlements.
- **Scoring coverage:** a held hour with a missing/non-finite basis endpoint or a missing/non-finite traded cost is
  unknown. Its whole UTC day is deferred and can be picked up on a later successful run. The carry kernel's legacy
  archive behavior remains the default; strict completeness is enabled only by this forward monitor.
- **Closed-hour bound:** R200's future/open tick rows are excluded at load time.
- **Decision status:** the script now reports the frozen 90-day R220 PASS/FAIL/INCONCLUSIVE rule using the first 90
  complete on-time calendar days per venue. It remains pending while any day in that window is missing; later days
  cannot revise the decision.
- **MEXC mapping:** apply R215's static plus current TradFi exclusions and reject ambiguous venue mappings before
  fetching per-contract series.
- These changes affect future runs only. Existing append-only tickets were not rewritten or independently re-scored.
  This checkout has no live venue snapshot or current R200 feed with which to validate a new paper ticket.
