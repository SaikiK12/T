# FINDINGS: level_probability_v2 (R333), the owner's break-or-rebound model at scale

**Answer: NULL at the lab's API cost, by the frozen decision. 4 of the 5 checks fail on the primary V0P1:**

| Check | Result | Pass? |
|---|---|---|
| 1x t ≥ 2 | +0.19 bp/day, t 0.05 | no |
| 2x mean > 0 | −17.8 bp/day | no |
| 1x without the best 10 days > 0 | −3.2 bp/day | no |
| Both halves > 0 | first half −7.4 (t −1.6), second +5.7 (t 1.0) | no |
| Log loss beats climatology, t ≤ −2 | t −3.46 | yes |

The model's probabilities do beat the base rates, so the passing check is real. The gain is small, though: log loss
1.0129 against 1.0150, and Brier 0.6034 against 0.6073 (t −5.36).

**Measured, not decided: the edge is real before costs, and costs take all of it.**
- **Gross:** V0P1 earns +18.1 bp/day (t 4.84), or +29.7 bp per trade.
- **The lab's API cost** averages about 9 bp a side here (6/8/12/20 bp by rank tier), a round trip of about 18 bp.
- **At 1 bp a side** (a 0/0-fee contract with a one-tick spread):
  - V0P1 earns +16.1 bp/day (t 4.30), and +12.7 without its best 10 days;
  - with R330's one-hour entry delay (V1P1), +15.6 bp/day (t 4.21).
- **Break-even:** about 9 bp a side on the day-weighted series, and 14.8 bp on the trade-weighted mean.

**Lane details**
- **Registry row:** R333, 11 trials.
- **PREREG:** sha256 `6dcea126…aa5a`, frozen and pushed in `ac077d2` before the run. All 17 inputs and the data digest
  `0374bd1c…` matched.
- **Run:** 2026-10-26, 20:40-21:10 UTC, on scikit-learn 1.9.1, numpy 2.5.3 and pandas 3.0.5.
- **Reproduce:** `python scripts/run_levels_v2.py --run` writes `results/summary.json` and
  `results/v0_oos_events.csv.gz` (every V0 out-of-sample event with its probabilities). The run log is `run.log`.
- **Gate 0, on seen hours:** the walk-forward test blocks run 2022-01..2026-09, each fit only on events that ended at
  least 24 h before its quarter.

## Books at the lab's cost (bp per day; t in brackets)
Day-weighted means: each calendar day's mean per trade, Newey-West t with lag 3.

| Book | Trades | 1x | 2x | 3x | 1x per trade | 1x without best 10 days | Breakout share |
|---|---|---|---|---|---|---|---|
| **V0P1** (primary) | 79,755 | **+0.19 (0.05)** | −17.76 (−4.74) | −35.71 (−9.54) | +11.52 | −3.24 | 66% |
| V0P2 | 9,799 | −9.25 (−0.59) | −26.68 (−1.71) | −44.12 (−2.82) | +46.74 | −31.03 | 70% |
| V0P3 | 11,693 | +0.15 (0.01) | −18.50 (−1.85) | −37.15 (−3.71) | +33.97 | −10.45 | 74% |
| V0P0 (decides at 1 bp) | 163,944 | −5.42 (−2.02) | −24.66 (−9.17) | −43.90 (−16.32) | −1.15 | −8.27 | 60% |
| V1P1 (1 h delay) | 73,915 | −0.34 (−0.09) | −18.30 (−4.93) | −36.26 (−9.78) | +10.71 | −3.89 | 64% |
| V2P1 (24 h levels) | 98,644 | −0.82 (−0.26) | −18.36 (−5.80) | −35.89 (−11.34) | +3.13 | −3.48 | 59% |
| V3P1 (168 h levels) | 57,386 | −2.68 (−0.60) | −20.97 (−4.71) | −39.26 (−8.82) | +13.35 | −6.66 | 64% |
| V4P1 (24 h horizon) | 85,421 | −1.19 (−0.28) | −19.62 (−4.56) | −38.06 (−8.84) | +10.28 | −5.29 | 65% |
| CLIM (base rates) | 6,299 | −10.27 (−0.54) | −25.18 (−1.32) | −40.08 (−2.09) | +39.71 | −29.35 | |
| THROUGH (always break) | 177,860 | −36.49 (−10.93) | −55.73 | −74.98 | −10.68 | −40.11 | 100% |
| AWAY (always fade) | 177,860 | −2.00 (−0.60) | −21.25 | −40.50 | −27.79 | −5.49 | 0% |

