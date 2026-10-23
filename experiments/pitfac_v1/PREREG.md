# PREREG: pitfac_v1 (R282). What the daily point-in-time panel's new sources say about a Binance perp's next days

Freeze with `lab.prereg.freeze()` before any forward return is read. Never edited afterwards; a change is a new lane.

- **Registry id:** R282 (Claude block R280-R299, claimed on issue #7 on 2026-10-21).
- **Gate:** 0.
  - The Binance returns (2021-01..2026-09) are the archive many lanes have read.
  - The Korean, mark-price, Coin Metrics, DefiLlama and six-venue inputs are new to every factor lane. R276 read
    Gate and Hyperliquid funding.
- **Methods:**
  - M268 Korean premium;
  - M269 print-wick frequency;
  - M093 size;
  - M270 volume / cap;
  - M271 fee yield;
  - M272 OI / cap;
  - M273 venue breadth;
  - M274 multi-venue funding gap, which generalizes R276's M262;
  - M275 listing age.
- **The engine:** `qx factors` (`engine/src/factors.rs`), the second lane on it after R276, with
  `factor_cost_policy = "complete_paid_v1"`.
- **The question:** does a coin's Korean premium, its traded prints beyond the mark, its size, turnover, fees, leverage
  or breadth, its funding against six other venues, or its age, rank its Binance perp's next 1, 3 or 7 days?
- **Direction is not assumed.** Every factor is tested two-sided.
- **Execution mode:** API for a daily book of about 30 longs and 30 shorts. Manual-web only if a later lane nets it to
  15 orders.
- **Paper only.** Nothing here places an order.

## What the author has seen
- **Binance cross-sections**, all NULL in discovery:
  - R222: momentum, beta, MAX, premium net of funding;
  - R238: weekly momentum and reversal, MAX, IVOL, skew, 52-week high, funding slope, Abdi-Ranaldo spread;
  - R226: trade size;
  - R211 and R234: top-trader positioning.
- **R276** (cross-venue factors):
  - every Gate and Hyperliquid funding-gap rank IC was negative (-0.011 to -0.023) and failed the reality check;
  - Binance's own 3-day funding (the reference) passed it.
  - `fund_gap_all_7d` extends those gaps to six venues. A pass there would be read as R276's direction, not as a new
    discovery.
- **R275 to R281** (cross-venue carry): the pair books, not the cross-section of single perps.
- **The daily panel** (`data/daily/`, built 2026-10-21):
  - coverage per column, and value quantiles of every column for QA (outlier hunting found the dead-tail defect);
  - BTCUSDT's last three rows;
  - no column was ever compared with a forward return, and no IC, quantile spread or return was computed.
- **The factor table:** counts only.
  - 297,093 rows, 2,092 days, 737 coins.
  - Non-missing: kr_rel_7d 150,432; wick_30d 294,648; size 247,014; vol_mcap 246,995; fee_yield 60,394; oi_mcap
    98,681; n_venues_7d 297,093; fund_gap_all_7d 274,882; age 297,093.
  - Days with at least 30 names: fee_yield 1,209; oi_mcap 1,762; every other factor 2,089-2,092.
  - **A tenth factor was dropped for coverage before freezing:** tvl_mcap, ln(TVL / cap), had 30 names on only 241
    days.
- **The engine:** R276's run and its unit tests.

## Inputs (frozen)

```inputs
experiments/pitfac_v1/factors.parquet  deb00da8d4bb62d232091b237bb719c02ac34b1102029466daeebb4e0202539c
experiments/pitfac_v1/spec.toml  43f7e1ec684a4e7e2d072e9a929c11104cab91b6aed3a9a28963651937e1876d
scripts/pitfac_factors.py  bdf3dd3fb16afc060fed3c7acabb5998ce62e8856f5b48b11d300e9da3afa67a
scripts/build_daily.py  7363ac7b8d3fea936931f42a5e9f879438a6247ffe57dbc8f4f317c65c8743cf
lab/daily.py  4475f8962fb723e798383c839d6b0cc390c51b373937755a6d6ed2a62663cad6
lab/venues.py  ff6d80e23b337ee3c26ae44c718ba5893fb8e988fd23753631ddedd28b03e820
scripts/qx_run.py  37d95b72580f5f91ab272d1223bc30b0235d1b8e9c4cce1e9d53c9b9607b9cef
engine/src/factors.rs  c88beac9b02464cfda09203a42716cf9861dffb060182796e17266a5d72c61e1
engine/src/spread.rs  4055ceacd7949b742f864a35dfc1698262c1163200ccf0e5386a3dc726711074
engine/src/data.rs  4f4ea1ae3047da42db6c248bee0aeb192ac2eb9fb0709cbfa43a96005fb3a146
engine/src/events.rs  31bc1b59ac055a164256b606e88dad4cd2f1e3ad8280fab3e914b4f725911474
engine/src/stats.rs  bbf7615e3fee7f523e5984f83cee841316f2fb77d465d2ea2afa42f3b0724c47
engine/src/main.rs  42184bc6302dd9c71f4a804d7882d7a549a8e6d958571c2e49e54baf49d5f8c2
engine/Cargo.lock  9fc3e3a75a0275d0f3af29e1bfd901d358977e47fc9fe3413ef3318be791e11f
rebuild: bash -c ".venv/bin/python scripts/build_daily.py --out {tmp}/daily > /dev/null && .venv/bin/python scripts/pitfac_factors.py {tmp}/daily/panel.parquet {tmp}/factors.parquet > /dev/null"
```

Data digests at freezing (`docs/provenance/<folder>.json`, combined sha256; `data/daily/manifest.json` lists them
all):

| Folder | Digest | Files | Recorded (UTC) |
|---|---|---|---|
| `klines_1h` | 77fffa8a9d94cae2 | 901 | 2026-10-20 21:45 |
| `fundingRate` | d80aa377b9283329 | 901 | 2026-10-20 21:46 |
| `markPriceKlines_1h` | 491ac305187a91d6 | 896 | 2026-10-21 05:37 |
| `metrics_1h` | 68c2ccbcde091f38 | 488 | 2026-10-20 21:45 |
| `gate_hist` | d7c9146708710203 | 3330 | 2026-10-20 22:16 |
| `mexc_hist` | f40c28647bf74481 | 1823 | 2026-10-20 16:55 |
| `kucoin_hist` | 3d1b69c4b1189f45 | 1450 | 2026-10-21 02:44 |
| `dydx_hist` | 90a18b3d9b23bb33 | 892 | 2026-10-21 03:06 |
| `hyperliquid` | 9c8ca0af334b0e3b | 703 | 2026-10-20 23:06 |
| `kraken_hist` | 4565c5ea8043903d | 418 | 2026-10-21 02:44 |
| `upbit_hist` | 1b2c60f44938a764 | 355 | 2026-10-21 02:44 |
| `bithumb_hist` | 3895ffc69b26e9a4 | 537 | 2026-10-21 02:44 |
| `coinmetrics` | ad488954d6906a0c | 1229 | 2026-10-21 02:44 |
| `defillama` | ebd8cefba21ab1b4 | 293 | 2026-10-21 02:44 |

## Factors (`scripts/pitfac_factors.py`, on `lab/daily.py`'s panel)
- **Decision:** each day at 00:00 UTC. A row's t is the open of the hourly bar that ends then; entry is its close.
- **Universe:**
  - a Binance USD-M perp is eligible on day d when the panel has its row d (it traded in the 24 h before);
  - and it ranks in the top 150 by 30-day Binance quote volume (`rank_qvol30`, 7 days at least).
- **Point in time:** every value uses panel rows up to d only. The panel places each source on the first 00:00 UTC
  it was known:
  - hourly bars on the next 00:00;
  - Bithumb's KST candles a day later;
  - Coin Metrics and DefiLlama values 2 days after their date.

  tests/test_daily.py and tests/test_pitfac.py change the future and check that no earlier row moves.
- **Reserved samples are never read:** no 2020 row, only `open/` venue folders, Binance perps only.

| Factor | Definition |
|---|---|
| kr_rel_7d | mean over the last 7 days (3 at least) of the day's mean of `upbit_rel` and `bithumb_rel`: the coin's price relative to BTC on the Korean venue over the same ratio on Binance, minus 1 |
| wick_30d | share of the last 30 days (10 at least) with a traded print 2% or more beyond the mark: `wick_up` ≥ 0.02 or `wick_dn` ≤ -0.02 |
| size | ln(`mcap_est`), Coin Metrics' free-float cap |
| vol_mcap | ln(mean Binance quote volume over the last 30 days (7 at least) / `mcap_est`) |
| fee_yield | DefiLlama fees over the last 30 days (20 at least) × 365 / 30 / `mcap_est` |
| oi_mcap | ln(`oi_usd` / `mcap_est`) |
| n_venues_7d | mean over the last 7 days of the venues (of six) whose price passes the panel's identity check |
| fund_gap_all_7d | sum over the last 7 days (4 at least) of Binance's funding minus the mean of the other venues' funding that day |
| age | ln(1 + days since the coin's first panel row). Coins already trading on 2021-01-02 count from that day |

## The report (qx `factors`, as R276)
- **Forward return at h = 24, 72 and 168 h:** the Binance perp from the entry close to the last traded close at or
  before entry + h, minus the funding a long pays over (entry, exit]. A bar is traded only when its volume is above 0.
- **Per day, factor and horizon,** with at least 30 coins holding both values:
  - IC and rank IC;
  - quintile mean returns;
  - the top-minus-bottom quintile spread;
  - top and bottom turnover.
- **Per series:** mean rank IC, its t (Newey-West through the engine's block), IR, share of positive days, the
  long-short mean and t, and the daily book's net at 7 bp per side.
- **Reality check:** max |t| of rank IC over all 27 series. Stationary block bootstrap of dates (block = max(7, the
  longest horizon in days)), 2,000 draws, seed 282.

## Decision (fixed now; `scripts/qx_run.py` `factor_passes`, frozen above)
- **A factor passes when both hold:**
  - one of its horizons beats the reality check (p_RC < 0.05);
  - its daily book (h = 24, step 24 h) is positive at 1x and 2x of the complete paid cost (engine gross minus net,
    entry included), taken in the direction of its 24 h rank IC.
- **Verdict:** PARTIAL if a factor passes, else NULL. The 3x net is reported.
- **What a pass earns (pre-committed):**
  - a forward paper lane with a new id, on the daily panel's live twin. Building that twin is a separate step, and
    nothing is traded before it exists;
  - the reserved 2020 batch only for size, vol_mcap and age, which 2020 data can compute (Coin Metrics and Binance).
    The Korean, venue and DefiLlama factors have no 2020 rows in this lab.
- **No pass:** the factors are recorded as tested, and the panel stays as infrastructure.

## Multiplicity
- Trials: 27 (9 factors × 3 horizons).
- Program trials before this lane: 9,478,358, after R281.
- The reality check covers this family only. The program count is reported next to it.

## Not modelled
- Market impact beyond 7 bp per side (R262's square-root model applies to books above about $100k).
- The latest-vintage character of Coin Metrics and DefiLlama values (size, vol_mcap, fee_yield, oi_mcap use them).
  Revisions after the fact could leak information. A pass on those factors needs vintage-checked data before any
  money.
- Borrow and availability of shorts on MEXC: the book is on Binance prices.
