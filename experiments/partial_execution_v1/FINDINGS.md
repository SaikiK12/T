# R231 partial_execution_v1: NULL — less turnover loses more gross return than it saves at ordinary costs

Frozen 2026-10-20 at 00:33:06 UTC before this lane parsed cached prices. Specification SHA-256 `aa39f71d3ff0de24add19532eaec3fb4fbefac4496f6c6ff60314b7ca4a181a2`; runner SHA-256 `877bd5f471a09c553dbefcfdb075827109f04b11a5a5835827130e85c07560e3`. The source/indicator/execution dependency hashes are in the specification and run manifest. No parameter changed after outcomes.

## Verdict and what it means

**NULL.** Moving halfway toward the unchanged R229 trend target each day reduces validation turnover and modeled transaction costs by about 30.5%, but the lost gross return exceeds that saving at 1x and 2x costs. A cheaper implementation is not necessarily a better strategy.

The frozen discovery rule selects alpha=0.5: discovery 2x Sharpe is 0.826 versus 0.763 for alpha=0.25. The unchanged full-adjustment control scores 0.942; it was excluded from the new-policy selection pool by design, and already performs better than either candidate on discovery. This fact is retained rather than hidden by the later selection.

The selected policy fails two of its four validation requirements against the discovery-risk-scaled full-adjustment control:

- 1x Sharpe is **1.246** versus **1.261**, a change of **-0.015**, below the required +0.15.
- Paired 1x mean improvement is **-0.090 bp/day**, 30-day-block 95% interval **[-0.412, +0.226] bp/day**. Its lower endpoint is not positive.
- The positive validation 2x mean requirement passes: **3.607 bp/day**.
- The no-worse 1x compound drawdown requirement passes: **9.61%** versus **9.72%**.

The primary result remains NULL. The quarter-adjustment diagnostic, 3x tier and already-viewed holdout cannot rescue it. R229's underlying signal already failed its own passive comparison; changing execution does not independently discover a signal.

## Precise model and evidence

Reuse the exact frozen R229 `trend_vol` target and six surviving Binance spot coins: BTC, ETH, SOL, XRP, DOGE and ADA. Every trade uses target[i-2] at close C[i-1] for the return ending at C[i]. No signal acceleration, new filters, new horizons or new data were added.

At each daily execution, compute pre-cost weights from the **drifted units and current cash**, then set desired post-cost weights to `(1-alpha)*drifted_weights + alpha*unchanged_delayed_target`. Solve the exact self-financing fee equation with R229's frozen account code. This is a partial adjustment in portfolio weights; fees mean dollar trades need not be exactly alpha times another account's trades. Cash stays nonnegative; no leverage, shorting, funding or cash yield applies. Zero signal targets decay residual positions under partial adjustment. Every account starts cash-only and liquidates fully at the final split close, charging exits immediately.

The mechanism is informed by Gârleanu and Pedersen's public *Dynamic Trading with Predictable Returns and Transaction Costs* manuscript, cover dated July 21, 2009: [primary PDF](https://archive.nyu.edu/bitstream/2451/28346/2/DynamicTrading.pdf), SHA-256 `57dfb02b14775cf6ef79aafc6c55869593df98b0815bb87df63e27c9a456d42a`. The downloaded 513,117-byte paper describes partial adjustment under quadratic trading costs and predictable signals. Its optimality result does not transfer to these fixed fractions and proportional crypto fees. No market-data download was needed for this lane.

The discovery-fixed control scale is **k=0.9979618573**. At validation 1x, annualized realized volatility is **11.006%** for partial adjustment and **11.133%** for the scaled control; mean invested exposure is **13.080%** versus **13.046%**. The small training scale does not force an exact future risk match and does not remove every path-dependent exposure difference.

## Selected policy versus training-risk-scaled full adjustment, 1x costs

| Period | Days | Mean bp/day, partial / control | Sharpe, partial / control | Compound DD, partial / control |
|---|---:|---:|---:|---:|
| Discovery 2022–2023 | 730 | 1.911 / 2.222 | 0.896 / 1.041 | 6.65% / 5.47% |
| Validation 2024–2025H1 | 547 | 3.757 / 3.847 | 1.246 / 1.261 | 9.61% / 9.72% |
| Known holdout 2025H2–2026Q3 | 457 | -0.606 / -0.510 | -0.311 / -0.254 | 12.02% / 12.68% |

Validation NAV from cash 1 is 1.21703 for the selected partial policy and 1.22277 for the matched full-adjustment control. Known-holdout NAV is 0.96962 versus 0.97369. All historical splits have been viewed before: the named holdout is descriptive reuse, not fresh confirmation.

