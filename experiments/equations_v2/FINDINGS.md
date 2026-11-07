# R311 — INCONCLUSIVE: the models run, but execution evidence and stressed net gain do not pass

Source-only repeat of R310, frozen and pushed in `60b727a` before outcomes.
PREREG SHA-256: `9d9372ecd4386cf5713fb28ef0213dfd15869e5a541fd39252dd115265accc61`.
The same twelve policies, controls, costs, dates and gates were retained. No
validation winner was substituted for the calibration choice.

## Source correction and scope

Recovered **1,318 actual Lighter funding events** using narrow queries with each
target strictly inside its request. Every addition matches its retained raw API
response; no original observation, price file or MEXC funding file changed.
All old R310 inputs/results remain intact. Combined acquisition used **7,757
requests and 229.85 MiB** response bodies, inside the original 8,000/250-MiB cap.
There was no interpolation or assumed zero payment.

All twelve policies now qualified for the calibration selection. The full
523-origin forecast archive contains 472/466/459 finite pooled basis coefficients
for H=1/7/14, and 487/493 finite AR coefficients for MEXC/Lighter. This resolves
R310's inability to exercise the 30-day and basis models; it does not prove alpha.

The fixed 117-pair R288 overlap is snapshot-conditioned and **not crypto-only**:
XPD is labelled palladium/TradFi/metals in the captured MEXC metadata. No symbol
was removed after results. Current lot rules, stablecoin parity and historical
trade-close funding-notional/fill proxies remain explicit assumptions.

## Registered comparison

Calibration alone selected **F0+B_h14**. Its leg-budget multiplier was 0.621660;
the reference's was 0.334328, with no leverage-up. These calibration-only budget
ratios do not guarantee equal realized validation risk.

Validation: 273 calendar days, 2026-01-01..2026-09-30, $10,000 total initial
capital segregated $5,000 per venue. The table reports **observed proxy dollar
totals including unscored intervals**, not fully verified funding cash or fills:

| Policy | 1x | 2x | 3x | Unscored days |
|---|---:|---:|---:|---:|
| Reference | +50.70 | -26.99 | -104.69 | 34 |
| F0_h1 | 0.00 | 0.00 | 0.00 | 0 |
| F0_h7 | +48.56 | +18.40 | -11.75 | 16 |
| F0_h14 | +82.87 | -13.70 | -110.28 | 39 |
| F1_h1 | +7.43 | +3.42 | -0.58 | 1 |
| F1_h7 | +48.04 | +17.20 | -13.64 | 16 |
| F1_h14 | +87.18 | -6.27 | -99.73 | 32 |
| F0+B_h1 | -2.91 | -4.08 | -5.26 | 1 |
| F0+B_h7 | +61.94 | +20.37 | -21.20 | 15 |
| **Preselected F0+B_h14** | **+100.52** | **-28.47** | **-157.45** | **36** |
| F1+B_h1 | +9.92 | +4.60 | -0.73 | 2 |
| F1+B_h7 | +47.63 | +15.85 | -15.93 | 18 |
| F1+B_h14 | +81.30 | +9.44 | -62.42 | 33 |

The selected account's decomposition at 2x was **+$235.47 funding proxy,
-$5.97 price PnL, -$257.97 cost = -$28.47 net**. It made 298 pair entries. Every
active policy's observed total was negative at 3x. F0_h1's validation zero was
inactivity, not a profitable strategy. F0+B_h7's positive 2x total cannot rescue
the preselected candidate after validation.

Only **224/273** days were common fully scored observations. The exact frozen
no-gap rule therefore returned **INCONCLUSIVE** and did not run SPA or selected
paired inference. No p-value or confidence interval is claimed. There was one
gross-breach day in F1_h14, none in the selected/reference accounts, and no
reported insolvency or terminal open leg in any policy/cost path.

## What blocks execution evidence

The remaining problem is largely the historical fill proxy, not the repaired
Lighter interior funding seams. Held-source diagnostics for the selected account
found **41 nontradable Lighter 01:00 candle observations across 34 days**, plus
five unknown MEXC funding observations. Neither selected nor reference had a
held missing-price observation. These are overlapping diagnostic counts, not
disjoint causal attribution of every unscored day; see `coverage_diagnostic.json`.

A known last traded close with zero volume is not a contemporaneous executable
quote. The frozen policy defers an unavailable exit and leaves that day unscored;
we did not manufacture a fill, remove those dates, or relax that rule afterward.
Likewise a funding schedule interval that cannot be certified stays unknown.
The next input requirement is synchronized, first-seen executable quotes/depth
and fair/index funding notionals, with explicit market-session availability.
More indicator combinations do not resolve these missing observations.

## Verification and current decision

- All **11 result artifacts** reproduced byte for byte in a separate folder.
- Independent signed-ticket/source-event reconstruction checked **40,716**
  venue/day/cost-tier balances; maximum absolute difference **$6.46e-11**.
  This verifies the stated proxy arithmetic, not historical execution or index prices.
- R310 and every earlier registry byte remain unchanged. R311 records 12 additional
  trials: **9,478,782** program trials, with R310/R311 in one decision group.
- Full Python suite: **1,060 tests, two skips**. The canonical intake/queue and
  generated views are reconciled without creating a second queue.

**No prospective paper lane is activated from this screen; zero new prospective
days exist.** The selected policy loses under the registered 2x stress scenario,
and complete common execution evidence is absent. Its positive 1x proxy result
does not establish a net executable edge. Historical dates are spent; source/rule
vintage, fair/index valuation, fill/latency/partials, margin, liquidation and
counterparty limitations remain. No orders, money movement, secret-value access, merge or recurring
research job were used.

Reproduction with the retained local source cache:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/run_equations_v2.py --out .cache/r311_replay
OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/run_equations_v2.py --audit-only
```

Use a fresh output path. Raw caches are local/ignored; the pinned manifests detect
source drift rather than promising that a future API fetch recreates the same vintage.
