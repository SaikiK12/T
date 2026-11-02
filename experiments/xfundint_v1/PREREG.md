# PREREG: xfundint_v1 (R384). Is R277's KuCoin carry an artifact of settlement intervals?

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a changed idea is a new lane.

- **Registry id:** R384
- **Owner (single writer):** Claude lane worker (this lane's folder, `scripts/run_xfundint.py`, `tests/test_xfundint.py`)
- **Date registered (UTC):** 2026-11-02
- **Gate:** 0 on seen data. An audit of saved archive data and a frozen engine; it is not new evidence and not prospective.
- **Method:** M059 (cross-venue funding carry), settlement-interval audit of R277 (R275 -> R277 KuCoin sets).

## Question
Does R277's KuCoin net funding depend on contracts whose settlement interval (1h, 4h) made the per-settlement rate
up to 8x or 2x too large before KuCoin began scaling funding by interval (2026-07-14/24), or does the book still
earn a positive net, with a Newey-West t of at least 2.0, after the scaling?

## What the author has seen
- **R277 in full** (`experiments/xfund_kd_v1/FINDINGS.md`, its saved `daily.csv` and `trades.csv`) and the post-hoc
  split in `docs/LEADS.md`: KuCoin sets net about +10%/yr at 1x over the 69 days from 2026-07-25, and the median KuCoin
  4h per-settlement rate fell to 5e-5 in July. Those numbers are not the decision here: this lane's cells are computed
  from the replay.
- **`data/kucoin_hist/contracts.csv`:** 692 contracts, `funding_ms` 3.6e6 (1), 1.44e7 (431), 2.88e7 (260); of the 642
  in R277's symbol table, 1 is 1h, 396 are 4h and 245 are 8h. This is the interval as of 2026-10-20, not its history.
- **Development of the run script** on the prefix window 2021-01-01..2021-06-30 only: whether the replay matches
  R277's first 159 daily rows (it does, to 5e-11), that the class sums equal the replay's totals, and the cell count.
  No class share, net or t-value of any cell was printed or read. The unit test uses synthetic data.
- **Not seen:** any class split, any pre/post split, any NW t, any 8h-only replay.

## Inputs (frozen)

```inputs
d399c923455e43893e4a503db8e67bb79e3f35812c2b5c110b182f97634d38e9  experiments/xfund_kd_v1/PREREG.md
03abb3bf671c018c38b641ebe3c7ccefa573e087a69212fb07fa491e0e584056  experiments/xfund_kd_v1/spec.toml
15c8054f7e10f921bd9a797fbf2b9ac927c99fdfbc2388a54199be0cace6fb3b  experiments/xfund_kd_v1/symbols.csv
0ab7db847cb9e0e51c93d59ad205a64888664a067fb8255a4093494c48d6b7ab  experiments/xfund_kd_v1/results/daily.csv
ffdd939197d8570bc6f5ed6425a6739dfa266a7565b51528a9b4118ddd4d7aa0  experiments/xfund_kd_v1/results/trades.csv
40305369e6d881fcc5c66a2964b57048aa1d12d63fbe5861fc3ffc14d13e2695  data/kucoin_hist/contracts.csv
715344696e69c0c3c1b426dfd991a5bab774c00fc87592765139c5619c829d6e  data/kucoin_hist/manifest.json
bc5abe62d763042bd2e01fe88f7b5bf367bdda263200c1cec67486fed19a4b13  docs/provenance/kucoin_hist.json
e496f80737a33ccffd3be5fb2d119310d91930021f7477338e124290950563c0  docs/provenance/gate_hist.json
84a3aadbf5ac0439b99209714c85ab0484b775f1258701835a64029c1ec3e4de  docs/provenance/fundingRate.json
55e45182aade91c169b5a58b94ea9c831a64bc7753828fd276b7c94ed26e8de6  docs/provenance/klines_1h.json
d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d  lab/xfund.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
21855489cb81e0f885c351d54787c3ac054953caf2e44d6be3cdda7f990bf147  scripts/xfund_parity.py
ba6baabd47fb2c135e7613f9b049d70baa8a89e2ea65ee185cc95658bfbc46a2  scripts/run_xfundint.py
```

- **Engine:** `lab/xfund.py`, the Python twin of `qx spread`, unedited. Its hash is the same as in R279's `FIXED`.
- **Data:** the files the replay reads (Binance `klines_1h` and `fundingRate`; Gate `candlesticks_1h` and
  `funding_applies`; KuCoin `candles_1d` and `funding`; 4,750 files for the R277 symbol table) are hashed against
  `docs/provenance/<folder>.json` by the run script before loading. Those four provenance files are in the block above.
- **No other data:** no 2020 row, no reserved folder, no MEXC, dYdX or Lighter file, no download.

## Method
- **Replay:** `lab.xfund.replay` over R277's universe (`symbols.csv`) and spec (start 2021-01-01, end 2026-09-30,
  daily axis, identity guard 0.9 / 30 d / 20 obs, costs 7 / 14 / 21 bp per leg per side), for the two books
  `gate+kucoin L14d th5% K20` and `binance+kucoin L14d th5% K20`.
