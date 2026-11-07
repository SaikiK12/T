# PREREG: squeeze_v1 (R274). Shorts after a negative-funding onset, with a protective cover, on Binance and MEXC

Freeze with `lab.prereg.freeze()` before any price return is read. Never edited afterwards; a change is a new lane.

- **Registry id:** R274 (Claude block R260-R279, claimed on issue #7 on 2026-10-20)
- **Gate:** 0.
  - Binance 2021-26 is the archive R273 already read.
  - The MEXC sample (2025-04..2026-09) is new for this question, but the same months and mostly the same coins.
- **Method:** M261 (`registry/methods.csv`), queued by R273's FINDINGS.
- **The question:** after a perp's funding first turns very negative (shorts pay), the median coin keeps falling, but a
  few squeezes outweigh all the wins (R273). Does a cover that exits on a large adverse move keep the median and cut
  the tail enough to make the short pay?
- **The same pattern elsewhere in the lab:** new-listing shorts (R188: median -9% to -10% over 14 days; squeezes kept
  |t| < 3; R189: squeezes to +710%). This lane tests the cover on funding onsets only.
- **Execution mode:** API. The cover needs a check at every hourly close. A MEXC trigger order fires inside the hour,
  which is a different rule and is not what this tests.
- **Code:**
  - `scripts/squeeze_events.py` builds the events from settled funding only;
  - the `qx` engine prices them, with the new `stops` field (`Series::leg_stop` in `engine/src/data.rs`, unit test
    `stop_rules`);
  - `scripts/qx_run.py experiments/squeeze_v1` verifies this file, checks the inputs below, rebuilds the legs byte for
    byte, then runs qx.
- **Engine parity:** with `stops = [0]`, the new qx reproduces R273's strategies.csv and legs_priced.csv byte for byte
  (checked 2026-10-20 before this file was written).
- **Paper only.** Nothing here places an order.

## What the author has seen
- **R273 in full:** means, medians, hit rates and t for neg0.3 / neg1 / neg2 shorts and longs at +1 / 8 / 24 / 72 h,
  with no cover, on Binance.
  - Example: neg0.3 short +72 h, mean -0.99%, median +2.83%, 59% of clusters won.
  - No price path inside a hold was looked at. No 168 h result exists.
- **R188 / R189** (listing shorts) and R208 (stops hurt the lab's daily books).
- **MEXC:**
  - the event counts below (funding only);
  - the identity check's median price levels (515 contracts kept, ratio 0.75-1.99).
  - No MEXC return has been read.
- **The reserved MEXC-only coins are never read:** 87 contracts have no Binance perp. The builder drops them before
  reading anything, as GATES requires.

## Inputs (frozen)

```inputs
experiments/squeeze_v1/legs.csv  b698e01138676ba06d8d91c90fe2740c4264194a326b5906107731ce13157189
experiments/squeeze_v1/mexc_map.csv  e5e794ba9dafcff1c73f07b63dec28a6610fc1845ff71f307bef0ef924576202
experiments/squeeze_v1/spec.toml  05151cde658022a94ae2c2841c87cc6fb93b32fc864262ecf195a854162cad9b
experiments/fundext_v1/legs.csv  a42893cb45f8bcb32b29b9d85f8c72187a959aa8af545878379a6c846b356f4e
scripts/squeeze_events.py  3cb5d1f03672d83359caf5b661e92402faf39c8fd182c32d1f64e6933c96a1cc
engine/src/data.rs  b458920ecf39a15d514d495ed1480598af47cd445ed66c5bdcdbfcc7ab89eda8
engine/src/events.rs  31bc1b59ac055a164256b606e88dad4cd2f1e3ad8280fab3e914b4f725911474
engine/src/stats.rs  bbf7615e3fee7f523e5984f83cee841316f2fb77d465d2ea2afa42f3b0724c47
engine/src/main.rs  da0f1b2429996bd2b5e5407110de6429c0ddb508383b8a27cd81394d14cb2d50
engine/Cargo.lock  9fc3e3a75a0275d0f3af29e1bfd901d358977e47fc9fe3413ef3318be791e11f
rebuild: python scripts/squeeze_events.py --out {tmp}
```

## Events (as built by `scripts/squeeze_events.py`)
- **Binance (kinds bn_neg0.3, bn_neg1, bn_neg2):** R273's negative onsets, unchanged (`experiments/fundext_v1/legs.csv`,
  frozen in R273). Priced on the Binance perp, 2021-01-04..2026-09-30.
- **MEXC (kinds mx_neg0.3, mx_neg1, mx_neg2):** the same rule on MEXC's settled funding (`data/mexc_hist/funding`).
  - An onset is a settlement at or below -0.3% / -1% / -2% with no settlement of the same contract at or below that
    level in the previous 72 h.
  - Only USDT perps whose base maps to a Binance perp in the archive (plain, 1000 or 1000000 prefix), with the median
    close within 3x after the multiplier. 515 of 607 contracts are kept:
    - 87 have no Binance perp (MEXC-only, reserved);
    - 2 fail the price check;
    - 3 have too little overlap.
  - Priced on the MEXC perp (`data/mexc_hist/klines_1h`, volume column `vol`), with MEXC funding.
  - History starts 2025-04-01, so events start on 2025-04-04.
  - `contracts.json` lists the 607 contracts live on 2026-10-20. Contracts MEXC delisted before then are missing. Coins
    that collapsed and were delisted would have helped a short, so this bias works against the short.

| Kind | Events | Clusters (settlement hours) | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|
| bn_neg0.3 | 3,359 | 2,294 | 241 | 224 | 221 | 254 | 1,066 | 1,353 |
| bn_neg1 | 994 | 864 | 1 | 28 | 85 | 77 | 372 | 431 |
| bn_neg2 | 372 | 353 | 1 | 8 | 41 | 34 | 145 | 143 |
| mx_neg0.3 | 1,974 | 1,316 | | | | | 843 | 1,131 |
| mx_neg1 | 629 | 549 | | | | | 239 | 390 |
| mx_neg2 | 220 | 209 | | | | | 85 | 135 |

## Trade (per leg): R273's rules, short only, plus the cover
- **r0** is the hourly bar that opens at the settlement. A leg needs its perp to have traded (volume > 0) on r0;
  otherwise it is `no_market`.
- **Entry:** the close of r0, one hour after the settlement.
- **Exit:** the close of r0 + h, for h = 24, 72 and 168.
  - If that bar did not trade, the last traded close is used, flagged `stale_exit`.
  - A leg without data to r0 + h + 1 is missing at that horizon.
- **Cover s** (0, 10%, 20% or 35%):
  - for s > 0, the short exits at the first traded hourly close in (r0, r0 + h] that is at least (1 + s) × entry;
  - s = 0 holds to the horizon;
  - the cover can fire at r0 + h itself; then it is the same exit.
- **Return:** -(exit / entry - 1) plus the funding settled in (entry, exit]. The short receives a positive rate and
  pays a negative one, so these shorts mostly pay.
- **Cost:** 40 / 80 / 120 bp round trip at 1x / 2x / 3x.
  - A cover fires in a fast market, where the spread is wider. The 2x and 3x lines are the check on that.
- **Data error guard (`max_bar_jump = 20`):** a leg is dropped and listed as `suspect` if its perp's close moves by
  more than 20× in one bar between r0 - 24 and r0 + 168.
- **One observation per cluster:**
  - a cluster is a (kind, r0) pair;
  - an instrument counts once per cluster;
  - the observation is the equal-weight mean net of the cluster's legs.
- **t:** mean / (sd / sqrt(n)), with ddof 1.
- **Halves:** in time order, floor(n/2) and the rest.

## The family and the decision
- **Strategies:** 6 kinds × short × {24, 72, 168 h} × {no cover, 10%, 20%, 35%} = **72**.
  - A kind with fewer than 10 priced clusters drops out, and the trial count follows the strategies run.
- **Reality check (RC):**
  - For each kind, its clusters are resampled with replacement, 2,000 times. Every strategy of the kind uses the same
    draw. Each strategy's cluster observations are demeaned.
  - Kinds are resampled independently.
  - **No winsorizing (`winsor = 0`):** the question is the tail, so the RC sees it raw.
  - The family statistic is the max t over all strategies.
  - p_RC = (1 + #(family max t >= the strategy's t)) / 2,001.
  - Seed 274, ChaCha8, as qx implements it.
- **Gates (each strategy, 1x):**

  | Gate | Rule |
  |---|---|
  | RC | p_RC < 0.05 |
  | G2 | both halves have a mean > 0 |
  | G3 | at least 3 clusters from 2025-01-01, with a mean > 0 |
  | G4 | matched null p < 0.05 |
  | G5 | the mean at 2x cost > 0 |

- **The G4 null (R267's, with the same cover):**
  - the same instruments, the same hour of day, on a random day 7-60 days before the event (180 days if fewer than 10
    days are admissible);
  - a day is admissible if every leg traded there and has data to its exit;
  - 2,000 draws; p = (1 + #(null mean >= observed)) / 2,001.
  - It is run for each strategy that clears the RC.
- **Verdict:**
  - **PASS (gate 0)** for each strategy that clears all gates. The registry row reads PARTIAL if any strategy passes,
    NULL if none does.
  - Gate 0 cannot confirm.

## Pre-committed (written before the result)
- **Forward lane on MEXC (new id, frozen before its first ticket).** MEXC has about 90 mx_neg0.3 onsets a month in
  2026, so a forward lane decides in weeks, not years.
  - If any mx_ strategy passes, the passing one with the highest t goes forward.
  - Otherwise, the mx_ strategy with a cover (s > 0) and the highest 1x t goes forward, whatever the family verdict, if:
    - its t >= 2,
    - its 2x mean > 0,
    - and its median > 0.
  - If none qualifies, no forward lane comes from this family.
- **2020 batch:** the bn_ strategy with a cover and the highest t joins the first reserved 2020 batch. Before reading,
  the batch PREREG states how many 2020 onsets exist; neg1 had 1 onset in 2021.

## Reported, not counted
- For every strategy: the no-cover baseline next to it (same kind and horizon) at 1x / 2x / 3x.
- For each strategy that clears the RC:
  - per year;
  - without the top 3 legs;
  - gross before cost;
  - the number of legs whose cover fired;
  - stale and delisted-in-hold counts.

## Program reading
- Read against `registry.program_trials()` after this row: 9,477,669 before it, plus 72.
