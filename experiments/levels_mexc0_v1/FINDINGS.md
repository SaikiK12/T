# FINDINGS: levels_mexc0_v1 (R336), R333's level model on MEXC's zero-fee perps

**Answer: PARTIAL (gate 0). All five frozen checks pass.** R333's break-or-rebound trades still pay on MEXC's zero-fee
perps after the measured spread, through 2x costs. They lose their significance at 3x.

| Check, primary book PZ_SUM | Result | Pass? |
|---|---|---|
| 1x t ≥ 2 | +147.8 bp/day, t 2.85 | yes |
| 2x mean > 0 | +109.5 bp/day (t 2.11) | yes |
| 1x without the best 10 days > 0 | +85.5 bp/day | yes |
| Both halves > 0 at 1x | 2022-23 +59.8, 2024-26 +211.8 | yes |
| 1x without the best coin (APT, 15.5% of the net) > 0 | +124.9 bp/day | yes |

- **bp per day:** the constant-size book. It is each day's summed net, in bp of one trade's notional.
- **Per trade, net at 1x:** +16.7 bp, from 15,327 trades on 55 coins, about 9 a day. Gross is +21.1 bp; break-even is
  10.5 bp a side.
- **Direction:** random sides on the same trades lose −4.6 bp a trade. None of 1,000 draws matched the model.

**Read it with the THROUGH control.**
- On these coins, always trading the breakout earns about as much per trade as the model: +17.6 bp at 1x, t 3.05 on
  the day sums.
- THROUGH fails the halves, though. All its gain is in 2025-26, when new small coins trended, and it lost money in
  2023-24.
- The model's book is positive in four of five years.
- So the model adds steadiness here, not a higher average.

**Lane details**
- **Registry row:** R336, 6 trials. PREREG sha256 `21fdff08…87c`, frozen and pushed in `ae2d658` before the run, and
  claimed on #7 (comment 6427816692).
- **Run:** 2026-10-26 21:35 UTC. All 46 inputs matched their frozen hashes.
- **Reproduce:** `python scripts/run_levels_mexc0.py --run` writes `results/summary.json`. The run log is `run.log`.
- **Gate 0.** R333 read these hours and fit this model. This lane only re-prices and re-filters R333's saved V0
  out-of-sample trades (2022-01..2026-09).

## The books (bp per day of one trade's notional; t in brackets)
| Book | Trades | Per day (median) | Gross | 1x | 2x | 3x | 1x per trade | Break-even, bp a side |
|---|---|---|---|---|---|---|---|---|
| **PZ_SUM** (primary) | 15,327 | 8.8 (7) | +186.1 (3.58) | **+147.8 (2.85)** | +109.5 (2.11) | +71.2 (1.38) | +16.7 | 10.5 |
| PZ_CAP7 (manual, first 7 a day) | 9,617 | 5.5 (7) | +101.4 (2.64) | +77.6 (2.02) | +53.8 (1.40) | +30.0 (0.78) | +14.0 | 9.1 |
| P1_TRADES (stricter threshold) | 9,071 | 5.2 (4) | +183.3 (4.09) | +146.8 (3.29) | +110.4 (2.48) | +74.0 (1.66) | +28.1 | 17.5 |
| THROUGH (always the breakout) | 19,405 | 11.2 (9) | +279.5 (4.30) | +196.5 (3.05) | | | +17.6 | |
| AWAY (always the rebound) | 19,405 | 11.2 (9) | −279.5 (−4.30) | −362.6 (−5.52) | | | −32.4 | |

PZ_MEAN, PZ's trades on R333's day-mean convention, gives +12.8 bp/day at 1x (t 2.37), +8.5 at 2x (t 1.57) and +4.2
at 3x.

**Per trade by year, 1x (bp):**

