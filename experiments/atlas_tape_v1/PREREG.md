# PREREG: atlas_tape_v1 (R386). One gate-0 screen of seconds-to-minutes conditional returns, at measured Lighter costs

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R386
- **Method:** parents M425 (Lighter quote lag) and M426 (minute-scale extremes); no new method id. A broad screen, not a rule.
- **Owner (single writer):** the Claude session that holds the R380-R389 block on issue #7 (lane agent for R386).
- **Date registered (UTC):** 2026-11-02
- **Code:** `scripts/run_atlas_tape.py`, tested by `tests/test_run_atlas_tape.py` (12 tests on invented data: the event
  kernel against a plain loop, thresholds, cluster t, tape loader, a planted signal and a null world, the grid count and
  the verify-first rule). The runner calls `verify()` on this file first and checks every input below by sha256.
  It imports R349's frozen `scripts/run_minflow.py` unchanged for the bar loader and the input check.

## Question
Over a closed grid of 303,520 cells (feature x gate x threshold x hold x coin set x side), priced at each coin's measured
Lighter $1k walk, which cells net a positive amount at 1x and 2x on validation days, pointing the same way in
discovery, and still stand after a max-statistic placebo over the whole grid? The answer is a ranked candidate list for
the reserved batch 2 (C17, on or after 2026-11-17). It is a screen. It claims no edge, and a candidate is only a name
to test on days nobody has read.

## Universe and data
- **Block A, minute bars.** Binance USD-M perpetual 1-minute klines for the 12 coins of the 1-second tape: BTC, ETH, SOL
  (`data/klines_1m`) and XRP, DOGE, BNB, SUI, ADA, LINK, AVAX, LTC, TRX (`data/klines_1m_tape`). Rows from
  2021-01-01 00:00 UTC to 2026-09-30 23:59 UTC, read by R349's `load_bars`, whose reader filter never loads a 2020 row. A
  bar with count 0 or a price <= 0 is NaN. SUI starts in 2023-05. 2020 stays reserved (`docs/GATES.md`).
- **Block B, 1-second tape.** `data/tape/{binance,lighter,mexc}/book` and `data/tape/binance/trades`, the seven sealed
  day files 2026-10-21, 10-22, 10-26, 10-27, 10-28, 10-29 and 10-30, the same 12 coins. Binance rows are dense. Lighter
  and MEXC write a row only when something changed, so their mid is carried forward at most 120 s (never across a
  recorder outage, which is any second with no Binance row) and their flow is 0 in a second with no row. Slots are
  laid out day after day, with a 2-hour NaN gap before a day that does not follow the previous calendar day.
- **Not read:** MEXC-only or Gate-only coins, any `reserved/` folder, 2020 rows, `data/hft`, `data/rawtape`, any day
  file after 2026-10-30, the current day's parts. No download, key or order.
- **Costs:** each coin's median $1k Lighter walk a side in bp, from R348's `walk_cost_bp` (checked by hash below):
  BTC 0.27, ETH 0.23, SOL 0.30, XRP 0.77, DOGE 1.95, BNB 0.81, SUI 2.00, ADA 2.72, LINK 1.65, AVAX 1.63, LTC 4.10,
  TRX 1.59. Lighter's fee is 0. Round trip = 2 x the walk.

## Feature lineage and point-in-time availability
All inputs are forward-captured or archive prints with no revision. Every feature at bar/second i uses only data up to
the close of i; the trade is entered afterwards. Quantile thresholds use only earlier time.

