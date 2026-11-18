# Data rebuild after the container replacement, 2026-11-17..18

On 2026-11-17 the container was replaced and the gitignored `data/` folder was lost. This page records, folder by
folder, what was rebuilt and how it compares with its record in `docs/provenance/`.

**Read with care.**
- Matching hourly coverage means the same files, the same first and last bar, the same number of bars and the same
  holes. It does not prove every value is equal.
- Parquet bytes differ almost everywhere, because the parquet writer changed. So no frozen data manifest that pins file
  bytes verifies against a rebuilt folder. A lane that must re-run byte for byte needs its own data branch.

**How it was checked.**
- `scripts/data_provenance.coverage` was run on each rebuilt file and compared with the recorded `coverage`.
- File lists were compared with the recorded `file_hashes`.
- Every parquet file of the folders below was opened. None was unreadable after the container restarts.

## Folders
| Folder | How rebuilt | Against the record |
|---|---|---|
| `klines_1h` | `python -m lab.data build klines 1h` | 900 of 900 files: same hourly coverage |
| `premiumIndexKlines_1h`, `markPriceKlines_1h` | `lab.data build` | 895 of 895 each: same coverage |
| `fundingRate` | `lab.data build fundingRate` | the same 900 files; settlements are not hourly, so rows were not compared |
| `metrics_1h` | `python -m lab.flow metrics` on the rebuilt `data/research` | 487 of 487: same coverage (see note 1) |
| `spot_1h` | `scripts/fetch_spot.py` on a rebuilt `data/spot_pairs.json` | 481 of 481: same coverage (see note 2) |
| `gate_hist` | `scripts/fetch_gate_history.py fetch` and `build` | all 3,329 open and reserved files; 860 candle files with the same coverage; `raw/` excluded, as recorded |
| `dydx_hist` | `scripts/fetch_venue_history.py dydx` (resumed once) | all 892 files |
| `kucoin_hist` | same, `kucoin` | 3 contracts no longer served (ANTHROPICUSDTM, MITOUSDTM, PTBUSDTM); 28 new ones |
| `kraken_hist` | same, `kraken` | PF_ANTHROPICXUSD no longer served; 3 new contracts |
| `mexc_hist` | `scripts/fetch_mexc_history.py --end 2026-10-20T11:00:00Z` | 672 files: same coverage; 434: the record has 4 more hours (note 3); 54 contracts no longer served, 13 new |
| `coinmetrics` | `scripts/fetch_coinmetrics.py` | all 1,229 recorded files present, plus completion receipts; latest vintage, so values can differ |
| `defillama` | `scripts/fetch_fundamentals.py` | latest vintage; BOND and CC not served, AERO and INJ new |
| `coinm_1h` | a scratch writer that repeats the legacy layout (note 4) | 272 of 272 contract files: same coverage |
| `cboe` | `scripts/fetch_cboe.py` | the same 13 indices and raw CSVs; daily, so no hourly record; history now runs to 2026-11-17 |
| `upbit_hist` | `scripts/fetch_venue_history.py upbit` | daily candles, so no hourly record; 4 files no longer served (KRW-SOPH, KRW-ZIL, reserved KRW-BLAST and KRW-ZIL), 6 new |
| `research` | `scripts/build_views.py` (feature bins 7.1 GB) | no provenance record |
| `data-archive` recordings | `scripts/handover.py restore` | 39,265 files, every sha256 checked (2026-11-17) |

**Notes.**
1. **`metrics_1h`.** The record's first 13 symbols in name order (0G … 4) cover every day from 2021-12. The rest cover
   only the days `lab.flow.needed_days` selects, so the first ones were fetched before that filter existed.
   - These 13 were refetched with `--all-days`. All 487 files then match.
2. **`spot_pairs.json`.** The perp → spot map lived only in `data/` and no script made it.
   - `scripts/make_spot_pairs.py` rebuilds it from the archive listing by the lab's name rule, restricted to the 481
     recorded perps.
   - Every recorded perp found its pair, and all 481 spot files match their recorded coverage.
3. **`mexc_hist`.** The recorded snapshot was resumed across clock hours without a pinned end.
   - Its files end at 2026-10-20 10:00 or 14:00 UTC.
   - The rebuild ends at 10:00 for all files. Every file is either identical in coverage or a 4-hour-shorter prefix of
     the record.
   - An earlier pull to 17:00 is kept at `data/mexc_hist_end18_rebuild`.
4. **`coinm_1h`.** The current `scripts/fetch_coinm.py` writes only `coinm_1h_v2` and refuses the legacy folder by
   design. The legacy folder is what `lab/daily.py` and three frozen lanes read.
   - It was rebuilt by a scratch writer that repeats the recorded layout: monthly 1h kline zips through `data.END`,
     `lab.data.parse(..., "klines")` with its generic column names, deduplicated on `t` and sorted.
   - All 272 contract files match their recorded hourly coverage. The writer's `manifest.json` says how it was made.

## Not rebuilt, or still running (2026-11-18 06:10 UTC)
- **Running:** `hyperliquid` (106 of 235 coins at 06:00 UTC), Bithumb, then Lighter.
  - Hyperliquid serves only the latest 5,000 hourly candles. The recorded 1h files run 2026-03-26..10-20; the
    rebuilt ones run 2026-04-23..11-18 (BTC). Those four weeks of hourly history are gone from the source. Daily
    candles and funding come back from their start (BTC funding: hourly from 2023-05-12).
- **`coinm_1h_v2`.** `scripts/fetch_coinm.py` stops on archive files whose header names field 7 `quote_volume`, where
  its schema check wants base-asset volume. This is Binance's labelling for COIN-M files, and the check is
  deliberate; whether to accept that header is the script owner's call. The legacy `coinm_1h` above does not depend
  on it.
- **`macro`.** FRED is not contacted again, by the owner's earlier rule, so `scripts/fetch_macro.py` was not run.
- **`daily`** (the point-in-time panel) and **`metrics_full`.** They wait for the venue folders above. They also lack
  `macro`, so a panel built now would differ from the recorded one in those columns.
