# PREREG: rrskew_v1 (R307). The Deribit 25-delta risk reversal as a weekly BTC and ETH timing signal (M174)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R307, in the Claude block R300-R319 claimed on issue #7 on 2026-10-22.
- **Method: M174.** The owner's reel DeKFE8OEq-i (2026-10-22, a quant job-interview game) asks why a 25-delta put
  costs more vol than a 25-delta call (`docs/REELS_TRANSCRIPT.md`, reel 16). That holds for equity indices. BTC's risk
  reversal changes sign with the regime (Amberdata; Coin Metrics). An unreviewed SMU dissertation (Deribit
  2021-04..2025-12, `https://ink.library.smu.edu.sg/etd_coll/887`) reports the 25-delta 90-day risk reversal
  predicting BTC returns: t 3.73 with 13 controls, 1.91 alone. This lane tests that on the lab's own option trades.
- **Owner (single writer):** the Claude session that froze it.
- **Code:** `scripts/run_rrskew.py`, tested on synthetic rows in `tests/test_run_rrskew.py`:
  - Black-Scholes deltas on the forward, with and without a basis;
  - the risk reversal from the two wings, amount weights, the minimum row count, the next-day decision instant;
  - the basis contract choice, the 14-day rule and the 24-hour gap fill;
  - rows outside [2021-01-01, 2026-10-01) dropped on read;
  - the z-scores on past values only;
  - the book's costs on entries, flips and exits, funding, Mondays and the week window;
  - the trial count and the decision rule.

  It calls `verify()` on this file first, then checks every input's sha256 (the `inputs` block) and the COIN-M file
  tree (the `trees` block; `--trees` prints it). The Deribit flow files are checked one by one against
  `docs/provenance/deribit_trades.json` as they are read.
- **Data:**
  - Deribit option trades as hourly per-option rows (`data/deribit_trades/{BTC,ETH}/flow`): the amount bought and
    sold, the amount-weighted trade IV and the last index price per option-hour.
  - Binance COIN-M hourly klines (`data/coinm_1h`): the BTCUSD and ETHUSD perps and every quarterly that expires after
    2021-01-01 (50 files), for the forward's basis.
  - Binance USD-M BTCUSDT and ETHUSDT 1-minute klines and funding (`data/klines_1m`, `data/fundingRate`): the traded
    perps.
- **Not reserved:**
  - Rows before 2021-01-01 and at or after 2026-10-01 are dropped on read, before any computation. The Deribit loader
    opens only the monthly files from 2021-01 to 2026-09.
  - No `reserved/` folder is read. BTC and ETH are not MEXC-only coins.
- **Execution mode: manual web.** Two orders a week per coin at Monday 00:00 UTC, on the two most liquid MEXC perps.
- **Gate: 0, on seen data.** The lab has read BTC and ETH prices and Deribit flow in these years (below). A pass
  earns a place in a reserved batch and a forward paper lane, not a confirmation.

## What the author has seen
- **R209 (`vrp_v1`):** DVOL minus realized vol as a BTC/ETH timing signal, NULL (8 trials). The BTC primary earned
  +7.5 bp/day (t 1.06) in-sample; ETH reversed.
- **R292 (`dealerflow_v1`):** dealer gamma from the same Deribit flow rows against next-day volatility, NULL.
- **R295 (`optflow_v1`):** Deribit option flow (blocks and net drift) leading the perps at 1-24 h, NULL. Gross per
  trade +0.3 to +16 bp against a 17 bp round trip.
- **R296 (`charm_expiry_v1`):** the Friday 08:00 UTC expiry, NULL.
- **The literature, read before this freeze:**
  - the SMU dissertation's abstract and summary (above);
  - Amberdata, "The Smile: Why Crypto's Skew Tells a Story Equity Markets Never Will": BTC calls trade rich in rallies
    and puts rich after crashes;
  - Coin Metrics' documentation of its constant-maturity, constant-delta skew series.

  So the author knows that the risk reversal moves with past returns. Whether it leads the next week is the question.
- **The author has not computed** any risk reversal value, signal value or book return on real prices before this
  freeze.
