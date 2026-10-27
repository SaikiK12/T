# PREREG: source-bound fee eligibility and fixed cost-survival envelopes

- **Registry id:** R345
- **Owner (single writer):** Codex
- **Date registered (UTC):** 2026-10-27
- Claim: issue7 comment6437034872; existing draft PR56.
- Canonical dependency: M409/FV26-ACCOUNT-API-FEE-ACCESS; readonly R336/M412 review.

## Binding question and preserved scope

R336 reports a positive gate0 break/rebound proxy at zero fees. Its execution
mode needs API, while public contract rates do not establish owner API fee
entitlement. Test this dependency BEFORE prospective activation: what additional
per-side fee could the fixed primary absorb under its original return convention,
and how do fixed fee/capital assumptions change that arithmetic? Join the newly
read fee-source contract to existing opportunity/risk guards. This is not a new
forecast fit, execution simulation, current offer or validated expected return.

R310/R311 evidence read:1318 actual seams repaired, all12calibration models run,
224/273 common validation days, selected2x/3x loses. No rerun of that incomplete
dataset, winner substitution, gap/tradability relaxation or leverage increase.
R336's forecasts/dates/cohort are already seen; no fresh holdout. All old frozen
code/results, sources, provenance and journals stay byte-identical. Claude's
R337/forward and M412 queue row are not edited.

## New source/data contract

Exactly2 ordinary STATIC documentation GETs were declared before dispatch:
official MEXC account-module index, then its directly linked Get Fee Details
page. Bound2attempts/1MiB per body/2MiB total/15s each/40s wall. Both200,
70442body bytes/0.912s recorded wall. Scope CLOSED; no actual private fee,
account, market, history, order, login, key, redirect, retry or alternate host.
Reader acquired both then hit its usage limit before semantic review; root
completed cached-body hash verification/read. Preserve original receipt and
later source_review separately; no claim of independent semantic peer review.

Public documentation describes GET/private/account/tiered_fee_rate/v2 with
View Order Details permission, optional symbol, real versus original fees,
separate discount/deduction states, NORMAL/LEVERAGE/TIERED, volume/window and
contract scope. Example zero fee has a nonzero next tier and an OLD FIXED
window. It is not an owner response or future API entitlement. Endpoint decimal
scaling/settlement asset/as-of semantics are not explicitly certified. Do not
reapply discount to real* fees, infer asset from suffix or select leverage for
a lower fee. Ignore private-balance/KYC/unknown fields; never copy the original
payload to output. The adapter cannot authenticate a redacted export itself.

Available historical inputs are exact saved V0 events and the published rounded
R336 summary. Only6/46 original R336 code/data inputs exist with their exact
hashes;40 raw contract/ticker inputs remain missing. Do not download, interpolate
or silently replace them. parent_availability.json pins every old path/hash.
This IS NOT exact R336 source or numerical reproduction. Old means/trades and
flags stay historical; the current audit consumes the serialized fields only.

## Finite economics before outcomes

- code_inputs.json SHA256 184ed425a4eab2491ad5591e108dd1760a9ce7cf5c88e70eaf33043276c874ac
- inputs.json SHA256 04589a90f06746cc765804817b780aad98ac6856beffd028685217347e2443c9
- fixtures.json SHA256 b85503b09e710383555a9b1e7842c9609af0cd3fc95ada2776cbed3f78b06e6a
- sources.json SHA256 3d547225ebe08223c024dc6c8b818af897354e618f77d5bb9b0781efb65290fc

Python3.12.14,61local code/test inputs,17source/evidence/test identities.
Final full1569tests pass in204.691s with3existing skips;31targeted tests pass
after restoration/control refinements. The prefreeze name-collision failure is
preserved separately; no original financial file remains modified.

Freeze/commit this spec, sidecar, full local code/test/runtime closure and all
source/input identities BEFORE new R345 economic calculations. Runner verifies
closure, runtime and committed own identities before/after. Use fresh output
directories, never overwrite originals. All source captures precede this finite
economic freeze; no claim otherwise. No source/market requests during reporting.

Three policies on the SAME possible/certain PZ event slots, same size/holding
times: preselected PZ, always-through and always-away matched controls. Controls
do not acquire extra exposure by trading every parent event; they are NOT the
old R336 all-event controls. PZ's original1x selection threshold |E_sigma*sig|>
4*spread remains fixed across all fee scenarios and cost tiers. No re-filtering
or selection based on outcomes, fee burden or a validation winner.

