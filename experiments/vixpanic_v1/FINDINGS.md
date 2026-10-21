# FINDINGS: vixpanic_v1 (R283). The VIX-panic signal leans the way the video says on US indices, but no cell clears the multiple-test bar

**Verdict: NULL (27 trials, gate 0).** No cell reaches p ≤ 0.05/27 = 0.00185 against random dates.

**The claim's own row (BOTH: VIX above VIX3M and VVIX in its top 5% on the same close) is the strongest on SPY and
QQQ at 5 and 10 days:**
- p 0.005-0.02;
- +84 to +158 bp over the average hold;
- 67-80% of onsets positive;
- positive in both halves (2009-17 and 2018-26) and without the best onset.

Six of the 27 p-values are at or below 0.05, against 1.35 expected under the null. But the cells are not independent:
SPY and QQQ move together, and the 5-, 10- and 20-day holds share their first days. So this is a lean, not evidence.

**On BTC** the sample is small (10-16 onsets in 2021-26). The means are large and noisy: the median is often below the
mean, and the worst onset is −11% to −34%.

**The video's own day did not trigger.** On closing values, 2026-10-16 had:
- VIX 19.99 below VIX3M 20.50, so no backwardation;
- VVIX 109.91 below its one-year 95th percentile of 123.4.

The "VVIX 120" and the backwardation in the video were intraday and VX-futures readings. Cash closes did not show
them.

**Reproduce**
- prereg sha 367c721d, frozen before the first statistic.
- Run `python scripts/run_vixpanic.py`. It takes about 10 s, and its log is in `run.log`.
- Input sha256s are in `results/summary.json`: three Cboe files, two Yahoo files and the BTCUSDT klines and funding.
- `results/cells.csv` has one row per cell. `results/onsets.csv` has one row per onset trade.
- Tests: `tests/test_vixpanic.py` covers onsets, triggers, the next-open entry and BTC funding, on synthetic data.

## The 27 cells
Costs per round trip are 2 bp at 1x for the ETFs and 14 bp for BTC; BTC is also net of funding. "Excess" is the
onset mean minus the mean of every eligible day's hold. The pass bar is p ≤ 0.00185.

| Trigger | Asset | h | n | Net bp 1x / 2x / 3x | Excess bp | Hit | Without best | 2009-17 / 2018-26 bp | p |
|---|---|---|---|---|---|---|---|---|---|
| BOTH | SPY | 5 | 30 | 107 / 105 / 103 | +84 | 0.67 | 91 | 75 / 148 | 0.012 |
| BOTH | SPY | 10 | 30 | 157 / 155 / 153 | +104 | 0.80 | 135 | 101 / 225 | 0.020 |
| BOTH | SPY | 20 | 30 | 122 / 120 / 118 | +11 | 0.70 | 93 | 172 / 69 | 0.45 |
| BOTH | QQQ | 5 | 30 | 139 / 137 / 135 | +107 | 0.70 | 104 | 81 / 209 | 0.009 |
| BOTH | QQQ | 10 | 30 | 228 / 226 / 224 | +158 | 0.80 | 197 | 161 / 309 | **0.005** |
| BOTH | QQQ | 20 | 30 | 148 / 146 / 144 | +1 | 0.67 | 112 | 225 / 64 | 0.50 |
| BOTH | BTC | 5 | 10 | 117 / 103 / 89 | +92 | 0.60 | −69 | – / 131 | 0.35 |
| BOTH | BTC | 10 | 10 | 566 / 552 / 538 | +503 | 0.50 | 176 | – / 580 | 0.078 |
| BOTH | BTC | 20 | 10 | 148 / 134 / 120 | +1 | 0.30 | −374 | – / 162 | 0.49 |
| BACKW | SPY | 10 | 42 | 128 / 126 / 124 | +76 | 0.71 | 113 | 129 / 131 | 0.040 |
| BACKW | QQQ | 10 | 42 | 155 / 153 / 151 | +85 | 0.74 | 132 | 142 / 174 | 0.059 |
| VVIX95 | SPY | 5 | 40 | 75 / 73 / 71 | +52 | 0.68 | 63 | 64 / 91 | 0.053 |
| VVIX95 | BTC | 10 | 16 | 494 / 480 / 466 | +432 | 0.50 | 262 | – / 508 | 0.063 |
| VVIX95 | BTC | 20 | 16 | 875 / 861 / 847 | +728 | 0.44 | 617 | – / 889 | 0.037 |

The other 13 cells have p from 0.08 to 0.68 (`results/cells.csv`). They include BACKW on BTC, which is negative at 5
and 20 days.

## Reading
- **US indices: what the video describes, measured honestly.**
  - The 30 BOTH onsets since 2009 include 2010-04, 2011-07, 2015-08, 2018-02, 2020-01, 2022-01, 2024-08 and 2025-03.
  - Five to ten days later, SPY and QQQ had usually bounced: in 67-80% of onsets, and by about 1-2% more than an
    average week or two.
  - At 20 days the excess is gone. It is a short bounce, not a trend change.
- **It is not enough to act on.**
  - The best cell is p 0.005 among 27 correlated cells and does not clear the bar.
  - The years were read before in other forms. R239's VIX-reversal rule passed its discovery here and then failed out of
    sample (R241).
  - There is no unread equity sample to confirm it on, and new onsets come about twice a year.
- **BTC.**
  - Too few onsets to say anything. VVIX95 at 20 days has p 0.037 with a mean of +8.8%, but its median is −0.8% and
    its hit rate is 44%: five rebounds of +22% to +50% (2021-01, 2021-07, 2021-09, 2023-03, 2023-10) carry it.
  - BACKW alone is flat to negative on BTC.
- **Against the program:** 27 trials on top of 9,478,385 (`registry.program_trials()`). Even the best cell here is
  ordinary for a search of this size.

## What happens next
- **No forward lane** (no pass, per the PREREG).
- **The rule stays recorded so nobody re-mines it.** If a future lane wants BOTH-SPY/QQQ at 5-10 days, it needs a new
  id and forward onsets only. Those come about twice a year, so expect a long wait.
- **BTC rows of 2020 are reserved.** One BOTH onset (2020-01-27) and the March 2020 VVIX spike fall there. With about 2
  onsets the 2020 sample cannot test this, so it is not proposed for the batch.
- `docs/VIDEO_DIG.md` and methods row M278 are updated with this result.