| Feature / formula | Parent fields | Venue, units | Window and close rule | Available by decision time? | Missing-value rule |
|---|---|---|---|---|---|
| A `ret_k` (k=1,3,5,15,30,60) | close | Binance perp, log return | last k bars to the close of bar i | yes, at the close of i | NaN if either end is NaN |
| A `flow_k` (k=1,3,5,15,30) | taker_buy_volume, volume | base units, d = 2*taker_buy - volume, summed | k bars to i | yes | NaN unless all k bars are valid |
| A `imb_k` (k=3,5,15,30) | same | sum d / sum volume | k bars to i | yes | NaN unless all k valid |
| A `div_k` (k=5,15,30) | flow, ret, volume | flow_k/(mean volume x sqrt k) minus ret_k/(mean abs 1-bar return x sqrt k); the means are the trailing 1,440 bars ending k bars earlier | to i | yes | NaN below half the trailing bars |
| A `rel_k` (k=1,3,5,15) | close of coin and leader | leader's ret_k minus the coin's ret_k; leader BTC, ETH for BTC | k bars to i | yes | NaN if either NaN |
| B `bret_k` (1,3,10,30,60 s), `lret_k` (3,10,30 s) | Binance, Lighter mid | log return of mid | k s to t | yes | NaN if either end NaN |
| B `bofi_k` (1,3,10,30), `lofi_k` (3,10,30), `mofi_k` (3,10) | `ofi` column of each venue's book | sum over k s | to t | yes | NaN unless every second is recorded; Lighter/MEXC 0 in a quiet second |
| B `bimb_k` (1,5,30) | bid_sz, ask_sz, Binance | mean of (bid_sz - ask_sz)/(bid_sz + ask_sz) | k s | yes | NaN unless all k recorded |
| B `btf_k` (3,10,30) | Binance trades | sum of buy_qty - sell_qty | k s | yes | 0 in a second with no trade while recorded |
| B `dev_bl`, `dev_ml`, `dev_bm` | mids | log(Binance/Lighter), log(MEXC/Lighter), log(Binance/MEXC) | instantaneous | yes | NaN if either mid NaN |

Input class: Binance archive klines are point-in-time archive prints; the tape is forward-captured. The 12 coins are the
tape's own list, fixed, so the grid is a venue-own-universe screen with the survivorship that implies (all 12 trade today).

## Rule or search space (closed; nothing is added after the freeze)
For each coin and base feature x, the **signal** is sign(x) and an **event** is |x| >= the q-quantile of |x| over the
7 days (A) or 2 hours (B) before the day (A) or 10-minute block (B) in which the bar falls, from at least 5,000 (A) or
3,600 (B) finite values; q in {0.90, 0.95, 0.98, 0.99, 0.995}. A **gate** keeps an event only if its condition holds.
- **Block A:** 22 bases (`ret` x6, `flow` x5, `imb` x4, `div` x3, `rel` x4) x 8 gates x 5 q x 7 holds x 14 coin sets x
  2 sides = **172,480** cells.
  - Gates: `none`; `hi_act` (volume of the last 5 bars >= 1.5 x the trailing 1,440-bar mean ending 5 bars earlier);
    `lo_act` (<= 1/1.5 of it); UTC clock windows of the signal bar's minute m: `asia` m<480, `eu` 480<=m<840, `us`
    840<=m<1260, `settle` (bars closing 15 min before to 5 min after 00:00, 08:00 and 16:00 UTC), `nyopen`
    (13:15-14:45 UTC).
  - Holds h in {1,3,5,10,15,30,60} minutes: entry at the open of bar i+1, exit at the close of bar i+h.
- **Block B:** 26 bases x 3 gates (`none`, `hi_act`, `lo_act` by Binance updates per second: last 60 s >= 1.5 x or <= 1/1.5
  of the trailing 1,800 s mean ending 60 s earlier) x 5 q x 12 holds x 14 coin sets x 2 sides = **131,040** cells.
  - Holds: entry delay d in {1, 3} s after the signal second, hold H in {5, 15, 30, 60, 180, 300} s, on **Lighter's mid**
    (entry at t+d, exit at t+d+H).
