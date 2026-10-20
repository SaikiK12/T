# PREREG: fundext_v1 (R273). Onset of extreme funding on every Binance perp: long and short, four horizons, one reality check

Freeze with `lab.prereg.freeze()` before any price is read. Never edited afterwards; a change is a new lane.

- **Registry id:** R273 (Claude block R260-R279, claimed on issue #7 on 2026-10-20)
- **Gate:** 0. This is the archive, 2021-01..2026-09, which the lab has used for other funding questions:
  - funding carry R190/R191;
  - carry crash R207;
  - settlement capture R223: holding across a settlement at |rate| >= 0.20% collected +47.6 bp of funding and lost
    72.3 bp on price;
  - R271: Binance's funding-frequency notices (issued when a perp's funding hits its cap) were followed by a rise in
    the next hour (+3.59%, t 3.31, n 35, family NULL).
- **The question:** does the price move in a predictable direction after a perp's funding first turns extreme? This
  turns R271's notice signal into a data-defined event with many more cases, and survivors can be confirmed on the
  reserved 2020 sample.
- **Execution mode:** API for 1 h and 8 h. 24 h and 72 h can be placed by hand.
- **Code:**
  - `scripts/funding_events.py` builds the events from settled funding only;
  - the `qx` engine prices them with `qx events experiments/fundext_v1/spec.toml`;
  - `scripts/qx_run.py experiments/fundext_v1` verifies this file, checks the inputs below, rebuilds the legs byte for
    byte, then runs qx.
- **Paper only.** Nothing here places an order.

## What the author has seen
- The event counts by kind and year below. They were computed from settled funding rates from 2021 on.
- R190, R191, R207, R223 and R271 in full.
- No price, volume or return has been read for any event at or after its settlement.
- **The 2020 funding rows are not read:** `funding_events.py` drops every row before 2021-01-01 before computing
  anything. 2020 is the reserved sample (docs/GATES.md).

## Inputs (frozen)

```inputs
experiments/fundext_v1/legs.csv  a42893cb45f8bcb32b29b9d85f8c72187a959aa8af545878379a6c846b356f4e
experiments/fundext_v1/spec.toml  4634db9e35224c85704068b97cd9e95b69a52ed28e26e60f1e9dca2f92d0e155
scripts/funding_events.py  375ee090de55889104fe55506ea21360db61488e097d4b8363ebfc788918eb6c
engine/src/data.rs  7e48666777878a4a6d71ac9fc7cea269b7944ab9ec288ebdd1837e66d8015c67
engine/src/events.rs  5c39c34d2336a00922f8dad437d8ef6bfebf2dcab1efaf33df4a3afea7f0ee1b
engine/src/stats.rs  bbf7615e3fee7f523e5984f83cee841316f2fb77d465d2ea2afa42f3b0724c47
engine/src/main.rs  da0f1b2429996bd2b5e5407110de6429c0ddb508383b8a27cd81394d14cb2d50
engine/Cargo.lock  9fc3e3a75a0275d0f3af29e1bfd901d358977e47fc9fe3413ef3318be791e11f
rebuild: python scripts/funding_events.py --out {tmp}
```

## Events (as built by `scripts/funding_events.py`)
- **Source:** `data/fundingRate/<perp>.parquet` for every Binance USD-M perp (901 files), settlements from
  2021-01-01 to 2026-09-30.
- **An event** is a settlement t of perp S whose settled rate reaches a level L in one sign, when no settlement of S in
  the previous 72 h reached L in that sign (the onset).
- **Kinds:**
  - pos0.3, pos1, pos2: rate >= +0.3% / +1% / +2% (longs pay);
  - neg0.3, neg1, neg2: rate <= -0.3% / -1% / -2% (shorts pay).
  - The levels are nested, so a 2% onset can also be a 1% and a 0.3% onset.
- **The first 72 h of 2021 are lookback only.** Events start on 2021-01-04.

