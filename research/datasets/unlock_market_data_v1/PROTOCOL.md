# Unlock market-data bundle v1 — operational collection protocol

This is acquisition/schema validation, not a strategy preregistration or a return
study. It implements the owner's request to continue Claude's committed direction
and make the required public data reusable from GitHub. No PnL, return mean, funding
contribution, predictive metric or liquidation outcome is computed here. Such an
outcome study needs its own frozen code/spec before calculating outcomes.

Collector SHA-256: `d85a58166d909a8212f4d8ed1a1c0ec9106364cbb7175dcd1d306ece9b150bb5`
Requests SHA-256: `9bf77edf3111495124c28aecf139056cb22f1e781470e0ee8bff30501e7773c2`
Catalogs SHA-256: `d9859c91e354c6d1d0cddc733f527c844716784abddcdde9f12c813f1f3d1e15`
R258 helper SHA-256: `49665efd36a97a1a076d38339ee678f90e4a0db5660dccf337544ee209df4c5b`

Freeze this file with lab.prereg.freeze and commit/push before downloading archive
payloads. Metadata-only S3 catalogs have already been read; no funding or mark
values have been opened. R258 traded-price results are already known, including
the STO excursion. This protocol does not create new independent market evidence.

## Fixed scope

Exactly the 98 Binance USD-M symbols in R258's frozen inventory (97 unlock coins
plus BTC), January2021 through September2026. REQUESTS.csv fixes 6,183 published
ZIP objects:3,058 settled-funding archives (3,377,117 bytes) and3,125 daily mark-price
archives (3,301,005 bytes). The196 catalogs occupy4,135,444 bytes. Preserve every
catalog's hash and zero/missing month coverage; a listed set does not imply that
all contracts existed or that every settlement/date is observed. No future refresh
or new symbol is substituted for missing coverage. Never read reserved2020/MEXC
outcome data. This is Binance data, not MEXC funding or execution.

Only unauthenticated static https://data.binance.vision objects and their public
.CHECKSUM companions, with normal proxy/certificate verification. Hard32MiB
response budget per pass including catalog/cache accounting; ZIP<=16KiB, inflated
CSV<=128KiB, checksum<=512 bytes, timeout20s, <=24 concurrent public static-object
requests. At most3 bounded fetch passes. Every failed pass/error is retained; a
later pass validates complete cached pairs and only downloads missing pairs. Never
overwrite complete manifests or partial pairs. No private/account/trade endpoint,
key, weight, hourly archive, calendar refresh or background schedule.

Each complete pair must match the publisher SHA256, catalog size, one exact CSV
member and ZIP CRC. Preserve original bytes. Record request start/end UTC for newly
fetched pairs (explicit null for cached verification), collection pass UTC bounds,
hashes, rows and first/last timestamps. Those local timestamps identify acquisition;
they do not prove original public availability or on-time prospective evidence.

## Schema validation and honest gaps

Funding:3 columns, optional calc_time header. Exact Unix milliseconds, observed
interval an integer1..24 hours, finite signed fractional rate within[-1,1]. Never
assume8h or floor timestamps. Mark-price daily candle:12 columns, optional open_time
or open time header, exact UTC-midnight milliseconds, close_time=open+day-1, finite
positive coherent OHLC. Ignore its volume fields for trading-liquidity purposes.
Require source month and2021..2026-09 bounds, no empty files or duplicate times.
Invalid schema/changed bytes fail closed. Global validation reports counts,
first/last times and time gaps; it neither fills gaps nor treats absent funding as0.
A COMPLETE acquisition means all frozen objects validated, not complete coverage
of every future strategy's holding times. No silently dropped bad shard.

## GitHub portability

Reuse R258's already-locked traded-price cache and its frozen source manifest;
verify every source/checksum byte again. Pack original ZIP/checksum pairs, catalogs,
complete manifests and attempt records into one deterministic gzip/USTAR bundle.
Prefix prices/ restores the exact R258 cache; auxiliary/ restores funding/mark data.
Do not replace the original R265 calendar/map-rebuild or hourly-data requirements.

Limits: <=24,000 source members, <=64MiB uncompressed file payload and <=32MiB
compressed bundle. Bundle index includes every member hash/size; Git companion
JSON pins the compressed file SHA256, source manifests and schema coverage.
mtime/uid/gid/gzip metadata are deterministic; another pack must have identical
bytes. Restore checks the companion hash and complete index before any output,
rejects traversal, absolute paths, links, duplicate or unknown members, and requires
a fresh destination. It writes file bytes explicitly, without tar.extractall.
Retain an interrupted output for inspection instead of silently repairing it.

Commit the compact bundle/descriptor, acquisition manifest, protocol, request list,
quality summary, restore command and source references. This is a source-data
artifact, not another methods queue/panel. M057 may record local data availability;
its tested/open scope and existing verdict remain unchanged. Do not append a
statistical research round or claim an edge from record counts/schema validation.

## Primary references inspected2026-10-20

- https://github.com/binance/binance-public-data : USD-M schema, archives, CHECKSUM
  and the warning that archives can later be revised. Preserve acquired versions.
- https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History
- https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Mark-Price-Kline-Candlestick-Data
  Both redirect to the official consolidated market-data reference. Funding rates,
  settlement times and mark candles are separate inputs; daily mark candles cannot
  identify a unique intraday fill or liquidation path. Source usage follows the
  provider's terms; this project grants no new license to source data.

The owner-linked Claude session was also attempted: the web tool could not open
it; an ordinary HTTP request returned only the Claude Code application shell,
without transcript/session messages. The full session was not read. The available
plan is docs/DIRECTION.md at83554e1 plus the owner's pasted handoff.
