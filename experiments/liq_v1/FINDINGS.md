# FINDINGS: liq_v1 (R206), do liquidation cascades overshoot?

**Verdict: NULL.** Fading Gate-measured liquidation spikes loses at every hold, before costs at 72 h and heavily after
costs at 4-24 h. Long cascades *continue* (buying after them loses gross at every hold); short squeezes do revert
within 4-24 h gross, but by less than the cost of trading them.

- **Registry row:** R206 (trials: 4)
- **Reproduce:** prereg sha 7b5d0844; `python scripts/fetch_gate.py`, then `python scripts/run_gate_lanes.py liq`.
- **Window:** 2026-05-09..2026-09-30 (145 days, after 360 hours of thresholds). Events: 7,730 long-cascade and 6,504
  short-squeeze coin-hours (q95/q05 of each coin's trailing 720 h).
- **Source claim:** `docs/CLAIMS.md` C07 (folklore, grade D).

## Numbers (slices of h hours, size 1/(h x K_L), K_L = 4.09; universe hedge; bp per day; NW t lag 5)
| h | book | net 1x | gross | cost 1x | t (net) | net 2x | net 3x | turnover/day |
|---|---|---|---|---|---|---|---|---|
| 4 | both | -93.3 | +24.2 | 117.5 | -2.36 | -210.8 | -328.2 | 10.6 |
| 4 | long leg | -72.1 | -1.9 | 70.2 | -2.36 | | | 5.8 |
| 4 | short leg | -30.6 | +26.1 | 56.7 | -1.15 | | | 4.8 |
| **12 (primary)** | **both** | **-35.9** | **+4.2** | **40.1** | **-1.96** | **-76.1** | **-116.2** | **3.6** |
| 12 | long leg | -30.0 | -6.1 | 23.9 | -1.57 | | | 2.0 |
| 12 | short leg | -9.2 | +10.2 | 19.5 | -0.44 | | | 1.6 |
| 24 | both | -19.7 | +0.7 | 20.4 | -1.35 | -40.1 | -60.4 | 1.8 |
| 24 | long leg | -22.9 | -10.8 | 12.1 | -1.43 | | | 1.0 |
| 24 | short leg | +1.8 | +11.5 | 9.7 | +0.09 | | | 0.8 |
| 72 | both | -22.2 | -15.3 | 6.9 | -2.21 | -29.1 | -35.9 | 0.6 |
| 72 | long leg | -13.4 | -9.3 | 4.1 | -0.87 | | | 0.3 |
| 72 | short leg | -9.3 | -6.0 | 3.3 | -0.63 | | | 0.3 |

Max drawdown of the primary 65%; of h = 72, 32%.

## Cost sensitivity
In the table: 1x already loses at every hold; 2x and 3x scale the losses (the 4 h book turns over 10.6 times a day).

## Reading
- **Long liquidation cascades are not overshoots on Gate's measure**: after the top 5% of long-liquidation hours, the
  coin keeps underperforming the universe for at least 72 h (long leg gross -2 to -11 bp/day). This is continuation,
  consistent with the lab's earlier finding that OI-vs-price moves keep going (R185 proxy).
- **Short squeezes revert a little** (short leg gross +10 to +26 bp/day at 4-24 h), which fits squeezes being forced
  buying, but the edge is about half the taker cost at 4 h and below it at 12 h.
- A maker-entry version of the short-squeeze fade, or a continuation book on long cascades, would be *new* lanes chosen
  after seeing this; both need forward data (Gate keeps 180 days; October 2026 on is unseen).
- Read against 9,471,649 program trials; the window is 145 days of one regime.

## Added after the run (reporting only)
Gross and cost per day were added to the output after the first run; the decision columns did not change.

## What this does not show
Binance's own liquidation feed (forceOrders is not public in bulk); minute-level timing of the cascade; anything
before 2026-04 (Gate keeps 180 days).
