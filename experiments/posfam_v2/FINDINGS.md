# FINDINGS: posfam_v2 (R212), top accounts' headcount as a contrarian signal

**Verdict: NULL (failed validation; holdout not read).** Betting against the top accounts (long where most of them are
short, short where most are long) kept its sign on 2024-2025H1 (+20.1 bp/day) but not its reliability (t 1.13, gate
1.5). Its residual against top_vs_crowd shrank from +12.3 bp/day in discovery to +5.6 (t 0.33): out of sample it is
mostly top_vs_crowd again. Almost all of it comes from the long leg.

- **Registry row:** R212 (trials: 4)
- **Reproduce:** prereg sha 2ceec67b; `python scripts/run_posfam.py --lane posfam_v2`.
- **Chosen on:** posfam_v1's discovery numbers (reversed). The holdout stays unread for these books.

## Numbers (72 h slices, universe hedge; daily net bp/day; NW t lag 10)
| book | window | gross | cost 1x | net 1x (t) | net 2x | net 3x | max DD | corr tvc | residual (t) |
|---|---|---|---|---|---|---|---|---|---|
| C (primary) | discovery (selection) | +26.3 | 1.9 | +24.5 (2.80) | +22.6 | +20.7 | 38% | 0.67 | +12.3 (1.92) |
| **C (primary)** | **validation** | **+24.4** | **4.3** | **+20.1 (1.13)** | **+15.8** | **+11.5** | **60%** | **0.52** | **+5.6 (0.33)** |
| L: bin 0 long | validation | +49.5 | 4.7 | +44.8 (1.38) | +40.1 | +35.4 | 102% | 0.39 | +26.9 (0.85) |
| S: bin 7 short | validation | +5.2 | 4.0 | +1.2 (0.10) | -2.8 | -6.8 | 56% | 0.56 | -10.7 (-0.89) |
| crowd_ls reference | validation | +17.3 | 2.7 | +14.6 (1.38) | +11.8 | +9.1 | 29% | 0.57 | +5.0 (0.50) |

## Cost sensitivity
C at 1x / 2x / 3x: +20.1 / +15.8 / +11.5 bp/day on validation. Slow book; costs do not decide it.

## Reading
- The top-account reversal and the crowd-contrarian reference behave alike on validation (+20 vs +15 bp/day, both
  t ~1.1-1.4, correlations 0.52-0.57 with top_vs_crowd). Positioning signals on Binance overlap heavily: three ratios,
  one underlying story (large traders right, the many wrong), and top_vs_crowd already holds most of it.
- The long leg (buy coins where top accounts are most short) carries the book: +44.8 bp/day gross of costs on
  validation but with a 102% drawdown (summed, not compounded). Long legs of crowding signals are squeeze-prone.
- Read against 9,471,705 program trials (after this lane).

## What this does not show
The holdout (unread); whether a book on all three positioning ratios together beats top_vs_crowd alone (a new lane
would need to be designed on discovery only).
