# PREREG: xvfac_v1 (R276). Cross-venue factors: what Gate and Hyperliquid say about a Binance perp's next days

Freeze with `lab.prereg.freeze()` before any forward return is read. Never edited afterwards; a change is a new lane.

- **Registry id:** R276 (Claude block R260-R279, claimed on issue #7 on 2026-10-20)
- **Gate:** 0. The Binance returns (2021-01..2026-09) are the archive many lanes have read. The Gate and Hyperliquid
  inputs are new to the lab.
- **Method:** M262 (new): cross-venue funding gaps, the Binance-Gate price-gap deviation and the change in Gate's
  volume share as cross-sectional predictors. The first lane on `qx factors` (`engine/src/factors.rs`).
- **The question:** a coin's positioning and attention differ by venue. When Binance longs pay more funding than
  Gate's (or Hyperliquid's), when Binance trades rich to Gate against its own recent norm, or when trading moves to
  Gate, does the Binance perp's next 1, 3 or 7 days differ across coins?
- **Direction is not assumed:** each factor is tested two-sided (crowding predicts reversal; information on one venue
  can also lead).
- **Execution mode:** API for a daily book of about 30 longs and 30 shorts. Manual-web only if a later lane nets it to
  15 orders.
- **Paper only.** Nothing here places an order.

## What the author has seen
- **Binance cross-sections (all NULL in discovery):** R222 (momentum, beta, MAX, premium net of funding), R238
  (weekly mom/rev, MAX, IVOL, skew, 52-week high, funding slope, Abdi-Ranaldo), R226 (trade size), R211 / R234
  (top-trader positioning).
- **The Binance funding level** as a carry signal: R190 / R191.
- **The inputs below:** counts only. 294,367 rows, 2,069 days, 700 coins. Non-missing values: fund_gap_3d 273,590,
  fund_gap_7d 272,184, hl_fund_gap_3d 92,822, price_gap_dev 248,053, vshare_chg 272,983, bn_fund_3d 293,050. Counted
  on a draft symbol table with fewer Hyperliquid coins. No distribution, no IC, no return.
- **The engine:** unit tests and one synthetic run (a planted factor found, noise not), never on real data.
- **R275 (cross-venue carry):** frozen the same day with the same symbol rule. Its result is not known when this file
  is frozen.
- **KuCoin and dYdX** (downloading when this file is frozen): row counts and first or last timestamps of three test
  files. No rate statistic.

## Inputs (frozen)

```inputs
experiments/xvfac_v1/symbols.csv  SYMBOLS_SHA
experiments/xvfac_v1/factors.parquet  FACTORS_PARQUET_SHA
experiments/xvfac_v1/spec.toml  SPEC_SHA
scripts/venue_symbols.py  VS_SHA
scripts/xvenue_factors.py  XF_SHA
engine/src/factors.rs  FACTORS_SHA
engine/src/spread.rs  SPREAD_SHA
engine/src/data.rs  DATA_SHA
engine/src/events.rs  EVENTS_SHA
engine/src/stats.rs  STATS_SHA
engine/src/main.rs  MAIN_SHA
engine/Cargo.lock  LOCK_SHA
rebuild: bash -c ".venv/bin/python scripts/venue_symbols.py {tmp}/symbols.csv > /dev/null && .venv/bin/python scripts/xvenue_factors.py {tmp}/symbols.csv {tmp}/factors.parquet > /dev/null"
```

Data digests at freezing (`docs/provenance/<folder>.json`, combined sha256): PROVENANCE_LINES

## Factors (`scripts/xvenue_factors.py`)
- **Decision:** each day at 00:00 UTC. A row's t is the open of the hourly bar that ends then; entry is its close.
- **Universe:**
  - a Binance USD-M perp is eligible on day d when its bar ending at day d traded;
  - and it ranks in the top 150 by Binance quote volume over the last 30 days;
  - coins come from `scripts/venue_symbols.py` (the R275 rule), so only coins with a Binance perp exist here;
  - reserved samples are never read: no Gate long tail, no MEXC-only coin, no row before 2021-01-01.
