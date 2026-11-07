# R318: one simulated account for fees, funding, execution and missing inputs

- **Registry id:** R318
- **Owner (single writer):** Codex, `codex/lab-consolidation`, existing draft PR #49
- **Date registered (UTC):** 2026-10-25
- **Canonical method:** M409, execution/funding inputs and integrated accounting

Code manifest SHA-256: 420b39bc9e0f902eeac2e0e3fd1e042bfc12b65329e8e764d6b96e2bd2453797
Held-data identity SHA-256: 26f6d8a6eccae44e641b6aae871452aa89742f31f94b09c2d411713156b1da75
Invented fixtures SHA-256: b93ca826e6d522e040fa0ec77cc232eca7a67f2cb9fe5f7e0fab262ed6106851

## Binding question and inherited evidence

Can the existing quote/funding/cost components feed one reproducible simulated
account without inventing cash, renewing an allowance on restart, hiding missing
inputs, or counting crossing twice? At fixed segregated capital, how do the
already-seen displayed cost/capacity bounds change with size? These are input
and engineering questions, not a new search for profitable historical policies.

Read R310/R311/R316/R317 before implementation. R311 repaired1,318 actual funding
events and exercised all12 policies, but remains INCONCLUSIVE on224/273 common
days. Its calibration-selected F0+B_h14 loses at registered2x/3x costs. Do not
rerun it, substitute another validation winner, loosen gaps/tradability/source
clocks, or increase leverage. R317's nominal and advertised fees were read after
R316; they are conditional public assumptions, not owner or as-of charged fees.
The original reserve remains10/4bp PLUS displayed crossing, as in R312–R317,
not a reinterpretation of R311's old all-in cost. No positive edge is asserted.

## Finite inputs, controls and chronology

Freeze and commit/push this spec,54-file code/dependency manifest, fixtures and
six exact R316 parent identities BEFORE new held-book size/account diagnostics.
The unchanged old loader verifies every sealed public metadata body/frame,
receipt, clock, connection, sequence and parent runtime/code inventory. No new
market/account/RPC/history request or model-weight download is authorized.
Historical accumulated spend stays7,757/8,000 requests and229.85/250MiB; the
rounded MiB figure is NOT an exact byte baseline or a renewed grant.

All fixtures.json prices, positions, statements, fee entitlements, budgets,
source/index bindings and sessions are INVENTED ENGINE VALIDATION inputs.
Unit tests and the reviewer's oracle exercise known invented arithmetic before
freeze; these are not outcomes from market data or prospective observations.

Exactly8 account fixture cases: closed_and_reversed at fixed1x/2x/3x fee
reserves, inactive_control, missing_fee_and_mark, long_bid_mark, short_ask_mark,
late_fill_reconciliation. The reversal sequence is +2@100,+2@110,-1@120,-5@90,
+2@80; no price selection/optimization. Each starts5,000USDT on MEXC and
5,000USDC on Lighter, with no cross-asset sum/conversion. Flat Lighter capital
does not create returns or subsidize MEXC collateral. Single-venue control
returns use that venue's5,000-unit initial capital; no portfolio risk equality
or return comparison to a historical strategy is claimed.

One additional funding integration starts a synthetic-.01BTC position at30,000
with a.3USDT model entry fee. Derive all exposure spans from accepted account
fills, starting at the declared flat baseline. Assess the synthetic MEXC10s
event only after observing its entire documented15s ambiguity window. Missing
event value creates a pending UNKNOWN cash amount; an explicit later bound
value resolves it by a new append, never by rewriting/zero-filling. Compare the
on-time.02% announcement with the original.01% settlement as forecast-error
arithmetic only. Test the corresponding Lighter input both without and with a
caller-declared pre-update index basis; neither is a source/proof verification.

Fee integration uses an invented regular10bp statement and its full entry/exit
validity. Feed its derived entry/exit fees into the same simulated account.
Keep missing statement, promotion reservation, duplicate reservation, exhausted
quota after persistent replay, and fee expiry before exit. Shared entitlement
ids cannot renew quota by changing export revision or instrument. Explicit
redacted import exists; this run accesses no owner's private fee document.

Operations integration dispatches ZERO requests. Its invented2request/100byte
budget reserves before dispatch, does not refund a timeout, and remains spent
after reopening. A separate illustrative historical baseline retains7,757
requests and unknown exact bytes, blocking dispatch. Synthetic streaming cases
are snapshot, nonce gap, bounded restart, old-epoch message, replacement snapshot,
and journal reopening; old transport never resumes as fresh liquidity.

## Fixed held-book size and exit experiment

