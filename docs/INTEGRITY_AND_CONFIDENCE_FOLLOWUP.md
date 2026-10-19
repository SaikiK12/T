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
  an open final kline or a symbol that disappears between signal and entry cannot become a completed ticket.
- `panel.resample` marks incomplete OHLC/volume blocks as missing and exposes close coverage, so a sparse 4-hour or
  daily bar cannot silently become a feature input.

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

Required synthetic controls are zero-drift IID returns, block-shuffled returns, a circularly shifted multiplier,
zero-return positive-cost returns, a planted state-dependent mean, and a one-bar-lag versus same-bar clock check. A
confidence rule that wins only without these controls is not ready for a venue-forward lane.

## Search discipline

The project has already run millions of correlated program trials. Brute force is useful for generating hypotheses, but
the null must rerun the complete declared search and preserve calendar phases. The next archive ideas should stay
mechanistic and small: trade-size/print-count features with complete windows, positioning changes, and a fixed
cross-coin residual/catch-up family. R219 already found an hourly big-coin lead before fees but it failed all net book
variants at taker costs. Do not expand the grammar until a candidate survives missing-data checks, matched-cost
controls, concentration reporting and a fresh forward period.

No new market statistic or real-order action was taken for this note.
