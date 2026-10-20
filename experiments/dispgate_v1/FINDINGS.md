# FINDINGS: dispgate_v1 (R260). Halve the flow books in high-dispersion alt bear markets

**Verdict: NULL.** All three gated books lost Sharpe against constant size in both windows.
- **Discovery Sharpe gain:** G-A -0.05, G-B -0.00, G-X2 -0.05. The test required > 0.
- **Validation Sharpe gain:** G-A -0.05, G-B -0.02, G-X2 -0.04. The test required +0.15.
- **The days the rule halves are not the books' bad days.** In discovery they were the books' best stretch.
- The holdout was not read.

- **Registry row:** R260 (trials 3). Program trials on this branch after it: 9,472,037.
- **Id:** R260, claimed on issue #7 before the freeze.
- **Gate:** 0.
- **Reproduce:** prereg sha 8d45ae97, frozen in commit 6298b06 before the run. Run `python scripts/run_dispgate.py`
  (about 1 minute).
- **Parity:** books A, B and X2 equal R217's `daily.npz` exactly (max |diff| 0).
- **Origin:** queue M003; rule #7 of `docs/SIZING_EVIDENCE.md` (the momentum-crash rule).

## When the gate was on (m = 0.5)

| Window | Half-size days | Top-tercile D30 | Alt 90 d < 0 | Episodes |
|---|---|---|---|---|
| Discovery 2021-01..2023-12 | 2.2% (24 days) | 8.2% | 49.1% | 2022-05-17..18 and 2022-05-20..06-10 (after LUNA, into 3AC) |
| Validation 2024-01..2025-06 | 18.6% (102 days) | 47.7% | 42.4% | Four short ones in Oct 2024 and Jan 2025, 2025-02-03..05-08 (95 days), 2025-06-01 |

- The rule needs 30 + 180 days of history before D30 has a tercile, so it could not fire before about August 2021.
- **High dispersion and a falling alt index rarely coincided before 2024.** In 2025 they coincided for three months.

## Books (per window, at 1x / 2x / 3x costs)

| Book | Window | Gated bp/day 1x / 2x / 3x | Control bp/day 1x / 2x / 3x | Sharpe 1x, gated vs control | Max DD 1x, gated vs control | Paired diff bp/day 1x (NW t) |
|---|---|---|---|---|---|---|
| G-A | Discovery | +10.67 / +7.70 / +4.73 | +11.19 / +8.20 / +5.21 | 1.76 vs 1.81 | 24.0% vs 24.0% | -0.52 (-1.28) |
| G-A | **Validation** | +12.22 / +6.85 / +1.49 | +13.60 / +8.00 / +2.40 | 1.34 vs 1.39 | 26.5% vs 26.1% | -1.38 (-0.95) |
| G-B | Discovery | +3.87 / +3.33 / +2.78 | +3.90 / +3.35 / +2.81 | 1.28 vs 1.28 | 10.8% vs 10.8% | -0.03 (-0.62) |
| G-B | **Validation** | +6.43 / +5.22 / +4.01 | +6.99 / +5.77 / +4.54 | 1.18 vs 1.20 | 15.6% vs 15.6% | -0.57 (-0.67) |
| G-X2 | Discovery | +14.89 / +11.30 / +7.72 | +15.47 / +11.85 / +8.24 | 1.91 vs 1.96 | 24.6% vs 24.6% | -0.58 (-1.24) |
| G-X2 | **Validation** | +18.08 / +11.50 / +4.92 | +19.68 / +12.75 / +5.82 | 1.64 vs 1.68 | 27.5% vs 27.5% | -1.61 (-1.04) |

Gated book per year at 1x (bp/day):
- G-A: 2021 +1.7, 2022 +4.5, 2023 +25.9, 2024 +8.1, 2025 H1 +20.7.
- G-B: 2021 +0.5, 2022 +1.2, 2023 +9.9, 2024 +3.6, 2025 H1 +12.1.
- G-X2: 2021 +2.1, 2022 +6.1, 2023 +36.5, 2024 +12.7, 2025 H1 +29.0.

- **Validation drawdowns:** the gate never lowered a drawdown. G-A's was slightly deeper (26.5% vs 26.1%).
- **Discovery drawdowns:** unchanged, because the gated days fall outside the deepest one.

## What the constant-size books earned on the gated days (control mean, bp/day at 1x)

| Book | Discovery: gated days / other days | Validation: gated days / other days |
|---|---|---|
| A | **+44.1** / +10.5 | +11.5 / +14.1 |
| B | +2.5 / +3.9 | +5.0 / +7.5 |
| X2 | **+49.7** / +14.7 | +14.0 / +21.0 |

- **Discovery:** the 24 gated days came after LUNA. On those days books A and X2 earned 3.4-4.2 times their mean on other days, and halving them gave that up. Book B earned less on them (+2.5 vs +3.9), but too few days to matter.
- **Validation:** the books earned less on gated days, 18-33% below their other days, but still well above zero. Halving a day that earns 80% of the usual mean costs more than it saves.

## Cost sensitivity
- Resizing on 126 days adds little turnover. The paired difference barely moves with cost: G-A goes from -1.38 bp/day at 1x to -0.92 at 3x.
- Every gated book stays positive at 3x in both windows. That is the flow books' own result, not the gate's.
- **Costs do not decide this verdict; the gate's timing does.**

## Reading
- **The rule cuts exposure in momentum crashes.** Momentum books lose when dispersion is high and the market is
  falling, because past losers rebound.
- **The flow books fade the crowd short.** They earned most in the same post-crash stress (R233 found them profitable in
  falling high-volatility regimes). So the rule removes profit, as the PREREG expected.
- **M003 can be closed for these books.** A dispersion gate would need a book that loses in stress, and the lab has no
  confirmed one to apply it to.
- **Read against the program:** 9,472,037 trials. Paired difference t-values from -0.6 to -1.3 say only that the gate did
  not help.

## Not checked
- Other thresholds (top quintile, a 60-day lookback) or a breadth measure instead of dispersion. Each would be a new lane
  and would be fitted after this read.
- The gate on the momentum and trend books of R238/R242, where the rule's rationale applies. Neither book passed
  validation, so there is nothing to protect.
- The holdout (spent at program level).
- `missing="raise"`: this lane uses the legacy path, as required for parity with R217.
