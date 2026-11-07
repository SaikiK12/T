# FINDINGS: sizecarry_v1 (R281). Sizing carry pairs by confidence does not pass: the books stay equal-weighted

**Verdict: NULL (30 trials, gate 0).**
- **No book passes.** The pre-committed bar is a per-book SPA p ≤ 0.0083 (0.05 / 6) on the daily difference from the
  equal book at 2x cost. The lowest p is R279 A's 0.026.
- **Pre-committed action:** the forward lanes stay equal-weighted. M266 is recorded as tested. Nothing joins the
  reserved 2020 batch from this lane.
- **What the sizing does:** tilting toward the widest spreads (`spread`, `spread_persist`) raises the 1x return on
  every book, by +1.3 to +8.7 %/yr.
  - It also doubles the trading, so the gain shrinks with cost: at 3x it is between −1.8 and +2.0 %/yr.
  - It cuts the NW t by up to half and deepens every book's drawdown.
  - The gain comes from 2025-26.

**Reproduce**
- prereg sha ad2f7a6d, frozen in commit 4a1618d before any score, weight or sized return was computed on market data.
- `nice python scripts/run_sizecarry.py` takes about 4 minutes.
- The parity guard passed on all 6 books: `equal` at 1x equals each engine run's daily net within 1e-9.
- `results/summary.csv`, `results/spa.csv` and `results/daily.csv` hold every number below.

## The decision (pre-committed, at 2x cost)
| Book | Days | SPA p (consistent) | RC p | Best variant | Best − equal, bp/day (NW t) | Halves | Best − equal at 3x | Passes |
|---|---|---|---|---|---|---|---|---|
| R278 A gate+hyperliquid L14 th5% K20 | 1225 | 0.849 | 0.849 | spread_vol | +0.075 (0.33) | +0.07 / +0.08 | −0.340 | no |
| R278 B binance+mexc L14 th10% K20 | 507 | 0.056 | 0.086 | spread | +0.559 (2.00) | +0.74 / +0.38 | +0.353 | no (p) |
| R278 C gate+mexc L7 th10% K20 | 514 | 0.266 | 0.266 | spread_persist | +1.465 (1.45) | −0.05 / +2.98 | +0.550 | no |
| batch binance+gate L14 th10% K20 | 2078 | 0.216 | 0.257 | spread_persist | +0.789 (1.43) | +0.28 / +1.30 | +0.422 | no (p) |
| R279 A gate+kucoin L14 th5% K20 | 2078 | 0.026 | 0.028 | spread_persist | +0.816 (2.47) | +0.23 / +1.41 | +0.455 | no (p) |
| R279 B binance+kucoin L14 th5% K20 | 2078 | 0.128 | 0.244 | spread | +0.400 (1.48) | +0.10 / +0.70 | +0.006 | no (p) |

- **"no (p)":** the book clears the halves test and the 3x test, but not the SPA bar.
- **R279 A comes closest.** Its p of 0.026 would pass alone, but not with 6 books tested.
- **Multiplicity:** 30 trials, 9,478,358 in the program after this lane. Read against that count, a p of 0.026 on a
  daily difference is not evidence.

## Each book at 1x / 2x / 3x cost (annual net on capital, %)
| Book | equal | spread | persist | spread_persist | inv_vol | spread_vol |
|---|---|---|---|---|---|---|
| R278 A | 9.73 / 8.51 / 7.28 | 11.02 / 8.27 / 5.52 | 9.85 / 8.54 / 7.23 | 11.27 / 8.56 / 5.85 | 8.99 / 7.49 / 5.99 | 11.52 / 8.78 / 6.04 |
| R278 B | 6.33 / 4.96 / 3.60 | 9.12 / 7.00 / 4.88 | 5.29 / 3.61 / 1.94 | 7.93 / 5.74 / 3.55 | 5.11 / 3.58 / 2.04 | 8.11 / 6.03 / 3.96 |
| R278 C | 16.29 / 12.99 / 9.69 | 22.74 / 16.02 / 9.29 | 16.77 / 13.24 / 9.71 | 24.98 / 18.34 / 11.70 | 14.69 / 11.00 / 7.31 | 20.63 / 13.83 / 7.03 |
| batch | 10.05 / 8.33 / 6.60 | 13.71 / 10.68 / 7.66 | 9.79 / 7.74 / 5.69 | 14.27 / 11.21 / 8.14 | 7.90 / 5.79 / 3.68 | 9.62 / 6.59 / 3.56 |
| R279 A | 11.76 / 10.34 / 8.92 | 16.19 / 13.40 / 10.61 | 11.26 / 9.70 / 8.14 | 16.06 / 13.32 / 10.58 | 9.73 / 7.95 / 6.16 | 13.72 / 10.90 / 8.08 |
| R279 B | 10.80 / 9.36 / 7.92 | 13.69 / 10.82 / 7.95 | 10.49 / 8.89 / 7.29 | 13.34 / 10.47 / 7.59 | 9.33 / 7.56 / 5.78 | 12.15 / 9.21 / 6.27 |

