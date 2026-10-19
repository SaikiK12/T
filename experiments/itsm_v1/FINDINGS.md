# FINDINGS: itsm_v1 (R203), intraday time-series momentum

**Verdict: NULL.** The day's first hour does not predict its last hour on Binance perps. Gate 1 failed on discovery;
the holdout was not read.

- **Registry row:** R203 (trials: 6)
- **Reproduce:** prereg sha e72930e0; `python scripts/run_itsm.py`.
- **Source claim:** `docs/CLAIMS.md` C13 (Shen, Urquhart, Wang 2022).

## Numbers (gross and net per trade-day, bp; NW t lag 5)
| clock | coin | discovery gross (t) | validation gross (t) | net 1x discovery | net 1x validation |
|---|---|---|---|---|---|
| UTC day | BTC (primary) | -2.2 (-0.96) | +0.7 (0.35) | -14.4 | -11.3 |
| UTC day | ETH | -1.2 (-0.42) | +3.0 (1.34) | -13.3 | -9.0 |
| UTC day | top 10 | +0.5 (0.19) | +1.1 (0.56) | -11.5 | -10.9 |
| volume clock | BTC | -4.2 (-2.24) | -2.4 (-1.14) | -16.4 | -14.4 |
| volume clock | ETH | -6.4 (-2.55) | -3.7 (-1.38) | -18.6 | -15.7 |
| volume clock | top 10 | -1.4 (-0.85) | -4.2 (-2.03) | -13.4 | -16.2 |

Hit rates 47-53%. Net at 2x and 3x: -21 to -43 bp per day.

## Cost sensitivity
In the table; every variant loses 9-19 bp a day at 1x, more at 2x and 3x.

## Reading
- The paper's momentum does not show at hourly resolution on these perps. If anything, the volume-clock variant leans
  to a reversal (the last hour against the first, -2 to -6 bp), in line with the lab's day-open mean reversion, and
  far below the 12 bp round trip.
- One trade a day of a few bp cannot pay a taker round trip; the paper's half-hour bars and volume clock are not
  reproduced exactly (hourly data).

## What this does not show
Half-hour or minute resolution; maker execution.
