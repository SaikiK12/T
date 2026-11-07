# PREREG: minflow_alts_v1 (R351). R349's frozen pick, unchanged, on nine more coins whose 1-minute bars no lane has read

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R351
- **Method:** M426 (minute-scale extremes on a zero-fee venue). No new rule: R349's selected rule is replayed as frozen.
- **Owner (single writer):** the Claude session that froze it. R351 is claimed on issue #7 (comment 6445173824) before
  the freeze.
- **Date registered (UTC):** 2026-10-27
- **Code:** `scripts/run_minflow_alts.py`, tested by `tests/test_minflow_alts.py` (9 tests on invented bars and
  trades). It imports R349's frozen runner `scripts/run_minflow.py` unchanged for the bars, ticks, funding, signal and
  trade code. The runner calls `verify()` on this file first and checks every input's sha256 against the block below.
- **Gate:** 1 in the coin dimension, 0 in time. No lane has read these coins' 1-minute bars. Their hourly and daily
  prices, and their funding, were read by many lanes. The rule was chosen on BTC, ETH and SOL over the same years.
- **Execution mode:** Lighter Standard API (no fee, 300 ms taker delay), about 2.5 trades a day per coin. MEXC web and
  the MEXC/Binance API are reported, not decided on.

## Why this lane
- **R349 passed its frozen rule** (gate 0, recorded PARTIAL). Its pick fades the most extreme 5 minutes of signed
  taker flow on BTC, ETH and SOL for 5 minutes. It nets +2.69 bp a trade at Lighter's book cost in 2024-01..2026-09
  (t 3.48), but only +0.59 since 2025-07.
- **Two open questions:**
  - Is the reversal general, or a property of three coins chosen after the fact?
  - Does it still pay anywhere now? Thinner coins may keep an edge that BTC, ETH and SOL have lost.
- **Speed:** the forward lane needs about 4,000 trades to confirm +2.7 bp a trade (about 500 days on three coins).
  These nine coins hold about 48,000 trades of history that no lane has read.

## What the author has seen
- **R349 in full:** its 57 rules on BTC, ETH and SOL, every window, year, coin and side, and its decay since
  2025-07 (`experiments/minflow_v1/FINDINGS.md`).
- **R348:** Lighter's measured $1k book walk per coin (the costs below), and that Lighter's quote catches Binance's
  within a second.
- **These coins' hourly and daily bars and funding,** through many lanes (R185, R219, R275 and others).
- **The new files** (`data/klines_1m_tape`, fetched 2026-10-27 with `scripts/fetch_klines_stream.py`): row counts,
  first and last bars, sizes and archive digests.
- **Plumbing before the freeze** (2026-10-27; counts and ticks only, no return after any signal computed; trades
  counted with `run_minflow.take`, which returns indices only):

  | Coin | Bars | Signals | Trades a day, 2021-04..2026-09 | Since 2025-07 | Tick, median bp (all / since 2025-07) |
  |---|---|---|---|---|---|
  | BNB | 3,022,287 | 17,358 | 2.62 | 2.56 | 0.17 / 0.14 |
  | XRP | 3,015,088 | 17,755 | 2.73 | 2.75 | 1.49 / 0.66 |
  | TRX | 3,015,063 | 17,804 | 2.60 | 2.40 | 0.92 / 0.31 |
  | AVAX | 3,022,273 | 17,613 | 2.74 | 2.51 | 0.48 / 0.98 |
  | LINK | 3,022,285 | 17,354 | 2.70 | 2.56 | 0.74 / 0.84 |
  | DOGE | 3,022,277 | 18,812 | 2.89 | 2.54 | 0.81 / 0.92 |
  | SUI (from 2023-05) | 1,794,565 | 10,291 | 1.64 | 2.47 | 0.87 / 0.89 |
  | ADA | 3,022,288 | 17,303 | 2.67 | 2.53 | 2.01 / 3.55 |
  | LTC | 3,015,085 | 17,769 | 2.67 | 2.61 | 1.18 / 1.70 |

  The signals take about 130 s for the nine coins.
