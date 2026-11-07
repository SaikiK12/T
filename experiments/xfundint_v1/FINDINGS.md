# FINDINGS: xfundint_v1 (R384). R277's KuCoin carry is not a settlement-interval artifact: label `robust`

**Label (frozen rule): robust for both sets, so the lead is `robust`.** Gate 0 on seen data; an audit of saved archive
data, not new evidence. The pre-scaling profit did come mostly from 1h/4h KuCoin contracts (A true), but the book
earned +10.0 to +10.5 %/yr at 1x after the scaling, with a Newey-West t of 3.1 to 3.7 over 69 days (C true).

- **Registry:** R384, 56 trials (cells, cost multiples counted once). Program trials 9,479,264 before, 9,479,320 after.
- **Reproduce:** prereg sha c1aecb9c, frozen before any statistic; `.venv/bin/python scripts/run_xfundint.py` (17 inputs
  match; 4,750 data files hash to `docs/provenance`; about 2 minutes after the hash check). Test: `tests/test_xfundint.py`.
- **Parity (the gate):** `lab/xfund.py` replay reproduces R277 for both books: 1,153 and 1,168 trades identical, 2,078
  days, date labels identical, max |net diff| 5.0e-11 at 1x, 2x and 3x (the saved file's 10-decimal precision). The
  attribution reconciles with the replay to 1e-16, and per-trade funding to R277's `trades.csv` to 6e-15.

## Decision cells (per set)
| Set | A: 1h/4h share of pre net funding | B: post 8h-class net 1x | C: post full-book net 1x, NW t | Post days | Label |
|---|---|---|---|---|---|
| gate+kucoin | 0.650 (>0.5: true) | +0.34 %/yr (<=0: false) | +10.52 %/yr, t 3.70 (true) | 69 | robust |
| binance+kucoin | 0.666 (true) | +0.07 %/yr (false) | +10.04 %/yr, t 3.11 (true) | 69 | robust |

## Net by KuCoin scaling period (%/yr on capital, 1x / 2x / 3x; NW t at 1x)
| Set | pre (to 2026-07-14, 1,999 d) | trans (07-15..07-24, 10 d) | post (from 2026-07-25, 69 d) |
|---|---|---|---|
| gate+kucoin | +11.83 / +10.44 / +9.04 (t 11.1) | +6.66 / +4.61 / +2.57 (t 2.2) | +10.52 / +8.45 / +6.37 (t 3.70) |
| binance+kucoin | +10.89 / +9.48 / +8.06 (t 10.9) | -3.49 / -5.79 / -8.09 (t -0.8) | +10.04 / +8.19 / +6.34 (t 3.11) |

## By KuCoin interval class (class net 1x / 2x / 3x on total capital; share of the period's net funding)
| Set | Class | pre share | pre net | post share | post net |
|---|---|---|---|---|---|
| gate+kucoin | 1h | 0.001 | +0.00 / +0.00 / +0.00 | -0.023 | -0.43 / -0.51 / -0.58 |
| | 4h | 0.649 | +8.05 / +7.42 / +6.80 | 0.998 | +10.62 / +8.71 / +6.81 |
| | 8h | 0.350 | +3.78 / +3.01 / +2.24 | 0.024 | +0.34 / +0.24 / +0.15 |
| binance+kucoin | 1h | 0.000 | +0.00 / +0.00 / +0.00 | -0.032 | -0.43 / -0.50 / -0.58 |
| | 4h | 0.666 | +7.53 / +6.92 / +6.32 | 0.989 | +10.40 / +8.82 / +7.25 |
| | 8h | 0.334 | +3.36 / +2.55 / +1.74 | 0.043 | +0.07 / -0.14 / -0.34 |

- The 1h class is one contract. After the scaling nearly all of the book's funding sits in 4h KuCoin contracts, now
  paying scaled rates; 8h contracts hold 2 to 4% of it. So the post-scaling net is not "8h contracts earning": it is 4h
  contracts earning at the scaled rate. B (8h-class net <= 0) fails only because that class is about zero (+0.07, +0.34).
- **Other leg (day class from its recorded settlement count):** Gate legs: post funding mostly on 4h days (0.71 of the
  book's funding) and negative on 8h days (-0.16). Binance legs: pre 8h 0.10, 4h -0.06, 1h -0.42; post 4h 1.13, 1h 0.50.
  These shares are large and of mixed sign (the other leg often pays); read them as "which days the funding was
  booked on", not as sources of profit.

## Full book by year (%/yr, 1x / 2x / 3x)
| Set | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (to 10-01) |
|---|---|---|---|---|---|---|
| gate+kucoin | +10.0 / +8.3 / +6.6 | +5.5 / +4.1 / +2.7 | +4.7 / +3.0 / +1.3 | +9.5 / +8.4 / +7.3 | +20.0 / +18.8 / +17.6 | +23.7 / +22.2 / +20.8 |
| binance+kucoin | +9.5 / +7.9 / +6.4 | +2.4 / +0.7 / -1.1 | +5.3 / +3.5 / +1.8 | +8.5 / +7.5 / +6.4 | +20.0 / +18.9 / +17.8 | +21.8 / +20.4 / +18.9 |

These equal R277's by-year table, as the parity gate requires. The pace of 2025-26 (+20-24%/yr) is about double the
post-scaling pace (+10%/yr), as the LEADS post-hoc split said.

## Binance's scaling date (2025-09-18), binance+kucoin
| Period | Days | Net 1x / 2x / 3x %/yr | NW t (1x) |
|---|---|---|---|
| pre (to 2025-09-18) | 1,700 | +7.93 / +6.49 / +5.05 | 10.9 |
| post (from 2025-09-19) | 378 | +23.69 / +22.27 / +20.85 | 7.0 |

Binance's scaling did not remove the carry; it was higher afterwards. Binance-leg day-class funding shares (`class_bn`
in `results/cells.csv`) are small and mixed in sign before (-0.05 / 0.15 / 0.15 for 1h / 4h / 8h) and negative for 1h
and 4h after (-0.99, -0.30): the Binance leg's funding on its short-interval days was a net cost in these trades (the KuCoin leg
earned more). Binance has no contracts file, so this uses the settlement count.

