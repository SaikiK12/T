# FINDINGS: vrp_v1 (R209), does the volatility risk premium time BTC and ETH?

**Verdict: NULL.** Going long BTC when implied volatility (Deribit DVOL) is high relative to realized volatility, and
short otherwise, earned +7.5 bp a day in-sample with t 1.06, and +1.1 bp a day on the holdout. The direction matches
the equity literature (BTC rose +20 bp/day on high-premium days and 0 on low ones in-sample), but it is not reliable,
and it did not repeat on the holdout (-2.3 vs -5.6 bp).

- **Registry row:** R209 (trials: 8)
- **Reproduce:** prereg sha 96b2622d; `python scripts/fetch_extra.py`, then `python scripts/run_vrp.py`.
- **Windows:** in-sample 2021-09-21..2025-06-30 (1,379 days; the first day with a 180-day threshold), holdout
  2025-07-01..2026-09-30 (457 days, this lane's own, now spent).
- **Source claim:** new C23 (Bollerslev, Tauchen, Zhou 2009, equities).

## Numbers (1x costs; daily net, bp; NW t lag 10)
| coin | split | rebalance | in-sample bp/day (t) | holdout bp/day (t) | in-sample: ret on long / short days | holdout: long / short days | Sharpe in / out |
|---|---|---|---|---|---|---|---|
| **BTC** | **median** | **daily (primary)** | **+7.5 (1.06)** | **+1.1 (0.12)** | **+20.4 / -0.0** | **-2.3 / -5.6** | **0.51 / 0.10** |
| BTC | median | weekly | -4.5 (-0.64) | -1.3 (-0.12) | +4.2 / +11.9 | -5.0 / -3.4 | -0.31 / -0.11 |
| BTC | tercile | daily | +3.3 (0.58) | -5.3 (-0.62) | +21.5 / +3.3 | -10.6 / +4.0 | 0.28 / -0.53 |
| BTC | tercile | weekly | +2.2 (0.37) | -0.8 (-0.08) | +14.3 / +5.2 | -7.3 / -5.0 | 0.18 / -0.08 |
| ETH | median | daily | +3.7 (0.41) | -1.0 (-0.06) | +10.4 / -1.2 | +4.6 / +7.6 | 0.19 / -0.06 |
| ETH | median | weekly | +7.3 (0.81) | -6.3 (-0.39) | +10.7 / -4.9 | -0.2 / +17.1 | 0.39 / -0.37 |
| ETH | tercile | daily | +6.5 (0.82) | -12.1 (-0.91) | +22.2 / -4.4 | -6.2 / +32.7 | 0.42 / -0.79 |
| ETH | tercile | weekly | +3.3 (0.44) | -6.5 (-0.44) | +17.1 / +4.9 | +3.1 / +39.1 | 0.21 / -0.42 |

Primary per calendar year (total net): 2021 (from Sep) +17%, 2022 -6%, 2023 +80%, 2024 -13%, 2025 +58%, 2026 -27%.
Descriptive (in-sample): DVOL above 30-day realized vol on 82% of days for BTC (mean premium +8.6 vol points), 69% for
ETH (+5.3). The premium correlates with the past 30-day return: +0.12 for BTC, +0.35 for ETH (rallies are calm, so
realized vol drops while DVOL stays).

## Cost sensitivity
Primary 1x / 2x / 3x: in-sample +7.5 / +6.5 / +5.4 bp/day (t 1.06 / 0.91 / 0.76); holdout +1.1 / -0.1 / -1.3. A daily
BTC position that flips about once a week costs little; costs do not decide this.

## Reading
- In-sample, 7 of 8 variants earn more on long days than on short days and 7 of 8 have a positive net mean; none is
  near t 2. On the holdout 7 of 8 lose, and ETH turned round (higher returns on low-premium days).
- Erratum: the registry row R209 says "6/8 variants lose on holdout"; the count is 7 of 8. The registry is append-only,
  so the row stays as written and this file is the reference.
- Same pattern as every directional BTC timing lane (itsm_v1, carrycrash_v1): with one or two assets and daily or
  weekly decisions there are only a few hundred independent bets, so a real effect of a few bp a day cannot be told
  from noise in five years. The lab's positive results all come from cross-sections (many coins at once).
- Read against 9,471,691 program trials (after this lane).

## What this does not show
Monthly or quarterly horizons (where the equity evidence lives: about 60 independent quarters here, too few); the
premium as a cross-sectional or risk-management input (e.g. sizing the flow book by DVOL), which would be a new lane.
