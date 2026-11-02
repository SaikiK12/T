# PREREG: presence_v1 (R383). Does R282's oi_mcap book depend on whether a row has Binance metrics? (M459)

Frozen with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R383
- **Method M459:** metrics-availability look-ahead audit. Narrow list item: R282 pitfac_v1 (top 150, oi_mcap factor).
- **Owner (single writer):** the Claude session that froze it. Writes only `experiments/presence_v1/`,
  `scripts/run_presence.py` and `tests/test_run_presence.py`.
- **Gate: 0, on seen data.** Every window was read by R282 and R332.

## Question
R282's factor table (`experiments/pitfac_v1/factors.parquet`) takes oi_mcap = ln(oi_usd / mcap_est) from
`data/daily/panel.parquet`, where a row holds `oi_usd` only if the coin was among the 100 most traded within 35 days
(R332, `experiments/mlrank_v3/FINDINGS.md`). Does the oi_mcap book still earn when `oi_usd` comes from
`data/daily_v2/panel.parquet`, which holds it for 99-100% of top-150 rows from 2022? And does a book that only asks
"does this row have `oi_usd`?" earn what R282's oi_mcap book earned?

## What the author has seen
- **R282's published result** (`experiments/pitfac_v1/FINDINGS.md`, `results/report.json`):
  - oi_mcap did **not pass** R282's frozen rule. Its rank IC is negative (-0.078 at 24 h), so the frozen direction is
    "long low OI/cap", and that book nets -37.8 / -39.7 / -41.5 bp/day at 1x / 2x / 3x.
  - The opposite direction (long the top fifth, short the bottom fifth) is a post-hoc observation recorded by R282:
    24 h gross +36.0 bp/day (NW t 3.26), net 1x +34.1 bp/day with Newey-West t 3.09, +124.5 %/yr, 1,761 dates,
    55.8 names a day, best 10 days 47% of the sum, carried by 2025-26.
  - Of R282's nine factors only oi_mcap reads a metrics column (`oi_usd`). `scripts/pitfac_factors.py` reads no other
    (`top_ls_pos`, `ls_acc`, `taker_ls` are not in its column list). The two factors that passed R282's rule, age and
    vol_mcap, do not read metrics.
- **R332's result:** on R304's panel a presence-only book earned +50.3 bp/day net (t 4.47) at hold 7; and the columns
  that differ between `data/daily` and `data/daily_v2` are `oi_usd`, `top_ls_pos`, `ls_acc` and `taker_ls` only.
- **Plumbing run of `scripts/run_presence.py --plumbing`** (builds the tables and compares them; no return is read,
  no engine run, no statistic split by presence):
  - R282's `factors()` on `data/daily` reproduces R282's frozen `factors.parquet` exactly (297,093 rows, NaN-aware
    equality on all nine columns).
  - On `data/daily_v2` the table has the same rows. Its eight other factor columns (kr_rel_7d, wick_30d, size,
    vol_mcap, fee_yield, n_venues_7d, fund_gap_all_7d, age) are **identical** to v1's; only oi_mcap differs.
  - oi_mcap has a value on 98,681 rows in v1 and 214,767 in v2. Rows both hold: 98,681; they agree to 1e-9 except 1.
    Rows only v2 holds: 116,086; rows only v1 holds: 0.
  - Names with oi_mcap per day, of 142 in the universe on average: v1 47.2, v2 102.7. Days with at least 30 names:
    v1 1,762, v2 1,763.
  - Share of universe rows holding `oi_usd`, v1 / v2: 2021 0.053 / 0.106, 2022 0.466 / 0.997, 2023 0.442 / 0.999,
    2024 0.439 / 1.000, 2025 0.439 / 0.999, 2026 0.440 / 0.992.
  - Days on which 20-80% of the universe rows hold `oi_usd` (the days on which a random fifth with against a random
    fifth without is well defined): v1 1,764, v2 0.
