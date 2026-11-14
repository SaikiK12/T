# PREREG: clockflow_v1 (R289). Fixed-clock flows on 1-minute bars: the US cash-open flush (M301) and the Deribit settlement window (M303)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R289 (Claude block R280-R299, claimed on issue #7 before the freeze). **Methods:** M301, M303.
- **Owner (single writer):** the Claude session that froze it.
- **Code:** `scripts/run_clockflow.py`. It calls `verify()` on this file first and checks every input's sha256 against
  the block below.
- **Source of the ideas** (`docs/TRADER_TALKS.md`):
  - **M301:** a French prop-trading-room founder (tier C) says his room trades the US cash open every day. A large
    seller flushes the index, everyone panics, and they buy the reversal: "on le prend tout le temps". His market is
    index futures. This lane asks whether crypto perps show the same flush and reversal in the first minutes after
    the US cash open.
  - **M303:** SEBI's interim order against Jane Street (2025; allegations, contested). A thin market was pushed in
    the hours before an index-option expiry, while the options book paid. Deribit settles on a 30-minute TWAP of its
    index from 07:30 to 08:00 UTC. This lane asks whether the move inside that window reverses or continues after
    08:00.
- **Gate:** 0. Every year read here (2021-04..2026-09) was read by earlier crypto lanes at hourly resolution. The
  1-minute bars are new to the lab.
- **Execution mode:** manual web. There are at most 6 orders a day (3 coins, entry and exit) at fixed clock times,
  within the owner's limit of about 15 orders a day. API costs are reported, not decided on.

## What the author has seen
- **The 1-minute files** (`data/klines_1m`, downloaded 2026-10-21):
  - row counts, and the first and last bar of each file;
  - the gaps: none in BTC or ETH; SOL misses 2022-02-26..28 and 2022-04-01..02 (7,200 minutes).
  - No price, return, volume or volatility statistic of the 1-minute data has been computed.
- **Earlier lanes on related clocks, at hourly resolution:**
  - R203: the first UTC hour predicting the last. NULL.
  - R246: the 8 AM New York range on hourly bars. NULL.
  - R185: the gross atlas's US-open hour cells (49% of cells replicated, gross, all coins, hourly).
  - R223: funding-settlement capture. NULL.
  - M289 (expiry pinning) and M175 (max pain) have not run.
- **Not computed in this lab:** no statistic of returns in the first 30 minutes after 09:30 New York, or around
  08:00 UTC on Fridays.

## Inputs (frozen)

```inputs
9e2c7fd717811a58bca2fa5816b92b4bf59aaa5d9706c10af2522af04a1c82a0  data/klines_1m/BTCUSDT.parquet
7c7c05b387d59fd3e40555718c28388fb66c737602102297a34de9af9c67da70  data/klines_1m/ETHUSDT.parquet
966602440c3573e677b7578feed150b5065d2062d84869acd54e79ad58af1706  data/klines_1m/SOLUSDT.parquet
b1cb8c15d60cc2495a8215e9c081e196c069ebf9a324f0e164a69ebdf2536ae3  data/fundingRate/BTCUSDT.parquet
3b640724ed7ed8985b3b8ce41d5ffb6b3eaea7a6b399389ee50ceb91ef2b2e89  data/fundingRate/ETHUSDT.parquet
e110881032024bc2f52a14511c0d3a70a0a444db5b6f4499e31418e7e93c967e  data/fundingRate/SOLUSDT.parquet
831fe1dfa2c794bc0467137bb10f9395895ecddecfffcbc860b2c6273faae18d  lab/sessions.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
```

## Data
- **Coins:** BTCUSDT, ETHUSDT and SOLUSDT, Binance USD-M perpetuals.
- **Bars:** rows with open time from 2021-01-01 00:00 UTC to 2026-09-30 23:59 UTC. Earlier rows are dropped on load,
  because 2020 is reserved (`docs/GATES.md`).
  - A bar is valid when count > 0 and close > 0.
- **Price at an instant τ:** P(τ) is the close of the bar that opens at τ − 1 minute, when that bar is valid.
  Otherwise P(τ) is undefined. Nothing is carried forward.
- **Funding:** `data/fundingRate/<SYMBOL>.parquet` (t, rate). The settlement time F is t rounded to the nearest
  minute. A position with entry time < F ≤ exit time pays side × rate, so a long pays a positive rate.

## Rules
Each rule is decided per coin and day. A trade is skipped when any price it needs is undefined.

**OPEN (M301), 24 variants:**
- **Days:** NYSE trading days, meaning weekdays not in `lab.sessions.NYSEHolidays`.
- **Open time:** T0 is 09:30 New York local time on that day, in UTC, so it follows daylight saving.
- **Window move:** for window w minutes, m = P(T0 + w) / P(T0) − 1.
- **Scale:** σ is the standard deviation (ddof 1) of m over the 60 most recent earlier NYSE trading days. Days where m
  is undefined are skipped. At least 40 defined values are needed, or there is no trade.
- **Signal:** |m| ≥ k σ and m ≠ 0.
- **Side:** s = −sign(m) for **fade**, and s = +sign(m) for **follow**.
- **Entry and exit:** entry at E = P(T0 + w + 1), one minute after the window ends. Exit at X = P(T0 + w + 1 + h).
- **Variants:** w ∈ {5, 15, 30}, k ∈ {1, 2}, side ∈ {fade, follow}, h ∈ {60, 120}.

**SETTLE (M303), 16 variants:**
- **Days:** Fridays. The day set is either **weekly** (every Friday) or **monthly** (the last Friday of each
  calendar month, which holds the monthly and quarterly expiries).
