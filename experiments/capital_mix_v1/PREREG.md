# R309 capital_mix_v1: a fixed carry–spot allocation in units of capital

- **Registry id:** R309
- **Method:** M403 (new capital-allocation scope, related to M281; R285 remains unchanged).
- **Writer:** Codex, claimed in issue #7; ongoing consolidation PR #49.
- **Gate:** 0, historical exploratory diagnostic. One candidate trial, no optimized weights.

## Question and prior knowledge

Does putting half the initial capital into the frozen MEXC+Lighter carry book and half into the frozen slow
spot-trend account improve risk-adjusted capital returns relative to both parents and a passive substitution?
The owner requested convergence across economic families, not further combinations of correlated flow signals.

R228/R233/R253's flow mixes were NULL. R257's PR27 description reports 36 spot trend/momentum/reversal mixtures
NULL; its artifacts are not imported here. R285 already combines carry, flow and events as a standardized
statistical index and reports equal-capital diagnostics. It has no spot sleeve and leaves margin feasibility
unresolved. R309 changes neither its series nor its forward decision. R294 already paper-tests MEXC+Lighter.

The designer has read the parent specifications, FINDINGS, saved schemas and source contracts. In particular,
R229's primary spot trend failed its own benchmark test and lost money in its known-holdout account; R288's
MEXC+Lighter book reports positive historical funding carry, with optimistic close/margin accounting. These
facts influenced this design. The R309 arrays, correlations, portfolio outcomes and uncertainty have not been
computed before this freeze. All calendar dates are spent at program level; there is no new out-of-sample claim.

This is not a fee-only rescue, a new alpha family, a prop-account simulation or an allocation optimizer. A
positive result would support further capital/execution investigation only. A null stays recorded.

## Frozen versions and input contract

Input manifest SHA-256: 2bd59240e736954da393146c0cf07ff1c18d3dddd6c922fbce7d6899c0aa807e

`inputs.json` pins the exact two archived daily CSVs, parent specifications/sidecars and source code, the R229
run manifest, this runner, `lab/capital.py` and `lab/stats.py`. Runner `scripts/run_capital_mix.py` verifies
the frozen PREREG, its manifest hash and every pinned file before parsing outcomes. No download or raw-history
rebuild. Parent hashes identify inherited artifacts; they do not independently verify original raw prices.

- Dates: exactly 2025-07-01 through 2026-09-30, all 457 UTC DAY-OPEN labels. This is R229's complete
  known_holdout account. Normalize intervals BEFORE joining: spot labels the candle open date, whose close
  is the next midnight minus1ms; carry labels the END midnight of its daily interval. Subtract ONE day from
  each carry CSV date. Thus raw carry2025-07-02..2026-10-01 aligns with spot2025-07-01..2026-09-30.
  A literal-date join would shift the streams by a day and omit carry's terminal liquidation: it is forbidden.
  The1ms close/ending-boundary convention is inherited; no intraday timing precision is claimed.
- Spot: `experiments/slow_trend_v1/results/daily.csv`, four saved accounts `trend_vol`, `passive_matched`,
  `trend_plain`, `passive`, separately simulated at cost_multiple 1/2/3. Selected six surviving Binance spot
  coins BTC/ETH/SOL/XRP/DOGE/ADA; no funding, leverage or borrowing. The discovery-fixed passive risk scale
  0.11175514757239029 is inherited, never refit. Actual realized risks need not match.
- Carry: `experiments/xfund_lt_v1/results/daily.csv`, ONLY `mexc+lighter L14d th5% K20`, at 1/2/3 costs.
  Gross and funding are already divided by 2*K=40; gross INCLUDES funding. `legs` counts traded legs and `held`
  counts pairs. Require `net = gross - c*legs/40` within 1.1e-10 (source CSV rounding). Do not divide gross by40
  again, add funding twice, or add the three repeated cost-tier copies.
