# Integrity and confidence follow-up (2026-10-19)

This follow-up records the code-level fixes and the sizing conclusion after the R217-R219 work. It does not reopen a
frozen lane or turn an exploratory result into a trading approval.

## Changes that affect false edges

- `lab.atlas.forward` now requires every return in a multi-hour label to be finite. The old prefix-sum path treated an
  internal gap as a zero return; `require_complete=False` remains available only when reproducing an old result.
- `lab.nulls.null_shifts` samples unique placebo shifts without replacement. `familywise_p`, SPA and MCS p-values use
  the finite-bootstrap plus-one correction, so a finite null cannot report a literal zero.
- `lab.search.shifted_returns` requires the discovery-window limit. A caller must choose the window explicitly instead of
  accidentally circularly shifting validation or holdout returns. The battery placebo keeps the hour and funding-clock
  phase random rather than rounding shifts to whole days.
- Pack hedge PnL now includes hedge funding. The real-money gate rejects non-finite returns instead of filtering only
  `NaN` values.
- The MEXC forward loader now caps scoring at a completed wall-clock bar and measures coverage at the delayed entry row;
  the numerator and denominator use the same entry date, including signals delayed across midnight. The scorer now
  reads those indicators from its state explicitly. Colliding source aliases abort before any price fetch or ticket,
  rather than counting the same MEXC contract as two independent instruments. Claude's closed-bar, failed-fetch and
  TradFi protections are retained.
- `panel.resample` marks incomplete OHLC/volume blocks as missing and exposes close coverage, so a sparse 4-hour or
  daily bar cannot silently become a feature input. Alignment expires the old value when a missing completed block
  arrives; smoothed higher-timeframe features also check that block's availability.
- Bootstrap inference rejects incomplete/non-finite matrices. An invalid statistic must not become a tiny p-value when
  every comparison with NaN evaluates false. The plus-one correction controls Monte Carlo resolution; it does not make
  a wrongly designed null exchangeable or remove serial dependence.
- The shared research holdout guard also checks the next-close dependency: `ret[t1-1]` uses `close[t1]`, so an
  evaluation ending exactly at an existing first holdout row is rejected unless the registered caller explicitly opts
  in. A synthetic panel ending before the cutoff remains usable. Battery R184 stays held; this fix does not implement
  its missing cost runs, decision rule or fold aggregator, or quantify historical impact.

These are integrity changes. Historical result files were not silently rewritten; any lane that uses the corrected
semantics needs a new run and a before/after record under its own ownership rules.

## What the sizing evidence says

R217 is a NULL against its predeclared bar. The square agreement book (a coin with `k` agreeing flow cells receives
`k²` slices) improved Sharpe over the linear control in discovery and validation, but the validation gain stayed below
the required 0.3. Its known holdout drawdown reached 62%. That is a concentration result, not permission to increase
live size. The time-series rules were worse than a constant multiplier; volatility targeting kept Sharpe roughly flat
while reducing drawdown, so it is a risk control rather than a new return edge. R218 is a separately registered forward
test of the square book.

The next sizing comparison should therefore be small and fixed before reading a fresh forward period:

1. constant exposure chosen in burn-in;
2. lagged, capped portfolio-volatility targeting;
3. one lower-confidence-bound multiplier;
4. the unscaled book.

For a forecast mean `mu`, standard error `se`, round-trip hurdle `h` and forecast volatility `sigma`, the confidence
candidate is bounded risk sizing:

```text
m = clip((mu - 1.645 * se - h) / sigma, 0, m_max)
```

`mu`, `se`, `h` and `sigma` must be available before the position is changed. The comparison must charge the exact
transition cost from `Q[t-1]` to `Q[t]`, report 1x/2x/3x cost stress, and compare every dynamic rule with a constant
multiplier having the same mean absolute exposure. A lower drawdown alone is a risk result; it is not evidence that the
multiplier predicts returns.

`lab/sizing.py` contains these bounded, causal primitives (`lagged_ewma_vol`, `volatility_multiplier`,
`lower_bound_multiplier`, `apply_multiplier`, and exact `turnover`) with synthetic tests. They are an implementation
building block for a new preregistered lane, not a retroactive rewrite of R217.

Missing or zero risk estimates default to zero size. An unavailable outcome resets EWMA history for the following
decision, and a positive minimum size cannot turn a negative lower bound into a trade. Invalid standard errors/cost
hurdles cannot increase conviction. Caps apply to the complete venue position matrix, including any hedge; adding a
hedge afterwards bypasses them. Matching applies the same caps to the dynamic and constant books. A constant matched
on the evaluation period is a descriptive control: freeze it in burn-in before deploying it.