- **Window move:** m = P(08:00) / P(07:30) − 1, in UTC.
- **Scale:** σ is the standard deviation (ddof 1) of m over the 60 most recent earlier calendar days, at the same
  clock and including weekends. Days where m is undefined are skipped. At least 40 defined values are needed.
- **Signal:** |m| ≥ k σ and m ≠ 0. With k = 0, every Friday in the set with a nonzero window move trades.
- **Side:** fade or follow, as in OPEN.
- **Entry and exit:** E = P(08:01) and X = P(08:01 + h).
- **Variants:** day set ∈ {weekly, monthly}, k ∈ {0, 1}, side ∈ {fade, follow}, h ∈ {60, 120}.

**Book:** each coin is one third of capital.
- A coin's trade returns s × (X / E − 1) − 2c − funding.
- The day's net is the sum of the coins' trade returns divided by 3.
- Every UTC day of a window is in the series. Days with no trade are 0.
- Every trade opens and closes within its UTC day.

**Cost** c per side, manual web on MEXC:
- 1x is 3 bp. That is the web taker fee on these three contracts (1-2 bp in R224's recorder) plus their half-spread
  (under 0.5 bp) and a margin for a hand-placed order.
- 2x is 6 bp, and 3x is 9 bp.
- Reported, not decided on: the API cost of 8.5 bp per side (8 bp taker plus the spread).

**Trials: 24 + 16 = 40.**

## Windows
- **Discovery:** 2021-04-01 .. 2023-12-31. Every variant is past its 40-value warm-up by then.
- **Validation:** 2024-01-01 .. 2026-09-30, with halves 2024-01-01 .. 2025-06-30 and 2025-07-01 .. 2026-09-30. The
  second half is the spent holdout, so all of this is gate 0.

## Test
Each sub-family (OPEN, SETTLE) is tested on its own. A Bonferroni split over the two sets each test's level at 0.025.
1. **Reality check (White, studentized),** as in R263 and R287:
   - over the sub-family's discovery series of daily net at 1x;
   - statistic: max_j sqrt(n) mean_j / sd_j;
   - null: a stationary bootstrap of the demeaned series (block 10 days, B = 2,000);
   - seeds 289 for OPEN and 2890 for SETTLE;
   - result: rc_p.
2. **Selected variant j*:** the largest studentized discovery mean at 1x within the sub-family.
3. **The sub-family PASSES** if all of these hold:
   - rc_p < 0.025;
   - j*'s validation Newey-West t (lag 10, `lab.stats.newey_west_t`) at 1x is ≥ 2.0;
   - j*'s validation mean at 2x is > 0;
   - j*'s mean at 1x is > 0 in both validation halves.

**Verdict:**
- **PARTIAL** if at least one sub-family passes. Its j* becomes a candidate for a later reserved batch: 2020, with
  1-minute bars held for BTC and ETH from 2020-01 and SOL from 2020-09. It also earns a forward paper lane with a new
  id, labelled manual web.
- **NULL** otherwise.

**Power:** validation has 1,004 calendar days. A t of 2 is reached with 80% power at an annual Sharpe of about 1.7 on
the daily series. OPEN at k = 2 trades on a small share of days, so a small edge there is a futility screen.

## Reported (not decided on)
- **Per variant and window:**
  - trades, hit rate, and mean gross per trade in bp;
  - net per day at 1x/2x/3x and at the API cost;
  - Newey-West t at 1x, and annual Sharpe at 1x;
  - break-even cost per side (gross per trade / 2).
- **For each j*:** net at 1x per calendar year and per coin, and the five best days' share of the summed net.
- **Placebo clocks,** with the same rules and parameters, reported and not decided on:
  - OPEN at 10:30 New York on the same trading days;
  - OPEN at 09:30 New York on weekdays that are NYSE holidays and on weekends;
  - SETTLE on Mondays to Thursdays. Deribit also lists daily expiries at 08:00 UTC, so these are smaller expiries,
    not a clean null.

  In each OPEN placebo, σ is taken over the 60 most recent earlier days of that placebo's own day set at its own
  clock, with at least 40 defined. In the SETTLE placebo, σ is SETTLE's calendar-day σ.
- **Read against** `registry.program_trials()`.

## Outputs
`experiments/clockflow_v1/results/`:
- `variants.csv`, one row per variant and window (placebos included, marked);
- `daily.csv.gz`, daily net at 1x per variant;
- `trades.csv.gz`, one row per trade: variant, coin, day, m, σ, side, E, X, gross and funding;
- `summary.json`: verdict, each sub-family's rc_p, j* and validation figures, the input hashes and program trials.

FINDINGS.md is written after the run, with 1x/2x/3x costs and the API column.

## Known limits (written before the result)
- **Prices are Binance's.** The owner trades on MEXC, where BTC, ETH and SOL track Binance within a few bp. MEXC's
  1-minute history is not held.
- **Fills:** each fill is at the 1-minute close one minute after the decision. A hand-placed order can be seconds
  late or early, and the spread at the open can be wider than its median.
- **Sides:** fade and follow are both in the family, so a pass in either direction counts once in the reality check.
- **The clocks are not the trader's.** Elmarhri trades index futures, and the Paris 15:30 open is the same instant as
  09:30 New York. Crypto has no cash open, so this tests a transfer, not his trade.
- **Deribit's calendar:** a Friday expiry moved for a holiday is not modelled. Deribit's TWAP uses its own index, not
  Binance's price.