The nonselected quarter-adjustment policy has validation 1x mean 3.866 bp/day, Sharpe 1.291 and drawdown 9.10%. It was not selected on discovery, cannot replace the primary, and is not nominated for forward use. Its known-holdout 1x mean is -0.675 bp/day. Complete results for both new candidates are preserved.

## Cost stress and gross return forgone

All three cost tiers were resimulated with separate self-financing paths. One-way modeled costs are 12/24/36 bp at 1x/2x/3x; these are R229's frozen assumptions, not verified account fees or real fills.

| Period | Selected mean bp/day, 1x / 2x / 3x | Selected compound DD, 1x / 2x / 3x |
|---|---:|---:|
| Discovery | 1.911 / 1.762 / 1.612 | 6.65% / 7.37% / 8.09% |
| Validation | 3.757 / 3.607 / 3.457 | 9.61% / 9.88% / 10.14% |
| Known holdout | -0.606 / -0.784 / -0.962 | 12.02% / 12.57% / 13.12% |

To isolate the execution change, the following validation decomposition uses the **unscaled** full-adjustment control. Every component is an average daily return contribution normalized by its own account's preceding NAV, not a common-notional dollar PnL. The identity is `net improvement = cost saving - foregone gross return`.

| Validation cost tier | Cost saving bp/day | Foregone gross bp/day | Net improvement bp/day |
|---|---:|---:|---:|
| 1x | +0.06593 | 0.16369 | -0.09776 |
| 2x | +0.13185 | 0.16359 | -0.03174 |
| 3x | +0.19778 | 0.16349 | +0.03428 |

At 1x validation, mean daily modeled costs fall from 0.21604 to 0.15011 bp/day and summed turnover from 9.84768 to 6.84243 of marked pretrade NAV. A small advantage appears at 3x costs, while both 1x and 2x lose net return; this is a sensitivity result and cannot replace the frozen primary tier. `decomposition.csv` retains every split/tier for both new fractions against both controls.

## Uncertainty, provenance and checks

The 30-day paired bootstrap uses 5,000 circular-block replicates. The nondecisive 10- and 60-day 95% intervals are **[-0.495,+0.290]** and **[-0.355,+0.178] bp/day**, respectively. All include zero. The fixed seed is `20261020231+block`. These are conditional historical uncertainty intervals, not program-wide multiple-testing correction. The starting repository already records **9,471,788 raw program trials**; the two new adjustment policies add two trials, alongside separately registered parallel lanes. A future fresh study would be required for a validation claim.

All 36 policy/split/cost accounts and **20,808 daily rows** are saved. Every one of the **5,202 unscaled full-control daily rows** reproduces frozen R229's archived returns, gross/cost decomposition, turnover, exposure, NAV/cash and held units **exactly**, across all splits and all cost tiers. An independent analytic piecewise-linear fee solver, rather than the runner's bisection method, reconstructed all 36 accounts: maximum absolute discrepancy **6.98e-14** across 20,808 rows. It independently recomputed the discovery policy choice and risk scale from exported returns.

The full repository suite passes **204 tests** (63.533 seconds), including seventeen new synthetic tests covering drifted-weight adjustment, full-control equivalence, fees/cash and final exits, residual positions, daily delay, no borrowing, training-only selection and scaling, tie handling, invalid inputs, provenance/output guards and deterministic bootstrap. A fresh-directory market rerun reproduced all six result artifacts byte for byte; every saved output SHA-256 verifies. Frozen specification and dependency hashes remained unchanged.

Reproduce with the original R229 cache present:

```sh
python3 scripts/run_partial_execution.py --out /tmp/partial_execution_fresh_results
```

The destination must be fresh and empty. The runner verifies its frozen spec/dependencies, the original R229 snapshot and its original source checksums before loading values. It performs no network access. `results/run_manifest.json` preserves source URLs and original archive hashes through the R229 manifest, all executable hashes, selection scores, software versions and derived output hashes. Original frozen files and old results are untouched.

## Scope of the conclusion

This result closes the fixed alpha=0.5/0.25 partial-adjustment screen on the unchanged R229 target and reused six-coin spot snapshot. It does not exclude all execution controls, calibrate live fill uncertainty, or settle the originally proposed slow-flow version, which still lacks raw target history here. It does not test order-book capacity, futures funding, broader point-in-time universes or a prospective period. There is no newly validated live-trading edge in this experiment.
