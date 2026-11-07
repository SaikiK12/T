# Unlock market data: portable Binance inputs

This package makes the public inputs for the unlock continuation available to another checkout. It follows the
[data-acquisition step of the committed direction](../../../docs/DIRECTION.md) and uses the exact 98-contract
universe of [R258](../../../experiments/unlocks_daily_v1/PREREG.md). It contains source data and validation metadata.
It does not establish a funding-adjusted edge, account return or new prospective paper evidence.

## What is included

- `prices/`: the exact publisher-verified traded daily-price cache already used by R258.
- `auxiliary/fundingRate/`: settled funding observations with the original timestamps and observed intervals.
- `auxiliary/markPriceKlines/`: daily mark-price OHLC, distinct from traded prices and liquidity.
- Catalog versions, original publisher checksum files, complete capture manifests and retained attempt records.

Scope: January 2021 through September 2026, Binance USD-M. No reserved 2020 or MEXC outcome sample. No historical
calendar refresh, account data, credentials or model weights. The original R265 hourly/snapshot requirements remain
unmet in this workspace; this package does not silently replace those inputs.

The acquisition algorithm, finite request list and their hashes were committed before payload downloads. See
[PROTOCOL.md](PROTOCOL.md), [REQUESTS.csv](REQUESTS.csv) and [catalogs.json](catalogs.json). Schema validation does
not imply complete coverage for every holding window. Missing settlements or mark bars must remain unknown in a
later study; do not impute funding as zero.

## Verified capture and gaps

Acquisition was frozen/pushed in `c2e3c2d` before payload reads and completed on 2026-10-20, 14:39–14:50 UTC,
on the first pass, with no failed object. The new responses occupy 11,395,410 bytes including catalogs/checksums.

| Input | Source ZIPs | Observations | Contracts |
|---|---:|---:|---:|
| Original R258 traded daily prices | 3,125 | preserved unchanged | 98 |
| Settled funding | 3,058 | 427,752 | 98 |
| Daily mark-price OHLC | 3,125 | 93,606 | 98 |

The bundle is **15,464,492 bytes**, containing 18,914 original files with 29,047,854 bytes of file payload.
SHA-256: `c55dd46019719db709e1a887626b418fb9f9c75ccc15a227f384c0c070a71998`.
The companion [descriptor](market-data.tar.gz.json), [capture manifest](capture_manifest.json),
[quality summary](QUALITY.json) and [validation proof](VALIDATION.json) retain source versions and coverage.

There are **146 gaps longer than one day** across the mark series, including the missing 2026-06-29 candle on
all 98 contracts. PUMP funding also has a 21-day gap between 2025-06-19 and 2025-07-10. See every observed
gap in [coverage_gaps.csv](coverage_gaps.csv). This timestamp-only report does not test shorter funding gaps,
unobserved times before/after a series, historical listing continuity or the reason for an absence.
All requested files are validated; those gaps still prevent complete measurement of affected holding windows.

Verification passed: 374 tests, a second pack with identical compressed bytes, and a fresh restore with all
18,914 source files byte-identical. Re-running R258 on the restored prices reproduces its five result artifacts
byte-for-byte. These are reproducibility checks, not additional independent market observations.

## Restore without changing an existing checkout

The bundle and its companion descriptor are stored in this directory. Retrieve this branch in a separate worktree
if the original Claude checkout has uncommitted work:

```sh
git fetch origin codex/unlock-market-data
git worktree add --detach ../T-market-data origin/codex/unlock-market-data
cd ../T-market-data
python scripts/unlock_market_data.py restore --out /path/to/new-cache
python scripts/unlock_market_data.py validate --raw /path/to/new-cache/auxiliary
```

The destination must not exist. The command verifies the compressed SHA-256, member hashes/sizes and safe paths
before writing. It never extracts links or overwrites an existing file. A failure is retained for inspection.

The original price-only R258 run can then use the restored source bytes:

```sh
python scripts/unlocks_daily_check.py run \
  --raw /path/to/new-cache/prices --out /path/to/new-r258-results
```

Use the software versions recorded in R258's manifest for byte-identical results. Raw restoration is byte-exact;
it does not require re-downloading all market inputs or installing model weights. The R258 result remains a
historical price-only screen. Any new financial calculation needs its own frozen finite study.

## Source and limits

[Binance public data](https://github.com/binance/binance-public-data) documents the archive schemas, checksums and
possible later archive revisions. Every acquired version is retained by hash. Source usage follows Binance's terms;
this repository grants no additional license to source data. The package is a compact transport artifact; local
caches and bulk future datasets remain outside Git.

The owner-linked [Claude session](https://claude.ai/code/session_01SNoRQbwZuX9qSfWE3gaq3C) was attempted through the
web tool and ordinary HTTP. HTTP returned the application shell without session messages; the complete transcript
was not retrieved. This work uses the committed direction and the handoff text the owner supplied.
