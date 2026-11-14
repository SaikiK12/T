# R312: first-seen paired quote inputs and conditional break-even costs

- **Registry id:** R312
- **Owner (single writer):** Codex, `codex/lab-consolidation`, existing draft PR #49
- **Date registered (UTC):** 2026-10-24
- **Canonical method:** M409; measurement component of the R310/R311 funding/basis decision group

Code/input manifest SHA-256: 99e1fec8824fc0fe071c914d2dbe46e3a87d6c6f0bb541acc23985927b56557b
Current gates SHA-256: e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926

## Question and received scope

Can our standard public REST access supply a common-lot, contemporaneously
observed MEXC/Lighter hedge, and what displayed crossing cost must it overcome?
This is an execution-input measurement, **zero predictive strategy trials**,
following R224's measurement convention. Two observations on six fixed pairs
are twelve measurements, not twelve alpha candidates. No inference, p-value,
optimizer, predictive selection, funding forecast or PnL is computed.

Prior information: R310 and R311 already inspected the fixed R288 mixed universe
and spent 2025-04-27..2026-09-30. R311 is INCONCLUSIVE: 224/273 common scored
validation days; selected F0+B_h14 loses at 2x/3x. Missing executable quotes,
session availability and fair/index settlement notionals remain material. The
old policies, archives, rows, results and all 24 counted strategy trials stand.
Program trials before this measurement: 9,478,782; this measurement adds zero.

## Frozen universe and collection

Exactly BTC, WIF, SKR, ROBO, MEGA and XPD, in that order, identified by R288's
`experiments/xfund_lt_v1/symbols.csv` pinned in `code_inputs.json`. BTC is a liquid
control; the four altcoins diagnose quiet/thin markets implicated in R311; XPD
is a deliberately retained metals/session control. This is diagnostic selection,
not a representative universe or a crypto-only filter. No substitutions.

`scripts/probe_pair_quotes.py capture` creates a new `evidence/` directory and
refuses an existing one, including failed captures. One global Lighter market
identity GET; per pair, MEXC contract details, current Lighter details, dedicated
MEXC fair price, then two paired book observations. MEXC depth: 50 levels;
Lighter: 100 orders per side. Plan: 43 requests; hard ceilings **48 GET attempts,
8 MiB total response bodies, 1 MiB per body, 180 seconds**. No retries, account
calls, historical data or daemon. Every attempted request and failed body is
retained. A response at its byte limit is rejected without reading another byte.
Do not start another request after the duration budget; any overrun of completed
collection blocks the report. No restarts or alternative sample after failures.

At most two book-request workers; one Lighter request at a time, minimum 1.1 s
between its starts, holding the **existing collector's machine-wide Lighter lock**.
Pace before launching each pair so local quota waiting does not age just one leg.
First availability is response-body receipt, individually stamped with UTC and
the same process's monotonic request/receive clocks, never the batch start.
This small current-data probe is separately scoped. It does not renew or consume
the R310/R311 historical allowance: already 7,757 requests/229.85 MiB of 8,000/250.

## Data contract and failures

Reuse `lab.mexc_depth` and `lab.microstructure.DepthLevel`. Convert MEXC contract
quantity using `contractSize`, not order count. Respect `marketOrderMaxLevel`;
more levels in the REST response cannot expand a market order's sweep limit.
Aggregate Lighter orders by price using remaining **base** amount. Sort validated
full sides and reject missing, nonfinite, nonpositive, locked/crossed books.

Keep MEXC's provider timestamp/version as separate reported fields. Its REST
system timestamp is not certified matching-engine age. Lighter's pinned official
REST response schema has no book-event clock; order transaction times do not
certify the current snapshot. Do not insert the local clock into either field.
Local first-seen quality requires each receipt age 0..5 s, request latency <=5 s,
UTC-versus-monotonic clock discrepancy <=50 ms, and inter-venue receive skew <=1 s.
These are fixed engineering guards, not fit thresholds or proof of source age.

Metadata ages are checked separately, 0..5 s at the second-leg receipt. MEXC
`state=0`/`apiAllowed=true`, Lighter `status=active`/`is_frozen=false` are reported
availability only. No current or historical session calendar is certified. An
active flag or visible resting book cannot silently override a market closure.
The dedicated MEXC fair price and Lighter index price retain their own receipt
ages; their observed q*price notionals are not verified settlement-time notionals.
Every observation remains **execution_ready=false** until source-age, sessions,
latency/fill and funding-settlement contracts are independently established.

## Fixed economic calculation and comparable capital

For each of the twelve snapshots independently, take the exact common base-lot
lattice of MEXC `contractSize*volUnit` and Lighter `10^-supported_size_decimals`.
Round down $250 divided by the larger venue midpoint to that lattice. Both legs
use the same q, satisfying current base/quote minima and maximum quantity, or
the row fails. Do not round each venue independently or substitute smaller fills.
Only the quantity of this independent cost measurement can change between its
two observations; they are not an entry/exit trade or evidence of a holding return.

Walk displayed asks and bids for **exactly q base** on each venue. Insufficient
depth remains unfillable, with no invented price. Report shown two-way capacity
as a lower bound limited by the requested depth, never a sustainable fill rate.
R310's **10 bp MEXC / 4 bp Lighter per side** were declared total-cost assumptions,
not verified exchange fees. In this measurement retain those numbers as an
explicit **transaction-charge reserve**, then add displayed crossing. This is
deliberately conservative, not an exact replay of the parent's all-in cost
profile or a measured fee schedule. Report crossing and reserve separately.
Public zero-fee labels do not replace this reserve or prove an account fee tier.

Same-snapshot round-trip crossing = M_buy-M_sell+L_buy-L_sell.
Fees = (M_buy+M_sell)*0.001 + (L_buy+L_sell)*0.0004.
For k=1/2/3, cost = k*(crossing+fees), stressing the whole transaction cost
including spread/depth. The same q, not increased leverage, is used in all tiers.
Report both direction-specific entry costs relative to each venue's midpoint;
they sum to round-trip cost. A cross-venue price difference is not counted as
instant executable profit or pooled cash. There is no assumption of a future
exit book, flat basis, settlement funding or fee rebate.

Capital is fixed **$10,000, segregated $5,000 per venue**. Reject a leg exceeding
its venue capital. Denominators: `break_even_leg_bp` uses q*mean(M_mid,L_mid);
`capital_cost_bp` uses $10,000. This does not certify equal realized strategy
risk, margin safety, liquidity persistence or future expectancy. Displayed
break-even is conditional on the recorded book, not a live execution bound.

## Freeze, provenance and stop rules

Freeze with `lab.prereg.freeze`, commit and push specification, code, tests,
source versions and universe identity **before any live collection or costs**.
Capture raw public bodies and per-request receipts without economic statistics.
Run `seal` once; it hashes every evidence file and binds them to frozen code.
Commit and push that **input identity before `report`** computes outcomes.
Report verifies the PREREG, code manifest, exact evidence inventory/body hashes,
and collection budget; byte-identical report reproduction is allowed, replacement
with different results is refused. No collection changes within this frozen lane.

Preserve all twelve rows, including failed, thin, inactive, unknown-clock and
stale observations. Report every fixed cost tier, failure and local availability
flag, without a selected profitable subset. No dependency-null or multiplicity
test is appropriate to these twelve descriptive snapshots; no significance or
strategy success verdict is permitted. Current admission requirements, reserved
samples, strict on-time paper scoring and prospective protocol stay unmet.
This measurement cannot activate a paper/live policy or repair R311's old bars.
