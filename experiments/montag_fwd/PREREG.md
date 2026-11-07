# PREREG: montag_fwd (R270). The Monitoring Tag short at +24 h, forward on MEXC paper

Freeze with `lab.prereg.freeze()` before the first ticket. Never edited afterwards; a change is a new lane.

- **Registry id:** R270 (Claude block R260-R279, claimed on issue #7 on 2026-10-20)
- **Owner (single writer):** the Claude session that froze it. It writes only `experiments/montag_fwd/journal/`.
- **Code:** `scripts/forward_montag.py`.
  - It uses `scripts/montag_events.py` (`parse`, the R269 title rule) and `lab/mexc.py`.
  - It reuses R268's helpers (`scripts/forward_delist.py`, `scripts/forward_unlocks.py`): contract lookup, spread
    lookup and bar opens.
  - It runs in every forward tick (`scripts/forward_all.sh`), right after R268, and is idempotent.
- **Gate:** 1 (forward, on-time).
- **Execution mode:** API. One short per contract at a fixed bar open, and one cover 24 hours later.
  - A manual order would also do, if the owner were alerted at detection. The archive's notices came out between
    02:00 and 11:00 UTC.
- **Paper only.** Nothing here places an order. Real money needs `lab.gate.go_real()` and the owner (AGENTS.md
  rules 5-6).

## Source
- **R269 (montag_v1)** was NULL on its primary (+1 h: +0.61%, t 0.71).
- **Its logged variant 2 (+24 h, unhedged)** cleared G1-G3:
  - +4.36% / +3.96% / +3.56% per notice at 1x/2x/3x (40/80/120 bp), t 3.81;
  - 24 notice clusters, 2023-10..2026-09;
  - halves +6.82% / +1.90%, 2025+ +4.31%.
- It was picked after the run, out of 6 variants. The tag began in 2023-07, inside the archive, so only notices after
  this freeze can test it.

## What the author has seen
- R269 in full, including every leg's archive return.
- **The fade:** 2026's 11 clusters averaged +1.31% at +24 h, and the last 5 (2026-06..09) -0.92%.
- **Post hoc, R269's matched null at +24 h:** p 0.0005 (null mean -0.30%).
- No notice first seen after this freeze, and no MEXC price for one.

## Events (point-in-time)
- **Source:** rows of `data/recorders/notices/binance_news.csv` and `binance_delisting.csv`, deduplicated by id.
  `scripts/record_notices.py` records both catalogs each tick.
  - Rows count if `first_seen_utc >= 2026-10-20T19:00:00Z`.
  - All rows recorded so far were first seen before 17:10Z on 2026-10-20, so they are out.
- **Tag notices only:** a row counts when `montag_events.parse(title)` returns kind `tag`. That is "Binance Will
  Extend the Monitoring Tag to (Include) A, B and C ...", with the names ending at ", (and) Remove ..." or
  " on <date>".
  - Untag names in the same title are not traded.
- **Legs:** one per ticker of the notice.

## Ticket (per leg): R268's rules, with the exit moved to +24 h
- **Contract:** the MEXC USDT perpetual of type 1, state 0, with base equal to the ticker, or to the ticker with a 1000
  or 1000000 prefix (multiplier 1e3 or 1e6), or to its `lab.mexc.ALIAS`. Without one, skip with reason
  `no_contract`.
- **Identity check:** MEXC last price / (Binance spot `<T>USDT` last price x multiplier) must lie in [1/3, 3].
  - The spot price comes from the public market-data mirror `data-api.binance.vision`.
  - Outside the range, skip with reason `mismatch`.
  - If the spot price cannot be read, the ticket is written with `check = unverified`.
- **Timing:**
  - Written at the first tick that sees the notice. `frozen_at` = now.
  - Entry: the open of the MEXC Min60 bar that starts at the first full hour after `frozen_at`.
  - If entry - `release_ms` > 3 h, skip with reason `missed`. The archive rule entered 0-60 min after release, and
    the hourly recorder adds about 6 min.
- **Exits:**
  - **Primary:** the open of the bar at entry + 24 h.
  - **Logged:** the open of the bar at entry + 1 h.
  - If the contract has no bar then, use the last close before it, and flag the ticket `stopped_trading`.
- **Gross:** `-(exit / entry - 1)`, unlevered.
- **Funding:** MEXC settled funding with settle time in (entry, exit]. The short receives `+rate`.
- **Measured cost:**
  - 2 x the contract's taker fee (from the contract list at freeze);
  - plus half the bid-ask spread at entry and at the +24 h exit, from the MEXC ticker recorder's files for those
    hours (`data/recorders/mexc_ticker/<date>/<HH>.parquet`).
  - A missing spread uses 10 bp for that leg, and the score is flagged.
- **Model cost:** 40, 80 and 120 bp round trip (R269's 1x/2x/3x).
- **Path, logged and not traded:** MAE (max high / entry - 1) over the +24 h hold. No stop.
- **Scoring:** after the +24 h exit bar has closed.

## Scores and decision
- **Primary per notice:** the mean, over its tickets, of `net = gross(+24 h) - measured cost + funding(+24 h)`.
- **Also reported:**
  - the model 1x/2x/3x nets;
  - gross;
  - the +1 h line (`gross_1h + funding_1h - model 1x`);
  - the unverified and stopped_trading counts.
- **t:** mean / (sd / sqrt(n)) over the notice observations, sd with ddof 1.
- **Decision at 12 scored notices:**
  - **PASS (gate 1 forward)** if t >= 2 and the mean net at the model 2x cost (+24 h, with funding) is > 0.
  - Otherwise **NULL**.
- **Futility:** at 6 scored notices, NULL if the primary mean is < 0.
- **Deadline:** 2028-06-30. With fewer than 12 scored by then, the same rule applies to what exists, labelled
  underpowered.
- **Power note:**
  - R269's variant had about 0.78 signal-to-noise per notice, so 12 notices give an expected t of about 2.7 if the
    2024-26 effect holds.
  - At 2026's level (+1.31%), the expected t is under 1, and the lane will likely be NULL.
  - 2026 had 11 tag notices in 9 months, so the decision is about a year out.
  - The variant was selected after the run, so its true effect is likely smaller.
- **Reported every tick, not gated:** `lab.gate.go_real()` on the primary nets.
- **Trials:** 1.
- **What PASS earns:** the owner may consider a small real stake through `go_real()`. A frozen per-notice size cap and
  a squeeze stop come first: R269's +72 h line lost 47% on one notice.
