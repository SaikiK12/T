# Data sources: what was downloaded, from where, and how to check it

`data/` is gitignored. Each download has a provenance record in `docs/provenance/<folder>.json`, written by
`scripts/data_provenance.py`. The record holds:
- every file's size and sha256, plus a combined digest;
- file counts per subfolder;
- for hourly parquet, each file's first and last bar, bar count and interior holes (missing hours between its first
  and last bar).

Re-run the script on a copy to prove it is byte-identical. Recorders (live journals) are separate: their daily
digests are in `experiments/recorders/journal/digests.csv`.

## Downloads (owner's yes: "we need all data possible", 2026-10-20)
| Folder | Source | Script | Files | Size | Coverage | Combined sha256 | Notes |
|---|---|---|---|---|---|---|---|
| `data/mexc_hist` | MEXC contract API (public): hourly kline, hourly index-price kline, settled funding | `scripts/fetch_mexc_history.py` | 607 contracts x 3 | 454 MB | 2025-04-01 .. 2026-10-20 14:00 UTC | f40c2864… | Contracts listed on 2026-10-20 only, so contracts delisted earlier are missing. Funding starts 2025-04-27 everywhere. Klines: 8 files have holes (GTC 5,997 h, BTW 582 h, SILVER 120 h, FX pairs about 6 h). Index klines: 27 files have holes. The run resumed after a container restart, so files end at their own fetch hour. |
| `data/spot_1h` | data.binance.vision spot klines (public zips) | `scripts/fetch_spot.py` | 481 pairs | 929 MB | 2017-08 .. 2026-09-30 | c78bbcd0… | The spot leg of each USD-M perp with a spot pair. 273 files have holes (23,133 h in all): delist/relist gaps and exchange outages. |
| `data/coinm_1h` | data.binance.vision COIN-M klines (public zips) | `scripts/fetch_coinm.py` | 272 contracts | 154 MB | 2020-06 .. 2026-09-30 | 87f2b9f8… | Perpetuals and dated quarterlies (basis). 62 files have holes (5,976 h). |
| `data/unlocks/2026-10-20` | DefiLlama emissions datasets (public) | `scripts/fetch_unlocks.py` | 373 | 44 MB | calendar as of 2026-10-20 | a2296e89… | Not point-in-time. The daily recorder (`scripts/record_unlocks.py`) keeps snapshots from 2026-10-20. Its own `manifest.json` also hashes the decompressed JSON. |
| `data/recorders/notices/articles` | Binance CMS article detail (public) | `scripts/fetch_notice_bodies.py` | 442 | 2 MB | delisting catalog to 2026-10-20 | in R267 PREREG (f155ba8d…) | Plain text of each delisting article. Used where a title does not name the coins. |
| `data/hyperliquid` | Hyperliquid `/info` (public) | `scripts/fetch_hyperliquid_history.py` | in progress | | | | Record when done. |

## Not downloaded yet
- **CoinGecko 365-day market caps:** the free API keeps 365 days only.
- **One month of aggTrades for about 5 coins:** for markout research. Full tick history is excluded for disk.