## Risk, trading and concentration (1x cost)
| Book | Score | NW t | Max DD | Notional traded / day (legs) | Mean largest weight |
|---|---|---|---|---|---|
| R278 A | equal → spread_vol | 8.63 → 6.81 | −2.1% → −2.4% | 1.92 → 4.29 | 1 → 2.48 |
| R278 B | equal → spread | 4.80 → 4.22 | −0.4% → −0.9% | 2.14 → 3.32 | 1 → 2.55 |
| R278 C | equal → spread_persist | 7.38 → 4.51 | −0.9% → −2.8% | 5.17 → 10.40 | 1 → 2.86 |
| batch | equal → spread_persist | 5.96 → 4.16 | −5.2% → −5.4% | 2.70 → 4.80 | 1 → 2.74 |
| R279 A | equal → spread_persist | 11.41 → 7.71 | −0.7% → −2.2% | 2.22 → 4.29 | 1 → 2.64 |
| R279 B | equal → spread | 11.17 → 7.56 | −2.3% → −3.0% | 2.25 → 4.50 | 1 → 2.54 |

- **The worst drawdowns:** `spread` and `spread_vol` on the batch book reach −14.8% and −14.4%, against −5.2%
  for equal.
- **`inv_vol` lowers the return on every book**, at every cost. It has the highest NW t on 3 of the 6 books, because
  it moves weight to the quietest pairs, which also pay the least.
- **`persist` is the equal book with noise:** −0.37 to +0.07 bp/day at 2x.

## Reported, not decided on
**Break-even cost.** This is the cost per leg per side at which the best variant's edge over equal reaches zero, from
the 1x and 2x differences (linear in cost):

| Book | Best variant | Best − equal at 1x / 2x / 3x (bp/day) | Break-even |
|---|---|---|---|
| R278 A | spread_vol | +0.49 / +0.08 / −0.34 | 15 bp |
| R278 B | spread | +0.77 / +0.56 / +0.35 | 33 bp |
| R278 C | spread_persist | +2.38 / +1.47 / +0.55 | 25 bp |
| batch | spread_persist | +1.16 / +0.79 / +0.42 | 29 bp |
| R279 A | spread_persist | +1.18 / +0.82 / +0.46 | 30 bp |
| R279 B | spread | +0.79 / +0.40 / +0.01 | 21 bp |

**By year (best − equal at 2x, bp/day).** The tilt earns in 2025-26 and about nothing in 2022-24.
- **batch:** 2021 +1.14, 2022 +0.03, 2023 −0.29, 2024 −0.55, 2025 +3.06, 2026 +1.55.
- **R279 A:** 2021 +0.81, 2022 +0.10, 2023 −0.17, 2024 +0.02, 2025 +1.51, 2026 +3.24.
- **R279 B:** 2021 +0.65, 2022 −0.29, 2023 0.00, 2024 −0.12, 2025 +0.66, 2026 +1.89.
- **R278 C:** 2025 −0.08, 2026 +2.82.

## Reading
- **The spread tilt is a bet on the widest spreads.** In 2025-26 those are the low-cap coins with high funding.
  - R280 found the books' short legs pumped 95% or more within a day on 155 days, 137 of them in 2025-26.
  - The sized books hold their largest pair at 2.5-2.9 slots on average, and the largest weight goes to the widest
    spread by construction.
  - So the extra 1x return comes with a larger version of R280's liquidation risk, and these books were not
    re-run through R280's margin model.
- **Lower costs:** at 7 bp per leg per side or less, all six books earn more with `spread` or `spread_persist`. The
  owner's zero-maker-fee MEXC contracts are in that range.
  - This is not a pass.
  - The decision was fixed at 2x, and no lower-cost test was registered.
  - A lane at maker cost would need a new id, a frozen PREREG, and fresh days or the reserved batch. These years are
    read.
- **Prior:** R217 also found that confidence scaling of the flow books had no out-of-sample support. Two tests of
  confidence sizing have now been null.

## Not modelled
- **Order-book depth at weight 3.** A $10k book puts up to $750 on one leg, three times R278's $250 capacity note.
- **Liquidation of the sized legs** (R280's model on these weights). See Reading.
- **Marks, fills and collateral moves.** The same limits as R275.
