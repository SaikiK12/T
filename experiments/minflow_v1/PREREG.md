# PREREG: minflow_v1 (R349). Minute-scale order flow and overreaction on the BTC, ETH and SOL perps, at Lighter's zero-fee cost

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R349
- **Methods:** M426 (new: minute-scale extreme-move, signed-flow and BTC-lead rules) and M306 (absorption and
  exhaustion on 1-minute bars, queued since 2026-10-21).
- **Owner (single writer):** the Claude session that froze it. R349 and M426 are claimed on issue #7 before the freeze.
- **Date registered (UTC):** 2026-10-27
- **Code:** `scripts/run_minflow.py`, tested by `tests/test_minflow.py` (13 tests on invented bars). The runner calls
  `verify()` on this file first and checks every input's sha256 against the block below.
- **Gate:** 0. Every year read here was read by earlier lanes: hourly by many, and on these same 1-minute files by
  R289-R293 for other rules (fixed clocks, auction levels, VPIN, efficiency).
- **Execution mode:** Lighter Standard API: no fee, a 300 ms delay on taker orders, about 2-45 orders a day per coin
  depending on the rule. MEXC web (manual, about 15 orders a day) and the MEXC/Binance API are reported, not decided on.

## Why this lane, and why now
- **The owner's format:** short-hold futures ("scalping futures to do quick money"), on a venue the owner can use.
- **The cost lever:** Lighter's Standard account charges no fee and allows the API.
  - R348 measured the median cost of filling $1k on its book: BTC 0.27, ETH 0.23 and SOL 0.30 bp a side.
  - A minute-scale rule on these three coins therefore needs only about 0.5-0.6 bp a round trip.
  - Binance's or MEXC's API needs about 17.
- **The latency:** R348 found Lighter's quote level with Binance's within one second. A rule that decides on a
  minute's close and fills on the next minute's open is therefore within reach of an API order. Holds of 5-60
  minutes leave the first second a small part of the trade.
- **The confirmation:** a pass here earns a forward lane on the recorded 1-second Lighter tape, with a new id frozen
  before its first day.
  - With 2-45 trades a day per coin, a real edge of about 1 bp a trade shows a t of 2 in weeks, not the 1-2 years a
    daily book needs (`docs/EDGE_SCOREBOARD.md`).
  - That forward test is the decision this lane cannot make: all of its history is seen.