**Random sides.** Giving V0P1's own trades random sides loses −18.15 bp per trade at 1x (the round trip). V0P1 itself
earns +11.52. None of 1,000 draws matched it, so the direction choice is not luck.

**V0P1 by year, 1x, bp per trade:**

| 2022 | 2023 | 2024 | 2025 | 2026 (to Sep) |
|---|---|---|---|---|
| +13.0 | −5.1 | +27.9 | +10.8 | +7.3 |

## Measured lines: gross, 1 bp a side, break-even
| Book | Gross bp/day (t) | At 1 bp a side, bp/day (t) | Without best 10 | Gross per trade | Break-even, bp a side |
|---|---|---|---|---|---|
| V0P1 | +18.13 (4.84) | +16.13 (4.30) | +12.71 | +29.65 | 14.8 |
| V0P0 | +13.82 (5.14) | +11.82 (4.40) | +8.97 | +18.08 | 9.0 |
| V1P1 | +17.62 (4.75) | +15.62 (4.21) | +12.07 | +28.87 | 14.4 |
| V2P1 | +16.71 (5.27) | +14.71 (4.64) | +12.05 | +20.95 | 10.5 |
| V3P1 | +15.61 (3.51) | +13.61 (3.06) | +9.62 | +31.77 | 15.9 |
| V4P1 | +17.25 (4.01) | +15.25 (3.54) | +11.15 | +28.80 | 14.4 |
| AWAY | +17.24 (5.17) | +15.24 (4.57) | +11.76 | −8.56 | −4.3 |
| THROUGH | −17.24 (−5.17) | −19.24 | −22.86 | +8.56 | 4.3 |

Break-even is half the mean gross per trade. On the day-weighted series it is about half the gross per day: about 9 bp
for V0P1.

**What the controls show**
- **Fading a level** (AWAY) earns about as much per day as the model (+17.2 gross), but loses per trade (−8.6).
  - Fades work on quiet days.
  - They lose on busy trend days, when most events happen and coins break out together.
- **The model's addition** is to go the breakout way on those busy days: 66% of its trades. It earns +29.7 gross per
  trade, against −8.6 for always fading and +8.6 for always breaking.

## Weighting caveat
- **Day-weighted (the frozen bp/day):** this is a statistical summary, not a sizing anyone could trade. Splitting each
  day's capital across that day's trades would need the day's trade count in advance.
- **Trade-weighted:** a book with a constant size per trade earns the trade-weighted mean. For V0P1 that is +11.5 bp at
  1x and +27.7 at 1 bp a side.
- **Not computed:** a t-stat on that book's daily sums, which are clustered on busy days. The frozen outputs do not have
  it, and computing it now would be a new, unregistered statistic.

## Reading
- **Trials:** the program goes from 9,478,982 to 9,478,993 trials with R333's 11.
- **At the lab's API costs** the idea does not pay, in any variant, at any cost level.
- **There is something real in "break or rebound at a level":**
  - the probabilities beat the base rates;
  - the direction beats random sides;
  - before costs it earns, on every variant and every level horizon.
- **Why it does not pay:**
  - the edge per trade (about 15 bp a side at break-even, 9 on the day-weighted series) is smaller than a normal API
    round trip;
  - it needs about 46 trades a day, so API execution only, beyond the owner's manual limit of about 15 orders a day.
- **This matches R306**, where plain level rules earned +7 to +9 bp gross per trade, below the 14.4 bp round trip.

## Not tested here
- **A near-zero-cost API venue.** Lighter Standard is about 2 bp a side, with a 300 ms taker delay. MEXC's 0/0
  contracts are about 1 bp a side, but their fee group changes from day to day. Both list different coins from
  Binance's top 100.
- **The fill.** Fills at the hourly close, on V0, and no slippage beyond half the spread.
- **The constant-size book's t-stat** described above.

## Next
No follow-up lane has been started.

The only test that could promote this would be a frozen forward paper lane on a zero-fee API venue:
- V1P1, with its one-hour delay;
- a constant size per trade;
- the daily-sum series pre-registered.

That needs the owner's go, and an API route the owner does not have today.