- **Parity check before the freeze:** this lane's code path, run on R349's own BTC, ETH and SOL files, reproduces
  R349's 5,443, 5,431 and 5,835 j* trades exactly (bar indices, sides, times and both prices).
- **Not computed in this lab:** any return after a signal on these nine coins' 1-minute bars.

## Inputs (frozen)

```inputs
40898910305c12f524c541e1413da04838939e1a5f585b35f461f1fb6da90d5f  data/klines_1m_tape/BNBUSDT.parquet
c7c45ead41d71f36ba6df5b023d2c197e5c723bdc171fdc97ce1b843896f6337  data/klines_1m_tape/XRPUSDT.parquet
9ce27636c171ca4d32870f537bbf66ed9988c4cd21380d1c20554fa4a43fe3ee  data/klines_1m_tape/TRXUSDT.parquet
d74f57c781c3c73078c1bbbdca6fa11d96d011508bb29b454efb21eecfdc667d  data/klines_1m_tape/AVAXUSDT.parquet
5c3db56d32b8693fcc765371056039a64437032cfc52a768e13e39826d39666f  data/klines_1m_tape/LINKUSDT.parquet
a11b79f5334757108c299336637248dba41dcb7ad16fb487e0899e6370b6aa15  data/klines_1m_tape/DOGEUSDT.parquet
c7dcdf637f207945b7fdb717519007bd8afea0c09ab60d77c52dfed712c5562f  data/klines_1m_tape/SUIUSDT.parquet
ba174cae3cbd17a9f80a7a255e214541aed6611c5acae7bcd7cbb28c96e6e1bb  data/klines_1m_tape/ADAUSDT.parquet
2590251cb7f8de210e36643af3713465027b15b57e6730766c4ad52092d4cc4a  data/klines_1m_tape/LTCUSDT.parquet
8438a5e31d85a31de85ea9b9c94f2ab3da2b8a564a84dfcedb5423fda8a9f02c  data/klines_1m_tape/manifest.json
64ed0b13086a8c8aed00607c268d3699afc75e709f3c3ea1feafd0832f83d4a7  data/fundingRate/BNBUSDT.parquet
8e7a20419d92be9ea66ca6327c94d5845f5768d59bc9f91f755d88c703637e3d  data/fundingRate/XRPUSDT.parquet
b6da5ba1a2dfd1ba8dc1d8857d56ac90e658d2d1040f4f3363ee404f92c2541f  data/fundingRate/TRXUSDT.parquet
1a202e0fced90bd6346beb94decc05a1638b50de80b813d3f88f47bac605e544  data/fundingRate/AVAXUSDT.parquet
ceec65d7cdbcfbe07f6900a62707ae687da80e65e1bbacd87f564e334eb07ef8  data/fundingRate/LINKUSDT.parquet
c360e679952aee2bf9ed1204452976876f00746e34e8e85de88814dafcfdf84f  data/fundingRate/DOGEUSDT.parquet
d2243590982286ef3cc96b51b75bd5bfc1c90fa117c2883371dd5b2c6be8d273  data/fundingRate/SUIUSDT.parquet
4d26df117d4f3e0cc3e23068622c08419be4ee3c8cd9467906704cf894252262  data/fundingRate/ADAUSDT.parquet
b84571f04fb3978f04e39bcf00689f7799fcb64a17ccc8302c70bd0d9f547cd7  data/fundingRate/LTCUSDT.parquet
68af544678c79567bbf6aab79ef18e5b65855debb00afc91e382bddf63a01d06  docs/provenance/klines_1m_tape.json
84a3aadbf5ac0439b99209714c85ab0484b775f1258701835a64029c1ec3e4de  docs/provenance/fundingRate.json
4f4690ff82f4f3c9dc458db8e29fc0a3eb0733a5ced0e8dd613b083de85ca778  experiments/tapelag_lighter_v2/results/summary.json
0c75a8c43c78440675dcbacfa6bf171ca6f82ac89a4d9d556cc51f2f21950a14  experiments/minflow_v1/PREREG.md
899a1771a67e737841c682ecfc4012a5276907b8ff8a4fe0b0519e2375aac814  experiments/minflow_v1/results/summary.json
692b7223b4d50353f4f88cd3f6f5652a6f87e8fffa4cbfb4351e3c09003e26f1  scripts/run_minflow.py
170d8603382af9bbe09d25d0b6575e50bc871db0ee1588be90a493719eee59a3  scripts/run_minflow_alts.py
2a029fe2e279930783ff793ade10bf09099b41eb0484dae8143724161a5e96c9  tests/test_minflow_alts.py
835dbb86fcb3a6752db9cacc51eedf3113e54a49da83dff77ff3888c1f8b553b  scripts/fetch_klines_stream.py
f61e0d053e4f37d4286f8a3a59516f799aa191cb88bb7f3c96715ddba966220c  tests/test_fetch_klines_stream.py
097ec5cd95aecea45497c68319d11a4ff2508c980a83c373b5afb4c61e90da13  lab/orderflow.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
```

