# FINDINGS: clockflow_v1 (R289). The US-open flush does not reverse out of sample, and the Friday settlement fade is too small to clear the test

**Verdict: NULL (40 trials, gate 0).**
- **OPEN (M301):** reality check p = 0.31 (best studentized discovery stat 1.80, null 95th percentile 2.66). The
  variant picked on discovery loses in validation (t −0.48).
- **SETTLE (M303):** reality check p = 0.87 (best stat 0.82, null 95th percentile 2.58). The picked variant stays
  positive in validation (t 1.37) and in both halves, but it is far from the bar and about 0.4 bp a day at 2x.

- **Registry row:** R289 (trials: 40; program trials after it: 9,478,495).
- **Reproduce:**
  - prereg sha 2cd79fe5, frozen before the first statistic. The inputs block holds the sha256 of the three 1-minute
    kline files, the three funding files, `lab/sessions.py` and `lab/stats.py`; the runner checks them before
    reading.
  - Run `python scripts/run_clockflow.py`. It takes about 3 minutes, and its log is in `run.log`.
  - Tests: `tests/test_clockflow.py`. They check the price convention (no carry-forward), the σ warm-up, a trade's
    entry one minute late and its funding inside the hold, the clocks across daylight saving, NYSE holidays and the
    last Friday, the input hash check, and that a planted open reversal is booked by the fade and lost by the follow.

## What was tested
Two clock ideas from `docs/TRADER_TALKS.md`, on Binance BTC, ETH and SOL perps, 1-minute bars (new to the lab):
- **OPEN (M301), 24 variants.** A French prop-room founder says his room buys the flush at the US cash open every
  day. On NYSE days, the move m over the first w minutes after 09:30 New York, scaled by its own 60-day σ. Trade when
  |m| ≥ kσ, fade or follow, enter one minute after the window and hold h minutes. w ∈ {5, 15, 30}, k ∈ {1, 2},
  h ∈ {60, 120}.