- **Coin sets:** each of the 12 coins, `all12` (trade-weighted over the 12 coins' trades) and `maj3` (BTC, ETH, SOL).
- **Sides:** `follow` (trade sign(x)) and `fade` (trade -sign(x)). Both are cells.
- **Trade rule:** one position per coin and cell. After a trade the next signal must come at the exit bar or later; an
  event with a missing price is skipped and blocks nothing; a trade must exit inside its period.
- **Net per trade:** side x (exit/entry - 1) - m x 2c, with c the coin's walk and m the cost multiple 1, 2, 3. No
  funding (holds <= 60 minutes) and no tick adjustment: the walk already contains the half spread.
- **Total trials: 303,520** (every cell, tested or not).

## Splits and cost
- **A:** discovery 2021-01-01..2023-12-31 (1,095 days), validation 2024-01-01..2026-09-30 (1,004 days). Thresholds for
  the first validation days use the preceding discovery days (earlier time only). No trade crosses the split.
- **B:** discovery the five days 2026-10-21, 10-22, 10-26, 10-27, 10-28; validation the two days 2026-10-29 and 10-30.
  Whole days only. Recorded seconds are limited (about 235,000 per coin in total, about 140,000 of them in validation).
- **Cost:** the coin's measured Lighter walk at 1x, with 2x and 3x in every table. MEXC web (3 bp a side) and MEXC API
  (8.5 bp a side) are reported columns, never decisions.
- Splits are this lane's own (the lab's `config.py` day split is for daily lanes); both end before any reserved sample.

## Statistics
For a cell and a period, trades are grouped into clusters (UTC days in A; 30-minute blocks in B). The mean net per trade is
the sum of nets over the sum of trade counts; the **t** is the cluster-robust t of that ratio mean (residuals
`R_c - mean * N_c` per cluster, a c/(c-1) factor, c = clusters with a trade). A cell is **eligible** if each period has
at least 100 trades and at least 10 clusters with a trade. Ineligible cells are still trials but carry no statistic.

## Pass rule (the only rule that puts a cell on the candidate list)
A cell is a **candidate** if all five hold:
1. eligible;
2. the mean net at 1x in discovery is > 0 (it points the same way);
3. validation net 1x t >= 2.0;
4. validation net 2x mean > 0;
5. its **family-wise p over the full grid <= 0.05**: the share of placebo replicas (with +1) whose largest centred
   validation t over all eligible cells and both sides is >= the cell's validation net 1x t.

Candidates are ranked by validation net 1x t. Nothing else enters the list.
- **PARTIAL** if at least one candidate exists (gate 0 on seen data), recorded with trials 303,520.
- **NULL** otherwise. The best cells are still tabulated, as a table of what the screen saw, never as candidates.
- Never CONFIRMED. A screen cannot confirm.

## Null (placebo, the lab's full-pipeline shifted-signal style)
- For each of **300 replicas** (seed 386 for A, 387 for B) the validation signals (the events and their sides) are moved by
  a common circular shift against the validation returns: a whole number of days between 14 and the validation length
  minus 14 in A (so clock gates keep their time of day), a number of seconds between 3,600 and the length minus 3,600
  in B. One shift is used for all coins, bases and gates of a replica, which keeps their cross-dependence. The whole
  grid is rerun.
- The replica's cell statistic is the **centred** t (cost 0), which is the t of a cell whose true gross equals its
  cost: the least-favourable break-even null for "net > 0". Its max over eligible cells and both sides is the replica's
  maximum. A and B maxima are joined (max of the two) for the family-wise p; A-only, B-only and discovery-selected
  p-values are also written and are reported, not decisive.
- **Chance count:** in each replica the number of cells that are discovery-eligible (point the same way), have centred
  t >= 2, and whose placebo gross exceeds the round-trip cost (the 2x analogue). `lab.nulls.search_verdict` compares
  the real count of cells meeting rules 1-4 with the 95th percentile of these counts: SIGNAL or NOISE. It is reported,
  not decisive.

## Multiplicity
- **This lane: 303,520 trials** (172,480 in A and 131,040 in B), registry row R386 once, after the run.
- **Program trials before this lane: 9,479,320** (`registry.program_trials`), 9,782,840 after. The raw sum is bookkeeping,
  not an effective count. The cells are heavily correlated (nested thresholds, overlapping windows, shared signals), which
  is why the placebo max over the whole grid, and not Bonferroni, is the correction.
