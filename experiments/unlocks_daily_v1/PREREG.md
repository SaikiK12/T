# R258 unlocks_daily_v1: fixed-event independent daily-price cross-check

- **Registry id:** R258
- Owner/single writer: Codex on `codex/unlocks-daily-check`; claimed issue #7.
- Runner SHA-256: `49665efd36a97a1a076d38339ee678f90e4a0db5660dccf337544ee209df4c5b`
- Requests SHA-256: `f20554eb1d505277b2c382a06a5954e457ae506218c6e2f645dd43c559f70d5b`
- Frozen source event list: R265 `experiments/unlocks_v1/events.csv`, SHA-256
  `24cd0d052bea6dcab1e4f862dad3227348644fb887ba61d14ca56cdb00cd794e`.

## Why this is separate

Claude froze R265 in 83554e1 but did not push its runner, price data or outcomes.
The owner asked Codex to continue autonomously. Its original snapshot/map-rebuild
requirement cannot be satisfied in this sandbox. Do not relax that frozen rule.
This new lane uses its already-frozen event selection as a received retrospective
cohort and independently acquires official Binance USD-M daily klines. It does not
rebuild the calendar or claim to finish/reproduce R265. The distinction is daily
close on an exact date versus R265's last positive-volume hourly close fallback.

Previously seen: the owner supplied Claude's aggregate claim of 422 priced events,
+3.24% net/event, t3.19 at1x, t2.79 at3x, six losses over40%, worst -132%. No event
return or archive price has been opened by Codex for this lane. The calendar was
revised after the events; symbols survived a hindsight map check. All 2021-26
windows are spent gate0. A pass cannot establish prospective evidence or executable
MEXC PnL, and no direction, threshold or strategy is selected from these outcomes.

## Fixed finite inputs and bounded collection

Read only the fixed 530 rows with venue=binance, window=archive and check in
{verified,unverified}; order by day_ms then perp. The 97 symbols plus BTCUSDT
(hedge) define all 98 requested contracts. All other event rows provide date
exclusions only; no reserved 2020 or MEXC price/funding sample is read.

REQUESTS.json fixes 3,125 already-listed monthly daily-bar ZIPs, Jan2021 through
Sep2026, with catalog sizes totaling 5,720,020 bytes. The S3 listing was read for
filenames/sizes only before freezing. No ZIP price values were read. Listings occupy
2,027,306 bytes. Fetch only these objects and each official .CHECKSUM. No pagination,
other symbols, hourly/tick data, calendar refresh, funding or model weights.
Hard aggregate response budget32MiB including catalogs, ZIPs and checksums; each ZIP
<=16KiB, CSV<=32KiB, checksum<=512 bytes, timeout20s, at most12 in-flight requests.
There are at most two fetch passes: a failed pass is retained and only missing
complete pairs may be fetched on the second. No data outcome run until every fixed
request succeeds and its publisher SHA-256/size/ZIP CRC match. Any unresolved request
makes acquisition INCONCLUSIVE; no convenient month/universe replacement. Failed
attempt manifests are retained. Complete original raw archives stay in external
cache; do not bloat Git with historical prices. Lock the complete data manifest in
DATA.sha256 and commit it BEFORE calculating outcomes. Runs reverify all bytes.

Public primary documentation inspected2026-10-20:
https://github.com/binance/binance-public-data (Futures Klines and CHECKSUM sections).
Futures daily rows have12 columns, millisecond open/close times, UTC midnight open
and close_time=open+86400000-1. The SPOT microsecond change does not apply to these
futures files. Archives may later be revised: preserve the acquired hashes, never
silently replace them. Header may be absent or exactly open_time/open time. Require
finite positive OHLC, coherent high/low bounds, nonnegative volume/quote-volume,
unique dates and no row outside2021-01-01..2026-09-30. Schema errors stop the run.

## One primary rule, all exclusions and one control diagnostic

For each fixed dayD short at the exact daily closeD-7 and cover at exact closeD.
Both daily bars must exist and have positive volume. If either fails, retain the
row as unpriceable; do not forward-fill, assume zero return or swap dates. Report
counts and every excluded row. Gross=1-closeD/closeD-7. Primary net=gross-.002*k
for k=1,2,3 (20/40/60bp round trip, same constant-entry-notional stress convention
as R265). This is a price-only event diagnostic: funding is NOT included and
fees on changing exit notional are not modeled. Thus even a positive price net is
not complete perp account PnL.

For every priced event, inspect daily highs AFTER entry (D-6..D). If all seven
positive-volume bars exist, record max(high/entry-1); otherwise record unknown path.
Do not clip losses at100%, infer liquidations from close returns or choose a stop.
Count close-net losses over40%/100% and high excursions over40%. These measure
adverse price paths only; no collateral, margin, liquidation or capacity model.

BTC control diagnostic on the same dates: add BTC's long price return when both
exact BTC endpoints exist. Charge a separate20bp round trip per leg:40/80/120bp
for the pair. Report its own n and1x/2x/3x but do not select it or rescue a primary
failure. Report primary by year and verified-only for context, no adaptive filters.

## Fixed statistics and gate0 decision

Primary mean, hit rate, worst and ISO-unlock-week clustered t. With n events and
G weeks, SE=sqrt(G/(G-1)*sum_week(sum_event(x-mean))^2)/n. Undefined primary
statistics make the study INCONCLUSIVE, not a pass.

Matched-date control:2,000 replications, NumPy default_rng265. For each scored
event independently with replacement, retain its symbol and sample uniformly from
its admissible dates2021-02-07..2026-09-30. A date must satisfy the same exact entry
and exit positive-volume rule and be strictly more than14 days from every kept
source event for that symbol, including nonarchive labels. Sort candidate dates
chronologically; draw in fixed event order within each replication. Null mean
uses the same20bp price cost. Empty pool for any scored symbol=>INCONCLUSIVE,
never remove that symbol. p=(1+count(null_mean>=observed_mean))/2001.

Use R265's four primary1x gates as a historical diagnostic, no tuning:
G1 week-cluster t>=2; G2 matched p<.05; G3 first/second date-ordered halves both
positive (odd extra event in second half); G4 mean positive after removing the
three symbols with largest summed net (alphabetical tie-break). All pass=>PARTIAL
historical screen only; otherwise NULL. No CONFIRMED verdict. Report2x/3x t and
means, do not reinterpret a failure using costs/control/years. Preserve nulls.
Count2 trials (primary and logged BTC hedge) conservatively; random replications
and cost stresses are not extra independent strategies. Read against total
program trials; week clustering/random-date p do not correct all lab searches,
retrospective calendar revisions, survivorship or dependencies between unlocks.

## Outputs and stop

Compact priced/excluded eventCSV, summaryCSV, fixed verdictJSON and hash manifest.
Fresh output directory only; a repeated run must reproduce result bytes. Original
R265 frozen files/journals remain unchanged. Update only the existing canonical
M057 exact-tested/open scope after a successful run and append one R258 result
row via registry helper; do not create another methods queue. If inputs/metrics
fail, record the exact block without claiming completed returns. No money,
orders, credentials, reserved-window consumption or automatic forward lane. A
future MEXC paper strategy requires its own prereg and point-in-time event cutoff.