Exactly9 conservatively charged policy/fee variants =3policies x additional
per-side0/4/8bp; report all1x/2x/3x =>27cost cells,9algebraic fee frontiers.
Primary is PZ/additional8bp (existing lab API reserve, not certified current owner
fee).0 is old spread-only convention;4 is prior generic public-rate context.
No scenario is promoted as actual entitlement. Add9trials to9479013 =>9479022;
same historical events underpin every cell, not9independent discoveries.

Published median_half_spread_bp and one_way_bp are rounded to0.001bp. Intersect
both +/-0.0005bp serialization intervals with the old1bp floor, rather than
using the rounded point as an exact spread. Contradictions fail. Compute exact
E_sigma*sig from SERIALIZED decimal values, not an assertion about the parent's
binary floating computations. Certain PZ inclusion if |edge|>4*upper_cost;
certain inactivity if |edge|<=4*lower_cost; otherwise ambiguity remains. Missing
prediction keeps inactivity with its reason; potentially active missing payoff
keeps total unavailable. Preserve every original decision/exit grid and the
stricter old decision-BAR-open nonoverlap rule. No source-clock widening.

For each possible active event use original convention
side*g -2*k*(spread+additional_fee), where g already contains Binance close and
funding proxies. No second spread debit or added funding credit. Actual fees
use each fill's own notional/asset; those exit notionals are unavailable here,
so this normalized-entry-notional formula is only a diagnostic convention.
Do not invent fill prices, account funding or fee proof to post g as cash.

Numerical outer bounds sum cost endpoints and, for ambiguous inclusion, include
both inactive0 and active payoff. The same rounded contract cost is shared by
many events; independent event endpoint relaxation gives conservative OUTER
envelopes, not necessarily attainable whole-policy optima or statistical
confidence intervals. Exact fractional arithmetic avoids false decimal precision.
Fee frontier is the algebraic extra fee giving zero sum on the CERTAIN cohort;
claim a whole-policy threshold only when ambiguity/missing payoff is absent.

Use one10000 quote-equivalent initial capital and500entry-notional scale for
all policies, no compounding/reinvestment. All1734original calendar days remain,
including inactivity. Compare scaled sums to whole-capital simple cash0/3%
annual scenarios over1734days. Those are conditional normalized-quote amounts,
not actual USDT/USDC conversion, available yield, marked account NAV or proof
that the uncapped book could execute. Negative totals are never clipped.

Report half-open [decision_bar+1h, exit_close) concurrency and original-notional
exposure floors, plus fixed3x roundtrip reserve ceilings. Same PZ slots give
matched gross/time constraints across directions. Neither terminal-payoff sums,
initial capital coverage nor those floors prove causal cash availability,
mark-to-market risk, maintenance margin or liquidation. No fabricated path or
claim of equal realized risk. Cost/gross floors can identify a problem; missing
marks and actual fees leave real capital sufficiency UNKNOWN.

## Integration, verification and decision limits

Decode public/example/redacted fee shapes with explicit source/instrument/unit
scope; unverified evidence supplies None/unknown to existing Opportunity/risk
guards. An invented otherwise-positive native account case must become blocked
by public-zero input while account/journal cash remains unchanged. These are
mechanics controls, not observed market profits or authenticated owner inputs.

Run full repository suite before new lab-code commit, targeted regressions,
independent stdlib raw-event/interval/heap-exposure/fee-frontier checker and
fresh-directory byte reproduction. Original financial module/test files were
temporarily overwritten by a prefreeze name collision, detected by full suite;
both restored byte-for-byte and new paths isolated BEFORE any commit/outcome.
Retain tests_name_collision_before_freeze.json and final test receipts. No old
financial file, frozen specification or result is published with changes.

PARTIAL dependency assessment at most. No sampling CI/p-value/positive expectancy
from deterministic rounding bounds or this already-seen sample. R321's lack of
accepted dependent inference is not bypassed; no statistical promotion or new
model selection occurs. All9variants are charged; failures/unknowns/controls
are retained, not summarized as profitable zero. Actual expected net staysNone,
activation false, prospective strategy days0. Historical result alone cannot
authorize a strategy; new scoring needs its own frozen protocol/on-time evidence.

Extend only the existing fee-access intake object and M409 component note after
results; append R345 via helper. No duplicate source queue/panel, no M412/Claude
edits, private values, real orders/money, merge/closure or permanent-process claim.
Historical allowance7757/8000requests and reported229.85/250MiB unchanged; prior
66-source, R340 and R343 scopes remain closed. No large dataset or weights.
