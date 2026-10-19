# FINDINGS: sizing_v1 (R217): agreement across coins helps; scaling by the book's own confidence does not

PREREG sha 3d04ff8b. Run 2026-10-19 by `scripts/run_sizing.py`. Results in `results/` (daily nets and multipliers
in `daily.npz`).

## Verdict: NULL (no rule met the frozen bar)
The bar was a Sharpe gain of 0.3 or more over the control in both discovery and validation. No rule met it.

The closest was **X2, square agreement weighting**: a coin flagged by k of the three flow cells holds k² slices
instead of k, at matched gross exposure. Its Sharpe gain was +0.15 in discovery, +0.29 in validation and +0.45 on the
known holdout. The ordering cap (X1) < linear (A) < square (X2) holds in every window and at every cost level.

## Cross-sectional agreement (book A variants, matched mean gross exposure on 2021-23)

Values are bp/day, NW t (lag 10), Sharpe.

| Variant | Discovery 2021-23 | Validation 2024-25H1 | Holdout 2025-07..2026-09 (known) | Max DD (disc / val / hold) |
|---|---|---|---|---|
| X1: any flag = 1 slice | +7.6, t 2.40, 1.46 | +8.7, t 1.39, 0.99 | +8.8, t 0.64, 0.54 | 25% / 27% / 49% |
| A: k slices (control) | +11.2, t 2.88, 1.81 | +13.6, t 1.90, 1.39 | +21.9, t 1.22, 1.05 | 24% / 26% / 47% |
| X2: k² slices | **+15.5, t 2.99, 1.96** | **+19.7, t 2.22, 1.68** | **+42.5, t 1.70, 1.49** | 25% / 27% / 62% |

X2 at 2x/3x costs: discovery +11.9 / +8.2, validation +12.8 / +5.8, holdout +36.3 / +30.2 bp/day. A at 2x/3x:
discovery +8.2 / +5.2, validation +8.0 / +2.4.

Reading: where all three order-flow signals agree on a coin, the edge per unit of exposure is larger than where only
one fires. Concentrating size there pays. Scaling down agreement destroys a third of the edge.

The cost is concentration. X2's holdout drawdown is 62%, and R216 found two coins already carry most of A's holdout
gross. A forward test should report the per-coin contributions.

## Time-series confidence (the book's own past, applied the next day)

Values are Sharpe at 1x: discovery / validation / holdout. The control C0 is A 1.81 / 1.39 / 1.05 and
B 1.28 / 1.20 / 2.46.

| Rule | Book A | Book B | Mean multiplier, A (disc / val / hold) | Effect |
|---|---|---|---|---|
| R1 volatility target | 1.72 / 1.19 / 1.06 | 1.46 / 1.16 / 2.47 | 0.77 / 0.73 / 0.53 | Sharpe about flat. **Max DD falls**: A 24/26/47% → 15/23/27%; B 11/16/16% → 5/12/10% |
| R2 shrunk Kelly | 1.06 / 0.55 / 0.77 | 0.79 / 0.57 / 0.92 | 0.88 / 0.51 / 0.15 | Hurts everywhere: it sizes on noise and sits near zero after flat spells |
| R3 own performance (1.5 / 0.5 on the 60-day sum) | 1.66 / 1.29 / 0.87 | 0.74 / 0.72 / 2.08 | 1.04 / 1.27 / 1.18 | Hurts: the book's daily returns do not trend |
| R4 dispersion + falling market cut | 1.81 / 1.35 / 1.12 | 1.28 / 1.21 / 2.47 | 1.00 / 0.91 / 0.71 | About neutral; the cut never triggered in discovery |

## Cost sensitivity
The full 1x/2x/3x table is in `results/results.csv`. The ordering of the rules does not change with costs. Costs from
changing the multipliers are included: the scaled positions run through the same slice engine.

## What follows
- **R218, a new forward lane:** book X2 on MEXC prices and funding next to R215's book A, from 2026-10-20. It is
  registered as a hypothesis chosen after seeing this table, not as a pass.
- **The volatility target is a risk tool, not an edge.** It is worth applying to any live size, because it halves
  drawdowns at a similar Sharpe. It belongs in sizing, alongside the prop-firm drawdown limits (R202).
- **Do not scale by trailing Kelly or recent profit.** Both lowered Sharpe in every window.
- Trials 10. Program trials after this lane: 9,471,728. Under that count, X2's validation t of 2.22 is not evidence
  on its own.

## Not checked
Capacity and slippage when size concentrates in the coins where all three signals agree. Agreement weighting in other
books (only the three flow cells were tested).
