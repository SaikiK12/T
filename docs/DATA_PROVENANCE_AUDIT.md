# Data provenance and gap-coverage audit

Reviewed 2026-10-19 by static inspection only. No market data were downloaded, no outcomes were read, and no tests or backtests were run. This note records code-path risks that can silently change a research sample even when a local dataset has a manifest hash.

## Findings

### 1. A strict fetch can trust a cached file without checking its source checksum

`lab/data.py:112` returns immediately if an archive file already exists. That bypasses the later `strict=True` checksum verification for the cached path. The ordinary build path also defaults to `strict=False`, where ZIP integrity is not the same as verifying Binance's published SHA-256. The processed-data manifest at `lab/data.py:173-184` records hashes for generated files, but not the source archive key, source checksum, retrieval time, or exact parser revision.

**Risk:** a reproducible hash of a processed Parquet file proves which local bytes were used, but not that those bytes match the official source archive or how they were produced.

**Required control:** in strict mode, verify cached files against the published source checksum before returning them. Record source URL/key, expected and observed source hash, retrieval timestamp, parser/code commit, processed hash, and any normalization steps in the manifest.

### 2. A manifest does not prove that all expected bars or archive shards exist

`lab/data.py:168-184` records row counts and first/last times, but does not enumerate expected monthly shards, missing shards, or per-symbol cadence gaps. Missing archive files can be omitted from the build. Monthly data are supplemented by daily files only after the latest monthly period (`lab/data.py:98`), so a missing older monthly shard may remain absent without an explicit incomplete-data flag.

**Risk:** a dataset can have a valid hash and plausible endpoints while missing interior bars or entire months. Later PnL code may then skip missing price returns or convert missing funding to zero.

**Required control:** store expected and fetched shard inventories, explicit unavailable/404 responses, and per-symbol missing intervals. A build should fail closed or label the affected symbol-period incomplete; consumers must not interpret a missing interval as no trade, no settlement, or zero return.

### 3. Tail refresh does not identify or repair interior holes

MEXC kline data are cached as Parquet and refreshed from the latest cached bar (`lab/mexc.py:97`). Binance live caches similarly refresh from their last row; the `.from` sidecar records earliest coverage, not every covered interval (`lab/live.py:181`). These paths can retain historical gaps or later source corrections indefinitely unless an independent coverage check detects them.

**Risk:** an append-only forward cache can look current while still containing a missing interval in the middle of its sample. A symbol may then silently disappear from a score or its outcome window.

**Required control:** persist coverage intervals and endpoint retrieval metadata, detect holes against the expected cadence, and refetch uncovered intervals or mark them unresolved. Make backfills append-only with source and retrieval timestamps; do not rewrite past research outputs silently.

### 4. Funding event time is reduced to an hourly bucket

Both MEXC and Binance paths floor funding settlement timestamps to an hour and deduplicate within that bucket (`lab/mexc.py:115`, `lab/live.py:239`). The MEXC carry note records that settlement can occur up to 15 seconds after the nominal time (`docs/PERP_CARRY_ACCOUNTING.md:19`). The hourly representation cannot determine precisely which virtual position was open when a delayed or boundary-time settlement occurred.

**Risk:** rates may be charged to the wrong side of a rebalance, or a missing event can be mistaken for a true zero because `lab.engine.forward_returns` maps NaN funding to zero.

**Required control:** preserve raw event milliseconds, rate, contract identity and receipt/retrieval time; derive hourly buckets as a separate view. Reconcile each instrument's expected funding schedule with observed events, including no-settlement and duplicate cases, before any carry PnL is scored.

## Work order

1. **Before another archive result:** make strict mode verify existing cached bytes and add expected-shard plus per-symbol cadence coverage to the source manifest.
2. **Before a forward return decision:** retain exact funding timestamps and distinguish complete zero-event windows from missing history. For MEXC, run gap checks over cached interiors as well as the newest tail.
3. **Before promotion of a signal:** require each lane to fail closed on unresolved input, eligibility, target-window, lifecycle or settlement gaps; report coverage by instrument age and liquidity group.

The Kronos R227 draft now requires a source manifest, exact lifecycle outcomes, a complete target-window gate and expected-funding reconciliation before its owner freezes or scores the lane. That experiment still cannot run until its manifest, deterministic ranks, funding coverage and model runner are supplied.

## Pointers

- Source ingestion and manifests: `lab/data.py:88-184`.
- Binance live cache: `lab/live.py:181-245`.
- MEXC cache and funding history: `lab/mexc.py:97-130`.
- Missing-value PnL behavior: `lab/engine.py:30-39,90-96`.
- Settlement precision: `docs/PERP_CARRY_ACCOUNTING.md:17-21`.
- Related identity and delisting risks: `docs/CONTRACT_LIFECYCLE_INTEGRITY.md` and `docs/IMPLEMENTATION_INTEGRITY_REVIEW.md`.