The `1.645` coefficient is a prespecified uncertainty haircut. It is not a calibrated 95% probability after selection,
and this helper does not estimate `se` or correct overlapping observations. The caller must provide an appropriate
dependence-aware estimate. The caps also do not impose beta neutrality, margin requirements or liquidation limits.

Required synthetic controls are zero-drift IID returns, block-shuffled returns, a circularly shifted multiplier,
zero-return positive-cost returns, a planted state-dependent mean, and a one-bar-lag versus same-bar clock check. A
confidence rule that wins only without these controls is not ready for a venue-forward lane.

## Strict accounting for a new lane

`lab.slices.run_exact` is an opt-in venue ledger; the frozen `slices.run` convention is retained for existing lanes.
It chooses hedge members before reading the next return, constructs `Q = signal + hedge`, and charges each instrument's
actual target change `abs(Q[t] - Q[t-1])`. A basket switching from one coin to another pays constituent turnover even
when its total notional stays constant. Offsetting signal and hedge legs net before the venue order. This is a
fixed-notional target model, not a fill or contract-unit simulator.

The output reports signal gross, hedge gross, their sum before netting and actual venue gross after netting. A held
instrument with an unavailable return or trading cost makes the hour and its day missing; it is not reassigned to a
different basket member after seeing the outcome. A subwindow can supply prior holdings. Terminal liquidation is an
explicit choice requiring costs at the exit boundary, so continuous forward runs do not pay a fictitious daily exit.

Regression fixtures check basket changes, internal offsets, missing held/unheld prices, missing costs and hedge members,
continuation, terminal liquidation and 1x/2x/3x cost stress. Multipliers are applied to positions before accounting:
halving a base position while doubling its multiplier leaves the venue target unchanged and pays no rebalance.

R215/R218 still follow their frozen missing-return treatment described in
[`mexc_fwd/DEVIATIONS.md`](../experiments/mexc_fwd/DEVIATIONS.md). `run_exact` is not substituted into their existing
PnL or gates. A fresh lane is needed to compare the changed accounting and any new sizing rule on unseen outcomes.

R225's daily-net scaling and mean-gross resize charge are also explicitly approximate. The difference from position
accounting can arise without a hedge: base positions `1 -> 0.5` and multipliers `1 -> 2` keep the actual target at `1`,
so the exact rebalance cost is zero. A separate `abs(delta_m) * gross` charge would still be positive. The regression
fixture covers this interaction; preserve R225's frozen formula and use full target positions for a future comparison.

## Search discipline

The project has already run millions of correlated program trials. Brute force can generate hypotheses, but the null
must rerun the complete declared search and break the alignment being tested while preserving relevant dependence.
R219's lead-lag/catch-up books, R222's slow cross-sectional alternatives and R223's settlement-capture books are already
NULL net of costs. Read their results before proposing the same families again. Trade-size/print-count inputs and
positioning changes remain possible small mechanistic studies, with complete windows and incremental controls.

## Remaining work

- A newly registered strict forward lane: actual signal receipt time, complete outcomes, contract lifecycle, and a fixed
  champion/challenger comparison. Existing replay or spent holdout results cannot confirm the replacement.
- Execution on MEXC: account-specific manual/API fees, spread/depth, quantity steps, capacity, fair-price margin and
  liquidation stress. R224 now records book-depth costs; use that collector's prospective data rather than creating a
  duplicate. R225 independently runs R217's volatility-target rule forward. The stricter ledger here does not change
  either lane's specification. Listed fees and hourly close markouts do not measure executable PnL.
- Funding event timestamps/cycle changes and interior cache gaps; these still need dedicated collection/coverage tests.
- Dependence-aware uncertainty and purged validation for overlapping strategies. DSR's raw row count and CSCV's
  unpurged block splits are still diagnostics with limitations.

The pinned Python 3.12 test dependencies and GitHub Actions now make the complete suite reproducible without market
downloads. The regression tests use invented feeds, temporary journals and synthetic returns.

Verified locally: all 188 unit/synthetic tests pass, Python compilation passes, and the research-integrity checker
reports zero errors (existing legacy warnings remain). Frozen specifications and journals match Claude's `e8c3189`
base byte for byte.

No new market statistic or real-order action was taken for this note.
