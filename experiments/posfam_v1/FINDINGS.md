# FINDINGS: posfam_v1 (R211), which half of top-vs-crowd carries the edge?

**Verdict: NULL (no book passed validation).** Splitting top_vs_crowd into its two halves shows where it lives: the
**whale half** (top traders' money against their own headcount) *is* the signal (its short book correlates 0.96 with
top_vs_crowd's), and adds nothing beyond it. The other half and the top-account ratio alone fail. The strongest effect
in the lane runs **against** the top accounts: shorting the coins where top accounts are most short lost 47.6 bp a day
in discovery (t -3.0), so their headcount is a contrarian signal. That reversal is a new lane (posfam_v2), not a result
of this one.

- **Registry row:** R211 (trials: 6)
- **Reproduce:** prereg sha f9dc5aa6; `python scripts/run_posfam.py` (about 1 minute).
- **Windows:** discovery 2021-01-01..2023-12-31, validation 2024-01-01..2025-06-30; no book reached the holdout, which
  stays unread for these books.

## Coverage (found during the run, applies to every flow lane)
Binance's archived positioning ratios (top_ls_count, top_ls_sum, ls_count) cover 10% of eligible coin-hours in 2021, 13%
in 2022 (ls_count 94%), and 99%+ from 2023. So "discovery 2021-2023" for any top-trader signal, top_vs_crowd included,
is mostly 2023.

## Numbers (72 h slices, universe hedge, daily net, bp/day; NW t lag 10; residual = intercept of a regression on the
top_vs_crowd short book, same window)
| book | window | gross | cost 1x | net 1x (t) | net 2x | net 3x | max DD | corr with tvc | residual (t) |
|---|---|---|---|---|---|---|---|---|---|
| whale_vs_top bin 0 short | discovery | +12.4 | 2.1 | +10.3 (1.47) stop | +8.2 | +6.1 | 47% | 0.96 | -3.9 (-2.28) |
| whale_vs_top bin 7 long | discovery | +24.7 | 1.8 | +22.8 (2.07) pass | +21.0 | +19.2 | 76% | 0.50 | +11.6 (1.26) |
| whale_vs_top bin 7 long | validation | +30.1 | 4.3 | +25.8 (1.31) stop | +21.5 | +17.2 | 71% | 0.44 | +13.2 (0.71) |
| topacct_vs_crowd bin 0 short | discovery | +18.9 | 2.8 | +16.1 (2.54) pass | +13.3 | +10.4 | 25% | 0.39 | +10.1 (1.83) |
| topacct_vs_crowd bin 0 short | validation | +26.5 | 6.0 | +20.4 (0.85) stop | +14.4 | +8.4 | 125% | 0.10 | +17.0 (0.71) |
| topacct_vs_crowd bin 7 long | discovery | +11.2 | 3.0 | +8.2 (1.21) stop | +5.2 | +2.2 | 51% | 0.34 | +3.4 (0.56) |
| top_acct bin 0 short | discovery | -45.5 | 2.1 | -47.6 (-2.99) stop | -49.6 | -51.7 | 544% | -0.50 | -32.2 (-2.43) |
| top_acct bin 7 long | discovery | -11.7 | 1.9 | -13.6 (-2.51) stop | -15.5 | -17.4 | 149% | -0.75 | -3.9 (-0.98) |

Totals behind the drawdowns are sums of daily returns at unit size (not compounded), so a "drawdown" above 100% is
possible.

## Cost sensitivity
In the table: these 72 h books cost 2-6 bp/day at 1x; no verdict depends on costs. The two that passed discovery still
had positive 3x means (+19.2 and +10.4 bp/day) and failed validation on t, not on costs.

## Reading
- top_vs_crowd = whale_vs_top + topacct_vs_crowd. Its edge sits in the whale half: when the top traders' *positions*
  lean short while their *accounts* do not, a few large traders are short, and that is what pays. The headcount half
  adds noise (validation t 0.85, drawdown 125%).
- The top-account ratio on its own points the wrong way in both tails (t -3.0 and -2.5): coins where most top accounts
  are short go up relative to the market, and the reverse. Read with top_vs_crowd, the money of the top traders is
  informative and their headcount is crowd-like, if anything contrarian.
- Read against 9,471,701 program trials (after this lane).

## What this does not show
The holdout of any of these books; a live journal of top_ls_count (the forward R200 journal does not store it).
