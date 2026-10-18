# PREREG: carry_holdout (R191), one-shot holdout of the funding carry

Freeze with `lab.prereg.freeze()` before the run. Run once. Never edited afterwards.

- **Registry id:** R191
- **Code:** `lab/carry.py`, `scripts/run_carry.py` (same functions), `scripts/run_carry_holdout.py`
- **Evidence that led here:** carry_v1 (R190): primary (theta_in 20% APR, spot cost 10 bp, 1x tier costs) earned
  +12.7%/yr net on discovery (t 3.80, 2 of 3 years positive) and +5.9%/yr on validation (t 2.82): SIGNAL, VALIDATED.
- **What has not been read:** any funding, basis or return after 2025-07-01. (The listings holdout, R189, read returns
  of new listings and the top-50 market return after that date; it read no funding or basis.)

## Test
The R190 primary, unchanged, on 2025-07-01..2026-09-30: short perp + long spot when trailing 72 h funding > 20% APR,
exit below 10%, top-50 liquidity and a spot pair required, 1/max(open, 10) per position, perp tier costs + 10 bp spot,
funding and basis (premium index) changes accrued hourly.

## Decision
**CONFIRMED** if net return over the window > 0 and Newey-West t (lag 10, daily) >= 2. Otherwise NOT CONFIRMED.
Reported with: funding and basis parts, costs, share of time invested, average open positions, max drawdown, the
same at 2x costs and at 5 bp spot, and the market-wide average funding APR in the window for context.
A confirmed carry goes to forward paper (no real money without `lab.gate.go_real`).

## Multiplicity
1 primary test (2 cost variants descriptive).
