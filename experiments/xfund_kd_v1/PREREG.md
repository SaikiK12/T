# PREREG: xfund_kd_v1 (R277). R275's best carry book replicated, unchanged, on venues R275 never read: KuCoin and dYdX

Freeze with `lab.prereg.freeze()` before any KuCoin or dYdX price return or funding statistic is read. Never edited
afterwards; a change is a new lane.

- **Registry id:** R277 (Claude block R260-R279, claimed on issue #7 on 2026-10-21)
- **Gate:** 0 in time (the archive window, 2021-01..2026-09). It is new evidence in venues: R275 read Binance, Gate,
  Hyperliquid and MEXC, and no lane has read KuCoin or dYdX funding or prices.
- **Method:** M059 (cross-venue funding carry), venue replication.
- **Source:**
  - R275 xfund_v1 (PARTIAL: 212 of 560 books pass gate 0).
  - Its PREREG pre-committed this lane, whatever the result: "applies one book's lookback, threshold and slots
    unchanged to four sets built only on venues this family never read: binance+kucoin, binance+dydx, gate+kucoin,
    kucoin+dydx".
  - "The book: the best passing book by 1x t". That is **gate+hyperliquid L14d th5% K20** (t 12.70).
  - "A set replicates when its NW t > 2.50 (one-sided p < 0.0125, Bonferroni over 4), HALVES holds and its 2x mean
    is > 0."
- **Execution mode:** API, as R275. Both legs are placed at the daily close on two venues.
- **Paper only.** Nothing here places an order.

## What the author has seen
- **R275 in full:** all 560 books, its audit and its by-year table. R278 (the forward lane) was frozen before this file.
- **KuCoin and dYdX**, from `scripts/fetch_venue_history.py`:
  - the fetch logs: row counts per symbol and kind;
  - while testing the fetcher (2026-10-20): row counts and first or last timestamps of the BTC, ETH and PEPE files;
  - while preparing this lane (2026-10-21): the BTC files' shapes, column types and first and last timestamps.
- **Not computed on KuCoin or dYdX:** no funding rate statistic, no spread and no return.
- **The symbol table** is built from file names and contract lists only (`lab/venues.py`).

## Inputs (frozen)

```inputs
INPUTS
rebuild: python scripts/venue_table.py --venues gate,kucoin,dydx --out {tmp}/symbols.csv
```

- **Engine:** the `qx spread` sources are byte-identical to R275's frozen ones (same hashes as in R275's inputs).
- **Symbol table:**
  - one row per Binance USD-M perp found on Gate, KuCoin or dYdX, under R274's name rule (`lab/venues.py`);
  - Gate rows are the same contracts R275 used;
  - KuCoin's and dYdX's long tail (no Binance perp) and 2020 rows are reserved (`docs/GATES.md`) and never listed.

## The family (4 books, no other parameter)
- **Books:** sets binance+kucoin, binance+dydx, gate+kucoin, kucoin+dydx, each at lookback 14 days, entry threshold
  5%/yr and 20 slots.
- **Engine:** `qx spread` (`experiments/xfund_kd_v1/spec.toml`).
- **Rule, accounting and costs:** identical to R275:
  - daily axis at 00:00 UTC;
  - identity guard (correlation ≥ 0.9 over 30 days, at least 20 observations);
  - widest pair, entries widest first, exit below th/2;
  - net on total capital at 7 / 14 / 21 bp per leg per side.
- **Venues:**

  | Venue | Prices | Volume column | Funding | Bar hours |
  |---|---|---|---|---|
  | KuCoin | daily candles (`kucoin_hist/open/candles_1d`) | volume | `kucoin_hist/open/funding` | 24 |
  | dYdX v4 | hourly candles (`dydx_hist/open/candles_1h`) | volume | `dydx_hist/open/funding` | 1 |

  Binance and Gate are as in R275.
- **Window:** 2021-01-01..2026-09-30. Each set starts when its venues' funding histories allow; dYdX v4 starts in
  2023-10.

## Decision
- **A set replicates when all hold** (columns of `results/strategies.csv`):
  - `t_nw_1x` > 2.50 (Newey-West, 10 lags);
  - `half1_bp` > 0 and `half2_bp` > 0;
  - `ann_2x_pct` > 0.
- **Lane verdict (registry):**
  - **CONFIRMED** (venue replication) if at least 3 of the 4 sets replicate;
  - **PARTIAL** if 1 or 2 replicate;
  - **NULL** if none does.
- **Reported, not decided on:**
  - the engine's own family gates (RC over the 4 books, RECENT, TRIM, HURDLE) and its `pass` column;
  - 1x / 2x / 3x annual net, by year, max drawdown, funding share, pairs held, trades, forced exits and the
    top-10-day share.
- **What a replication earns:**
  - Evidence that R275's carry is a property of cross-venue funding, not of the four venues it read.
  - A replicating set with a venue the owner can trade may get its own forward lane (a new id). Nothing else changes:
    R278 keeps its frozen books.

## Known limits (written before the result)
- **Survivorship:**
  - KuCoin's contract list holds only contracts open on 2026-10-20 (692 USDT perps), so coins KuCoin delisted are
    missing.
  - dYdX's includes 223 settled (delisted) markets.
- **KuCoin prices are daily bars:**
  - A KuCoin close is fresh only when that day's bar traded.
  - Its intraday path is not seen, as with Hyperliquid in R275.
- **The engine is R275's**, so its known flaw stays: when one venue stops trading a coin, that leg's close is carried
  forward for a day while the other leg moves. A delisting fix belongs to the next engine version.
- **Same ticker, different coin:** the correlation guard rejects such pairs. It is not proof of identity.
- **Not modelled (as R275):**
  - liquidation above 1x;
  - moving collateral;
  - fills at the close on two venues at once.

## Multiplicity
- Trials: 4.
- Program trials before this lane: 9,478,322 (after R278).
- The bar (NW t > 2.50) is Bonferroni over the 4 sets. The lane is a confirmation of R275, not a new search.
