# PREREG: announce_v1 (R271). Every Binance announcement type as one family: long and short, four horizons, one reality check

Freeze with `lab.prereg.freeze()` before any price is read. Never edited afterwards; a change is a new lane.

- **Registry id:** R271 (Claude block R260-R279, claimed on issue #7 on 2026-10-20)
- **Gate:** 0. This is the archive, 2021-01..2026-09, which the lab has used for other questions.
  - The old session read Binance listing notices on the Binance perp (R165: n 34, +1 h long +3.19%, t 1.06; 24 h
    short -1.99%, t -0.35). That is disclosed; the other types are unread to the author's knowledge.
  - The three event lanes that worked so far are all Binance warnings followed by a slow repricing:
    - unlock short R265;
    - spot delisting R267 (variant);
    - Monitoring Tag R269 (variant).
  - This lane asks whether Binance's other announcements move prices after the first hourly open, in either
    direction.
- **Execution mode:** API for +1 h. +24 h and longer can be placed by hand if the owner is alerted within the hour.
- **Code:**
  - `scripts/announce_events.py` builds the legs from titles and file names only.
  - The `qx` engine (`engine/`, Rust) prices them with `qx events experiments/announce_v1/spec.toml`. qx reproduces
    R269 to 9 decimals (`tests/test_qx_parity.py`).
  - `scripts/qx_run.py experiments/announce_v1` verifies this file, checks the inputs below, rebuilds the legs byte
    for byte, then runs qx.
- **Paper only.** Nothing here places an order.

## What the author has seen
- The titles of all 7,183 catalog rows, and the type counts and leg list below.
- R267 and R269 in full.
- No price, volume, funding or return has been read for any leg at or after its notice.

## Inputs (frozen)
- **Catalogs:**
  - `data/recorders/notices/binance_{news,delisting,listing}.csv`, deduplicated by id;
  - rows released before 2026-10-20T17:00:00Z (7,183 rows).
  - sha256 of those rows' `id,code,title,release_ms` as CSV:
    bc5383ccf96bf2c31ea99dbb4dee4e4e0ac1986c595092f6be80b782b018ae22.

```inputs
experiments/announce_v1/legs.csv  ee98416d8960fbf2322f916f5d7269120b83670d43d2c0197c82979de5215224
experiments/announce_v1/spec.toml  17dd1ef383ab051d9a61ea3780e0ad04e1582aa918a2457efdbc46da8fe1a247
scripts/announce_events.py  37eba18ff884823a4b1a762dfc9a44deb5cbc200fb2235c1c3b58c72cf3f4ec2
engine/src/data.rs  7e48666777878a4a6d71ac9fc7cea269b7944ab9ec288ebdd1837e66d8015c67
engine/src/events.rs  51b412d2cad7f0adfba8a947425ed9c4572e2cae6f6658b9067b1b7872d6bdd7
engine/src/stats.rs  bbf7615e3fee7f523e5984f83cee841316f2fb77d465d2ea2afa42f3b0724c47
engine/src/main.rs  da0f1b2429996bd2b5e5407110de6429c0ddb508383b8a27cd81394d14cb2d50
engine/Cargo.lock  9fc3e3a75a0275d0f3af29e1bfd901d358977e47fc9fe3413ef3318be791e11f
rebuild: python scripts/announce_events.py --out {tmp}
```

- **Legs:** 1,724 notices give 2,505 legs in all.
  - The sample is `window == archive`, released 2021-01-01..2026-09-30.
  - Notices from 2020 (`reserved_2020`) and after the archive are never priced here.

  | Type | Archive notices | Legs |
  |---|---|---|
  | spot_list | 163 | 184 |
  | perp_launch | 370 | 473 |
  | prelist | 139 | 139 |
  | margin_add | 128 | 330 |
  | earn_add | 180 | 209 |
  | pairs_add | 106 | 381 |
  | fund_freq | 37 | 40 |
  | upgrade | 122 | 122 |
  | holder_drop | 3 | 3 |

  holder_drop has fewer than 10 clusters, so it is out of the family by the rule below.
- **Prices:** hourly, 2021-01-01..2026-09-30, from three venues:
  - Binance USD-M perps: `data/klines_1h`, with funding from `data/fundingRate`;
  - MEXC perps: `data/mexc_hist`, from 2025-04, with MEXC funding;
  - Binance spot: `data/spot_1h`, no funding.
  - No row before 2021 is read; qx refuses an earlier start.

## Events and legs (as built by `scripts/announce_events.py`)
Each type below is defined by a title rule (see the script for the exact rules):

| Type | Title rule |
|---|---|
| spot_list | "Binance Will List / Lists Name (TKR)". Innovation Zone, Seed Tag and HODLer listings are included; leveraged tokens are not. |
| perp_launch | "Binance Futures Will Launch USDⓈ-M ... Perpetual". No TradFi, equity, COIN-M, USDC, quarterly, pre-market or "Multiple" titles. |
| prelist | "Introducing Name (TKR) on Binance Launchpool / Launchpad / HODLer Airdrops / Megadrop". |
| margin_add | Cross or isolated margin enabled or added for named coins. |
| earn_add | Convert, Simple Earn, Staking, Auto-Invest or Savings adds a named coin. |
| pairs_add | The base coins of "Binance Adds A/B, C/D Trading Pairs". |
| fund_freq | A change to one perp's funding settlement frequency, not "resumed". |
| upgrade | "Binance Will Support the Name (TKR) Network Upgrade / Hard Fork / Token Swap / Rebrand / Migration". |

- Stablecoins and quote assets are dropped.
- **Instrument candidates (names only):**
  - the Binance perp `<T>USDT` (or its 1000/1000000 prefix);
  - the MEXC perp, only if the coin has a Binance perp in the archive. So the reserved MEXC-only coins are never read;
  - the Binance spot pair `<T>USDT`.

## Trade (per leg): R267/R269's rules
- **r0** is the hourly bar that contains the notice. The leg trades on the first venue, in the order perp, MEXC, spot,
  whose symbol traded (volume > 0) on r0. Otherwise it is `no_market`.
- **Entry:** the close of r0, which is the first hourly open after the notice.
- **Exits:** the close of r0 + h, for h = 1, 24, 72 and 168. If that bar did not trade, the last traded close is used,
  flagged `stale_exit`. A leg without data to r0 + h + 1 is missing at that horizon.
- **Return:**
  - short: `-(exit / entry - 1)` plus funding settled in (entry, exit];
  - long: the negative of that.
  - Spot legs have no funding. In practice they would be traded on the MEXC perp.
- **Cost:** 40 / 80 / 120 bp round trip at 1x / 2x / 3x.
- **One observation per cluster:**
  - a cluster is a (type, r0 hour) pair;
  - an instrument counts once per cluster;
  - the observation is the equal-weight mean net of the cluster's legs.
- **t:** mean / (sd / sqrt(n)), with ddof 1.
- **Halves:** in time order, floor(n/2) and the rest.

## The family and the decision
- **Strategies:** every type with at least 10 clusters × {short, long} × {1, 24, 72, 168 h} = 8 × 8 = **64**.
- **Reality check (RC):**
  - For each type, its clusters are resampled with replacement, 2,000 times. Every strategy of the type uses the same
    draw. Each strategy's cluster observations are demeaned.
  - Types are resampled independently.
  - The family statistic is the max t over all 64.
  - p_RC = (1 + #(family max t >= the strategy's t)) / 2,001.
  - Seed 271, ChaCha8, as qx implements it.
- **Gates (each strategy, 1x):**

  | Gate | Rule |
  |---|---|
  | RC | p_RC < 0.05 |
  | G2 | both halves have a mean > 0 |
  | G3 | at least 3 clusters from 2025-01-01, with a mean > 0 |
  | G4 | matched null p < 0.05 |
  | G5 | the mean at 2x cost > 0 |

- **The G4 null (R267's):**
  - the same instruments, the same hour of day, on a random day 7-60 days before the notice (180 days if fewer than
    10 days are admissible);
  - a day is admissible if every leg traded there and has data to its exit;
  - 2,000 draws; p = (1 + #(null mean >= observed)) / 2,001.
  - It is run for each strategy that clears the RC.
- **Verdict:**
  - **PASS (gate 0)** for each strategy that clears all gates. The registry row reads PARTIAL if any strategy passes,
    NULL if none does.
  - Gate 0 cannot confirm.
- **Pre-committed (written before the result):** every passing strategy goes to the first reserved 2020 batch (from
  2026-11-03, docs/GATES.md), priced by these rules on the 2020 notices. If none passes, the top 3 by t go instead.
  - 2020 has spot_list 214, perp_launch 66, pairs_add 70, margin_add 65, prelist 23, upgrade 19 and earn_add 11
    notices.

## Reported, not counted
For each strategy that clears the RC:
- per year;
- without the top 3 legs;
- by venue;
- gross before cost;
- the move in the notice's own hour, in the strategy's direction;
- a BTC-hedged line (BTC perp over the same rows, 10 bp);
- stale and delisted-in-hold counts.

## Program reading
- Read against `registry.program_trials()` after this row (64 trials).
- **Forward option, if PASS:** the notice recorder already journals all three catalogs hourly. A new frozen lane
  would trade each surviving type on MEXC, like R268 and R270.