- **The plumbing run of this script** (counts only):

  | Series | Discovery days with an RR / days | Validation days with an RR / days |
  |---|---|---|
  | BTC 30 d | 1,091 / 1,095 | 1,004 / 1,004 |
  | BTC 90 d | 1,083 / 1,095 | 1,004 / 1,004 |
  | ETH 30 d | 1,091 / 1,095 | 1,004 / 1,004 |
  | ETH 90 d | 1,083 / 1,095 | 994 / 1,004 |

  Option-hours with a basis: BTC 4,918,564 of 4,926,124, ETH 3,823,047 of 3,827,847. Hours with a basis: 50,304 of
  50,377.
- **A smoke run of `main()`** with the prices replaced by a constant and zero funding, to exercise the code: it read
  the real risk reversals and printed costs only. So the author has seen the turnover of BTC 90 d `sign`: about 0.4
  units a week in discovery and 0.2 in validation. No return.

## The risk reversal
- **Decision instants:** every 00:00 UTC D from 2021-01-01 to 2026-10-01. D uses the option-hours in [D − 24 h, D).
- **Rows used:** IV in (0, 500) percent and a traded amount above 0.
- **Forward:** F = index × exp(b × T).
  - b is the annualized log basis ln(F_q / S) / τ, with:
    - F_q the COIN-M quarterly with the shortest time to expiry τ of at least 14 days;
    - S the COIN-M perp;
    - both taken at the close of the hourly bar that ends at the start of the row's hour.
  - A missing b is carried forward up to 24 hours. A row without b is dropped.
  - T runs from the middle of the row's hour to its 08:00 UTC expiry.
- **Delta:** Black-Scholes on F with the row's own IV and zero rates. A call's delta is N(d1), a put's N(d1) − 1.
- **Tenor buckets:** 30 d is 14-60 days to expiry; 90 d is 60-150 days.
- **Wings:** calls with delta in [0.15, 0.35] and puts with delta in [−0.35, −0.15]. Each wing's IV is the
  amount-weighted mean of its option-hours, and needs at least 3 of them.
- **RR = call-wing IV − put-wing IV**, in vol points. Positive means calls are rich.

## The family (24 trials)
- **Signals** per coin and tenor, on the daily RR series:
  - `sign`: the RR itself;
  - `z`: the RR against its previous 90 daily values (at least 60), (RR − mean) / standard deviation;
  - `chg7`: RR minus RR 7 days earlier, z-scored the same way.
- **Directions:**
  - `follow`: long the perp when the signal is above 0, short below;
  - `fade`: the reverse.
- **Books:** coin {BTC, ETH} × tenor {30 d, 90 d} × signal {sign, z, chg7} × direction = 24. `follow` and `fade` of
  one signal are mirror images before costs; they are counted as 24 trials all the same.
- **Trading:** each Monday 00:00 UTC, the USD-M perp is held long or short for 7 days at one unit.
  - The entry price is the close of the 1-minute bar that ends at Monday 00:00. The exit is the same 7 days later.
  - A week whose signal or return is missing is flat.
  - Funding: a long pays, and a short receives, the rates settled in (D, D + 7 d].
