# FINDINGS: xvenue_v1 (R205), top traders vs the crowd measured on Gate

**Verdict: NULL (does not replicate at t >= 2; adds nothing).** Gate's top_vs_crowd, traded as the R197 short slice
book on Binance, earned as much as Binance's own signal on the same window (+38% vs +37% over 157 days) but with three
times the drawdown and t 1.43. The coins that Gate flags and Binance does not (G_only) earned nothing.

- **Registry row:** R205 (trials: 3)
- **Reproduce:** prereg sha c1b1ab2c; `python scripts/fetch_gate.py` (Gate keeps 180 days: refetchable only until
  each hour ages out), then `python scripts/run_gate_lanes.py xvenue`.
- **Window:** 2026-04-27..2026-09-30 (157 days), inside the spent flow72 holdout. **Cannot confirm anything**; as
  pre-registered, the question was whether a second venue tells the same story.
- **Source claim:** `docs/CLAIMS.md` C06.

## Numbers (72 h short slices, size 1/(72 x 9.316), universe hedge; daily, bp; NW t lag 10)
| book | total 1x | net bp/day 1x | gross bp/day | cost bp/day 1x | t | Sharpe | max DD | net 2x | net 3x |
|---|---|---|---|---|---|---|---|---|---|
| G (Gate signal, primary) | +38.4% | +24.4 | +25.5 | 1.1 | 1.43 | 2.50 | 28.2% | +23.3 | +22.3 |
| B (Binance signal, same coins) | +37.5% | +23.9 | +25.0 | 1.1 | 2.08 | 3.20 | 9.0% | +22.8 | +21.7 |
| G_only (Gate bin 0, not Binance's) | -2.1% | -1.4 | -0.3 | 1.0 | -0.11 | -0.20 | 27.6% | -2.4 | -3.4 |

Signal agreement: hourly cross-sectional Spearman between the two signals averages 0.46 (10th-90th percentile 0.26 to
0.65); the bin-0 sets overlap by 31% (Jaccard).

Per month (total net, 1x):

| month | G | B | G_only |
|---|---|---|---|
| 2026-04 (from 27th) | +2.7% | +3.5% | +0.9% |
| 2026-05 | +11.4% | +2.9% | +8.6% |
| 2026-06 | -11.2% | +7.4% | -14.8% |
| 2026-07 | +11.3% | +12.6% | -7.4% |
| 2026-08 | +12.6% | +3.0% | +3.1% |
| 2026-09 | +11.5% | +8.1% | +7.4% |

## Cost sensitivity
1x / 2x / 3x net per day: G +24.4 / +23.3 / +22.3 bp; B +23.9 / +22.8 / +21.7 bp. The 72 h book turns over slowly,
so costs are about 1 bp a day per 1x; the verdict does not depend on costs.

## Reading
- The *same idea* measured on a second venue has the same sign and size of gross (+25 bp/day), which is weak evidence
  that top_vs_crowd reflects positioning across the market, not a Binance artefact. It is weak because the signals
  share half their ranking (Spearman 0.46) and the window is one bull-ish half-year.
- Gate's version is noisier: one bad month (June, -11%) driven by the coins only Gate flagged. G_only is ~0 gross, so
  Gate's extra information is noise, not edge. Use Binance's signal; Gate does not add.
- Read against the program: 9,471,645 trials after this lane; a t of 1.4 on a window already used for the reference
  signal carries no weight on its own.

## Added after the run (reporting only)
Gross and cost per day were added to the output after the first run; the decision columns did not change.

## What this does not show
Whether a combined Binance+Gate signal is better (not tested, would be a new lane); October 2026 on (Gate keeps 180
days, so the forward period can be scored later without a collector).
