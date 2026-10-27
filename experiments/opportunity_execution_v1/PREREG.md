# PREREG: R338 durable shared paper capital and receipt bridge

- **Registry id:** R338
- **Owner (single writer):** Codex
- **Date registered (UTC):** 2026-10-27
- Claim: https://github.com/SaikiK12/T/issues/7#issuecomment-6431066697

## Question and economic constraint

R334's one-batch conditional allocation is explicitly insufficient for repeated
paper use: independent batches can reuse the same still-pending capital. Finish
that bridge with durable reservations, source receipts, the existing financial
account and persistent risk history. A forecast, request, cancellation request,
unconfirmed full fill or unknown payment must never become earned or freed cash.

This is finite, invented engineering validation for the common account needed by
M007/M240/M409/M410/M412. No strategy, method queue, new predictive equation or
prospective protocol is introduced. R334, R319, all old specifications, acquisition
journals and Claude's R337/forward files remain unchanged. R310/R311 stay
INCONCLUSIVE; neither their incomplete inputs nor their validation choices are
reused as new outcomes. Real quote/depth/session/fee and fair/index settlement
contracts are still prerequisites for real evidence.

## Frozen identity

- code_inputs.json SHA256 7e2ccc0535759f0bc3ae8b008d2cf1b52f42931060470ba1dfb99e00e97e0497
- data_inputs.json SHA256 faeb8a549a62ec841075c739a9806943938f5cb1c14d5c97673bfd049538efab
- fixtures.json SHA256 103f188232c2d23e202c901775e8bbdc25135ea591bc67a647b5dfc487027ea6

Manifests pin the Python runtime, parent account/risk/assessment code and the new
coordinator, driver, independent checker, toy input builder and tests. No mutable
panel or queue is used as a numerical input. The driver/checker verify all hashes
before and after their run and refuse missing preregistration. Freeze and commit
these files BEFORE the finite diagnostic reporter. Unit tests before the commit
are implementation checks on invented inputs, not market or candidate outcomes.

## One cash ledger and conservative capital

Use ONE dedicated PaperAccount append-only financial/evidence journal plus its
existing PaperRisk journal. An fcntl writer lease uses R319's existing local
account lock path; binding another paired coordinator, policy, relative risk path
or missing/replaced risk prefix fails closed. This is a cooperating local-writer
protocol, not a distributed transaction system or protection against a caller
directly mutating the underlying files/account. Financial sources are caller
contracts; source authenticity, actual permissions and fills are never inferred.

Reuse R334's ordered assessment and strictly positive error-adjusted 3x hurdle.
All stress tiers have identical quantities, opportunities and action streams.
Keep each admitted forecast's original identity, first clock and terminal horizon.
Rejected identities also cannot be refreshed into a different forecast. Original
reserve R is entry notional + 3*(same-book round-trip cost + future-exit reserve).
Original gross floor G is worst-direction notional. No collateral is borrowed,
no USD/USDT/USDC parity is assumed, and unrealized gains cannot finance entries.

For same-sign open model quantities q_i in an instrument, attribute the actual
account locked collateral L and conservative actual gross S pro rata by current
absolute quantity. Exact rational arithmetic preserves the total even for thirds.
The actual kernel's reported collateral is authoritative for this attribution.
Retain extra capital sum(max(0,R_i-L_i)) and extra gross sum(max(0,G_i-S_i)).
Thus required capital is L plus the extra hold, not L plus R twice. A flat but
unreleased allocation retains its entire floor; partial execution never silently
shrinks its original R/G. New segregated capacity is at most
max(0,min(cash,liquidation NAV)-L-extra capital). Apply actual plus extra gross
to BOTH symbol and venue ceilings. Floors are planning holds, not PnL expenses.
Financial PnL uses the actual account's pooled average basis, not fictional
per-model basis or a second model money ledger. Opposite model directions in the
same instrument remain blocked; hedge-mode/netting semantics are not assumed.

Bound this first contract to linear perpetuals, four opportunities per call,
64 active allocations, eight order submissions per allocation, base resolution
at most 40 decimal places and horizon at most 12 hours. Existing R334 quote clocks,
lot contracts, supplied fees and old risk policies are not loosened. These bounds
are engineering scope limits, not a declaration that long carry is executable.

## Receipts, failures and explicit recovery

Separate economic and first-seen clocks. Source fills deduplicate globally by
venue/asset/symbol/trade id, preserving the first allocation/order/clock. Financial
event ids and complete payloads must join to those original receipts exactly.
Record observed overfills, late fills, source gaps and revisions as exposure and
issues; do not discard them to make a model fit. Unknown fees/funding retain known
cash components and UNKNOWN qualified cash/NAV/capacity until explicit source
resolution. No automatic close, requested fill, cancellation success or cash is
manufactured. Frozen account rejection of a late financial event stays visible.