## Data
- **Coins:** BNBUSDT, XRPUSDT, TRXUSDT, AVAXUSDT, LINKUSDT, DOGEUSDT, SUIUSDT, ADAUSDT and LTCUSDT, Binance USD-M
  perpetuals: the 1-s tape's coins other than BTC, ETH and SOL.
- **Bars:** `data/klines_1m_tape/<SYMBOL>.parquet`. Open times run from 2021-01-01 00:00 UTC to 2026-09-30 23:59 UTC
  (SUI from its listing in 2023-05).
  - They were built from the public monthly archives, each checked against its published SHA-256.
  - 2020 was never fetched; it stays reserved (`docs/GATES.md`).
  - Read by R349's `load_bars`: a full minute grid; a bar with count 0, close ≤ 0 or open ≤ 0 is NaN.
- **Funding:** `data/fundingRate/<SYMBOL>.parquet`, as R349.
- **Tick:** R349's `month_ticks`: per coin and calendar month, the smallest positive gap between two distinct printed
  prices, to 6 significant digits.

## The rule (R349's j*, `flow_fade_k5_h5`, unchanged)
- **Signal:** S(i) = the sum of d = 2·(taker buy volume) − volume over bars i−4..i, with all five bars valid.
- **Threshold:** the hour's threshold is the 99.5th percentile of |S| over the previous 168 hours, from at least
  7,200 finite values. Bars of the current hour never enter it.
- **Trade:** when |S(i)| reaches the threshold and S(i) ≠ 0, trade −sign(S(i)).
  - Entry is at the open of bar i+1, and exit at the close of bar i+5.
  - One position per coin. A trade skipped for a missing price blocks nothing. After a trade, the next one needs a
    signal at its exit bar or later.
  - Both prices are moved half the month's tick against the trade.
  - Funding settled inside the hold is paid.
- **Net per trade:** side × (exit / entry − 1) − funding − 2c.
- **Trials: 1.** The late twin and the full-tick twin below are reported, not decided on.

## Costs
c a side is each coin's median $1k book walk on Lighter Standard (fee 0), from R348's `results/summary.json`
(`walk_cost_bp`), rounded to 2 decimals. The runner checks the constants against that file.

| BNB | XRP | TRX | AVAX | LINK | DOGE | SUI | ADA | LTC |
|---|---|---|---|---|---|---|---|---|
| 0.81 | 0.77 | 1.59 | 1.63 | 1.65 | 1.95 | 2.00 | 2.72 | 4.10 |

- **2x and 3x:** twice and three times c.
- **Reported only:** MEXC web at 3 bp a side and the MEXC/Binance API at 8.5 bp a side (as R349).

## Book
- Each coin holds a ninth of capital and trades it in sequence.
- The day's net is the sum of its trades' nets divided by 9, each trade on the UTC day of its entry.
- Every UTC day is in the series, and days without a trade are 0. A coin with no bars yet (SUI before 2023-05)
  leaves its ninth idle.

## Windows
- **Warm-up:** 2021-01-01 .. 2021-03-31, as in R349.
- **All:** 2021-04-01 .. 2026-09-30.
- **Halves:** early 2021-04-01 .. 2023-12-31 (R349's discovery span) and late 2024-01-01 .. 2026-09-30 (its
  validation span).