- **Definitions:** every value uses only bars and settlements at or before day d.

  | Factor | Definition |
  |---|---|
  | fund_gap_3d | Binance funding settled over the last 3 days minus Gate's |
  | fund_gap_7d | the same over 7 days |
  | hl_fund_gap_3d | Binance minus Hyperliquid, last 3 days (Hyperliquid from 2023-05) |
  | price_gap_dev | ln(Binance close / Gate close) at day d minus its median over the last 30 days (at least 20 days) |
  | vshare_chg | ln(Gate volume 7 d / 30 d) minus ln(Binance volume 7 d / 30 d) |
  | bn_fund_3d | Binance funding over the last 3 days alone (the known level, as the reference) |

- **Funding windows:** a window counts only if the venue's history covers it and it settled at least once in it.
  Settlements are floored to the hour and belong to the day that ends at or after them.

## The report (qx `factors`, `engine/src/factors.rs`)
- **Forward return at h = 24, 72, 168 h:** the Binance perp from the entry close to the last traded close at or
  before entry + h, minus the funding a long pays over (entry, exit].
- **Per day, factor and horizon:** needs at least 30 coins with both values.
  - IC and rank IC (Spearman, average ranks);
  - quintile mean returns, by factor rank, ties by symbol;
  - long-short = top quintile minus bottom;
  - turnover of the top and bottom quintiles versus the previous day.
- **t:** Newey-West with lags = h / 24.
- **Cost:** 7 bp per side. Net long-short is computed for h = 24 only (a book rebalanced daily): spread minus 2 x cost
  x (top turnover + bottom turnover).

## The family and the decision
- **Family:** 6 factors x 3 horizons = **18** series.
- **Reality check (RC):**
  - moving-block bootstrap of days, blocks of 7, 2,000 replications, ChaCha8 seed 276;
  - each rank-IC series is centred on its own mean;
  - the family statistic is the max |t| over the 18 series.
  - p_RC = (1 + #(family max |t| >= the series' |NW t|)) / 2,001.
- **A factor passes (gate 0)** when:
  - one of its horizons has p_RC < 0.05;
  - and its daily book is positive at 1x and at 2x cost: s x LS - 2 x m x 7 bp x (top + bottom turnover) > 0 for
    m = 1, 2, where s is the sign of its h = 24 rank IC (computed in `results/SUMMARY.md` from the report).
- **Verdict:** the registry row reads PARTIAL if any factor passes, NULL if none does. Gate 0 cannot confirm.

## Pre-committed (written before the result)
- **Each passing factor:**
  - gets a `lab/screen` spread-book lane (new id, frozen before it runs): the factor's direction from this report,
    daily 72 h slices, universe hedge, the standard discovery, validation and holdout windows, so its accounting
    matches R197 / R238;
  - and its h = 24 book joins the first reserved batch (Binance and Gate 2020 rows).
- **Each passing funding-gap factor (fund_gap_3d, fund_gap_7d, hl_fund_gap_3d) is also replicated on an unread
  venue:**
  - a new lane, frozen before it runs, with the same factor built against KuCoin in place of Gate (or Hyperliquid);
  - the same universe, horizons and report;
  - it replicates when the rank IC at the passing horizon has the same sign with NW t > 2 (one-sided, Bonferroni over
    the factors replicated) and the h = 24 book is positive at 2x.
- **If none passes:** nothing from this family goes further. bn_fund_3d is the reference; on its own it earns nothing
  either way.

## Reported, not counted
- Per series: IC, rank IC, IR, share of days with IC > 0, quintile means, long-short and its t, turnover, mean names
  per day, and the h = 24 net in %/yr.
- `results/ic.csv` holds the daily series for the dashboard.

## Known limits (written before the result)
- **Survivorship:** Hyperliquid histories hold only coins live on 2026-10-20.
- **Gate holes:** Gate has no bar in an hour with no trade, so price_gap_dev needs Gate's bar ending at 00:00 UTC.
- **Volume units:** Gate volume is in contracts and Binance's in coins. The units cancel in vshare_chg, which compares
  each venue with its own 30 days.
- **One venue for returns:** all forward returns are Binance's. A factor that only works on Gate is not looked for.

## Program reading
- Read against `registry.program_trials()` after this row: 9,477,741 plus R275's 560 before it, plus 18.
