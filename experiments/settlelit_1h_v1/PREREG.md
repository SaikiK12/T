# PREREG: settlelit_1h_v1 (R387). R363's Lighter settlement scalp on Binance's 1-hour-interval settlements

Freeze with `lab.prereg.freeze()` before the scored run. Never edited afterwards; a change is a new lane.

- **Registry id:** R387
- **Claim:** Claude block R380-R389, claimed on issue #7 on 2026-11-02.
- **Method:** M460, the M267 family (settlement-window trade), Lighter route.
- **Gate:** 0 (archive). No forward evidence comes from this lane.

## Why
- **R363's result.** It found a Lighter position against the side that received a deep Binance funding lump.
  - The position is entered at the last trade before T and covered at the last trade before T + 1 min.
  - It made +23.4 / +19.6 / +15.8 bp a hop at 1x / 2x / 3x, CR1 t 4.34, on 134 hops.
  - It was not blind: R362 had read those hops' Binance seconds.
- **The unread population.** R363's hops were R354's, and R354 keeps only Binance settlements whose interval is 4 h or
  8 h. R353 kept gaps of 4-24 h. R356 and R362 decided R354's hops. So no settlement lane has read a Binance settlement
  that follows the previous one by 1 hour.
- **The new rule makes such settlements common.**
  - Since 2025-05-02 08:00 UTC, Binance moves a perp to hourly settlement after a print at its cap or floor (web-deep
    source SRC1103-010, verifier-confirmed).
  - The archive holds 292 switches to 1 h on 214 symbols, 220 of them at a cap or floor print.
- **The question:** does the capture crowd's exit after a deep lump also happen when the lump comes every hour?
  - The position pays Lighter's own hourly settlement at T, and on these coins Lighter's rate can be deep too: its big
    clamp is 0.5%/h.
  - Lighter charges no fee.

## Events (selected from Binance rates and the existence of a Lighter settlement at T, never its value)
- **Coins:** every Binance perp in R353's symbol table (`experiments/settlehop_v1/symbols.csv`) with a Lighter symbol, a
  Lighter market id (`data/lighter_hist/contracts.csv`) and a Lighter funding file.
- **Binance settlements:**
  - From `data/fundingRate/<coin>.parquet`, stamps rounded to the nearest hour.
  - Read with a filter that loads only rows stamped from 2024-12-31 22:00 UTC (T0 − 2 h) to before 2026-10-01. No 2020
    row is read.
- **A hop at T** needs all of:
  - the previous Binance settlement is exactly at T − 1 h;
  - T ≥ 2025-01-01 and T + 1 h < 2026-10-01;
  - the previous settled rate r_prev (settled at T − 1 h, known an hour before T) has |r_prev| ≥ 0.3%;
  - Lighter has a settlement stamped at T.
- **Direction:** d = sign(r_prev).
  - r_prev < 0 means Binance's longs received at T − 1 h, so the position is short on Lighter (d = −1), as in R363's
    convention.
  - Binance's own rate at T is reported (sign persistence), never used to select.
- **Cost a side:** R353's Lighter volume band (`run_settlehop.lighter_cost_bp`) of the coin's Lighter quote volume over
  the 24 hourly bars opening in [T − 25 h, T − 2 h].
- **Count (plumbing, before this freeze):**
  - 222 hops on 9 coins at 222 settlement times, in 30 coin-days, 2025-10..2026-09.
  - Per coin: RIVER 65, 0G 61, SKR 43, AZTEC 22, ZK 16, PIPPIN 7, BIRB 4, STABLE 3, PROVE 1.
  - Band costs a side: 1.09 bp (145 hops), 0.51 (56), 4.17 (19), 26.67 (2).

## Rule (R363's, unchanged: `scripts/run_settlelit.py` `trade`, `net`)
- **Position:** d on Lighter's perp.
- **Entry:** the close of the last traded Lighter minute bar opening at or before T − j − 1 min, for j in {0, 5}. No
  traded bar in [T − 10 min, T − j − 1 min] means no trade.
- **Exit:** the close of the last traded bar opening at or before T + x − 1 min, for x in {1, 2, 5}.
- **Funding:** the position takes Lighter's settlement at T, −d × rate(T).
- **Net:** price + funding − 2 × m × cost a side, for m = 1, 2, 3.
- **Trials:** 6 (j × x). **Primary:** j = 0, x = 1.

## Decision (primary trial, all hops)
PASS needs all seven:

| # | Check | Bar |
|---|---|---|
| 1 | CR1 t of the 1x net, clustered by coin and UTC day | ≥ 2.0 |
| 2 | 2x mean net | > 0 |
| 3 | 3x mean net | > 0 |
| 4 | 1x mean net in each half of the calendar | > 0 |
| 5 | 1x mean net without the best coin | > 0 |
| 6 | GATES' trimmed mean of the 1x net (10 each side) | > 0 |
| 7 | GATES' leave-two-coins-out mean of the 1x net | > 0 |