## What the author has seen
- **The 1-minute files** (`data/klines_1m`, BTC and ETH from 2020-01, SOL from 2020-09):
  - row counts, first and last bars, and the gaps (R289's PREREG).
  - 2020 is reserved, and this lane never loads it: the reader filters the rows by time.
- **Plumbing for this lane before the freeze** (2026-10-27; signal and trade counts only, no price change after any
  signal computed):
  - **Rule frequency, per coin:**
    - ret and flow rules fire about 8 times a day;
    - absorption about 20;
    - exhaustion 66-84;
    - BTC's lead about 5 on ETH and SOL.
  - **Trades a day after the one-position rule:** 1-6 (ret, flow), 10-20 (absorption), 15-45 (exhaustion), 1-4 (lead).
  - **Monthly ticks:** SOL 0.0001-0.01, BTC 0.01-0.1.
  - **Runtime:** the signals take about 100 s.
- **Earlier results on these files and horizons:**
  - R289: the US-open flush does not reverse out of sample. The Friday settlement fade is small (validation t 1.37).
  - R290: auction levels carry no more structure than random clocks.
  - R291: VPIN adds no volatility forecast.
  - R293: efficiency is barely predictable.
- **Earlier results elsewhere:**
  - **R348 (tape, today):** one second after Lighter's quote leaves Binance's, nothing is left to catch.
  - **R219 (hourly):** the altcoin lead-lag spread is real but far below taker cost.
  - **R185 (hourly atlas):** flow cells replicate gross but are below taker cost per trade.
- **Not computed in this lab:** any statistic of the return after an extreme minute, an extreme signed-flow window, an
  absorption or exhaustion bar, or a BTC move that ETH or SOL has not followed, on 1-minute bars.

## Inputs (frozen)

```inputs
9e2c7fd717811a58bca2fa5816b92b4bf59aaa5d9706c10af2522af04a1c82a0  data/klines_1m/BTCUSDT.parquet
7c7c05b387d59fd3e40555718c28388fb66c737602102297a34de9af9c67da70  data/klines_1m/ETHUSDT.parquet
966602440c3573e677b7578feed150b5065d2062d84869acd54e79ad58af1706  data/klines_1m/SOLUSDT.parquet
b1cb8c15d60cc2495a8215e9c081e196c069ebf9a324f0e164a69ebdf2536ae3  data/fundingRate/BTCUSDT.parquet
3b640724ed7ed8985b3b8ce41d5ffb6b3eaea7a6b399389ee50ceb91ef2b2e89  data/fundingRate/ETHUSDT.parquet
e110881032024bc2f52a14511c0d3a70a0a444db5b6f4499e31418e7e93c967e  data/fundingRate/SOLUSDT.parquet
8bd9a1236948344161bc651a6c6eb08d0af7b3f3703556a2a7d770b63d152e73  docs/provenance/klines_1m.json
84a3aadbf5ac0439b99209714c85ab0484b775f1258701835a64029c1ec3e4de  docs/provenance/fundingRate.json
4f4690ff82f4f3c9dc458db8e29fc0a3eb0733a5ced0e8dd613b083de85ca778  experiments/tapelag_lighter_v2/results/summary.json
692b7223b4d50353f4f88cd3f6f5652a6f87e8fffa4cbfb4351e3c09003e26f1  scripts/run_minflow.py
dcea9ff15384ab60f5bf098e786c3d49c969b8aadb13ab66e99cf0aab5ec4db8  tests/test_minflow.py
097ec5cd95aecea45497c68319d11a4ff2508c980a83c373b5afb4c61e90da13  lab/orderflow.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
96053b6a8ba4e22469acfa4da4fb59f1d56e610e5b18460a50e40e82da8d4a6f  lab/inference.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
```

## Data
- **Coins:** BTCUSDT, ETHUSDT and SOLUSDT, Binance USD-M perpetuals.
- **Bars:** open times from 2021-01-01 00:00 UTC to 2026-09-30 23:59 UTC, on a full minute grid.
  - A bar is valid when count > 0, close > 0 and open > 0. Missing or invalid bars are NaN, and nothing is carried
    forward.
  - Delta d = 2·(taker buy volume) − volume (`lab.orderflow.delta`).
- **Funding:** `data/fundingRate/<SYMBOL>.parquet`, rows inside the same span. A settlement time F is t rounded to the
  minute. A trade with entry time < F ≤ exit time pays side × rate, so a long pays a positive rate.
- **Tick:** for each coin and calendar month, the smallest positive gap between two distinct prices printed that month
  (open, high, low or close), rounded to 6 significant digits.

## Rules
Every statistic at bar i uses bars up to and including i, and is known at bar i's close.

**Thresholds.** For a statistic S, the threshold of the hour that holds bar i is the 99.5th percentile of |S| over the
bars of the previous 168 hours.
- It needs at least 7,200 finite values; otherwise there is no threshold and no trade.
- Bars inside bar i's own hour never enter its threshold.

**Signals.** k ∈ {1, 5, 15} minutes.
1. **ret (M426):** R_k(i) = ln(C_i / C_{i−k}), with both bars valid.
   - It fires when |R_k| reaches the threshold and R_k ≠ 0.
   - **follow** trades sign(R_k), and **fade** trades −sign(R_k).
2. **flow (M426):** S_k(i) = the sum of d over bars i−k+1..i, with all k bars valid.
   - It fires as ret does.
   - **follow** trades sign(S_k), and **fade** trades −sign(S_k).
3. **absorb (M306):** `lab.orderflow.absorption(d, ln(C/O), window 60, k 3, m 0.5)`, the module's defaults.
   - A bar's |delta| is at least 3 times the median |delta| of the previous 60 bars, and its |ln(C/O)| is at most
     0.5 times the median |ln(C/O)| of those bars.
   - The flag is +1 when buyers were absorbed and −1 when sellers were.
   - **book** trades −flag (absorbed buyers are a bearish read), and **anti** trades +flag.
4. **exhaust (M306):** `lab.orderflow.exhaustion(H, L, d, window 60)`.
   - A new 60-bar high while the running delta sum is below its 60-bar maximum is −1; the mirror at lows is +1.
   - **book** trades the flag, and **anti** trades −flag.
5. **lead (M426), ETH and SOL only:**
   - BTC's R_k(i) reaches BTC's own ret threshold, and the coin's residual E = R_k^coin − β·R_k^BTC has the opposite
     sign to BTC's move: the coin has not followed.
   - β is the OLS slope of the coin's 1-minute returns on BTC's over the previous 168 hours (at least 7,200 pairs), per
     hour.
   - It trades the coin in the direction of BTC's move.

**Trades.**
- **Entry:** a signal at bar i enters at the open of bar i+1.
- **Exit:** at the close of bar i+h, h ∈ {5, 15, 60} minutes, so the hold is exactly h minutes.
- **Missing prices:** if either price is missing, the trade is skipped and blocks nothing.
- **One position per rule and coin:** after a trade, the next one needs a signal at its exit bar or later.
- **Prices:** both are moved half the month's tick against the trade. A long pays open + tick/2 and receives
  close − tick/2, which is about a one-tick round trip on top of the venue's cost.
- **A trade's net:** side × (exit / entry − 1) − funding paid − 2c.
- **Late twin (reported, not decided on):** the same signals entered at the close of bar i+1 (one minute late) and
  exited h minutes after.

**Variants:**
- ret and flow: 2 sides × 3 k × 3 h = 18 each.
- absorb and exhaust: 2 sides × 3 h = 6 each.
- lead: 3 k × 3 h = 9.
- **Trials: 18 + 18 + 6 + 6 + 9 = 57.**

**Book.** Each coin holds a third of capital and trades it in sequence.
- The day's net is the sum of its coins' trade nets divided by 3, with each trade on the UTC day of its entry.
- Every UTC day of a window is in the series. Days with no trade are 0.
- lead uses ETH and SOL only, and its book is still divided by 3.

**Cost** c a side, Lighter Standard, taken from R348's `results/summary.json` (`walk_cost_bp`):
- **1x:** the median cost of walking $1k into Lighter's book over 20 snapshots. That is BTC 0.27, ETH 0.23 and SOL
  0.30 bp, with no fee.
- **2x and 3x:** twice and three times c.
- **Reported, not decided on:** MEXC web at 3 bp a side (as R289) and the MEXC/Binance API at 8.5 bp a side.

## Windows
- **Warm-up:** 2021-01 .. 2021-03, which the thresholds and β need.
- **Discovery:** 2021-04-01 .. 2023-12-31 (1,005 days).
- **Validation:** 2024-01-01 .. 2026-09-30 (1,004 days).
  - Its halves are 2024-01-01 .. 2025-06-30 and 2025-07-01 .. 2026-09-30.
  - The second half is the spent holdout, so all of this is gate 0.

## Test (as R289)
1. **Reality check (White, studentized):**
   - over the 57 discovery series of daily net at 1x;
   - statistic: max_j sqrt(n) mean_j / sd_j;
   - null: a stationary bootstrap of the demeaned series, block 10 days, B = 2,000, seed 349;
   - result: rc_p.
2. **Selected rule j*:** the largest studentized discovery mean at 1x.
3. **PASS** if all of these hold:
   - rc_p < 0.05;
   - j*'s validation Newey-West t (lag 10, `lab.stats.newey_west_t`) at 1x is ≥ 2.0;
   - j*'s validation mean at 2x is > 0;
   - j*'s mean at 1x is > 0 in both validation halves.
4. **Verdict:** PASS or NULL.

**What a PASS earns:**
- A forward paper lane for j* on the live 1-second tape, at Lighter's own quotes one full second after the signal. It
  gets a new id and is frozen before its first day.
- A place for j* in a later reserved batch (2020: BTC and ETH from 2020-01, SOL from 2020-09).
- Nothing trades with money: that needs paper to show a net gain, then `lab.gate.go_real()` and the owner.

**Power:**
- Validation has 1,004 days.
- A t of 2 is reached with 80% power at an annual Sharpe of about 1.7 on the daily series.
- A rule trading 5-40 times a day reaches that Sharpe with a mean of a small fraction of a basis point per trade above
  the per-trade noise. This screens out rules whose edge is a rare tail.

## Reported (not decided on)
- **Per rule and window** (discovery, validation, both halves):
  - trades and trades a day;
  - hit rate, and gross and 1x net per trade in bp;
  - daily net at 1x/2x/3x, MEXC web and API;
  - Newey-West t at 1x, and annual Sharpe at 1x;
  - break-even cost a side (net of funding);
  - the late twin's gross per trade and 1x daily net.
- **Sub-family reality checks** (ret, flow, absorb, exhaust, lead), each with seed 351.
- **Hansen's SPA p** over all 57 in discovery (`lab.inference.spa`, seed 350).
- **For j*:**
  - net at 1x per calendar year;
  - validation net by coin (leave-coins-out reading);
  - the 10 best validation days' share and the mean without them;
  - a 5% trimmed mean of the validation days with a trade.
- **Read against** `registry.program_trials()`: 9,479,011 on this branch before this lane, and 9,479,068 after it.

## Outputs
`experiments/minflow_v1/results/`:
- `variants.csv`: one row per rule and window;
- `daily.csv.gz`: daily net at 1x per rule;
- `trades_best.csv.gz`: j*'s trades;
- `summary.json`: the verdict, the decision figures, SPA, the sub-families, j*'s detail, the costs and the input hashes.

FINDINGS.md is written after the run, with 1x/2x/3x costs and the web and API columns.

## Evidence lineage and admission
- **Methods:** M426 and M306. M264 (the 1-10 s tape scalp) is related but not tested here.
- **Parents:**
  - R289-R293 read these 1-minute files for other rules.
  - R348 read the tape for Lighter's lag.
  - R185 and R219 read hourly flow and lead-lag.
- **Decision group:** this lane's PASS feeds one forward tape lane. Its sub-family checks are not extra chances.
- **Samples:**
  - Seen: 2021-01..2026-09, by many lanes, at hourly or coarser resolution and on these minute files.
  - Fresh: the forward tape after a future lane's freeze, and the reserved 2020 minutes.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa…a926`. This is gate 0. Gate 1 needs an unread window, which only the
  forward lane or the reserved batch can give.
- **Controls:**
  - the dependent null is the stationary bootstrap of daily series;
  - the 10-best-days share, the by-coin split and a trimmed mean are reported;
  - power is above.

## Known limits (written before the result)
- **Prices are Binance's prints, not Lighter's quotes.**
  - R348 shows the two level within a second.
  - The half-tick moves stand in for the spread at the print.
  - The 1x cost is Lighter's walk measured in October 2026, applied to 2021-2026. Lighter did not exist in 2021, and
    its book then would have differed.
- **Fills:** the next bar's open is the first print after the signal, a few milliseconds after it. An API order on
  Lighter fills about 0.3-1 s later. A rule whose gross lives in that first second is fragile; the late twin and the
  forward tape lane show it.
- **Size:** $1k a trade. Larger trades walk further into Lighter's book; 2x and 3x stand in for that.
- **Sides:** fade and follow of the same signal are both in the family, so a pass in either direction counts once in
  the reality check.
- **Clustering:** the thresholds adapt weekly, so a volatile week has as many signals as a quiet one. An absolute
  threshold is not tested.
- **Not tested:** the 1-10 s tape horizons (M264), absorption at prior levels (M306's "at M305's levels"), other
  coins, and maker entries.

## Stop rules
- No new rule, threshold, hold, coin, cost or window after seeing results. A changed idea is a new lane with a new id.
- A NULL closes these 57 rules on 1-minute Binance bars at Lighter's cost. A crash before any statistic is recorded as
  ABANDONED with 0 trials, and the rerun gets a new id.