| Kind | Events | Clusters (settlement hours) | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|
| neg0.3 | 3,359 | 2,335 | 241 | 224 | 221 | 254 | 1,066 | 1,353 |
| neg1 | 994 | 865 | 1 | 28 | 85 | 77 | 372 | 431 |
| neg2 | 372 | 353 | 1 | 8 | 41 | 34 | 145 | 143 |
| pos0.3 | 748 | 322 | 408 | 8 | 5 | 13 | 95 | 219 |
| pos1 | 30 | 28 | 0 | 0 | 1 | 2 | 12 | 15 |
| pos2 | 12 | 12 | 0 | 0 | 0 | 1 | 7 | 4 |

All six kinds have at least 10 clusters, so all are in the family.

## Trade (per leg): R271's rules, on the Binance perp only
- **r0** is the hourly bar that opens at the settlement. A leg needs the perp to have traded (volume > 0) on r0;
  otherwise it is `no_market`.
- **Entry:** the close of r0, one hour after the settlement.
- **Exits:** the close of r0 + h, for h = 1, 8, 24 and 72.
  - If that bar did not trade, the last traded close is used, flagged `stale_exit`.
  - A leg without data to r0 + h + 1 is missing at that horizon.
- **Return:**
  - long: `exit / entry - 1` minus funding settled in (entry, exit];
  - short: the negative of the price move plus that funding.
- **Cost:** 40 / 80 / 120 bp round trip at 1x / 2x / 3x.
- **Data error guard (`max_bar_jump = 20`):** a leg is dropped and listed as `suspect` if its perp's close moves by
  more than 20× in one bar between r0 - 24 and r0 + 72. Examples are redenominations and contract swaps.
- **One observation per cluster:**
  - a cluster is a (kind, r0) pair;
  - an instrument counts once per cluster;
  - the observation is the equal-weight mean net of the cluster's legs.
- **t:** mean / (sd / sqrt(n)), with ddof 1.
- **Halves:** in time order, floor(n/2) and the rest.

## The family and the decision
- **Strategies:** 6 kinds × {long, short} × {1, 8, 24, 72 h} = **48**.
- **Reality check (RC):**
  - For each kind, its clusters are resampled with replacement, 2,000 times. Every strategy of the kind uses the same
    draw. Each strategy's cluster observations are demeaned.
  - Kinds are resampled independently.
  - Before the bootstrap, each strategy's cluster observations are winsorized at its 5th and 95th percentiles
    (`winsor = 0.05`). The RC's observed t is computed on the same winsorized observations. Reported means, medians
    and t are raw.
  - The family statistic is the max t over all 48.
  - p_RC = (1 + #(family max t >= the strategy's t)) / 2,001.
  - Seed 273, ChaCha8, as qx implements it.
- **Gates (each strategy, 1x):**

  | Gate | Rule |
  |---|---|
  | RC | p_RC < 0.05 |
  | G2 | both halves have a mean > 0 |
  | G3 | at least 3 clusters from 2025-01-01, with a mean > 0 |
  | G4 | matched null p < 0.05 |
  | G5 | the mean at 2x cost > 0 |

- **The G4 null (R267's):**
  - the same instruments, the same hour of day, on a random day 7-60 days before the event (180 days if fewer than 10
    days are admissible);
  - a day is admissible if every leg traded there and has data to its exit;
  - 2,000 draws; p = (1 + #(null mean >= observed)) / 2,001.
  - It is run for each strategy that clears the RC.
- **Verdict:**
  - **PASS (gate 0)** for each strategy that clears all gates. The registry row reads PARTIAL if any strategy passes,
    NULL if none does.
  - Gate 0 cannot confirm.
- **Pre-committed (written before the result):** every passing strategy goes to the first reserved 2020 batch (from
  2026-11-03, docs/GATES.md). There it is built by these rules from the 2020 funding of the 81 reserved perps. If
  none passes, the top 3 by t go instead.

## Reported, not counted
For each strategy that clears the RC:
- per year;
- without the top 3 legs;
- gross before cost;
- the move in the hour before entry, in the strategy's direction;
- a BTC-hedged line (BTC perp over the same rows, 10 bp);
- stale and delisted-in-hold counts.

## Program reading
- Read against `registry.program_trials()` after this row (48 trials).
- **Forward option, if PASS:** MEXC's next funding rate is already recorded hourly (`data/recorders/mexc_ticker`). A
  new frozen lane would trade the onset on MEXC paper at the next settlement.
