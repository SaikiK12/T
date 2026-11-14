# R423: exact sampled CDE rate-field mapping passes

**SAMPLED_CONTRACT_PASS.** The pre-named Advanced outer funding field equals
the public MDA hourly-decimal field at its exact declared UTC hour in every
fixed observation. There was no multiplier, time shift, tolerance, missing-row
fill, alternate field or selected follow-up sample.

| Asset | Observations | Exact matches | Mismatches | Missing final rows | Nonzero matches | Distinct nonzero values |
|---|---:|---:|---:|---:|---:|---:|
| BTC |8|8|0|0|8|6|
| ETH |8|8|0|0|6|2|

The fixed native packet hours are04,05,07,08,09,10,11,12UTC on2026-11-07;
06UTC is absent and not filled. No declared timestamp is later than its
original receipt. Exact Decimal and independent Fraction equality agree.
For example, the first BTC metadata string `0.000002` equals MDA's
`0.0000020` numerically at04UTC, without a fitted factor. All16 raw pairs and
original receipt times are preserved in [report](results/report.json).

The112-input closure and protocol were frozen as
`04b979b7d6630aba3f0bb8f7e6806114b3ed45d13576bc4616260a68840c270f`,
committed and pushed at15dde5cc before the single measurement. The exclusive
[run marker](results/RUN_STARTED.json) binds that commit. Report SHA256:
`410e82ed484d51b1c0339f278f5f2ebef9343798f66e2cdecdf1abe3070f508d`.
The [full-suite receipt](validation.json) records **2,551tests OK,3skipped,
439.656seconds**,9new synthetic tests, integrity0errors/14legacy warnings
and matching staged catalogs. No test reads the ignored market-data folder.

## Economic meaning and limits

This qualifies one observed field mapping for M488. It resolves the sampled
Advanced/MDA scale-and-time question; it does not establish historical funding
marks, actual broker funding cash, revision policy, global field stability,
exchange/book units, collateral rules, legal entitlement or profitability.
Both fields are from **the same provider**; this is not independent cleared-
cash confirmation. MDA's final history was fetched after the original metadata
observations: this is ex-post source qualification, not an out-of-sample
trading test or proof that the history's current vintage was then available.
The original field was available at its recorded receipt; no trading signal
or return is evaluated here.

The two tiny historical-tail requests were already acquired counts-only
before freeze:32rows per asset,5,420client bytes. Their exact source URLs,
Coinbase organization, undated publication status, UTC access timestamps,
HTTP receipts and conservative cumulative allowance accounting are in the
frozen [intake](../../research/intake/funding_notional_20261103/cde_rate_contract_20261107/).
No acquisition or native forward tick occurred during this measured run.

**Costs1x/2x/3x: N/A, not0.** Financial PnL and funding cash are null. R421's
separate measured execution costs remain unchanged. **0predictive trials**;
read against `registry.program_trials('registry/rounds.csv')` = **9,784,345**
at this run. Sixteen field comparisons are not independent alpha trials.
No financial gate or real-money admission. M488 stays **PARTIAL**: a registered
economic successor still needs defensible price/cash mechanics, actual fee
sensitivity, separate venue wallets and margin/one-leg stress before net
carry can be assessed.
