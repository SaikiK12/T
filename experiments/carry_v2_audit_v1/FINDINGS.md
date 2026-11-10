# FINDINGS: carry_v2_audit_v1 (R437)

**Verdict: all 7 books SURVIVE the frozen rule (registry: DONE, CONFIRMED).**
- R275's carry family keeps its edge on its own archive once the three defects of the 2026-11-04 audit are fixed:
  - freshness that depends on bar length (H1);
  - constant-notional marks (H2);
  - dead legs valued at a stale last trade (F4).
- All four forward books survive: R278 A, B and C, and R390 A.
- The engine fixes do not cut returns; they raise them on five books. That rise comes from two sources, and neither
  should be counted as edge:
  - fixed-quantity legs whose notional, and so funding, grows when prices rise;
  - in the two Gate-and-Binance books, large positive "blowout" exits.
- With blowout and dead-leg trades removed (post hoc, descriptive), every book is back near its v1 level and its t rises.
- This is gate 0 on seen rows. It can only lower confidence, and it did not. The forward lanes remain the decider.

## Read
- **Run once** on 2026-11-10 with `scripts/run_carry_v2_audit.py --run` (exit 0, about 2 minutes). The PREREG
  (eb684ffd) and its inputs matched.
- **Order:**
  - PREREG frozen and registry row R437 appended in e566afe, then pushed, then the run.
  - The CLAIM was posted on #7 before the run.
  - Outputs in ce5b836.
- **Data identity:** in the run and at plumbing, v1 reproduced R275's frozen 1x daily net to 5e-11 on all seven books.
  It used the same archive and the same rule as R275.
- **Outputs:**
  - `results/books.csv` and `report.json`.
  - `results/daily.csv`: v1 and v2 daily nets at 1x, 2x and 3x.
  - `results/trades_v2.csv` and `run.log`.
  - The post-hoc diagnostic: `diagnostics/decomp.py` and `diagnostics/decomp.out`.

## Results (%/yr on book capital; costs 7, 14 and 21 bp per leg)
| Book | Forward | v1 1x | v1 NW t | v2 1x | v2 2x | v2 3x | v2 NW t | v2 halves bp/day | v2 2025+ bp/day | v2 max DD | v2 top-10-day share | Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gate+hyperliquid L14d th5% K20 | R278 A | +9.73 | 8.63 | +12.09 | +10.86 | +9.63 | 8.05 | +5.13 / +1.49 | +1.53 | -1.7% | 9% | SURVIVES |
| binance+hyperliquid L14d th10% K20 | | +8.63 | 8.95 | +10.33 | +8.72 | +7.10 | 8.73 | +4.27 / +1.40 | +1.42 | -1.2% | 11% | SURVIVES |
| binance+mexc L14d th10% K20 | R278 B | +6.33 | 4.80 | +6.05 | +4.68 | +3.30 | 4.55 | +2.44 / +0.88 | +1.66 | -0.5% | 38% | SURVIVES |
| binance+gate+hyperliquid+mexc L14d th10% K20 | | +13.21 | 7.68 | +16.99 | +15.41 | +13.83 | 4.77 | +2.89 / +6.42 | +6.76 | -5.9% | 33% | SURVIVES |
| gate+mexc L7d th10% K20 | R278 C | +16.29 | 7.38 | +18.08 | +14.76 | +11.45 | 6.06 | +4.10 / +5.80 | +4.95 | -1.9% | 39% | SURVIVES |
| binance+gate L14d th10% K20 | R390 A | +10.05 | 5.96 | +13.42 | +11.62 | +9.83 | 3.48 | +2.31 / +5.04 | +7.30 | -6.7% | 49% | SURVIVES |
| hyperliquid+mexc L3d th5% K20 | | +7.98 | 4.02 | +8.12 | +3.15 | -1.81 | 4.21 | +2.02 / +2.43 | +2.22 | -1.2% | 39% | SURVIVES |

- **Above cash:** every book's v2 1x beats R275's 4.13% T-bill hurdle. At 3x, hyperliquid+mexc turns negative
  (−1.81). It trades the most (L3d) and has the lowest margin over costs.
- **Exits under v2:**
  - Dead legs: 2 to 40 per book; blowouts: 0 to 22 per book.
  - The unobserved-interval rule bound on 2 to 72 pair-days per book.
  - Average pairs held barely moved (binance+gate 18.6 → 19.0).

## Why v2 is higher than v1 (post-hoc diagnostic, `diagnostics/decomp.out`; descriptive, no decision)
Annual P&L on book capital, split into funding, price and costs (v1 → v2):

| Book | Funding | Price | Costs | Price on blowout exits (v2) | Price on dead exits (v2) |
|---|---|---|---|---|---|
| gate+hyperliquid | 11.47 → 14.11 | −0.52 → −0.78 | 1.22 → 1.23 | −0.06 | −0.66 |
| binance+hyperliquid | 9.81 → 12.04 | +0.43 → −0.09 | 1.61 → 1.62 | +0.20 | −0.19 |
| binance+mexc | 7.58 → 7.60 | +0.11 → −0.18 | 1.37 → 1.38 | none | −0.12 |
| all four | 14.06 → 17.28 | +0.67 → +1.29 | 1.52 → 1.58 | **+3.39** | −1.46 |
| gate+mexc | 22.34 → 24.34 | −2.75 → −2.94 | 3.30 → 3.32 | +0.22 | −0.13 |
| binance+gate | 11.51 → 13.73 | +0.27 → +1.48 | 1.72 → 1.80 | **+3.46** | −1.26 |
| hyperliquid+mexc | 12.25 → 12.70 | +0.70 → +0.38 | 4.96 → 4.96 | none | −0.16 |