- **SETTLE (M303), 16 variants.** From the SEBI order against Jane Street: a thin market pushed before an expiry. The
  move from 07:30 to 08:00 UTC on Fridays (Deribit's settlement TWAP window), weekly or last Friday of the month,
  k ∈ {0, 1}, fade or follow, h ∈ {60, 120}.
- **Book:** each coin is a third of capital; days without trades count as 0. Cost is manual web on MEXC, 3/6/9 bp
  per side at 1x/2x/3x; the API cost (8.5 bp) is reported. Discovery is 2021-04 to 2023; validation is 2024-01 to
  2026-09, and its second half is the spent holdout.

## Numbers
bp per calendar day on the whole book (one coin's trade is a third of it); gross is per coin trade. Full table in
`results/variants.csv`.

| Variant | Window | Trades | Hit | Gross bp/trade | Net 1x / 2x / 3x | API | NW t (1x) | Break-even bp/side |
|---|---|---|---|---|---|---|---|---|
| OPEN w15 k2 fade h120 (j*) | discovery | 105 | 70% | +124.6 | +4.06 / +3.86 / +3.65 | +3.68 | 1.56 | 62.3 |
| | validation | 115 | 46% | −8.6 | −0.56 / −0.79 / −1.01 | −0.98 | −0.48 | — |
| OPEN w15 k1 fade h120 | discovery | 398 | 56% | +39.3 | +4.34 / +3.54 / +2.75 | +2.88 | 1.43 | 19.7 |
| | validation | 539 | 48% | −4.3 | −1.82 / −2.89 / −3.97 | −3.79 | −0.90 | — |
| SETTLE weekly k1 fade h120 (j*) | discovery | 122 | 62% | +19.3 | +0.55 / +0.30 / +0.06 | +0.10 | 0.82 | 9.7 |
| | validation | 136 | 59% | +20.5 | +0.65 / +0.38 / +0.11 | +0.16 | 1.37 | 10.3 |
| SETTLE weekly k0 fade h120 | discovery | 428 | 60% | +11.4 | +0.77 / −0.08 / −0.94 | −0.79 | 0.68 | 5.7 |
| | validation | 429 | 56% | +12.9 | +0.98 / +0.12 / −0.73 | −0.59 | 1.28 | 6.4 |
| SETTLE monthly k0 fade h120 | discovery | 98 | 70% | −0.1 | −0.20 / −0.39 / −0.59 | −0.56 | −0.26 | — |
| | validation | 99 | 67% | +27.8 | +0.72 / +0.52 / +0.32 | +0.35 | 1.88 | 13.9 |

**OPEN j*:**
- **By year at 1x:** 2021 +1.39, 2022 +8.92, 2023 +1.12, 2024 +0.19, 2025 +1.09, 2026 −3.77 bp a day.
- **Validation halves:** +0.46 and −1.77. The five best days are 87% of the summed net.
- **Gross per trade by coin (both windows):** BTC +24.5, ETH +34.9, SOL +104.6 bp.
- **Across the family:** every w15 fade was positive in discovery (t 1.4-1.7) and every w15 follow negative (t down
  to −2.2). In validation all of it is gone: the w15 fades are −0.5 to −1.8 bp a day. The discovery edge was 2022,
  and mostly SOL.

**SETTLE j*:**
- **By year at 1x:** 2021 −0.10, 2022 +0.72, 2023 +1.47, 2024 +1.17, 2025 +0.45, 2026 +0.24 bp a day.
- **Validation halves:** +0.84 and +0.43. The five best days are 72% of the summed net.
- **Gross per trade by coin (both windows):** BTC +17.5, ETH +24.6, SOL +24.1 bp.
- **Across the family:** all four weekly fades are positive in both windows (gross +5 to +20 bp per trade, hit
  56-65%), and all four weekly follows negative. The monthly fades are flat in discovery and positive in validation.

## Cost sensitivity
- **OPEN:** j* loses at 1x, 2x, 3x and the API cost in validation. The best OPEN validation t is 0.74.
- **SETTLE j*:** +0.65 / +0.38 / +0.11 bp a day at 1x / 2x / 3x, +0.16 at the API cost. Its break-even is about
  10 bp per side in both windows, so it survives manual web costs, but it trades on about one Friday in three per
  coin and earns about 2.4% a year at 1x on the whole book. The k0 version trades every Friday and does not survive
  2x.
- **Read against the program:** 9,478,495 trials. Even before multiplicity, neither j* reaches the frozen t of 2.

## Placebo clocks (reported, not decided on; seen after the run)
- **SETTLE on Mondays to Thursdays:** the fade is +2 to +4 bp gross per trade in discovery and −2 to −10 in
  validation. The Friday reversal is larger than on other days, which fits an expiry effect, but the Friday edge
  itself is not significant.
- **OPEN at 10:30 New York:** the fade loses in both windows (gross −5 to −38 bp per trade; w30 k1 h120 t −2.06 and
  −2.00). Moves in the hour after 10:30 continue rather than reverse.
- **OPEN at 09:30 New York on weekends and NYSE holidays:** the fade wins in both windows (for example w30 k1 h60:
  gross +20.7 / +22.7 bp per trade, validation t 2.67). This is the opposite of what the trader's story predicts:
  the reversal is cleaner when the US cash market is shut.
- These are 56 placebo variants, looked at after the run. They are seeds for a new lane at most, and only on reserved
  2020 bars or forward data.

## What this does show
- **The US-open flush and reversal (M301) does not transfer to crypto perps.** The fade looked good in 2022 on SOL,
  then disappeared. A trader's "on le prend tout le temps" on index futures is not a crypto edge.
- **Price moves inside Deribit's settlement window tend to reverse after 08:00 on Fridays,** by about 15-20 bp per
  trade at k = 1, in both windows and in all three coins. It is too small and too rare to pass a 40-trial reality
  check: the annual Sharpe on the book is 0.5 in discovery and 0.7 in validation.
- **Continuation after 10:30 New York:** the placebo fade has t near −2 in both windows. It was not a frozen trial.

## What this does not show
- **Prices are Binance's.** MEXC's 1-minute history is not held. Fills are at a 1-minute close; a hand-placed order
  at 08:01 UTC or 09:46 New York can be seconds off, and the spread at the open can be wider.
- **Deribit's own index and expiry calendar** (holiday moves) were not used.
- **The 2020 1-minute bars stayed unread.** They are reserved for a frozen batch.

## Next
- **M301 stops here.** The OPEN family does not go to a reserved batch.
- **M303 (SETTLE weekly k1 fade h120) does not earn a batch slot by its frozen rule.** If a later lane takes the
  settlement window up again, it should be one pre-registered variant, read on the reserved 2020 bars and on forward
  Fridays, with Deribit's index and with options open interest as a dose variable. That would be a new id.
- **The two placebo patterns** (closed-market open fade, continuation after 10:30) go to `docs/DIRECTION.md` as
  seeds, not results.
