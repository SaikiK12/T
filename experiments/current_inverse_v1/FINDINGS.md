# R340 — PARTIAL: fee reserves and sale hurdles; current API access blocked

Acquisition freeze `4e4512b` preceded dispatch; economic freeze `d24b05f` preceded
the finite report. **Actual executable expected return remains UNKNOWN**, with
zero new predictive trials or prospective days. The original independent oracle
stopped on its own exact-type mismatch; that failure is retained, not a PASS.
R341 registers a separate checker-only correction over these SAME result bytes.

## Received inputs and access

The official Binance COIN-M exchange-information documentation returned302. The
collector did not follow it. Its public exchange-information API returned451 and
the collector stopped. It requested no spot metadata, current book, remaining
documentation, history, private account or order. Source semantic reading0;
unrequested/unread pages and exact hashes/URLs are in `sources.json`.

The one accumulated new budget closed at **2attempts,362actual response bytes**,
with1MiB/16s conservative charges. Remaining14slots are unused/closed. Historical
7757requests/reported229.85MiB and the old closed66-request source batch remain
unchanged. The failed API body, first-seen receipt and hash-chained budget are
retained; raw static HTML stays private. No redirect, region/login/API-limit bypass
or alternative endpoint was attempted. All12current coin/maturity/cost slots stay
unknown; no current Binance offer or executable price is reported.

## What the new component checks

For inverse short USDface Q, summed inverse entry cost A=sum(q_i/f_i), collateral
B and coin fees C, residual D=B-C-A determines the model's coverage:

`coin equity at mark M = Q/M + D`.

The ideal one-times argument needs D>=0. Paying fees from an exact B=A hedge
creates D<0. The separately written oracle constructs a positive-mark
counterexample for every such case; that is algebra, not observed liquidation
or a certification of a venue's maintenance-margin rules. An independent reader
supplied the core invariant; its full note/probes were not delivered after the
environment restart, so no completed external-review claim is made.

The new guard also calculates the amount to buy BEFORE fees: quote-debit fees
increase quote expenditure; base-debit fees require buying additional coins.
Explicit lot rounding is upwards, retains residual coin and still does not certify
an exchange grid. Missing fee currency/costs never become zero.

Conditional final sale proceeds are `[Q*(1-delivery fee)+D*settlement price]`
times the actual sale/settlement/FX ratio and sale-fee factor. The new hurdle
compares those proceeds plus ONE copy of idle cash with the SAME entire initial
capital. It also supports explicit benchmark/idle growth factors; R340 reports
only a same-quote uninvested-cash control. It does not invent T-bill interest or
USD/USDT parity. Missing future sale ratio keeps actual terminal cash/net unknown.

## Finite, reused evidence and costs

The report retains72old R328 coin/depth/fee/cost/settlement-scale guard slots:
54have conditional inputs,18preserve missing ETH top-depth. It uses published
Deribit plan projections, not current Binance data or a rerun of the old accounts.
The solved sale-ratio hurdle remains conditional on settlement price, fees and
optimistic other-cost0. An actual future quote/transfer cost is still unknown.

All129published rounded R335 ticket metadata rows are retained, across both coins,
all three hurdle labels and both spot-source robustness sets. Normalizing S0=B=1
produces1,548 dependent algebra cells at1x/2x/3x, zero-charge/old-rate controls and
base/quote spot-fee debits. Rounded gross is not a real fill, price path or size.
No historical portfolio PnL, annual return, gate or strategy choice is recomputed.

At the OLD R335 fee assumptions, normalized unreserved coin residual is:

| Spot fee debit | 1x | 2x | 3x |
|---|---:|---:|---:|
| Quote, future fee in collateral | -0.0005 | -0.0010 | -0.0015 |
| Base, future fee in collateral | -0.0015 | -0.0030 | -0.0045 |

The reporter records774unreserved one-times model-coverage failures and0after
explicit exact prefunding; the774zero-charge controls have zero residual. These
are conditional proof diagnostics, not774 market failures or profitable trades.
The normalized cells' delivery/other cost0 is an optimistic floor, not newly read
public terms. Unknown owner fees and eventual executable sale prices still block
any actual profit/activation. R335's original DATA_PASS/provenance is intact.

## Validation and preserved failure

Before economic freeze: **1,537tests PASS /three skips,194.312s**, including11new
capture/math/oracle regressions. The frozen reporter reproduced `results.json.gz`
and `summary.json` byte for byte in two fresh directories. Gzip result SHA256:
`bdd17375854913a1c42e150b0a80304ea1423aa3c5eeba9be372bf55bc480cfc`.

The original oracle halts on `Fraction(25000,25941) != 0.9637253768166224`.
In its zero-charge branch, integer division creates1.0 and its reference hurdle
then becomes a binary float. Exact equality correctly refuses that comparison.
`oracle_failure.txt` retains the original stack; no tolerance or frozen repair
is introduced. R341 must normalize only exact numeric arguments and reject
noninteger floats before invoking the original assertions, with its own freeze.

```sh
python scripts/run_current_inverse.py --out .cache/r340-fresh
python scripts/check_current_inverse.py --out .cache/r340-fresh
```

The second command fails as retained. Use R341's separately frozen checker for
the corrected audit; reporter/schema/data/formulas remain unchanged. No new
authenticated source, funding/index notional, actual margin rule, market expected
return or paper day was acquired. Program denominator9,479,013 unchanged. No real
order, money, secret, historical/model download, PR merge/closure or scheduler.