Otherwise NULL.

**Deviations from R363, all stated here before the run:**
- **Clustering by coin-day, not settlement time.** Consecutive hourly hops of one coin are not independent, and here
  every hop has its own T. The settlement-time t is reported.
- **Checks 3 and 7 are added.** R364's PREREG measured $1k Lighter round trips far above the band cost (RIVER 61 bp),
  and the events are concentrated in three coins.
- **The trigger is r_prev, not R354's predicted rate.** With a 1 h interval, nothing of the current interval is known
  an hour before T.

## Reported, not decided on
- The other five trials.
- 1x/2x/3x for each trial; the settlement-time CR1 t; hit rates; the median.
- Per-coin hops, price, funding, cost and net.
- Sign persistence: the share of hops where Binance's rate at T has the sign of r_prev.
- **The primary 1x net with RIVER at R364's measured 61 bp round trip** instead of its band cost (other coins at
  band).
- Stale entries and exits.

## Power
- **Effective sample:** 30 coin-days.
- **At R363's spread** (SD 63 bp a hop), with hops inside a coin-day partly dependent, the standard error of the mean
  is roughly 10-16 bp.
- **At R363's +23.4 bp,** the t is then about 1.5-2.3. A PASS is far from certain even if the effect carries over.
- **A NULL here** does not refute R363 on 4 h and 8 h lumps. It says the hourly-cycle population, as small as it is,
  did not show it net of Lighter's own settlement.

## What the author has seen before this freeze
- R353-R364 in full (PREREGs, FINDINGS, R364's measured costs).
- The web-deep archive counts: switch counts and trigger rates only.
- This lane's counts above.
- **One disclosure.** An earlier counting script loaded whole Binance funding files, 2020 rows included, into memory
  before filtering to T ≥ 2025-01-01.
  - The only 2020-derived output it printed was BTCUSDT's first timestamp.
  - No 2020 rate entered any number.
  - The frozen runner filters on load.
- **Not read:**
  - any Lighter minute price in `data/settlelit1h_1m`;
  - any Lighter funding value at these T;
  - any Binance price around these settlements;
  - Binance's rate at T as a statistic.

## What a PASS earns
- A frozen forward paper lane (new id) on live Binance hourly-cycle settlements, with R364's live cost gate.
- Gate 0 alone moves no money.

## Code and inputs
- Runner: `python -I scripts/run_settlelit_1h.py`. It verifies this PREREG and every input below, each data file in
  `data_files.csv`, and each minute file against `docs/provenance/settlelit1h_1m.json`.
- Minute windows: `data/settlelit1h_1m/lighter/<symbol>/<T ms>.parquet`.
  - 222 files, Lighter 1-minute bars opening in [T − 10 min, T + 10 min).
  - Fetched 2026-11-03 through `lab.carrylane`'s shared Lighter limit, counts only.

```inputs
0d088dd2b4cf9a8ba7434a5741cc84b3f3b00105487bee6caf8b7f349a4a3544  scripts/run_settlelit_1h.py
35e095fff0734c0ceabdb100a9e54a95cae9aba363c3fc94f949a988b2bdef11  scripts/run_settlelit.py
009145b050e50f4394499e318737fe4ef86a00ef21136fb327658d4072c86829  scripts/run_settlehop.py
f81769a74f97074ea32d44ee927bd342272672157cebe81be9d39f8c8cd47e44  scripts/run_settlehop_exit.py
bea20ba88c511261038f9e1e4fadca258cd37349ad9fc9f4b911f5feb4ca146c  scripts/settlehop_rule.py
ca7b6583d28ea9512d08a469f93a3e687b214a16dd7a0167d4a491a883c0ae35  scripts/fetch_settlelit_1m.py
aa34e5e4586bdc5f2adf4bb744cf1a6c78f6e72627565e950763465a2e4c94b3  experiments/settlehop_v1/symbols.csv
bd040f363ec869ffc6aeacd58f66bece070471b56b7fcf122269319a6df2e398  data/lighter_hist/contracts.csv
79b86d10a5bbf23aa0f8a1d677b0526ca2cbe9b4e8635b5df09af2119d016f7c  experiments/settlelit_1h_v1/data_files.csv
b9f59e8a2a2446214fb48def43de0e4078ad90aafe9589d098e188ffec940aa8  docs/provenance/settlelit1h_1m.json
```

## Multiplicity
- **Trials:** 6. The primary decides; the family is reported against Bonferroni over 6 (one-sided 5%: t 2.39).
- **Program trials before this lane:** 9,782,841 (`registry.program_trials('registry/rounds.csv')` on 2026-11-03).