- **Costs per side on each unit traded:**
  - manual web 3 bp at 1x (R289's figure for BTC and ETH on MEXC), 6 bp at 2x, 9 bp at 3x;
  - reported, not decided on: the API cost of 8.5 bp.
  - An entry is 1 unit, a flip 2 and an exit 1. A move to flat, and the end of a window, close the position in the
    last week held.

**Windows:** a week counts in a window when it starts on or after the window's start and ends by its end: discovery
2021-01-01..2024-01-01, validation 2024-01-01..2026-10-01. A window's book starts flat and ends flat. `z` has its
first value about 2021-03-02 and `chg7` about 2021-03-09; until then those books are flat.

## Statistics
- **The decided series:** each window's weekly net returns over the weeks with a position. Flat weeks are gaps.
- **The t:** Newey-West, lag 4. With fewer than 20 weeks there is no t, and the book cannot be picked.
- **Reported per book and window, at 1x, 2x, 3x and API:** weeks, the mean (bp per week), the t, the hit rate and the
  mean without the 10 best weeks.
- **Also reported:** buy-and-hold of each perp net of funding, per window.

## Decision
- **The pick:** the book with the highest discovery net 1x t, among those with a positive discovery mean.
- **It passes** only if, in validation, all three hold:
  1. net 1x t ≥ 2.0;
  2. the net 2x mean is positive;
  3. the net 1x mean without its 10 best weeks is positive.
- **Verdict:** PARTIAL (gate 0) if the pick passes, else NULL. Validation is read once, with no second pick.
- **What a pass earns:**
  - a place in a reserved batch (2020 BTC and ETH perps; Deribit trades exist from 2016 for BTC and 2019 for ETH);
  - a forward paper lane with its own id on MEXC prices.
- **What a NULL means:** the Deribit 25-delta risk reversal, built this way, does not time BTC or ETH by the week in
  2024-26 at a power that detects an annual Sharpe of about 1.7 (below). It does not rule out the dissertation's
  smaller effect.

## Power
- **Validation** has about 143 weeks. A ±1 BTC book has a weekly standard deviation of about 6-9%.
- **t = 2 on average** needs a weekly Sharpe of 2 / √143 = 0.17, an annual Sharpe of about 1.2: about 110 bp a week
  at a 6.5% weekly standard deviation.
- **80% power** at t ≥ 2 needs an annual Sharpe of about 1.7.
- **The dissertation's** t of 1.91 alone over about 4.7 years is an annual Sharpe of about 0.9. This lane is a screen
  for a large effect, not a test of that one.

## Known limits
- **Seen data:** the lanes above read these years; the author knows the risk reversal moves with past returns.
- **The forward:** Binance COIN-M's basis stands in for Deribit's own forward; their gap was not measured. A gap of 1%
  a year moves a 90-day 25-delta wing by about 0.003 of delta.
- **No delay:** the entry is at the decision instant itself. A hand-placed order lands minutes later.
- **Trade IVs** are the prices traders paid, not a fitted surface. A wing with few rows is noisy, so it needs 3
  option-hours a day.
- **One coin at a time:** BTC and ETH move together, so the 24 books are far from independent.
- **Prices:** Binance only; MEXC is not checked here.

## Outputs
- `results/summary.json`: every book and window at 1x/2x/3x and API, buy-and-hold, basis coverage, input hashes.
- `results/weeks.csv`: per Monday, the four RR series, the weekly returns and funding, and every book's net 1x week.
- `run.log`
- FINDINGS.md with 1x/2x/3x costs, read against `registry.program_trials()`.

## Inputs (frozen)

```inputs
9ab09b14cc503d6ead4ca14ea16c0e32ed0f428a82b52c0cbf17567797d6a188  docs/provenance/deribit_trades.json
9e2c7fd717811a58bca2fa5816b92b4bf59aaa5d9706c10af2522af04a1c82a0  data/klines_1m/BTCUSDT.parquet
7c7c05b387d59fd3e40555718c28388fb66c737602102297a34de9af9c67da70  data/klines_1m/ETHUSDT.parquet
b1cb8c15d60cc2495a8215e9c081e196c069ebf9a324f0e164a69ebdf2536ae3  data/fundingRate/BTCUSDT.parquet
3b640724ed7ed8985b3b8ce41d5ffb6b3eaea7a6b399389ee50ceb91ef2b2e89  data/fundingRate/ETHUSDT.parquet
a32e993454728aa37e52559d798406ee64bffdcd9196b183ec908addd63b5dbe  lab/data.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
7df0959df85c12323c948e6301b3a5d7f1a05c4464e534197fa546f800a8c665  scripts/run_optflow.py
77632eb621be13d91c3fbe926a2363dc23bf8760df5f0f4229be07164d555946  scripts/run_msnr.py
e4583c7d44c6e988fd47ee49adf2b5e238abbc00f56a0ce10f52dbf4805eb42d  scripts/run_rrskew.py
```

```trees
0eb68df0100ff8bfc851601acb3865b6b8387cb2280dfb5ddafc8af062bdd31e  coinm_1h
```
