# Point-in-time recorders (data collection, no statistics)

Started 2026-10-20 (docs/DIRECTION.md, Days 1-3). Each runs at the start of every forward tick
(`scripts/forward_all.sh`), is idempotent, and writes under `data/recorders/` (gitignored). Its output exists only
from the first run on: none of it can be backfilled.

| Recorder | Output | What it keeps |
|---|---|---|
| `scripts/record_mexc_ticker.py` | `mexc_ticker/<date>/<HH>.parquet`, one per UTC hour | every MEXC perp: displayed next funding rate, caps, cycle and settle time; last, bid1/ask1, index, fair, 24 h volume, holdVol (open interest) |
| `scripts/record_funding_board.py` | `funding_board/<date>/<HH>.parquet`, one per UTC hour | normalized funding observations from six venues, with per-venue response-completion bounds on new files |
| `scripts/record_notices.py` | `notices/binance_{delisting,listing}.csv`, append-only | Binance announcement id, title, release time and the UTC time this recorder first saw it |
| `scripts/record_unlocks.py` | `unlocks/<date>.json.gz`, one per UTC day | DefiLlama emissions index (upcoming unlocks, circulating supply, market cap) as published that day |

For new MEXC ticker files, `request_start_ms` marks the start of the capture,
`funding_recv_ms` and `ticker_recv_ms` are local response-completion bounds,
and `recv_ms` is the later ticker bound. Files are still named for the request's
starting UTC hour, even if a response finishes in the next hour. These times use
the local wall clock; synchronization and subsequent durable publication still
need independent evidence. Older files lacking the two per-response columns used
`recv_ms` for request start, so that value is not a receipt-time bound and must
not be treated as one in an M090 forecast test. Missing hours remain missing.

For new cross-venue funding-board files, `request_start_ms` is the snapshot
start, `venue_start_ms` marks the start of that venue's collection, and
`recv_ms` is recorded after all responses used for that venue. Older board
files without `venue_start_ms` stamp the whole capture's start as `recv_ms`;
they have no per-venue completion bound. All of these use the local wall clock,
and neither response timing nor a file's name proves durable, on-time
publication. Clock-quality and publication evidence remain required.

## The local clock (measured 2026-10-29)
Every `recv_ms` and `lag_ms` comes from this machine's wall clock, which nothing disciplines. After the container's last
restart (05:48 UTC on 2026-10-29) it ran slow by 99 ppm (5.9 ms a minute), 1.7 s behind by 10:22 UTC. Three exchange
clocks (MEXC, Deribit, OKX) put it +1.68 to +1.81 s behind then, and the tape's own `lag_ms` medians (Binance, Lighter,
MEXC: -5.9 ms a minute, zero near 06:05 where true feed delay is about 0.1 s, about -1.5 s at 10:20) agree; the fit
extrapolates back to no offset at the 05:48 restart. Days 10-21 to 10-28 show normal lags (daily medians 40 to 150 ms), so
this boot is the exception; the drift can differ on each boot.
- **Correction for data from this boot before 10:22:** local time is early by about `5.9 ms x minutes since 05:48 UTC` (1.6 s
  at 10:22); add that to `recv_ms`, and remove it from `lag_ms`. Hourly ticker files from 06:15 to 10:15 carry it too.
  Earlier boots that day were not measured.
- **From 10:22 UTC** `scripts/clock_check.py slew` removes the offset gradually with `adjtime` (at most 0.5 ms a second, never
  a step). Measurements to 13:47 UTC are in `experiments/recorders/journal/clock_check.csv` (median offset and each venue's
  offset only). Later runs are rows of `clock_check_v2.csv`: local time, estimated true time, median offset, which venues
  were used, `bound_ms` (half the longest round trip used, the error each venue's offset can carry if the network delay is
  lopsided), `spread_ms` and each venue's offset and round trip. Positive `median_offset_ms` means the local clock is
  behind. Round trips are timed on the monotonic clock, and a sample whose wall-clock interval disagrees with it (a step of
  the wall clock during the request) is dropped; a venue's offset is itself only as good as that venue's clock.
- **Cadence:** nothing in the repository schedules the check. `restart_all.sh` runs it once at a restart, and the session
  that watched on 2026-10-29 ran it by hand about every 10 minutes (the clock drifted about 6 ms a minute before it was
  slewed). A reading bounds the offset at that moment only. Without a person or a scheduler running it, the offset grows again
  by roughly 0.35 s an hour on a boot like this one.
- **Who is affected:** lanes that align recorded times to a true-time event (R369's EIA release at 14:30 UTC, whose PREREG says
  the clock was not measured; R364 and R355 entries at T - 10 s). R367 stamps every venue with the same local clock in 100 ms
  buckets, so a common offset cancels between venues. This is a measurement of the clock, not a change to any frozen rule.

`scripts/record_digest.py` runs last in the tick and appends the size and sha256 of every new or changed file to
`journal/digests.csv` (committed), so a later lane can show its inputs were recorded before it was frozen.

Logs: `tick.log` here. Fixture tests: `tests/test_recorders.py`.
