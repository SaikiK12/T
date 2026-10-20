# PREREG: delist_fwd (R268). The spot delisting-notice short, forward on MEXC paper

Freeze with `lab.prereg.freeze()` before the first ticket. Never edited afterwards; a change is a new lane.

- **Registry id:** R268 (Claude block R260-R279, claimed on issue #7 on 2026-10-20)
- **Owner (single writer):** the Claude session that froze it. It writes only `experiments/delist_fwd/journal/`.
- **Code:** `scripts/forward_delist.py`.
  - It uses `scripts/delist_events.py` (`parse`, the R267 title rule) and `lab/mexc.py`.
  - It runs in every forward tick (`scripts/forward_all.sh`), right after the notice recorder, and is idempotent.
- **Gate:** 1 (forward, on-time). **Execution mode:** API. One short and one cover per contract, an hour apart, at fixed
  bar opens. A manual order would also do, if the owner were alerted at detection.
- **Paper only.** Nothing here places an order. Real money needs `lab.gate.go_real()` and the owner (AGENTS.md
  rules 5-6).

## Source
- **R267 (delist_v1)** was NULL on its primary (all notices, +1 h: -0.12%, t -0.06).
- **Its logged variant 5 (spot notices, +1 h)** cleared G1-G3:
  - +4.15% / +3.75% / +3.35% per notice at 1x/2x/3x (40/80/120 bp), t 3.07;
  - 25 notice clusters, 2023-26;
  - halves +3.90% / +4.38%, 2025+ +5.61%.
- It was picked after the run, out of 8 variants. No reserved notices exist, because the catalog starts in 2022, so
  only notices after this freeze can test it.
- **Futures notices are not traded.** In R267 they had a squeeze tail (ANC -95%, SLERF -87% in an hour).

## What the author has seen
- R267 in full, including every leg's archive return.
- **Release minutes:** 19 of the 25 archive spot clusters were released in the first 5 minutes of an hour. The other 6
  (minutes 29-59) would have entered one hour later under this lane's detection rule. That variant was not run on
  the archive.
- No notice first seen after this freeze, and no MEXC price for one.

## Events (point-in-time)
- **Source:** rows of `data/recorders/notices/binance_delisting.csv`, the Binance delisting catalog that
  `scripts/record_notices.py` records each tick.
  - Rows count if `first_seen_utc >= 2026-10-20T18:00:00Z`. The catalog's backfill rows were all first seen at
    2026-10-20T12:42Z, so they are out.
- **Spot notices only:** a row counts when `delist_events.parse(title)` returns kind `spot` from the title alone. That
  is "Binance Will Delist A, B and C on <date>" and its vote-to-delist variant. Margin, futures and other titles are
  ignored.
- **Legs:** one per ticker of the notice.

## Ticket (per leg)
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
  - Primary: the open of the bar at entry + 1 h.
  - Logged: the open of the bar at entry + 24 h.
  - If the contract has no bar then, use the last close before it, and flag the ticket `stopped_trading`.
- **Gross:** `-(exit / entry - 1)`, unlevered.
- **Funding:** MEXC settled funding with settle time in (entry, exit]. The short receives `+rate`.
- **Measured cost:**
  - 2 x the contract's taker fee (from the contract list at freeze);
  - plus half the bid-ask spread at entry and at exit, from the MEXC ticker recorder's files for those hours
    (`data/recorders/mexc_ticker/<date>/<HH>.parquet`).
  - A missing spread uses 10 bp for that leg, and the score is flagged.
- **Model cost:** 40, 80 and 120 bp round trip (R267's 1x/2x/3x).
- **Path, logged and not traded:** MAE (max high / entry - 1) over the +1 h and +24 h holds. No stop.
- **Scoring:** after the +24 h exit bar has closed.

## Scores and decision
- **Primary per notice:** the mean, over its tickets, of `net = gross(+1 h) - measured cost + funding`.
- **Also reported:**
  - the model 1x/2x/3x nets;
  - gross;
  - the +24 h line (`gross_24h + funding_24h - model 1x`);
  - the unverified and stopped_trading counts.
- **t:** mean / (sd / sqrt(n)) over the notice observations, sd with ddof 1.
- **Decision at 12 scored notices:**
  - **PASS (gate 1 forward)** if t >= 2 and the mean net at the model 2x cost (+1 h, with funding) is > 0.
  - Otherwise **NULL**.
- **Futility:** at 6 scored notices, NULL if the primary mean is < 0.
- **Deadline:** 2028-06-30. With fewer than 12 scored by then, the same rule applies to what exists, labelled
  underpowered.
- **Power note:**
  - R267's variant had about 0.6 signal-to-noise per notice, so 12 notices give an expected t of about 2.1.
  - The archive saw about 8 spot notices a year with a traded perp, so the decision is about 1.5 years out.
  - The variant was selected after the run, so its true effect is likely smaller.
- **Reported every tick, not gated:** `lab.gate.go_real()` on the primary nets.
- **Trials:** 1.
- **What PASS earns:** the owner may consider a small real stake through `go_real()`. A frozen per-notice size cap
  comes first.
