# PREREG: capsizing_v1 (R496). Does sizing each carry trade by its ENTRY spread beat a fixed size, out of sample?

Freeze with `lab.prereg.freeze()` before any validation trade is read. After that this file is never edited.

- **Registry id:** R496
- **Owner (single writer):** OpenHands agent, branch `openhands/session-persistence-factor-report`
- **Date registered (UTC):** 2026-11-15

Method M545. Gate 0. **No reserved sample is read.** The trades are R277's already-published archive
trades; the split below is what makes the test honest, not a fresh sample.

## Question
Does a size rule driven by the **entry-time funding spread** produce more net dollars than a fixed
size on **unseen** trades, at 1x/2x/3x cost?

## Why this is not look-ahead
`spread_in_ann` in `experiments/xfund_kd_v1/results/trades.csv` is written at entry by
`lab/xfund.py::replay` from `p.spread_in`, which `Book.entries` takes from
`u.candidate(c, vset, d, lookback)` — the trailing spread over the lookback **through day d**, the
same quantity the frozen entry threshold already uses. It is known before the trade is placed.
**Realised `price_pnl` and `funding_pnl` are never used to choose a size.** An earlier exploratory
look showed that filtering on realised gross would "save" $147k; that was rejected as look-ahead and
is not tested here.

## Prior art (the equation is not novel)
`n* = (g/(a(1+beta)))^(1/beta)` under `cost = a·n^beta` is standard: **Almgren (2003)**, *Applied
Mathematical Finance*, DOI `10.1080/135048602100056`, whose abstract states impact is "a power law
function of the trading rate, with an arbitrary positive exponent... includes... the square root
law". What is tested here is not the closed form but **whether an ex-ante spread forecast is good
enough to exploit it net of cost**. `research/CAPACITY_EQUATION_20261115.md` carries the correction.

## Data
- Trades: `experiments/xfund_kd_v1/results/trades.csv` (R277, 3,156 executed carry trades, committed).
- Cost curves: measured **per venue** by `scripts/record_kucoin_costs.py` in this lane for **KuCoin**
  and **dYdX**, the two venues R495 did not cover. Every R277 trade touches KuCoin or dYdX, so this
  removes the cross-venue mismatch an audit flagged (R277 pairs vs R495's binance/gate curves).
  Binance and Gate curves are read from R495's committed `experiments/bgcosts_v1/results/books.csv`.
- Endpoints, public and keyless: KuCoin `api-futures.kucoin.com/api/v1/level2/snapshot` and
  `/api/v1/contracts/<sym>`; dYdX `indexer.dydx.trade/v4/orderbooks/perpetualMarket/<sym>`.
  **KuCoin sizes are contracts** and are scaled by the contract `multiplier`; dYdX sizes are in base
  units. A contract with no multiplier is skipped, never priced as if it were coins.

## The rule (one, frozen)
For each trade, at entry:
1. `g_hat = k · spread_in_ann · (hold_days_expected / 365)`, i.e. the entry annualised spread converted
   to an expected per-trade gross. **`k` and `hold_days_expected` are fitted on DISCOVERY only.**
   `hold_days_expected` is the discovery median hold; `k` is the discovery OLS slope of realised gross
   on `spread_in_ann · hold/365` **through the origin**, no intercept.
2. `n = constrained_notional(g_hat, a, beta, depth_usd, fit_range=(1000,10000), capital_cap=10000)`
   using the **worse** of the trade's two venue curves (conservative: both legs must be paid).
3. If `g_hat <= 0`, take the minimum tradable size (1,000), not zero: skipping is a different rule and
   is not tested here.

**Baseline:** fixed $10,000 on every trade, the size the lab's $10k cost benchmark implies.
Both are scored on the same trades with the same measured curves.

## Splits
- **Discovery:** trades with `entry < 2024-01-01`. Fits `k` and the hold median. Nothing else.
- **Validation:** trades with `entry >= 2024-01-01`, **read once**, after this freeze.
- No reserved sample, no 2020 rows, no forward day. This is a split of an already-published archive,
  so it is gate 0 and cannot confirm anything out of sample in the program's sense.

## Statistic and gates
Net dollars per trade `= n · (gross_realised − cost(n)/1e4)`, summed over validation trades, for the
rule and for the baseline, at cost multiples **1x, 2x, 3x** of the measured curve.
- **Primary:** total net dollars of the rule minus the baseline, at **1x**, on validation.
- **PASS** if that difference is **> 0** AND its **moving-block bootstrap 95% CI excludes 0**
  (block 20 trades, 2,000 reps, seed 20261115, resampling trades in entry order) AND the difference is
  still **> 0 at 2x**.
- **FAIL** otherwise. A FAIL is recorded as NULL with the same care.
Reported, deciding nothing: per-trade means, hit rates, the fitted `k`, the share of trades bound by
each constraint, and the same comparison at 3x.

## Multiplicity
**Trials: 1.** One rule, one baseline, one split, decided once. Program trials before: **9,785,317**;
**9,785,318** with it. The discovery fit is two parameters on 1,445 trades, disclosed above.

## Limits stated before the read
- Cost curves are **one snapshot per venue**; R224 needed 102 for a stable surface.
- Current listings only: a delisted contract has no measurable book and is scored at its venue's
  median curve, which is stated per trade in the output.
- The gross forecast is a single linear map from the entry spread. It is deliberately simple; a
  better forecast is a new lane.
- The archive's trades were selected by R277's frozen entry rule, so this tests **sizing within that
  rule**, not a new entry signal.

## Stop rules
One run of `scripts/run_capsizing.py`. No new parameters, splits, venues or thresholds after the
validation read. A crash fixed after the freeze is documented in FINDINGS with the changed sha.

```inputs
ffdd939197d8570bc6f5ed6425a6739dfa266a7565b51528a9b4118ddd4d7aa0 experiments/xfund_kd_v1/results/trades.csv
8867c8b16465fb38138d63f1aab234319523bcd11eec3d6629bb146e3d66bd9e experiments/bgcosts_v1/results/books.csv
42cc56035730ef66ed65be6c4cdc98318542f9ea5d52a594a4abf6e4bca1233b scripts/run_capsizing.py
ba5664017ddf94f50cebecad0310556958a446ff25e48369d7eaefd05045ec05 scripts/record_kucoin_costs.py
df3fe38961200e8e4ae0ccd2a71dec3380fd11fd3c94f60fb9cbf599355c0e8c tests/test_run_capsizing.py
e1bab9d4ec42d968bd37e27056132a7064693b9fb720e00f85f6a02aedb9c146 lab/capacity.py
```