1. **Funding up by 2 to 3 points a year on the Hyperliquid and Gate books.** Under v2 a leg holds a fixed quantity,
   so its notional, and the funding on it, grows as the price rises. Returns are still divided by capital fixed at
   entry. In the 2023-2025 up-market the book was therefore partly more levered than v1's daily re-based legs. A real
   fixed-quantity position would collect this funding, but on rising margin. It is leverage drift, not new edge, and
   the v1 figure is the fairer capital-neutral number.
2. **Blowout exits carry +3.4 points a year of price P&L in the two books with both Binance and Gate.** Those books
   are all four and binance+gate. A blowout means the legs' price ratio moved more than 20% from entry. A
   cross-venue divergence that large, closed at a daily last-trade price, is exactly the kind of print whose
   executability is doubtful (thin Gate contracts, settlement and delisting moves). It is also what lowered these
   books' t (binance+gate 5.96 → 3.48; all four 7.68 → 4.77).
3. **Dead legs now cost money** (−0.1 to −1.5 points a year), as the audit's F4 predicted. v1 had been valuing them at
   stale prints.

**Sensitivity: v2 with the P&L of blowout and dead-leg trades removed day by day, costs kept (post hoc):**

| Book | Trades removed | 1x %/yr | 2x %/yr | NW t | Halves bp/day |
|---|---|---|---|---|---|
| gate+hyperliquid | 13 | +12.09 | +10.86 | 8.68 | +5.03 / +1.60 |
| binance+hyperliquid | 13 | +9.67 | +8.06 | 8.39 | +4.25 / +1.05 |
| binance+mexc | 4 | +6.13 | +4.75 | 4.68 | +2.44 / +0.92 |
| all four | 62 | +14.30 | +12.72 | 10.40 | +2.87 / +4.97 |
| gate+mexc | 7 | +16.55 | +13.23 | 5.86 | +4.10 / +4.96 |
| binance+gate (R390 A) | 62 | +9.69 | +7.90 | 8.35 | +2.29 / +3.02 |
| hyperliquid+mexc | 3 | +6.96 | +2.00 | 4.05 | +2.02 / +1.79 |

- Without those trades every book stays strong, and the t rises on the books that had blowouts.
- **Read:** the carry itself, net funding on held pairs, carries these books. The exotic exits do not.
- For R390 A, the defensible backtest figure is about +9.7%/yr at 1x (t 8.35), not v2's +13.42%.

## Read against the program
- **Program trials:** 9,784,979, including this lane's 7.
- These seven books were themselves selected as the best of R275's 560 by 1x t. This audit inherits that selection.
  It is not a new discovery and does not raise any book's evidence above R275 plus R286's blind 2020 pass (C14).
- **What it changes:** the main doubt from the 2026-11-04 audit was that the carry family's backtest was an
  accounting artifact. On R275's own venues it is not. The F4 estimate (+1.1%/yr of fake P&L) shows up here as dead-leg
  losses of 0.1 to 1.5 points a year, more than offset by the other fixes.
- The forward lanes keep their frozen accounting and stay the decider.

## Limits
- **Seen data, current-survivor universe** (R275's): gate 0 only.
- **Fills** are modelled at daily last-trade closes on both venues at 00:00 UTC. No mark prices were used (a
  PREREG choice, applied alike to all venues). Moving collateral between venues is not priced.
- **Fixed-quantity capital:** v2 reports returns on entry notional while the notional drifts. A margin-aware capital
  base (R280's leverage work) was not combined with v2 here.
- **The 20% blowout threshold** is v2's fixed constant and was not varied. The sensitivity table drops those trades;
  it does not re-price them at a realistic exit.
- **Costs** are R275's flat 7/14/21 bp per leg. R402/R404 measure long-tail book costs separately.

## Addendum (2026-11-10, measured in R438; post hoc, no decision changes)
Point 1 above ("leverage drift, not new edge") was an assumption. R438's `diagnostics/drift.py` measured it on these
seven books.
- **Drift is the source of the funding rise.** Pricing v2's funding on constant entry notional gives back v1's funding
  on the Hyperliquid books and on gate+mexc. On binance+gate (R390 A) and all four, about +1 point a year comes from
  the other v2 changes.
- **About half of the drift is leverage, the rest covariance.**
  - Average notional held is 0.91-1.12 times entry. That accounts for about half of the drift on the Hyperliquid books,
    gate+mexc and all four.
  - It accounts for almost none on R390 A: mean notional 1.014, drift +1.15.
  - The rest is a covariance: funding spreads widen on legs whose price rose since entry.
- **What this means:** a real fixed-quantity position would collect that covariance. v1 stays the conservative
  figure, but it is not the only fair one. Tables and caveats are in `experiments/carry_v2_audit_kc_v1/FINDINGS.md`.
