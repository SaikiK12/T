# R426: simple touch quoting loses on this short conditional pilot

**PARTIAL_EXECUTION_DIAGNOSTIC_ONLY.** Among36fixed cases,18have a numerical
before-funding outcome, all negative;6WTI1000cases have an unpriced terminal
exit;12NATGAScases have no trade file. Unknown cases were never scored0.
No size, fee, time window, clock, spread or maker rule was changed afterward.
This is not a global rejection of market making or an income-rate estimate.

The source window is **2026-10-29 01:31:45..01:35:30UTC**,225seconds, on
previously seen source dates. Total model capital10000quote-currency units,
allocated10000/3per market, fixedQ chosen from100/1000quote notional. Two
conditional fee profiles, three fixed markets, cost1x/2x/3x. Every number below
is a **model outcome before unmeasured funding**, not certified economic net.

| Market | Quote notional | Fee hypothesis | Candidate fill reports/case |1x|2x|3x|State|
|---|---:|---|---:|---:|---:|---:|---|
|WTI|100|standard|8|-0.136899|-0.136938|-0.136977|CONDITIONAL_BEFORE_FUNDING|
|WTI|100|premium|8|-0.163453|-0.190047|-0.216640|CONDITIONAL_BEFORE_FUNDING|
|WTI|1000|standard|27|unknown|unknown|unknown|EXIT_DEPTH_UNQUALIFIED|
|WTI|1000|premium|27|unknown|unknown|unknown|EXIT_DEPTH_UNQUALIFIED|
|NATGAS|100|standard|unknown|unknown|unknown|unknown|NO_TRADE_FILE|
|NATGAS|100|premium|unknown|unknown|unknown|unknown|NO_TRADE_FILE|
|NATGAS|1000|standard|unknown|unknown|unknown|unknown|NO_TRADE_FILE|
|NATGAS|1000|premium|unknown|unknown|unknown|unknown|NO_TRADE_FILE|
|BRENTOIL|100|standard|4|-0.251760|-0.260709|-0.269658|CONDITIONAL_BEFORE_FUNDING|
|BRENTOIL|100|premium|4|-0.315297|-0.387783|-0.460269|CONDITIONAL_BEFORE_FUNDING|
|BRENTOIL|1000|standard|4|-1.935204|-2.003823|-2.072442|CONDITIONAL_BEFORE_FUNDING|
|BRENTOIL|1000|premium|4|-2.421118|-2.975651|-3.530184|CONDITIONAL_BEFORE_FUNDING|

At100quote notional with the zero-fee hypothesis, WTI loses0.136899and
BRENTOIL0.251760at1x. Price/inventory losses already outweigh the captured
spread in this fragment; removing fees alone does not establish an edge.
At1000WTI, the model ends **short11.391base units**; shown terminal liquidity
cannot certify closing it, so **no liquidatable PnL** is reported. Its1x
Standard mark-only loss−1.2809835is not substituted for an executable close.
NATGAS's missing trade file is unknown flow, not zero activity or profit.

## What was implemented and checked

One two-sided touch rule on a15second decision grid;1second placement and
cancel hypotheses, fresh received BBO, post-only rejection at arrival, no
fills at equal-price touches, and partial fills no greater than printed contra
volume. Liquidation prints/old bootstrap executions are excluded. Old order
history is retained: a late receive can still report a pre-cancel execution.
Fixed-base inventory and all fees remain in signed cash. Inventory/capital
guard failures stop before recovery; no such breach occurred in this sample.
Terminal leftovers need a fresh BBO and sufficient shown size, rather than a
free mark close. Independent Decimal checks pass **90cash/inventory/fee/exit
identities**. They prove arithmetic, not actual execution or alpha.

The observed trade reports are model fill candidates, not actual accepted
orders. Alternative sizes/profiles/costs reuse the same prints and are not
independent bets. No monthly/daily throughput, win probability, Sharpe,
annualization, profitable capacity or reliable-return claim follows.

**Costs1x/2x/3x:** maker/taker profile fees and terminal mid-to-touch crossing
are stressed exactly as registered. The Standard0/0and Premium0.4/2.8bp
profiles are retained primary-source hypotheses from R317, not owner rates.
Nov7public metadata confirms instrument identity/current minima and nominal
market zeros, not the Oct29account tier or actual historical commission.
Fresh doc-reader failures are disclosed in the frozen source note.

## Unresolved mechanics and evidence grade

**OOS/live:no. Costs:partly. Evidence:C, conditional short-fragment model.**
Funding is unmeasured, source matching/local clock alignment is not calibrated,
private order/cancel/fill acks and queue position are absent, counterfactual
impact is unproved, historical tick/minimum equivalence is assumed, and
French-owner venue access is not determined. These gaps block full net and
paper/live admission even if a cell had been positive. No money/order/account
or credentials; no native tick or recorder ran here.

The next informative improvement is to qualify inventory/quote selection,
real fills/ack-clock evidence and funding on a separately registered source
scope. This source fragment cannot decide which adaptive filter works. Do
not tune a width/skew or fee after these outcomes and call it unseen evidence.

## Source and immutable execution lineage

The bounded public archive restore used1407398bytes; all20original member
hashes match. Only5eligible Lighter quote/trade files were decoded for this
lane. Other15HFT/tape/rawtape members stayed opaque; no R367read or full-day
recovery. Three current metadata GETs add5221bytes; RPC denial adds17.
Conservative cumulative original allowance is **7811calls/249746402bytes**,
without renewing8000calls/250MiB. All source URLs, exact access clocks,
read scopes, raw hashes and QAcounts are in the frozen
[intake](../../research/intake/maker_pilot_20261107/SOURCES.md).

The50-input closure froze
`67b52c8b7cb8e9255ce4775b34a5fe0599324020f6dc7e63200ce06f805e34d0`,
committed/pushed**3cf2f2c7before one run**. [Run marker](results/RUN_STARTED.json),
[original report](results/report.json) and
[independent accounting](results/independent_accounting.json) are retained.
Original report SHA256:
`6bce4e83b178cd526284fd0d8ec1386a0398502cd7ab1c6f9e92899034007c29`.

A metadata defect in the frozen runner: its early missing-source result omits
size/cost labels. The immutable report is unchanged. The code-generated
[case index](results/case_index.json) binds each native list position to the
frozen Cartesian case order, so all12NATGASarms remain identifiable. This
companion changes no fill, price or outcome and is not another strategy run.

[Validation](validation.json): **2575testsOK,3skipped,493.882seconds**,12new
synthetic execution tests, integrity0errors/14legacy warnings, staged catalogs
match. **12economic arms** including missing/failed cases; program trials
**9784361** via registry.program_trials. Cost tiers are sensitivities, not
independent alpha. Native partial verdict and M474PARTIAL do not admit gate1.