| Book | 2022 | 2023 | 2024 | 2025 | 2026 (to Sep) |
|---|---|---|---|---|---|
| PZ_SUM | +21.4 | −0.6 | +22.5 | +13.9 | +18.8 |
| PZ_CAP7 | +21.9 | +0.5 | +16.3 | +31.4 | −5.3 |
| P1_TRADES | +12.1 | +6.6 | +33.6 | +23.0 | +44.4 |
| THROUGH | +5.4 | −6.6 | −0.3 | +21.5 | +40.7 |

**Coins.**
- 39 of the 55 coins are positive at 1x.
- The largest shares of the net: APT 15.5% (1,328 trades, +30.0 bp), AVAX 9.8%, JASMY 9.5% and ORDI 7.2%.
- Several 2025 listings contributed few trades with large per-trade results: LYN (59 trades, +363 bp), BLESS, POWER,
  EVAA and RIVER.
- The worst: BR (77 trades, −272 bp), BSB, KAITO, JTO and ESPORTS.

## Risk, for sizing a futures account
- **One trade is volatile.** These coins move 2-10% within the 12-hour hold. Net per trade at 1x:

  | 1% | 5% | 25% | 50% | 75% | 95% | 99% |
  |---|---|---|---|---|---|---|
  | −18.7% | −8.7% | −2.9% | +0.1% | +3.2% | +8.9% | +20.5% |

- **Leverage:** a 5x position would lose about 94% of its margin on the 1% trade. Sizing has to keep leverage low.
- **The book** (PZ_SUM at 1x, in units of one trade's notional):
  - max drawdown 4.2, worst day −1.6;
  - at most 20 trades open at once, and 9 or fewer 95% of the time.
- **Example:** with each trade at 1/20 of the account and no leverage, the history averages about 7 bp of the account a
  day, with a drawdown near 21%. This is arithmetic on seen data, not a forecast.

## Reading
- **Trials:** the program goes from 9,478,993 to 9,478,999 trials with R336's 6. Against that count, a t of 2.85 on
  seen hours is a reason to test forward, not evidence of an edge.
- **What changed from R333:** only the cost. R333 charged 6-12 bp a side; here the median MEXC half-spread is 0.4-3.5
  bp on most of these coins, with a 1 bp floor. The same model's trades move from NULL to positive.
- **The coin selection leans on the present.**
  - The zero-fee list is October 2026's, and it includes many 2025 listings that trended hard. That is why THROUGH looks
    strong here. On R333's whole top 100 it lost 17.2 bp/day gross, on R333's day-mean convention.
  - The model is the steadier book across years. Its advantage over the naive breakout is not shown in the average.
- **Manual execution** (PZ_CAP7, 7 trades a day) keeps about half the result. It is t 2.02 at 1x and not significant
  at 2x, and 2026 is negative. The full book needs about 9 trades a day, up to 36, placed right at the hourly close:
  that is API execution.

## Not tested here
- **MEXC prices:** g is Binance closes and Binance funding. MEXC's perps on thin coins can lag or gap.
- **The fill:** orders at the hourly close; barriers read on closes; no queue, latency or depth at the owner's size.
  2x and 3x stand in for these.
- **Fee persistence:** MEXC's zero-fee groups change daily, with 98 to 150 zero-fee contracts per snapshot. A live
  system must check the fee at each order.
- **Spreads before October 2026:** not measured.

## Next (what a PARTIAL earns)
A **frozen forward paper lane on MEXC's zero-fee perps**, with a new id, frozen before its first forward day.
- **Model:** R333's model, refit once on all events that ended before the freeze, then frozen with its sha.
- **Each hour:** live Binance features; the MEXC fee and quote checked at each signal; tickets frozen before entry;
  exits at ± sigma12 or after 12 h, priced on MEXC.
- **Books:** PZ as the primary, with THROUGH and AWAY recorded beside it as controls, so the breakout question is
  answered forward.
- **No orders.** A real trade needs paper to show a net gain first, then `lab.gate.go_real()`, small stakes, and the
  owner placing it.