## Without any 1h/4h KuCoin contract (8h-only replay, reported, not decided)
| Set | All days 1x / 2x / 3x (NW t) | Post, 69 d, 1x / 2x / 3x (NW t) |
|---|---|---|
| gate+kucoin | +6.63 / +5.22 / +3.82 (11.1) | +1.28 / -1.53 / -4.34 (1.1) |
| binance+kucoin | +5.97 / +4.57 / +3.16 (10.9) | +2.31 / +0.87 / -0.58 (2.0) |

The book restricted to 8h KuCoin contracts earns about half the full pace over the whole window (about 6 against 11
%/yr) and about +1-2% at 1x after the scaling, which does not survive 2x. The carry is mostly a 4h-contract carry.

## Reading
- **Against program trials (9,479,320):** a labelling audit of a known lead, not a search. Its decision cells are
  3 per set, on data R277 already used. It adds no independent evidence about profitability.
- **What it shows:** the old unscaled 4h rates carried about two thirds of the pre-scaling funding (A), but the book
  still earned the same order after KuCoin scaled (C), so the lead is not only the old inflated per-settlement rates.
  The pace is about half of 2025-26's (+10 against +20 to +24 %/yr at 1x); whether the halving is the scaling or
  something else is not separated here.
- **The 69 days are one short regime** (2026-07-25..2026-10-01). A t of 3.1-3.7 with 10-lag NW over 69 days is a
  bar the rule set; it is weak evidence, and nothing here is prospective. The lead stays as LEADS states it.

## Not checked
- **Whether recorded rates equal paid rates:** the history endpoint gives published rates, not amounts charged. Nothing
  public shows each contract's rate factor before the scaling date.
- **The interval history of each contract:** `contracts.csv` holds 2026-10-20 intervals. For 33% (gate+kucoin) and 32%
  (binance+kucoin) of KuCoin-leg position-days the settlement count of that day implies a different class than the
  static one (a contract that changed interval, a missing settlement, or a day count of 4-8 around changes). The A
  shares use the static class; they were not recomputed with the day class (that would be a new lane).
- **The exact scaling date per contract** (07-14 to 07-24 across contracts): the 10 transition days are excluded.
- **Delisted KuCoin contracts** are absent (R277's survivorship limit); capacity, fills, transfers, liquidation are not
  modelled; the Binance and Gate legs' intervals were inferred from counts, not from a contracts file.
- **Counterfactual rescaling** of pre-scaling 1h/4h rates by interval/8h was not run (it assumes the premium
  component scales proportionally, which is unverified).
- Data-folder integrity was checked only for the files read, by sha256 against `docs/provenance`.
