# R257 mixed_signals_v1 — NULL

## Decision

The discovery-selected mixture does not improve on the separately discovery-selected
plain-trend control. Four of five frozen validation requirements fail. All 36 rules
were tested, including the reversal-heavy bear templates; no validation reranking
or retuning was performed. This exact family is closed by this NULL result, not
every possible combination of trading methods.

Frozen code/spec commit **8765740** was pushed before the first outcome calculation.
Runner SHA-256: `d312aa6b1493682cba196dd6ed7065f73dfbd3d00e50b963909eb8152a96d29f`.
Prereg SHA-256: `0360355e30af42f58eca62c6df74e08ee9b6fbf92e74c74910406b8a069b37c8`.
The unfinished R254 draft was reassigned to R257 before freezing/outcomes to
respect the coordination room's disjoint round blocks. No old frozen file changed.

## Selected executable rule

BTC trailing 56-day return determines the regime. In bull: 75% of the
plain nine-channel trend target plus 25% of the top-three 28-day momentum target.
Otherwise cash. Discovery-only capital scale is 0.8258035704, control scale 1.
Signals wait a full daily bar; combined holdings execute in one self-financing
account with drift, initialization, daily rebalance and terminal exit costs.
All three full cost paths were actually rerun, not inferred from a saved net path.

Validation: 547 days, 2024-01-01 through 2025-06-30.

| One-way costs | Mixture mean bp/day | Trend mean bp/day | Mixture cumulative net | Trend cumulative net |
|---|---:|---:|---:|---:|
| 12 bp (1x) | 9.5636 | 10.0051 | 55.9682% | 58.5966% |
| 24 bp (2x) | 8.7914 | 9.4001 | 49.5243% | 53.4455% |
| 36 bp (3x) | 8.0193 | 8.7951 | 43.3466% | 48.4617% |

Positive standalone historical returns do not establish an added edge. The paired
1x mean difference is **-0.4415 bp/day**, 30-day-block 95% interval
**[-3.6781, +3.1440] bp/day**; 36-family max-statistic p **0.9726055**.
Sharpe is 1.07636 vs 1.07763 (required gain +0.15); compound drawdown is
28.9963% vs 25.6501%. Only the positive 2x mean gate passes. Block 10/60
sensitivities also fail and cannot rescue the verdict. All pair/control/split/cost
metrics, including descriptive known_holdout, remain in the artifacts.

## Verification and limits

355 unit tests pass, including 12 new synthetic tests for causal prefixes,
full-bar delay, actual holdings drift, self-financing fee arithmetic at 1x/2x/3x,
discovery-only selection, registration guards and deterministic output.
A fresh-directory rerun reproduces all nine result files byte-for-byte.

Inputs are the existing publisher-checksummed daily Binance SPOT cache for six
surviving major coins. No new market download. These dates and related mechanisms
were already seen; every split is exploratory gate 0. This does not demonstrate
MEXC perpetual execution, funding, short availability, capacity or new prospective
paper evidence. The components all use prices and are not independent alpha sources.
No live bot, paper lane or scheduler was launched. A later different rule requires
a new finite frozen study; a pass would still need genuinely new on-time days.

## Reproduce

```sh
NUMBA_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 python scripts/run_mixed_signals.py \
  --raw-dir /workspace/quant-small-data/slow_trend_v1/raw \
  --out /new/empty-path-r257
```

Use the pinned dependencies and versions recorded in manifest.json. The output
path must not already exist. The source cache is not duplicated in this PR.
Owner requested completion then stop: no further grid or background job is pending.
