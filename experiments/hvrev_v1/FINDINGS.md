# FINDINGS: hvrev_v1 (R380). 8-10 week reversal inside the high-volatility tercile (M457)

**Verdict: NULL by the frozen rule.** The pick (highest discovery net 1x t among the 6 family books) is `L9w hv raw`. It made +12.0 bp/day in discovery (t 1.12) and **-58.6 bp/day in validation (t -2.37)**. It fails all three checks: t >= 2.0 (no), 2x mean > 0 (no, -60.5 bp/day), mean without the 10 best periods > 0 (no, -664 bp per week).

- **Registry row:** R380, trials 8 (6 family + 2 ungated controls). Program trials after it: 9,479,264.
- **Gate: 0, on seen data.** Every window was read by R238, R299, R304, R305 and R332 with other features.
- **Reproduce:** PREREG sha `37ad71b9aff84cfab4a204ceac84a6a09e1e7943dca646daf3e88c623d1db02d`, frozen before the run. `python scripts/run_hvrev.py` (about 30 s). Tests: `python -m unittest tests.test_run_hvrev` (5 pass, synthetic noise only).
- **Setup (as frozen):** weekly rebalance from 2022-01-01, hold 7 days, top-150 Binance perps, gate = top tercile by vol30 (about 45 names), long the 8/9/10-week losers and short the winners (top/bottom fifth, about 9 names a leg). Residualised books regress the rank on the ranks of vol30, mom7 and max7. API cost 8.5 / 17 / 25.5 bp per side on turnover, funding paid.

## Numbers: net bp/day at 1x / 2x / 3x (NW t at 1x in brackets)
Discovery 2022-01..2023-12 (102 weekly periods) and validation 2024-01..2026-09 (142 periods).

| Book | Discovery 1x | 2x | 3x | Validation 1x | 2x | 3x |
|---|---|---|---|---|---|---|
| L8w hv raw | +10.9 (0.94) | +9.0 | +7.1 | -66.1 (-2.61) | -68.0 | -69.9 |
| L8w hv resid | +6.7 (0.67) | +4.2 | +1.7 | -61.3 (-2.22) | -63.7 | -66.2 |
| **L9w hv raw (pick)** | **+12.0 (1.12)** | **+10.1** | **+8.2** | **-58.6 (-2.37)** | **-60.5** | **-62.4** |
| L9w hv resid | +9.9 (1.07) | +7.4 | +4.9 | -71.3 (-2.60) | -73.8 | -76.2 |
| L10w hv raw | +4.0 (0.36) | +2.1 | +0.3 | -52.2 (-2.21) | -54.1 | -56.1 |
| L10w hv resid | +10.1 (1.05) | +7.6 | +5.2 | -61.3 (-2.29) | -63.7 | -66.1 |
| L9w all raw (control) | +9.0 (1.33) | +7.6 | +6.1 | -30.7 (-2.66) | -32.2 | -33.7 |
| L9w all resid (control) | +1.6 (0.26) | -0.3 | -2.2 | -33.5 (-3.34) | -35.5 | -37.5 |

Costs are small next to the result: turnover is 1.5-2.1 per week, so 1x costs 2-3 bp/day and each extra multiple adds about 2 bp/day. Gross validation is equally negative (pick -56.7 bp/day, t -2.29).

## Reading
- **Discovery was weak, not a hit.** No book reached t 1.4 in discovery (best by t: the ungated control, 1.33; the pick, 1.12). The pick's mean without its 10 best periods is already negative in discovery (-65 bp/week).
- **Validation has the opposite sign, in every book.** All 8 books lose at every cost, with t from -2.2 to -3.3. The losses are concentrated in 2025-26. The pick's net 1x by decision year, in bp/day: 2022 +36.0, 2023 -12.0, 2024 -6.2, 2025 -76.7, 2026 -105.6. Both legs lose: the losers' long leg -164 bp/week and the winners' short leg -232 bp/week for the pick. In the high-volatility tercile the recent winners kept running and the recent losers kept falling (continuation).
- **Not stronger in high-volatility tokens here.** Paired difference, high-vol gate minus ungated, 9 weeks:
  - Discovery: +4.0 bp/day (t 0.47) raw and +8.4 (t 1.13) residualised. This is in the paper's direction but far from significant.
  - Validation: -27.9 (t -1.46) raw and -37.8 (t -1.87) residualised, in the opposite direction.
- **Residualising changes little.** The tilt explains about 21-25% of the rank variance of the reversal score (mean R^2 per rebalance). Each raw book correlates 0.71-0.78 (discovery) and 0.82-0.90 (validation) with its residual twin. Neither version earned anything, so there was no edge for the residualisation to remove.
- **SPA over the 6 family books:** discovery p 0.29 (best L9w hv resid); validation p 1.0 (no book beats the zero benchmark).
- **Against `registry.program_trials()`:** 9,479,264 trials in the program with this lane's 8. A best discovery t of 1.1-1.3 in a family of 8 is within what noise produces. Nothing selected needs deflating, and the validation sign is negative. The raw program sum is bookkeeping, not an independent-test count.
- **No inverted book is claimed.** The negative validation (continuation) was not registered. An inverted book would be a new lane with its own id, on the same seen windows, and 2025-26 earned most of the loss.
- **What a NULL closes:** these six books on this panel. M457 is not reopened by another lookback, gate width or tilt set.

## Diagnostics (reported, not decided on)
- Names per leg 8.5-8.9 (hv books) and 27 (ungated). Mean hv group 45-46 names. Two of 248 rebalances were skipped (hv group under 30, R299's rule).
- Zero-exit names (no close in the whole hold, credited 0): about 0.02 per period for the long leg, 0.00-0.01 for the short leg. That cannot move the result.
- Full detail (legs, by-year nets, SPA, paired differences) is in `results/summary.json`; every period is in `results/periods.csv`.

## Not checked
- **A fresh sample:** none in this lane. The 2021-26 archive holdout is spent; 2020 is reserved and was not read.
- **The preprint:** not read by us. Its volatility measure, reversal skip-week, weighting and universe are unknown. This lane fixed its own choices (total vol30 as the volatility sort, no skipped week, equal weights, top-150 perps, weekly hold) and did not try others.
- **Idiosyncratic volatility:** total vol30 stands in for R238's IVOL in the tilt. A BTC-beta-residual vol was not built.
- **Other holds and rebalance anchors** (only 7 days from 2022-01-01), other gate widths (tercile only), value weights, and a hold that skips the most recent week.
- **GATES.md requirements:** dependent-null calibration, strict on-time clock, leave-two-coins-out, 10-day trimming and an 80%-power calculation were not run. The verdict is the lane-native one only. 142 validation weeks resolve about t 2 at roughly +30 bp/day, so a small edge could not have been seen either way.
- **Execution:** no live fills, borrow or MEXC availability of the names, and no capacity or depth check for the 9-name legs of high-volatility coins.
- **Survivorship:** the panel is point in time, but `lab.coverage`'s survivor-versus-delisted comparison was not run.
- **Transcription:** the tables above were taken from the lane agent's report of `results/`. The main session re-read the PREREG hash, the registry row and the pick's discovery and validation net and t against `run.log`; the other cells were not individually re-checked.