- **Never computed before the freeze:** any return of any book on `data/daily_v2`; any presence book; any statistic
  that splits returns by whether a row has metrics.

## Books (5 trials; the engine runs them side by side, each cross-section independent of the others)
One table, `results/table.parquet`, rows = R282's factor rows (top 150 by `rank_qvol30`, on days the perp traded),
columns:

| Book | Values | Role |
|---|---|---|
| oi_mcap_v1 | R282's oi_mcap on `data/daily`, from `scripts/pitfac_factors.py` `factors()` unchanged | reproduction of R282; decision input |
| oi_mcap_v2 | the same function on `data/daily_v2` | decision input |
| oi_mcap_v2_on_v1 | oi_mcap_v2 kept only where oi_mcap_v1 has a value (v1's rows, v2's values) | diagnostic: separates new rows from changed values |
| presence_v1 | 1 + u where the row holds `oi_usd` in `data/daily`, else u; u ~ U(0,1) from `numpy.random.default_rng(383)`, one draw per table row in (t, sym) order | presence control; decision input |
| presence_v2 | the same with `oi_usd` of `data/daily_v2` and the same u | sanity: nearly every row has metrics, so this book is close to a random book |

- **The presence control is R332's presence book on R282's universe, hold and cost:** the engine's top fifth is a
  random fifth of the rows with `oi_usd` and its bottom fifth a random fifth of the rows without it, whenever each
  group holds a fifth of the rows. It holds no model and no feature other than whether row D has `oi_usd`.
- **Other factors:** none of R282's eight other factors reads a metrics column, and their columns are identical on the
  two panels (plumbing above). They are not re-run as books. The runner repeats that identity check and stores it.