Use the same6 R316 symbols BTC,WIF,SKR,ROBO,MEGA,XPD, grids10/20/30/40/50/60s,
and deadlines0/+300ms: exactly72 dependent book/deadline records. XPD remains
non-crypto/metal in the inherited evidence; this adapter does not guess any
missing base asset/class/session or settlement asset from a ticker name.

For every record assess exactly6 leg budgets25/50/100/250/500/1000 quote units:
432 descriptive size cases, ALL retained including failures/inactivity/missing.
Each size fixes its common-lattice quantity using immediate books; a delayed
book cannot create or resize it. Keep the original250-unit reserve cost as a
separate untouched control. Check each venue's actual buy AND sell quote
minimum, common lot, contract size and capital. Require original source/receive
ages, cross-venue skew, sequence and disconnection rules; no guard relaxation.

Capital stays10,000 quote-equivalent,5,000/venue, with declared USDT/USD-quote
parity only for this cost diagnostic. It is not settled cross-margin capital.
For fillable displayed sweeps, crossing = M_buy-M_sell+L_buy-L_sell;
reserve = .001*(M_buy+M_sell)+.0004*(L_buy+L_sell). Retain1x/2x/3x of their SUM,
the original one-leg and total-capital bp denominators and all missing costs.
Size-dependent depth is capacity evidence, not a predictive trial or equal-risk
strategy result. Do not choose an optimal size after seeing this sample.

Exactly3 adverse exit shocks0/20/50bp, both long/short on both venues for each
eligible size: up to5,184 conditional exit quotes. Future exit fees are declared
20/8bp and additional exit delay500ms; the observed quote is NOT restamped or
changed into an observed future fill. Minimum additional venue delays0/300ms
stay distinct from decision-to-evaluation, quote receipt offset and unknown
total order-to-fill latency. No actual order was submitted.

For eligible250-unit states, illustrate the quote-to-account close mark using
an explicitly hypothetical midpoint entry basis and UNKNOWN entry fees. Use
bid liquidation for a long, ask for a short, separate future exit fees, and
require a current matching-quantity mark. These accounts MUST have UNKNOWN
net cash/PnL/NAV; full sale/repurchase notional is never futures profit.
Keep complete instrument/session/permission/reference flags for every row.
Actual Lighter pre-update event/proof/API-unit binding remains absent.

## Accounting and persistent-state invariants

Opening futures notional reserves model1x collateral; it is not a spot purchase
cash debit. Adding uses weighted basis; partial closes/reversals realize only
closed signed quantity. Model cash = initial + realized price + funding - paid
fees + explicit external capital flows. Execution drag embedded in fill prices
is diagnostic only, never another deduction. Open liquidation PnL and future
exit fees remain separate. A deposit is not profit. No FX or venue netting.

Keep economic time and first-seen UTC/monotonic receipt distinct. Stable event
ids deduplicate even a later delivery; conflicting financial revisions or late
fill ordering make totals unknown pending reconciliation. No source clock
refresh, future observation, unobserved fee/funding zero or backdated snapshot.
Journal attempts and fee/funding assumptions append with hash chain, fsync and
writer lock; reopening cannot reset baseline, position, quota or budget.
Known cash components remain visible when total cash or equity is unknown.

No legacy proxy position/return is imported as actual cash. New strict views
retain UNKNOWN when executable/event/fee/session inputs are absent. Existing
frozen forward/xfund equations, results and journals are not rewritten.
The legacy projection is an input-admission boundary, not migration/re-scoring
of every historical lane or proof that their model conventions are identical.

## Outputs, verification and decision limits

One report/results.json links every component; observations.jsonl.gz retains
all72 records/432 size cases. One offline French account.html/account.txt view
uses reported numbers without recomputing/aggregating PnL or fetching anything.
The reviewer-written Decimal oracle plus root-added artifact adapter separately
checks accepted synthetic postings, conservation, asset segregation, nulls,
funding units and1x/2x/3x held sweep arithmetic. It does not independently decode
raw market frames, verify actual fills/fees or supply a statistical null.
Reproduce artifacts byte-for-byte in a fresh directory and report limits.

Full suite before lab code commit;75 focused new tests are feedback, not a
replacement. Component tests include crashes before durable restart/dispatch,
hash-chain corruption, future/stale values, quota reuse, unknown marks/fees,
partial close/reversal and no double counting. The current full run is1,248
tests with2 intentional skips; all financial code tested is in this manifest.

Zero predictive trials, zero new prospective paper days, no strategy activation,
no statistical uncertainty/SPA/multiplicity claim from engineering cases or
dependent already-seen books. Program trials remain9,478,782. Actual risk tiers,
margin liquidation, two-leg recovery, sessions/account permission, event-bound
funding and executable paid fills remain necessary before a fresh frozen paper
protocol can score a positive expected net return. Retain nulls and every failure.
