# R253 optimizer_v1: static risk allocators do not improve the incumbent

**Verdict: NULL.** Equal risk contribution was selected on discovery, then failed the frozen validation criteria.
This result concerns exactly three static A/B/X2 allocations; it does not close dynamic allocation, other signals,
other covariance definitions or other markets.

The specification, implementation and synthetic tests were frozen and pushed in commit `fd57e69` BEFORE any lane
outcome was computed. Spec SHA-256: `7c05a75c5a20665b116b4828b383ce1297c9749452df864e2db625dc0e2fb0aa`.
Source versions and actual reading scope: [SOURCES.json](SOURCES.json). All dates are spent, exploratory gate 0.

## Main evidence

| Method | Weights A / B / X2 | Validation Sharpe | Candidate / matched incumbent DD | Mean bp/day 1x / 2x / 3x |
|---|---|---:|---:|---:|
| min_variance | 0.0% / 100.0% / 0.0% | 1.201 | 15.57% / 11.67% | 6.993 / 5.767 / 4.540 |
| equal_risk | 24.2% / 56.9% / 19.0% | 1.529 | 18.31% / 16.01% | 10.994 / 7.631 / 4.267 |
| hrp | 10.4% / 83.2% / 6.4% | 1.379 | 16.08% / 12.64% | 8.488 / 6.443 / 4.399 |

The incumbent is R228's previously selected 30% B / 70% X2. Its validation Sharpe is
1.688. Each drawdown comparison uses discovery-only risk matching, scaling the
higher-risk side down without leverage. Drawdowns are additive fractions of fixed reference notional, not
compounded account-NAV drawdowns. The risk scale for the selected candidate is 1.0; incumbent scale
0.687740.

Selected validation Sharpe difference: **-0.159** (required >=+0.15).
The paired mean gain is only **+0.076 bp/day**, 95% circular-block interval
**[-2.219, +2.318] bp/day**; three-method family-max diagnostic
p=0.544. The 10/60-day block sensitivities also span zero. Candidate mean remains positive at
2x/3x, but its validation drawdown is larger than the matched incumbent's. Four of six decision conditions fail.

## Cost and account interpretation

1x daily paths are the exact saved R217 net streams combined at constant sleeve weights. 2x/3x means are exact
weighted source summary means. Their daily paths, Sharpe, drawdown, t and intervals are unavailable and remain NA.
There is no average-fee path fabrication, cross-book netting refund, NAV-rebalance model or switching-cost claim.
This is segregated fixed-reference accounting. The portfolios share the same underlying signals and inherit the
original archive's data-quality/fill assumptions; no raw market panel was reconstructed here.

The known holdout remains descriptive in the tables. In particular, minimum variance reduces to B alone; any
attractive B holdout statistic is an old sleeve on spent dates and cannot replace the discovery-selected method or
rescue this validation failure. No MEXC transfer, executable fill, fresh prospective day or real-money claim follows.

## Validation and reproduction

- All 321 repository tests passed before freeze, including 11 new synthetic tests.
- An independent reviewer compared all allocators on 300 synthetic positive-definite matrices: minimum-variance
  objective vs SciPy SLSQP differed by at most 4.75e-14; ERC weights vs independent convex/root solves by 7.39e-11;
  HRP weights vs independent single-linkage/tree allocation by 3.34e-16. Reference-solver retries were synthetic
  checks only; the registered solver did not change. Optional recipe: `verify_synthetic.py` (SciPy required).
- Provenance guards run before outcomes are loaded; frozen specs and dependency/input hashes are pinned.
- A second run into a fresh directory reproduced all seven actual result files byte for byte. The final integrity
  audit has 0 errors, 68 verified frozen specifications and the same 12 historical warnings.
- Reproduce from repository root with `NUMBA_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 python scripts/run_optimizer.py
  --out /tmp/optimizer-r253-fresh` using a fresh directory. The original nonempty results directory is protected.
- `metrics.csv`, `risk_matched.csv`, `selection.json`, `bootstrap.json`, `manifest.json`, `verdict.json` and the
  deterministic `selected_daily.csv.gz` contain the reproducible result. No raw-market download was performed.

Three new method trials are appended once through `lab.registry`; controls, internal simplex faces, resamples and
14 owner-scope extraction records are not added market trials. M027 retains PARTIAL scope: these static definitions
are now tested; dynamic/rolling variants and other universes remain open. Existing forward decisions are unchanged.