- **R282's own construction, unchanged:** engine `qx factors` (`engine/src/factors.rs` and its inputs, hashed below),
  entry at the close of the bar ending 00:00 UTC, forward return to the last traded close at or before entry + h minus
  the funding a long pays, quintiles by factor rank with ties broken by symbol order, at least 30 names a date,
  7 bp per side at 1x, **h = 24 h book rebalanced every 24 h** (R282's decision book), h = 72 and 168 reported.

## Windows and costs
- **Decision window ALL:** 2021-01-01..2026-09-30, R282's own window and its single window. R282 had no
  discovery/validation split, so this lane's "validation" is read as this whole window.
- **Reported, not decided on:** D 2021-01-01..2023-12-31 and V 2024-01-01..2026-09-30 (R332's validation span), each
  an engine run on the same table; gross by calendar year, the gross median and the gross mean without the best 10
  days (from `ic.csv`).
- **Costs:** the engine's net at 7 bp per side (1x), 14 bp (2x) and 21 bp (3x), each a separate run on window ALL with
  its own Newey-West t. Spec files `spec_all_1x.toml`, `spec_all_2x.toml`, `spec_all_3x.toml`, `spec_d_1x.toml`,
  `spec_v_1x.toml` are frozen below.

## Decision (fixed now)
Let t(F) be the engine's `ls_net_t` for factor F, window ALL, h = 24, 1x cost: the Newey-West (1 lag) t of the daily
net of the book long the top fifth and short the bottom fifth. It is signed.
- **The audited book** is the one with a positive net in R282's table: long high oi_mcap. R282's frozen direction
  (long low) did not pass; it is reported from the same output (-gross - k x paid cost) and does not enter the rule.
- **Precondition (reproduction):** oi_mcap_v1 must reproduce R282's report.json for oi_mcap (rank IC, IC, dates,
  gross spread at h = 24, 72, 168; net and net t at h = 24) within a relative difference of 1e-6, and t(oi_mcap_v1) ≥
  2.0. If not, the label is `INVALID` and the verdict NULL.
- **Label `survives`** if t(oi_mcap_v2) ≥ 2.0 (same sign as R282's positive t, and at least 2.0).
- **Label `metrics-leak`** if t(presence_v1) ≥ 2.0 **and** t(oi_mcap_v2) < 2.0 (signed: a sign flip counts as below).
- **Label `not-reproduced`** if t(oi_mcap_v2) < 2.0 and t(presence_v1) < 2.0: the book does not survive complete
  metrics, and presence is not shown to be the cause.
- **Verdict:** PARTIAL (gate 0) for `survives`, NULL for every other label. If `survives` and t(presence_v1) ≥ 2.0 as
  well, both are reported and the book is read as partly presence.
- **What `survives` earns:** only a registered forward or reserved-sample lane for the long-high-oi_mcap direction,
  which was chosen after seeing R282's table. No money. It would still need vintage-checked market caps (R282 "Not
  modelled") and a check of the delisting-notice squeezes that carry the book.
- **What the other labels mean:** `metrics-leak` closes the oi_mcap lead from R282's table and labels it
  `metrics-leak`; `not-reproduced` closes it without attributing the cause.
- Read against `registry.program_trials()` in FINDINGS. One run; no second pick; no change of window or seed after
  seeing a statistic.

## Reported, not decided on
- Per book and window: dates, names, gross and net bp/day, NW t of gross and net, rank IC, turnover, 1x/2x/3x.
- The decomposition oi_mcap_v1 → oi_mcap_v2_on_v1 → oi_mcap_v2.
- R282's frozen direction (long low oi_mcap) net at 1x/2x/3x for the three oi_mcap books.
- **Other lanes** that read `data/daily/panel.parquet` metrics columns on a universe wider than the top 50: listed in
  FINDINGS from a grep of their PREREGs; **none is re-run here.**

## Known limits
- **Seen data, post-hoc direction:** the audited direction came from R282's table. A survival would not be evidence.
- **One draw of the presence control** (seed 383). Its random tie order moves the book's t a little; other seeds are
  not run.
- **The presence control is not a model of the 35-day rule;** it measures what presence alone earns on this universe.
- **2021:** Binance's metrics start in December 2021 for most coins; the 2021 rows are thin in both panels.
- **The engine ranks only rows with a finite factor and a finite forward return,** so oi_mcap_v1 ranks about 47
  names a day against v2's about 103 in the same universe. That is the point of the comparison, and the diagnostic
  oi_mcap_v2_on_v1 holds the rows fixed.
- **Latest-vintage Coin Metrics caps** (R282's "Not modelled") are in both panels and cancel in the comparison.

## Inputs (frozen)

```inputs
b44a28f0f009b00ce481adf66e6bb0b3fb93981a523fc1eaf4c47fad13ef27f6  data/daily/panel.parquet
09ff274763e1476cdbf178f87eb0fba0884fa314927dfa7fbdffbe52617105d1  data/daily_v2/panel.parquet
9e2600d87cfe58df534a5028678dee3cb0d800b3791879e511f539517d1cbffd  data/metrics_full/metrics_1h/manifest.json
55e45182aade91c169b5a58b94ea9c831a64bc7753828fd276b7c94ed26e8de6  docs/provenance/klines_1h.json
84a3aadbf5ac0439b99209714c85ab0484b775f1258701835a64029c1ec3e4de  docs/provenance/fundingRate.json
f3f756400347ed74864c6cd9d025c34f38d12eb6aa4ad7519c774ab3d3e08c25  experiments/pitfac_v1/PREREG.md
43f7e1ec684a4e7e2d072e9a929c11104cab91b6aed3a9a28963651937e1876d  experiments/pitfac_v1/spec.toml
deb00da8d4bb62d232091b237bb719c02ac34b1102029466daeebb4e0202539c  experiments/pitfac_v1/factors.parquet
b8ac5ade80d81af2cd95c7b5cc4d13f44f619e579bcb36d876f400b3cd74d5e8  experiments/pitfac_v1/results/report.json
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
e41bd2df1746e9e7db037ed7f7e8100f5b0ebd08872d3a6c1c8334a0157251ce  lab/runtime.py
4475f8962fb723e798383c839d6b0cc390c51b373937755a6d6ed2a62663cad6  lab/daily.py
7363ac7b8d3fea936931f42a5e9f879438a6247ffe57dbc8f4f317c65c8743cf  scripts/build_daily.py
7cce10ac02834e3de4727a51255e566923e449a19c12c4ebaec2777827a02427  scripts/build_daily_v2.py
bdf3dd3fb16afc060fed3c7acabb5998ce62e8856f5b48b11d300e9da3afa67a  scripts/pitfac_factors.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
0eda951060e2df881f6af9807b37ffaad658e8fc1d1b999b16282cea8dda4362  scripts/qx_run_verified.py
263880c55017a571775d42c4d87ad4cf0043a6ea28a8c6bc67e11fd6ecc4c959  scripts/run_presence.py
478c5f104adb24896a1dcfc7f0fde7e45cc6b0c382d6a381e5329b3d4bcaae0a  experiments/presence_v1/spec_all_1x.toml
eeb8b1f4f37fb612ec17bafc73fefbf1b1c03eac546ebc269998d87fcaea255e  experiments/presence_v1/spec_all_2x.toml
a1c30c21d5865ea650bec84acab7e2eddb3979786469ec984d1b6fa47cc2c101  experiments/presence_v1/spec_all_3x.toml
37a7ab9a4fb7faf75472e4ab53a35106dae762aa2a1cbbee9555607823370baa  experiments/presence_v1/spec_d_1x.toml
51b775698ad6a8b09cd9b2ce9e64a11cab94208a9a4be53c47a8622af69da175  experiments/presence_v1/spec_v_1x.toml
4f4ea1ae3047da42db6c248bee0aeb192ac2eb9fb0709cbfa43a96005fb3a146  engine/src/data.rs
47e4160e525fadc15dc5ec9d53c713a0d07e92397c9ddd07f779ad1896ddb58d  engine/src/events.rs
636eaef71ea28cedac413e728ba71470933b9f719a3ac40880b80a19ed65c31f  engine/src/factors.rs
2e523e2bd1d251096b10ee92bd9bca002a8afc1300aa8c0d3aa8281a5e107f45  engine/src/main.rs
02397aa28548fea14eaac24d311b0f658f74055eadab5cf6b3712375732d4ee6  engine/src/reserved.rs
3f49b5c545fdaf0c03185d15da8b6c0adc0fec417463e5f4e93b80d8f22414d5  engine/src/spread.rs
bbf7615e3fee7f523e5984f83cee841316f2fb77d465d2ea2afa42f3b0724c47  engine/src/stats.rs
af64b8d2d3aa9b9e179615432249a058b5669c2e4c79b9fe4bc9a2a64b3c8d2c  engine/Cargo.toml
9fc3e3a75a0275d0f3af29e1bfd901d358977e47fc9fe3413ef3318be791e11f  engine/Cargo.lock
34e3ddf699da9112942c06ab3f0d532a95b53dfd1cbe4cb3acead3e6c1853ff1  engine/target/release/qx
```

The runner (`scripts/run_presence.py`) calls `prereg.verify` first, checks every input above, verifies
`docs/provenance/klines_1h.json` and `docs/provenance/fundingRate.json` against their data folders before and after the
engine runs, builds the table, runs the five specs, and writes `results/summary.json`. The engine binary
`engine/target/release/qx` is hashed as it stands (built 2026-10-21, not rebuilt here); the reproduction check
against R282's report is its test.

## Outputs
- `results/summary.json`, `results/table.parquet`, `results/<run>/report.json` and `ic.csv` for the five runs, `run.log`.
- `FINDINGS.md`, with 1x/2x/3x costs, read against `registry.program_trials()`, "gate 0 on seen data" and what was
  not checked.