- Both sides, all gates and every unrun or ineligible cell are in the 303,520. The screen is one decision family and is
  read once.

## Evidence lineage and admission
- **Canonical method ids:** M425, M426.
- **Parents and previous inspected outputs:** R347/R348 (`tapelag_lighter`, 6 rules on tape days 10-21, 10-22, 10-26; walk
  costs), R349 (57 rules on BTC, ETH, SOL minute bars, picked flow fade k5 h5, PARTIAL), R351 (that pick on the nine alts, NULL).
  This lane re-reads those minute bars, so the **time dimension is seen** for those 12 coins; the grid itself (22 bases x 8
  gates x 5 q x 7 holds, 14 coin sets, minutes) was never run, and none of its statistics has been read.
- **Tape days 2026-10-27..10-30:** no earlier lane read a statistic on them. R347's sealed-day confirmation lane was
  conditional on a PASS or PARTIAL and R348 was NULL, so it is not earned and does not hold them.
- **Decision group:** this screen decides only which cells go to reserved batch 2 and the forward tape; it feeds one list.
- **Proposed fresh sample:** reserved batch 2 (C17) on or after 2026-11-17 and the tape days recorded after 2026-10-30.
  Exact overlap with this lane: none. This lane reads no reserved folder.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`. Requirements this
  lane meets: preregistered finite grid, frozen runner, placebo family-wise control, 1x/2x/3x costs, trials read against
  the program. **Unmet, left to the batch that tests a candidate:** the strict on-time clock for tape latency, 10-day trimming,
  leave-two-coins-out, an 80%-power calculation for that batch, and cross-family control beyond this grid. The result stays
  exploratory.
- **For a reserved batch:** the finite candidate list is `results/candidates.csv`. Prior-batch information used: none. Any
  later batch must re-register its own error control across adaptive batches; within-batch Bonferroni alone is not enough.

## Resource limits and run
Run once with `nice -n 10 python scripts/run_atlas_tape.py --run --workers 3 --placebos 300`, at most 3 worker processes,
under 8 GB of memory, writing only to `experiments/atlas_tape_v1/results/` (about 20 MB). The run stops if free disk is
under 2 GB. No recorder or forward process is touched. `run.log` carries progress and the final line only.

## Outputs
`experiments/atlas_tape_v1/results/`: `grid.csv.gz` (all 303,520 cells with discovery and validation figures, p-values and flags),
`candidates.csv`, `top200_by_val_t.csv`, `placebo.csv` (the replicas' maxima and counts), `summary.json`. FINDINGS.md is
written after the run, with a 1x/2x/3x table of the top cells, the trial count read against the program, passes against
the chance count, and a list of what was not checked.

## Known limits (written before the result)
- Block A prices are Binance prints, not Lighter's quotes; the cost is Lighter's October 2026 book applied to 2021-2026 (as R349/R351).
- Entry at the open of the bar after the signal assumes the order reaches the book within the same second; this box's
  websocket round trip is about 233-255 ms and Lighter's zero-fee takers wait 300 ms. Block B's shortest entry (1 s) is
  the earliest that is even close to executable; no rule shorter than that is tested.
- Queue position, partial fills, capacity beyond the $1k walk, funding on holds, and live adverse selection are not modelled.
- Block B has two validation days; its p-values rest on about 80 half-hour clusters. It can screen but not confirm.
- The placebo shifts signals against returns, so it breaks signal-return links but keeps volatility clustering of each side
  separately; it calibrates the max of this grid, not a causal claim.

## Stop rules
- The lane ends when the run finishes or crashes. After a crash that printed no statistic, the same PREREG may be rerun
  once unchanged; a crash after a statistic was printed is recorded and the fix is a new lane.
- Not allowed after seeing results: new features, thresholds, holds, gates, coin sets, splits, costs or a different
  pass rule. A cell outside the candidate list is not promoted by any later argument.
- No money, orders, keys or downloads. Real money needs paper to show a net gain, `lab.gate.go_real()` and the owner.

## Inputs (sha256, path)
```inputs
9e2c7fd717811a58bca2fa5816b92b4bf59aaa5d9706c10af2522af04a1c82a0  data/klines_1m/BTCUSDT.parquet
7c7c05b387d59fd3e40555718c28388fb66c737602102297a34de9af9c67da70  data/klines_1m/ETHUSDT.parquet
966602440c3573e677b7578feed150b5065d2062d84869acd54e79ad58af1706  data/klines_1m/SOLUSDT.parquet
f575a7c9632c84df2860c20c2de5d37b52e21a4961b518284c1962a670accae6  data/klines_1m/manifest.json
8bd9a1236948344161bc651a6c6eb08d0af7b3f3703556a2a7d770b63d152e73  docs/provenance/klines_1m.json
c7c45ead41d71f36ba6df5b023d2c197e5c723bdc171fdc97ce1b843896f6337  data/klines_1m_tape/XRPUSDT.parquet
a11b79f5334757108c299336637248dba41dcb7ad16fb487e0899e6370b6aa15  data/klines_1m_tape/DOGEUSDT.parquet
40898910305c12f524c541e1413da04838939e1a5f585b35f461f1fb6da90d5f  data/klines_1m_tape/BNBUSDT.parquet
c7dcdf637f207945b7fdb717519007bd8afea0c09ab60d77c52dfed712c5562f  data/klines_1m_tape/SUIUSDT.parquet
ba174cae3cbd17a9f80a7a255e214541aed6611c5acae7bcd7cbb28c96e6e1bb  data/klines_1m_tape/ADAUSDT.parquet
5c3db56d32b8693fcc765371056039a64437032cfc52a768e13e39826d39666f  data/klines_1m_tape/LINKUSDT.parquet
d74f57c781c3c73078c1bbbdca6fa11d96d011508bb29b454efb21eecfdc667d  data/klines_1m_tape/AVAXUSDT.parquet
2590251cb7f8de210e36643af3713465027b15b57e6730766c4ad52092d4cc4a  data/klines_1m_tape/LTCUSDT.parquet
9ce27636c171ca4d32870f537bbf66ed9988c4cd21380d1c20554fa4a43fe3ee  data/klines_1m_tape/TRXUSDT.parquet
8438a5e31d85a31de85ea9b9c94f2ab3da2b8a564a84dfcedb5423fda8a9f02c  data/klines_1m_tape/manifest.json
68af544678c79567bbf6aab79ef18e5b65855debb00afc91e382bddf63a01d06  docs/provenance/klines_1m_tape.json
fdc1d02f1671d793a7263ee33e7b881017e4c13d16277737929da509329108f1  data/tape/binance/book/2026-10-21.parquet
a4b8839a433135b917992a4f111f7a3c32fc21df188f6812fd9f3542f0735669  data/tape/lighter/book/2026-10-21.parquet
12a0855531b225750160e61c350cc87085a78d4e2d52ed082b4a18c7812dbdd0  data/tape/mexc/book/2026-10-21.parquet
cb85306c6e7fd640eefaefad9441102cebc6db6f1f2459b4b283aa9aa9fc42bc  data/tape/binance/trades/2026-10-21.parquet
f41acb94963194aeb677d7ac21fb15632835ad4abb0b6e1ca2dac7812010b597  data/tape/binance/book/2026-10-22.parquet
4e29666cb43a90300c5204706f944fbfaef2c1b54248bd1996e33aa83925a21e  data/tape/lighter/book/2026-10-22.parquet
c34ecc3a2aca547d543c73c55f1447303230c831ee9c089a6b4f74545ce59717  data/tape/mexc/book/2026-10-22.parquet
90d66dce8c472b92fdc5c5b0e1c6a3b96e681569708541eadc697f8ed32cbfa3  data/tape/binance/trades/2026-10-22.parquet
d33ab971f501a41c282ae67bb5fe8d8f222d1437a54ee3e02ca854633c0b21fa  data/tape/binance/book/2026-10-26.parquet
8397f29667c394bde732afea7b70f523bb72462f3c998ce9f3992594ca95874b  data/tape/lighter/book/2026-10-26.parquet
165ecc944ecb198cc0912090f765f128b2efb45c37675a2b68e74b17d057680f  data/tape/mexc/book/2026-10-26.parquet
dec9b973e046ea6d0fa6a8c1ac115c2abfd2a32075eb46976c15a9928a9da1e9  data/tape/binance/trades/2026-10-26.parquet
957c789fbcc8cb919b18d16023909ae989ba465510a66c574f8edf7b351648dc  data/tape/binance/book/2026-10-27.parquet
634c4b273f8f4a3aab10c7cf1a885cb1a43931cdb86f597f50af03dbac022815  data/tape/lighter/book/2026-10-27.parquet
62e61a92e8f4968f2be8265c3036329120684eb8f7a7d7af89b47ac8dbc0e5ee  data/tape/mexc/book/2026-10-27.parquet
afbca5a0103bab863dfac496a8a393e5d5c0c7ad540d2776b06abc116af5532d  data/tape/binance/trades/2026-10-27.parquet
2740953bd7f09ad15160a6558077f6afc5fa13d166c31ef62015ebab614c0cb0  data/tape/binance/book/2026-10-28.parquet
48ac897a110a599481f8644bb42a435563b6aaa6be4a2a33e9f86cada677863e  data/tape/lighter/book/2026-10-28.parquet
c37da01ba05120328b5757493540ecd0f398cd37ea6b810861b2ba1838c9125b  data/tape/mexc/book/2026-10-28.parquet
5d71fa9731078085c333a0b06203a3c7bbffe948c440d28633248c1ba578c338  data/tape/binance/trades/2026-10-28.parquet
ae99f183a9972c48b65689dee56c50ff0f99273addc65453cf692c4e3e35f7da  data/tape/binance/book/2026-10-29.parquet
cae5c74d5a82ac38db316fd701b500f7344c898d46962206f47664b2c5eb6f90  data/tape/lighter/book/2026-10-29.parquet
eff1cc4a359ea76f7ba1c0a119ae2f68122b9745003a7ad94c00c53883a38d12  data/tape/mexc/book/2026-10-29.parquet
85c6fa4b3ac6f4edbebfabb1387338dcbfe5f6304be08cd2ba80599db43dd091  data/tape/binance/trades/2026-10-29.parquet
9844a7c63ee5cf9dd53a2b2542154fd5869f1e1e5720073acc3dc424c6624869  data/tape/binance/book/2026-10-30.parquet
cb2116e05391a40d0c89a75e95c31bb6379e236d49b3273761fa83b9d4f8173a  data/tape/lighter/book/2026-10-30.parquet
3cdc14044be4dfa6aab5baa353b1ef8e166f4cfec56f41e234520d01fc5d905a  data/tape/mexc/book/2026-10-30.parquet
efb097cd2b95af3819e5133e9b795289d34aa55ba87fe6cf72b88bff15c64da6  data/tape/binance/trades/2026-10-30.parquet
4f4690ff82f4f3c9dc458db8e29fc0a3eb0733a5ced0e8dd613b083de85ca778  experiments/tapelag_lighter_v2/results/summary.json
e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926  docs/GATES.md
692b7223b4d50353f4f88cd3f6f5652a6f87e8fffa4cbfb4351e3c09003e26f1  scripts/run_minflow.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
871ba5a956064e5ae336323654ec6269e92b3f015a44ab295b3d6e3be957e358  lab/nulls.py
bcfb9b3376e8f7be62940288a8d358f72597a2b95bbde84f76d409b00f4b8e59  lab/config.py
ef8bef6d3bf509325c2e9a2478fd3271492e54b0fe91cd627ca20879afbefaef  scripts/run_atlas_tape.py
b7aa545fd21bff25e432056376012fd69cf9cc52bdf3d44944283ed6a1a0561c  tests/test_run_atlas_tape.py
```