- To establish the carry inventory at the initial boundary, read ONLY the same book/tier's canonical
  2025-06-30 `held` (RAW carry CSV2025-07-01, the preceding interval ending at the new account's start).
  Add an entry expense `c*held/20` on day one, over and above subsequent native turnover: re-establish both legs
  of every inherited pair before the native day-one trades. This conservative extra boundary expense does not
  recreate trade-level positions or fills. Native final liquidation costs remain in the final source row.
- Spot initialization and final liquidation are already included in its complete split. Validate daily
  gross-minus-cost/net, cumulative NAV, nonnegative cash bounded by NAV, fee/turnover and terminal cash= NAV.
- Reject missing, duplicate, out-of-order or nonfinite selected rows, invalid leg/pair counts, broken identities
  or nonpositive sleeve/portfolio equity as INCONCLUSIVE. No fills, shortened calendars, replacement venue or
  retuning. Even a zero-weight comparator cannot conceal an insolvent source. No silent top-up/restart.

## Capital accounting and finite books

Each account starts with total capital1; a table also shows dollar PnL on initial capital10,000. The spot and
carry allocations remain segregated, with no cash transfer or periodic rebalancing between them. Unallocated
cash earns zero interest; this is an explicit no-exposure control, not a contemporaneous T-bill investment.

- Spot equity S[d]=product(1+spot_net[t]), t<=d. Its dollar gross and cost on d equal their archived return
  fractions times S[d-1]. Saved fee tiers are distinct self-financing accounts: do not reprice one spot path.
- Carry equity C[d]=1+sum(carry_gross[t]-c*legs[t]/40)-entry_cost. It uses a fixed INITIAL reference notional,
  never compounded daily. This preserves the parent's constant-notional model; it does NOT repair its known
  crash/stale-leg mechanics or certify margin solvency. No additional capital is supplied after losses.
- Portfolio equity E[d]=wS*S[d]+wC*C[d]+(1-wS-wC). Daily dollar PnL is its change. Actual portfolio return is
  dollar PnL/E[d-1], not dollar PnL compounded as though it were a return on current NAV. Funding is disclosed as
  part of gross. Costs are expressed in initial-capital dollars; gross-cost must reconcile to net PnL.

| Book | Spot account | Initial spot/carry/cash |
|---|---|---|
| carry_trend, sole candidate | trend_vol | 50/50/0% |
| carry_passive_matched, substitution control | passive_matched | 50/50/0% |
| carry_cash, de-risking control | none | 0/50/50% |
| carry, parent | none | 0/100/0% |
| trend, parent | trend_vol | 100/0/0% |
| passive_matched, parent control | passive_matched | 100/0/0% |
| trend_plain, diagnostic | trend_plain | 100/0/0% |
| passive, diagnostic | passive | 100/0/0% |
| cash, no-exposure control | none | 0/0/100% |

Every book is run at all three parent cost tiers. Spot uses12/24/36 bp per side; carry uses5.5/11/16.5 bp
per leg per side. Multiples are execution-cost stresses, not leverage and not identical venue schedules.
R288's1x MEXC cost assumption is slightly optimistic versus its published API schedule;2x/3x do not supply fills.

## Metrics, uncertainty and decision

For each book/tier report457-day ending equity, dollar profit on10,000, annualized profit divided by INITIAL
capital, CAGR, actual daily-return mean/volatility/Sharpe, NW(10)t, maximum peak-to-trough drawdown including
the starting1, and dollar gross/funding/cost totals. Report minima of the inherited source-account equities.
Sharpe uses sample std and sqrt365, risk-free rate0; a zero-variance series has a display Sharpe0. NW may be
undefined (CSV NaN), never a discovery. Parent capital bases remain explicit. Record date coverage.

Paired circular moving-block bootstrap:5,000 replicates; primary block30days and nondecisive10/60 sensitivities;
seed20261023309+block. Draw ceil(457/block) starts uniformly, wrap blocks, concatenate and truncate to457.
Use identical indices for candidate and every comparator, preserving contemporaneous dependence. Compute
candidate minus comparator Sharpe in each draw and percentile95% intervals. Also report paired daily dollar
PnL differences per initial capital (bp/day) and their intervals. The latter difference against
carry_passive_matched cancels carry exactly: it is a spot-inclusion diagnostic, not a diversification test.
Comparators in the uncertainty table are carry, trend, carry_passive_matched and carry_cash; the last asks
whether adding spot helps relative to leaving half the capital idle and is nondecisive.
Bootstrap resamples observed portfolio returns for conditional uncertainty, not execution paths or fills.

The sole candidate earns PARTIAL only if ALL hold:
1. Its1x Sharpe exceeds BOTH carry and trend standalone by at least0.15.
2. Both paired1x Sharpe-difference95% lower bounds at block30 are above0.
3. Its1x Sharpe exceeds carry_passive_matched's1x Sharpe.
4. Its1x maximum drawdown is no greater than trend standalone's.
5. Its total net profit is positive at BOTH2x and3x costs.

Otherwise NULL. No control, sensitivity, calendar, alternate weight or diagnostic can replace it. Failed
input/accounting validation yields INCONCLUSIVE, not a NULL economic test. No CONFIRMED verdict is possible.
The fixed candidate counts as one new trial even if NULL; comparators are controls, not searched candidates.
Program trials before R309:9,478,757. Bootstrap uncertainty does not adjust for all prior program selection.

## Artifacts and limits

Save metrics.csv, paired.csv, deterministic compressed daily.csv.gz, verdict.json and manifest.json containing
spec/input/output hashes, software versions, dates and extra carry entry charges. Existing output directories
are rejected. Reruns use a fresh --out path. Compact FINDINGS summarizes all costs and preserves every null.

The result is an accounting-consistent combination of two archived MODELS, not executable account evidence.
Carry's intraday margin, liquidation, cross-venue collateral transfers, stale-leg/constant-notional bias,
capacity and joint fills remain unresolved. Spot's survivor selection, close proxies and zero cash yield remain.
No actual index-fund or prop-firm candidate is tested here; those need eligible streams and account rules.
No download, market order, credential, new paper lane, scheduler or gate promotion. Further outcomes or allocation
choices require another finite specification, and any confirmation requires genuinely new prospective data.

Verification failures (untrusted code/spec/input bytes) stop without writing any output. After successful
verification, a selected-data/accounting failure writes only a fresh INCONCLUSIVE verdict receipt with its
error and spec hash; no partial economic tables. Existing output paths are always rejected.
