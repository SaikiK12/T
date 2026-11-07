# FINDINGS: cbprem_v1 (R210), does the Coinbase premium lead BTC and ETH?

**Verdict: NULL.** Trading the Binance perp after the Coinbase premium's 30-day z-score passes +/-2 earned +0.2 bp a
day for BTC in-sample (t 0.34) and +0.7 on the holdout (t 0.88) at 1x, and nothing at 2x. The gross spread after
extremes has the claimed sign in both windows, but it is noisy, and the signal is rare (about 4% of hours).

- **Registry row:** R210 (trials: 4)
- **Reproduce:** prereg sha cf97c443; `python scripts/fetch_extra.py`, then `python scripts/run_cbprem.py`.
- **Windows:** in-sample 2021-01-01..2025-06-30 (the premium exists from 2021-05-04, when Coinbase's USDT-USD starts),
  holdout 2025-07-01..2026-09-30 (this lane's own, now spent).
- **Source claim:** `docs/CLAIMS.md` C18 (grade D).

## Numbers (slices of size 1/h, so the position is at most 1; daily net including idle days, bp; NW t lag 10)
| coin | h | in-sample 1x (t) | holdout 1x (t) | in-sample 2x / 3x | holdout 2x / 3x | max DD in / out |
|---|---|---|---|---|---|---|
| **BTC** | **24 (primary)** | **+0.21 (0.34)** | **+0.72 (0.88)** | **-0.22 / -0.65** | **+0.18 / -0.37** | **8.2% / 2.5%** |
| BTC | 4 | -0.51 (-0.43) | -1.31 (-0.71) | -3.02 / -5.54 | -4.42 / -7.53 | 19.9% / 12.0% |
| ETH | 24 | +0.03 (0.04) | +0.98 (1.10) | -0.39 / -0.80 | +0.48 / -0.01 | 12.3% / 3.0% |
| ETH | 4 | -1.34 (-1.05) | +4.14 (1.67) | -3.79 / -6.24 | +1.06 / -2.01 | 31.6% / 7.5% |

Signal hours: BTC 825 up / 721 down in-sample (of about 36,000 with a premium), 313 / 221 on the holdout; ETH similar.

Gross forward returns of the perp after an extreme (mean over signal hours, bp; overlapping, so no t):

| coin | horizon | after z > 2: in / out | after z < -2: in / out | spread in / out |
|---|---|---|---|---|
| BTC | 1 h | +0.8 / +4.8 | -1.0 / -4.8 | +1.8 / +9.6 |
| BTC | 4 h | +10.2 / +3.2 | -6.5 / -10.1 | +16.7 / +13.4 |
| BTC | 24 h | +47.8 / +13.3 | +19.5 / -44.0 | +28.2 / +57.3 |
| ETH | 1 h | -3.6 / +1.0 | -6.4 / -8.3 | +2.9 / +9.3 |
| ETH | 4 h | +6.4 / +24.8 | -3.1 / -29.9 | +9.5 / +54.7 |
| ETH | 24 h | +23.5 / +30.9 | +0.2 / -36.6 | +23.3 / +67.5 |

The hourly change in the premium correlates +0.10 (BTC) and +0.08 (ETH) with the same hour's return: partly a
by-product of the move.

## Cost sensitivity
In the first table. The 24 h book's edge, if any, is smaller than one extra unit of cost: it turns negative at 2x
in-sample and at 3x on the holdout. The 4 h book loses at 2x everywhere.

## Reading
- The direction the claim states shows up in every spread above (12 of 12 positive), larger on the holdout. But the
  signal hours cluster into a few episodes, the book holds only about 4% of capital on average, and its daily t is
  0.3-1.1. As a trade it is too rare and too small to pay; as information, the premium is a weak, slow-moving tilt.
- A forward score is cheap (Coinbase and Binance spot are live): a new lane could fix the 24 h rule as is and score
  it from 2026-10-01. It would take years at this frequency to reach t 2 if the holdout's size is the truth.
- Read against 9,471,695 program trials (after this lane).

## What this does not show
Minute-level lead-lag (the claim is often about minutes during US opens); the premium as a filter for other books.
