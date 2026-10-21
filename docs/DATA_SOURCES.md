# Data sources: what was downloaded, from where, and how to check it

`data/` is gitignored. The comparison with other projects' data is in `docs/BENCHMARK.md`. Each download has a provenance record in `docs/provenance/<folder>.json`, written by
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
| `data/hyperliquid` | Hyperliquid `/info` (public) | `scripts/fetch_hyperliquid_history.py` | 234 coins x daily candles, hourly candles (recent window only), funding | 162 MB | funding from 2023-05; to 2026-10-20 | 9c8ca0af… | Includes 56 coins that ended before 2026-10-01 (R275 FINDINGS). Hourly candles are limited by the API's 5,000-bar window. |
| `data/hyperliquid/vaults` | Hyperliquid `/info` vaultDetails (public) | `scripts/fetch_hlp.py` | the HLP vault's account value and pnl history, one JSON per fetch | 60 KB | 2023-05 ..; two-week steps all-time, daily for the last month | 54191e05… | A yardstick (M285), not a lane input. Deposits blur step returns; drawdowns inside a step are not visible. |
| `data/kucoin_hist` | KuCoin Futures API (public) | `scripts/fetch_venue_history.py kucoin` | 692 USDT perps (642 open, 50 reserved) x daily candles, funding | 52 MB | 2021-01 .. 2026-10-20 | 3d1b69c4… | Contracts open on 2026-10-20 only (KuCoin's list omits delisted ones). Long tail (no Binance perp) and 2020 rows reserved (`docs/GATES.md`). |
| `data/dydx_hist` | dYdX v4 indexer (public) | `scripts/fetch_venue_history.py dydx` | 296 markets incl. 223 settled x hourly funding, daily and hourly candles (231 open, 65 reserved) | 184 MB | 2023-10 .. 2026-10-20 | 90a18b3d… | Candles carry open interest. Trade prices print crash wicks far from other venues (2025-10-11, R277 FINDINGS): a mark needs the oracle price, which these files do not hold. |
| `data/kraken_hist` | Kraken Futures API (public) | `scripts/fetch_venue_history.py kraken` | 207 perps (176 open, 31 reserved) x daily candles, funding | 53 MB | candles 2022-03 .., funding 2025-10-15 .. 2026-10-20 | 4565c5ea… | The public funding history goes back one year only. |
| `data/upbit_hist` | Upbit API (public) | `scripts/fetch_venue_history.py upbit` | 297 KRW spot markets (244 open, 53 reserved) x daily candles | 15 MB | 2021-01 .. 2026-10-20 | 1b2c60f4… | Korean spot, for the kimchi premium per coin. 2020 rows reserved. |
| `data/bithumb_hist` | Bithumb API (public) | `scripts/fetch_venue_history.py bithumb` | 487 KRW spot markets (367 open, 120 reserved) x daily candles | 25 MB | 2021-01 .. 2026-10-19 | 3895ffc6… | Korean spot. 2020 rows reserved. |
| `data/coinmetrics` | Coin Metrics community API v4 (no key) | `scripts/fetch_coinmetrics.py` | 904 assets (903 open files) | 63 MB | each asset's history to 2026-10-20 | ad488954… | Daily market cap, supply and the on-chain metrics the community tier serves. Latest vintage, not point-in-time. |
| `data/defillama` | DefiLlama API (public) | `scripts/fetch_fundamentals.py` | 300 perps mapped to a protocol (255 with files) | 16 MB | each protocol's history to 2026-10-20 | ebd8cefb… | Daily TVL, fees and revenue per Binance perp (`mapping.csv`). DefiLlama revises history: latest vintage, not point-in-time. |
| `data/gate_hist` | Gate public bulk archive (S3 `gateio-public-data`, listed with ListObjectsV2) | `scripts/fetch_gate_history.py` | 63,960 monthly files built into 1,619 contracts (861 open, 758 reserved) | 450 MB built (447 MB raw gz) | 2020-01 .. 2026-09 | d7c91467… (raw/ excluded; its S3 ETags are in raw/listing.json, sha256 50fc050f…) | Hourly candles and every funding settlement for every USDT perp, delisted ones included. Each file's MD5 is checked against its S3 ETag. `open/` = bases with a Binance perp from 2021; `reserved/` = the rest (GATES). Open hourly: 860 files, 14.4M bars, 1.16M interior holes in 747 files (Gate writes no row for an hour with no trade). |
| `data/macro` | alternative.me, FRED graph CSV (no key), DefiLlama free API | `scripts/fetch_macro.py` | 20 daily series plus raw responses | 14 MB | each series' full history to 2026-10-20 (`manifest.json`) | 851a4ce0… | Crypto Fear & Greed; US 3m/2y/10y yields, 10y-2y, fed funds, VIX, HY spread (FRED keeps 3 years), broad dollar, 10y breakeven, Fed assets, reverse repo, TGA; stablecoin supply (all, USDT, USDC), DeFi TVL, DEX volume, DeFi fees, options volume. Latest vintage, not point-in-time: weekly FRED series are dated by their week and published days later; DefiLlama revises history. DefiLlama's derivatives and bridge charts are paid (402). |
| `data/markPriceKlines_1h` | data.binance.vision USD-M mark price klines (public zips) | `lab/data.py` (`python -m lab.data build markPriceKlines 1h`) | 895 perps + manifest | 627 MB | 2020-01 .. 2026-09-30 | 491ac305… | Hourly OHLC of Binance's mark price, the price liquidations are triggered on: the median of two index-based prices and the last price, so a one-print wick of the traded price does not move it. Volume columns are 0. 779 files have holes (36,024 h in all). 2020 rows reserved (`docs/GATES.md`). For R280's open question: a liquidation path that does not follow traded prints. |
| `data/binance_recent` | data.binance.vision USD-M hourly klines, monthly and daily zips (public), each checked against its published SHA-256 | `scripts/fetch_binance_recent.py --end 2026-10-20 --unlock-post-archive` | 16 perps + manifest | 24 MB | each perp's first month .. 2026-10-20 | d91780e4… | Prices past the archive's end (2026-09-30) for R265's post_archive unlock events, plus BTCUSDT. The archive in `data/klines_1h` is unchanged. No funding (published monthly). |
| `data/cboe` | Cboe daily index history CSVs (`cdn-api.cboe.com`, public, no key) | `scripts/fetch_cboe.py` | 13 series + raw CSVs + manifest | 4 MB | VIX 1990 .., VVIX 2006 .., VIX3M 2009-09 .., VIX9D 2011 .., VIX1D 2022 .. ; to 2026-10-20 | 047ddf6c… | The VIX term structure (VIX1D, VIX9D, VIX, VIX3M, VIX6M, VIX1Y), VVIX, SKEW, and the vol indices of the Nasdaq-100, Russell 2000, Dow, oil and gold. A day's close is public about 21:15 UTC. |
| `data/recorders/funding_board` | Gate, Hyperliquid, OKX, Bitget, KuCoin, dYdX public APIs | `scripts/record_funding_board.py` (hourly, in `forward_all.sh`) | 1 per hour | | from 2026-10-20 21:00 | `experiments/recorders/journal/digests.csv` | Live funding of every USDT perp on six venues, normalized to 8 h. Point-in-time: none of these venues keeps the history of its displayed rate. |
| `data/news` | 22 public feeds: Bloomberg (markets, economics, politics, technology, crypto), WSJ, MarketWatch, CNBC, FT, Fed, SEC, ECB, CoinDesk, Cointelegraph, The Block, Decrypt, Blockworks, Kraken, Coinbase status, OKX listings | `scripts/record_news.py` (a daemon polling every 60 s; `forward_all.sh` restarts it) | one JSONL per UTC day | | from 2026-10-21 10:01 | `data/news/status.json` | Every new headline once, with the publisher's time and the time this machine first saw it (`seen_utc`). A study may act only after `seen_utc`. Feeds keep their latest items only, so no history before the recorder started. Upbit, Bithumb and Bybit refuse this machine (HTTP 403). |
| `data/tape` | Binance USD-M websockets (`/public` bookTicker, `/market` aggTrade) and MEXC contract websocket (`push.depth.full` top 5, `push.deal`), public | `scripts/record_tape.py` (a daemon; `forward_all.sh` checks it every hour and merges finished days) | one parquet per venue, book or trades, and UTC day | about 90 MB a day; capped at 3 GB | from 2026-10-21 06:35 UTC, 12 coins (BTC ETH SOL XRP DOGE BNB SUI ADA LINK AVAX LTC TRX) | `data/tape/sessions.csv` lists every connection and its gap | One row per (venue, coin, second) with an update (`lab/tape.py`): last best bid and ask with sizes in coins, the order-flow imbalance summed over the second, update count, worst receive lag; trades split by aggressor side with notional and first/last/low/high price. Point-in-time, cannot be backfilled. For M264 (order-flow scalp). |

## Derived tables (rebuilt from the folders above, never edited by hand)
- **`data/daily/`: the daily point-in-time panel** (`lab/daily.py`, built by `scripts/build_daily.py`).
  - **Shape:** one row per (day, Binance perp) on which the perp traded, 2021-01-02..2026-09-30: 591,598 rows, 899
    perps, 64 columns.
  - **Columns:** Binance price, volume, funding, premium, mark gap and wicks, order flow, depth, spot basis and
    COIN-M quarterly basis; each venue's price gap, funding and funding gap against Binance (Gate, MEXC, dYdX,
    Hyperliquid, KuCoin, Kraken); the Korean premium over BTC (Upbit, Bithumb); Coin Metrics and DefiLlama
    fundamentals; age and liquidity rank.
  - **Market table:** one row per day of every series in `data/macro`, each on the day it was public.
  - **Point in time:** every value sits on the first 00:00 UTC at which it was known, and a test changes the future
    and checks that no earlier row moves. Coin Metrics, DefiLlama and macro values are the latest vintage (`kind`
    column).
  - **Reserved rows:** none are read (no 2020 row, `open/` folders only, Binance perps only).
  - **Bookkeeping:** `columns.csv` defines every column; `manifest.json` holds the coverage per column, the code's
    sha256 and the combined sha256 of each input folder.
  - **Load it with** `lab.daily.load(columns=[...])` and `lab.daily.load_market()`.
- **Zero-trade bars.** Since 2021, 8.75% of Binance's hourly klines (1.36M bars) have no trade. 95% of them sit in
  the dead tails of 148 delisted perps, where the archive keeps writing bars at a frozen close (BTCST from 2021,
  RAY, FTT and SC for years). The daily panel drops them. The hourly research panel (`lab/panel.py`) keeps them as
  prices (MAP, known data defects).

## Not downloaded yet
- **CoinGecko 365-day market caps:** the free API keeps 365 days only.
- **One month of aggTrades for about 5 coins:** for markout research. Full tick history is excluded for disk.