- **Recent:** 2025-07-01 .. 2026-09-30.

## Decision
- **REPLICATES** if all four hold:
  1. the Newey-West t (lag 10, `lab.stats.newey_west_t`) of the 1x daily net over All is ≥ 2.0;
  2. the 2x mean over All is > 0;
  3. the 1x mean is > 0 in both halves;
  4. at least 6 of the 9 coins have a positive mean gross return per trade over All.
- **LIVE** if it REPLICATES and the Newey-West t of the 1x daily net over Recent is ≥ 2.0.
- **NULL** otherwise.

**What each verdict earns:**
- **LIVE:** the nine coins join a forward paper lane on Lighter's recorded quotes, with a new id, frozen before its
  first day. Nothing trades with money: that needs paper to show a net gain, then `lab.gate.go_real()` and the owner.
- **REPLICATES:** the reversal is real beyond R349's coins but does not pay on them now. No forward lane for these
  coins. Their reserved 2020 minutes may be named in a later batch.
- **NULL:** R349's pick fails on new coins. It stays recorded for BTC, ETH and SOL only, and its forward lane carries
  that weight.

**Power (approximate, assuming R349's 62 bp a trade of noise and about 23 trades a day across the book):**
- **All** (2,009 days): a t of 2 with 80% power at about +0.9 bp a trade net.
- **Recent** (457 days): the same power at about +1.9 bp a trade net. LIVE therefore needs about two-thirds of R349's
  validation edge, kept through 2025-07..2026-09.

## Reported (not decided on)
- **Windows** (All, halves, Recent, each calendar year):
  - trades and trades a day, hit rate, and gross and 1x net per trade;
  - daily net at 1x/2x/3x, MEXC web and API, NW t at 1x;
  - break-even cost a side;
  - the late twin's 1x daily net (entry at the close of bar i+1, one minute late);
  - the full-tick twin's 1x daily net (each price moved a full tick against the trade instead of half).
- **Per coin and window:** trades, gross and 1x net per trade, the t of the per-trade net, and longs and shorts.
- **The 10 best days' share** of All, and All's mean without them.
- **Read against** `registry.program_trials()`: 9,479,068 on this branch before this lane, 9,479,069 after it.

## Outputs
`experiments/minflow_alts_v1/results/`:
- `summary.json`: the verdict, the decision figures, the costs and the input hashes;
- `windows.csv` and `coins.csv`;
- `daily.csv.gz`: the book's daily net at 1x/2x/3x;
- `trades.csv.gz`: every trade.

FINDINGS.md is written after the run, with 1x/2x/3x costs and the web and API columns.

## Evidence lineage and admission
- **Method:** M426.
- **Parents:**
  - R349, which chose the rule;
  - R348, for the costs;
  - R185 and R219, which read these coins hourly.
- **Decision group:** this lane alone decides whether the nine coins join a forward lane. R349's own forward lane
  (BTC, ETH and SOL) does not depend on it.
- **Samples:**
  - Fresh in the coin dimension: these nine coins' 1-minute bars.
  - Seen in time: every year here was read for other coins and rules.
  - Still fresh: the forward tape after a future freeze, and the reserved 2020 minutes.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa…a926`.

## Known limits (written before the result)
- **Prices are Binance's prints, not Lighter's quotes** (as R349). The 1x cost is Lighter's book in October 2026,
  applied to 2021-2026.
- **Coarse ticks:** ADA's median tick is 2-3.6 bp, and LTC's and XRP's 1-1.7 bp at times. A fade bought at a print on
  the flow's side of the spread gains part of the bid-ask bounce; half a tick against each fill removes only part of
  it. The full-tick twin shows how much depends on it.
- **Same years as the choice:** a market-wide regime that made R349's rule work in 2021-23 would touch these coins
  too, so this is a replication across coins, not across time.
- **Size:** $1k a trade.
- **Not tested:** other rules from R349's family, other coins, maker entries, and Lighter's own fills.

## Stop rules
- No new rule, threshold, hold, coin, cost or window after seeing results. A changed idea is a new lane with a new id.
- A crash before any statistic is recorded as ABANDONED with 0 trials, and the rerun gets a new id.