- **Parity gate (BLOCKED.md if it fails):** per book, the replay's trade list (coin, long venue, entry, exit) must equal
  R277's `trades.csv`, and its daily net at 1x, 2x and 3x and its date labels must equal `daily.csv` (max |diff| < 1e-9,
  the precision of the saved file). On failure the run writes `BLOCKED.md` and reports no statistic.
- **Attribution:** the run script repeats the replay loop with each open position's gross (price plus funding), funding
  and leg count booked to the **interval class of its KuCoin contract** (1h, 4h, 8h) from `contracts.csv` `funding_ms`.
  Class sums must equal the replay's totals (gross, funding, legs, held) within 1e-12, else BLOCKED. Class net on capital
  is `(gross_c - cost * legs_c) / (2K)` with K = 20, so the classes add up to the book. Annualised net is
  `mean(daily net) * 365 * 100` (%/yr on capital) over all days of the period, days with no position counting as zero.
- **Other leg:** each position's non-KuCoin leg funding is booked to that leg's **day class**, implied by the number of
  settlements in its recorded funding file that day (at most 3: 8h; 4 to 8: 4h; more: 1h). There is no contracts file
  for Binance or Gate. The KuCoin leg's day class is also compared with the static class (one cell).
- **Periods** (by the daily row's date label; funding settled in (label - 1 day, label] is booked under the label):
  - KuCoin: `pre` = labels up to 2026-07-14; `trans` = 2026-07-15..2026-07-24; `post` = labels from 2026-07-25.
  - Binance (legs of binance+kucoin only): `pre` = labels up to 2025-09-18; `post` = labels from 2025-09-19.
  - Years: calendar years 2021..2026 (to the last row, 2026-10-01); partial years annualised by their mean.
- **8h-only replay (reported, not decided on):** the same book on the universe without the KuCoin series of 1h and 4h
  contracts removed, costs as above. Its trades are not compared with R277's (a different book).

## The cells (56 trials)
A cell is one (set, table, period, class); its 1x / 2x / 3x versions count once, as in R277. Per set (2 sets):

| Table | Cells | Content |
|---|---|---|
| year | 6 | full-book net 1x/2x/3x %/yr and NW t (1x), 2021..2026 |
| period_kc | 3 | full-book net 1x/2x/3x, NW t, days: pre, trans, post |
| class_kc | 6 | KuCoin class 1h, 4h, 8h x pre, post: share of the period's net funding, net 1x/2x/3x |
| otherleg_kc | 6 | other leg's day class x pre, post: share of the period's net funding |
| implied_vs_static | 1 | share of KuCoin-leg position-days whose day class differs from the static class |
| only8h_replay | 2 | 8h-only replay: all days, post: net 1x/2x/3x, NW t |

binance+kucoin adds 8 cells: `period_bn` (2: full-book net pre/post 2025-09-18) and `class_bn` (6: Binance-leg day class
x pre, post: share of net funding). Total 2 x 24 + 8 = 56. Share of a class = the class's funding summed over the
period divided by the book's funding summed over the period.

## Decision (fixed before any statistic)
Per set, with `post` = KuCoin post-scaling days:
- **A** = the 1h and 4h KuCoin classes' share of the book's net funding in `pre` is greater than 0.5.
- **B** = the 8h-class net 1x in `post` (%/yr on capital) is <= 0.
- **C** = the full-book net 1x in `post` is > 0 and its Newey-West t (lag 10, `lab.stats.newey_west_t`) is >= 2.0.
- **Set label:** `robust` if C; else `interval-artifact` if A and B; else `inconclusive`. If C holds together with A and
  B, the label is `robust`: the post-scaling days are a clean test, and A and B are reported as a pre-scaling caveat.
- **Lead label:** the common label if both sets agree, else `inconclusive`. The number of `post` days is reported; with
  about 69 days a t of 2.0 is a weak bar (10-lag NW over 69 observations), so `inconclusive` is a likely outcome.
- **Registry verdict:** PARTIAL if `robust`, NULL if `interval-artifact`, PARTIAL with the label in the notes if
  `inconclusive`. This is an audit: no lane or forward book changes on its result.

## Reported, not decided on
All other cells; per-trade attribution (`positions.csv`); funding recomputed per position against R277's `trades.csv`
(max |diff| of funding and price PnL); cost sensitivity 1x / 2x / 3x everywhere.

## Cannot be checked from public data
- **Whether recorded rates equal paid rates:** KuCoin's history endpoint gives the published funding rate per
  settlement, not the amount charged to an account. Pre-scaling rate factors per contract and date are not published,
  so the replay uses the recorded rate as paid.
- **The interval history of a contract:** `contracts.csv` holds the interval on 2026-10-20 only. A contract that
  changed interval earlier is caught only by the one `implied_vs_static` cell.
- **Contracts KuCoin delisted** are missing from the universe (R277's known survivorship limit).
- **Capacity, fills, transfers and liquidation** are not modelled, as in R277.

## Multiplicity
- Trials: 56 (counted above).
- Program trials before this lane: 9,479,264 (`registry.program_trials()` on 2026-11-02).
- A reading against that count: this lane tests no new return source; its cells decide a label for a known lead.