Write assessment intent before observing risk and checkpoint the risk prefix in
the completed admission. A loss between those writes is visible as an incomplete
assessment; only the identical saved request may resume. Write fill evidence
before its financial join. A crash leaves the missing join visible, later writes
blocked and capital unavailable until explicit recovery posts the ORIGINAL event
and first clock. Reopening alone does not infer recovery. Qualified capacity is
UNKNOWN during unresolved component issues; known arithmetic components remain
visible for reconciliation. Account/source history is never edited or reset.

Full filled quantity does not imply order terminality. Explicit complete,
cancelled or rejected reports need a known cumulative total equal to received
fills. Release additionally requires own flat quantity, all financial joins and
known cash; requests/acks alone cannot release capital. A known never-submitted
flat allocation can be released with explicit causal confirmation. Safe release
does not clear persistent new-entry risk stops.

Snapshot is read-only. Risk observations are EXPLICIT durable zero-opportunity
assessments using the same intent/checkpoint protocol. The caller must supply
required observation times and fresh liquidation marks; the component is not a
continuous/intrabar monitor, collector, scheduler or guarantee of forced exit.
The diagnostic observes risk after each scripted operation except while a join
or assessment is incomplete. The stateless control receives the same invented
financial state and risk observations, without durable pending capital floors.

## Finite inputs, controls and costs

Exactly 15 cases in fixtures.json, each at fixed 1x/2x/3x execution costs, 45 paths:

1. Cross-batch capital across restart, partial cancellation, actual close/release.
2. Pending symbol concentration floor.
3. Pending venue gross floor.
4. Same-sign models at different entry prices and the account's pooled basis.
5. Cancellation request and unknown final cumulative quantity.
6. Crash after fill evidence/before cash; deferred ack and explicit recovery.
7. Crash after risk observation/before admission; exact saved-request recovery.
8. Global trade identity cannot transfer between models/orders.
9. Unknown fee and funding, separate explicit resolutions, release remains gated.
10. Source gap, expired horizon and a late observed fill retained as exposure.
11. Weak, missing-funding and uncalibrated forecasts remain rejected/null.
12. MEXC USDT/Lighter USDC capital segregation, no cross-currency aggregation.
13. Short flat-price round trip.
14. Observed adverse liquidation mark, then recovered price with sticky risk stop.
15. Observed fill larger than the submitted order, retained without unsafe release.

All inputs, forecasts, clocks, fees, source identifiers and markets are INVENTED.
An illustrative favorable forecast is not a calibrated market opportunity. Expected
admissions/releases in the fixture are fixed ex ante checker assertions, never an
input used by the coordinator to select outcomes. Each complete action is retained,
including failures; no tier/row/winner is substituted after execution.

Fill price = mid + signed order side*k*half-spread. Fill fee = abs(base)*price*
10bp*k. Current conservative liquidation marks use the matching opposite side and
exit fee at the same k. Actual funding payments do NOT scale with execution costs.
Admission conservatively retains R334's existing 3x planning buffer at every tier.
Report every realized-price/fee/funding and open liquidation component separately.
No double additive spread charge: the crossing is already in fill prices.

Control: unmodified R334 single-batch assessment at the SAME actual financial
state, supplied forecast, risk limits and source contracts. This isolates whether
durable pending reservations change the capital decision; the control does not
execute a different strategy/account or provide independent profitable returns.
No leverage optimization or capital/risk rescaling to rescue a loss.

## Checks and decision

Run full unittest suite before the lab code commit. Then run the frozen reporter,
independent standard-library Fraction checker and a second fresh-directory run.
Require byte-identical results and gzip journal archive. The checker imports no
production financial, allocation or execution module; it verifies hash chains,
snapshot prefixes, full first-clock cash joins, original reserves, 1x/2x/3x
thresholds, invented stress fills, pooled cash/basis, unknown amounts, exact
capital attribution and explicit terminal release. Retain every failing path and
checker finding; a repair after freeze requires a new correction id/spec.

PARTIAL means verified component behavior only, with actual executable expectation
UNKNOWN. There is no alpha verdict, new fitted uncertainty, confidence interval,
p-value, holdout read, candidate activation or paper day. Actual order permission
and activation are always false. No authentic sessions, fees, source fills, funding
notionals, connector latency or forecast calibration are certified. Integration
into a real collector/new prospective protocol remains separate authorized work.

Predictive strategy trials: 0. Fifteen dependent cases at three cost tiers are 45
engineering paths, not 45 independent market hypotheses or owner enhancements.
Current program trials 9,479,013; this round adds zero. Claude's R337 remains his
unfinished claimed scope and its results are not computed here. No new queue/panel.
Append one R338 result via lab.registry.append without changing old bytes.

Market/source HTTP requests and downloaded bytes: 0. Historical accumulated budget
remains 7,757/8,000 requests and REPORTED 229.85/250 MiB; exact remaining bytes are
unknown. The prior 66-request source batch remains closed, unused allowance is not
reopened. No orders, money, secret values, model weights, new market archives,
external messages beyond authorized GitHub coordination, merge or PR closure.
