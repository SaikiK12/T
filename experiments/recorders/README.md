# Point-in-time recorders (data collection, no statistics)

Started 2026-10-20 (docs/DIRECTION.md, Days 1-3). Each runs at the start of every forward tick
(`scripts/forward_all.sh`), is idempotent, and writes under `data/recorders/` (gitignored). Its output exists only
from the first run on: none of it can be backfilled.

| Recorder | Output | What it keeps |
|---|---|---|
| `scripts/record_mexc_ticker.py` | `mexc_ticker/<date>/<HH>.parquet`, one per UTC hour | every MEXC perp: displayed next funding rate, caps, cycle and settle time; last, bid1/ask1, index, fair, 24 h volume, holdVol (open interest) |
| `scripts/record_notices.py` | `notices/binance_{delisting,listing}.csv`, append-only | Binance announcement id, title, release time and the UTC time this recorder first saw it |
| `scripts/record_unlocks.py` | `unlocks/<date>.json.gz`, one per UTC day | DefiLlama emissions index (upcoming unlocks, circulating supply, market cap) as published that day |

`scripts/record_digest.py` runs last in the tick and appends the size and sha256 of every new or changed file to
`journal/digests.csv` (committed), so a later lane can show its inputs were recorded before it was frozen.

Logs: `tick.log` here. Fixture tests: `tests/test_recorders.py`.
