# PREREG: same-venue spot/inverse carry costs and whole-capital hurdle

- **Registry id:** R343
- **Owner (single writer):** Codex
- **Date registered (UTC):** 2026-10-27
- Canonical method: M244 / YT26-04-DATED-CASH-CARRY.
- Claim: issue7 comment6435624406, existing consolidation draft PR56.

## Question and binding constraint

R329 obtained42 spot routing/lot/fee mechanisms but explicitly did not implement
or measure the same-venue portfolio. Resume that unfinished component. Can the
fixed public Deribit spot and dated inverse books supply a fully prefunded
purchase/short portfolio, and what future sale/TWAP/FX ratio would be necessary
to beat the SAME whole initial cash after fixed costs? This is a conditional
economic input/capacity assessment, not a positive expected-return test.

Read R310/R311 FINDINGS: R311 fixed1318 actual missing funding events, used all
twelve calibration models, and remains INCONCLUSIVE224/273 common validation
days; preselected2x/3x loses. Do not rerun that dataset, substitute a validation
winner, relax its gaps/tradability or increase leverage. R342 completed the
original confidence selection with frequency NULL_INACTIVE; do not rescue it.
This mechanical purchase/hedge has no direction predictor or confidence filter.

## Identities and order

- code_inputs.json SHA256 e98680ff3df0966d1055ec4c26593635b3bf54ec3aa4b9b41a1fe7c0db6e1861
- inputs.json SHA256 333cb91ac9c1f1982b350f73f18ba5a514a1ce8e499031d6d54c0ac4bff66813
- fixtures.json SHA256 ea46f63d37f5558dfdcb5770c62af0f532ad1e2849ddaf5fcc225bd532e2d085
- sources.json SHA256 0d6c555f02cfc399b6584106ed9ce15dae75e913e70adbf13c36c676bd7b66ec

Python3.12.14 and61 recursive/inherited local code/test inputs are pinned, with
12 source/evidence identities. Bounded independent review used invented inputs
only: it found and rechecked receipt/publication cardinality and exact-bool
routing fixes, then checked same bought-coin earmark and single-cash terminal
algebra. It did not collect prices, run this market assessment, certify actual
margin or review the complete independent checker. Ten unit tests include exact
raw-source reconstruction and changed-cash journal detection; run the required
full suite before committing lab code. Full1549tests pass in206.445s with3
existing skips; preserve tests_before_freeze.json.

Freeze with lab.prereg.freeze and commit spec/sidecar, fixtures, manifests,
adapter, collector, runner, oracle and tests BEFORE ANY new market dispatch.
Collector verifies these identities and committed freeze first. Seal every raw
body, first-seen receipt and charged budget in data_inputs.json and commit them
BEFORE economic report. Run script verifies closure/raw inventory/committedness
before and after. Independent stdlib oracle imports NO production financial,
price, selector or report function. Preserve failures; frozen code is never
patched. Reproduce compact results/journals/audit bytes in a fresh folder offline.

## Exactly one new finite current acquisition

Maximum8 public GET attempts,512KiB conservative body reservations,56s cumulative
reserved duration,7s per attempt,90s wall. R343/one-same-venue-current-capture is
a NEW one-time current-input scope; no historical or old source allowance is
renewed. Four exact get_instrument calls, then one concurrent batch of four
get_order_book depth5 calls. Fixed host www.deribit.com/api/v2/public; fixed
instruments BTC_USDC, ETH_USDC, BTC-25DEC26, ETH-25DEC26. Stop after failed metadata
or403/429/451/redirect/server/network boundary; the already dispatched finite
book batch may finish. Never retry, redirect, replace symbol/maturity or bypass
access. No trade/candle/history/discovery/account/order/chain endpoint, login,
secret, subscription, model weight or large dataset. Unused allowance closes.

Reuse R325's bounded child-process/no-redirect recorder and append-only budget
reservations. Failure/uncertain tails stay charged; separate accepted bytes from
reserved upper bounds. Do not reset even after process failure. Accumulated
R310/R311 historical spend remains7757/8000requests, reported229.85/250MiB;
reported MiB is not an invented exact byte count. Prior static source scope66
and R340's closed2 attempts are unchanged. No new static pages/search requests;
the exact42 historical R329 records are reused, not counted as new reading.

## Typed contract, causal availability and missing inputs

Source units: spot amount is base coin, quote/counter USDC, contract_size1;
inverse/reversed futures amount is USD face, quote/counter USD, coin settlement,
Dec25,2026 08:00UTC expiry and month settlement. min_trade_amount is BOTH minimum
and amount increment; contract_size is not the increment. Exact positive finite
numbers only; no silent resort, interpolation, extrapolation or lot/price guess.
All shown bid/ask quantities must match the source increments; validate tick
and ordered tick_size_steps. Both sides1..5 levels, strict order and uncrossed.

Both routing flags exactly true mean Coinbase-routed; both keys absent mean
native under the received query contract. False/int/contradictory shapes fail.
Routed public book API is allowed (R329-S33); unavailable public routed trade,
candle or ticker-history methods are not requested. Native0fee never inferred
for BTC_USDC/ETH_USDC. Public is_active and state=open are visibility only, not
owner permission or current executable matching-engine attestation.

Keep actual UTC and monotonic request-start/full-body first-seen clocks. Fixed
2s request/body age,1s joint receipt skew,50ms own/cross clock step and2s source
publication age, with100ms negative-publication allowance only in the common
clock check; typed parsers still reject native timestamps later than receipt.
No gate relaxation if missed. Require all FOUR book receipts qualified at the
common last receipt; pair-specific guards also remain. Publication is not the
effective value/quote lifetime. Static metadata own first-seen identity remains,
but current source-rule revision timing is not established. Missing metadata,
bad units, failed/depth-limited/stale/closed input remain explicit failed cells.

## Fixed portfolios, reserve and single ownership

Four independent alternatives: face target1000 or5000USD PER coin, each full
five-level depth or top-only control. Each alternative starts with ONE10000USDC
cash account, fixed order BTC THEN ETH. No winning coin/size/profile chosen from
outcomes. Admit both only if the ordered conservative shared reserve fits; a
capital-rejected second coin stays inactive, with remaining cash retained. A
source/depth failure makes that portfolio's aggregate economics incomplete,
never a profitable cash zero. Do not resize fixed face to rescue missing depth.

For each target use the full future bid book to obtain stressed3x harmonic
A3=sum(face_i / stressed_entry_i). Buy q=ceil_step[A3*(1+3*future_fee)/(1-3*spot_fee)].
Use SAME q/face across full/top, cost and fee-debit controls. Top-only failure
cannot resize. Check current spot bids can also consume q, solely a present
capacity observation, NOT an expiry exit promise. Reserve3x crossed spot outlay
times(1+3*spot_fee), covering the more expensive quote-debit prefunding case.

Public-standard spot5bp and inverse-entry3.5bp are fixed floors; larger current
metadata taker hints are charged. Dated delivery2.5bp floor. Compare explicit
zero-charge control, never assume actual owner fee waiver. Two spot entry debit
controls: base fee reduces bought coins, quote fee increases USDC cash debit.
One common base purchase covers both at3x; fee tier, debit asset, minimum fee
and venue rounding remain unknown. k=1,2,3 multiplies entry crossing relative to
the same source midpoint and modeled entry/delivery/exit fees. Same consumed
depth quantities; no second spread debit. Future exit spread/impact/latency
cannot be stressed from today's book and remains unresolved.

One SpotCashAccount buys q, spends USDC principal/fee once; the SAME net purchased
coin is virtually earmarked as InverseCashAccount.initial, not another capital
deposit. Coin entry fees deducted once there. Physical spot holdings are NEVER
added again to combined terminal NAV. Unspent USDC stays in the ONE spot account.
Check restart, cash+spends=10000, unearmarked coin=0 and D=B-entry_coin_fee-A>=0.
E(M)=Q/M+D at positive marks is a MODEL1x coin coverage identity, not actual
haircuts/maintenance margin/liquidation/ADL/insurance/custody safety proof.

Model fills/journal clocks are explicitly CONSTRUCTED after the source receipt
anchor with source_identity=hypothetical-source-book-sweep. A public quote is
not a matched order or exchange receipt. Do not invent fill latency/probability,
private trade ids, settled-wallet permission or transfer/collateral fungibility.
Same API platform includes Coinbase routing; actual account mode, custody and
ability to use just-purchased settled coin as collateral are still unverified.

## Terminal worlds, benchmark, limits and counting

48 model cells =4portfolio alternatives x2fee controls x2debit controls x3costs.
For each,3 delivery reference scales X=(1/2,1,2)*source future midpoint and3
annual cash scenarios(0,3%,5%) simple interest until fixed expiry give432 EXACT
conditional worlds. These are dependent algebra cases on ONE new book batch,
not432trades/opportunities or independent return observations. No candidate is
selected. Count all48/432 cells and missing outcomes. These are0new predictive
strategy/optimization trials; program total9479013 remains unchanged. No
historical data/model fit/outcome rerun or new forecast variant.

Unit proceeds per coin at supplied X are [Q*(1-delivery_fee)+D*X]*(1-spot_exit_fee).
Combined terminal cash is idle_USDC + rho*SUM(unit_proceeds), with idle credited
ONCE and cash benchmark on the WHOLE10000USDC ONCE. Compute common break-even
rho_min=(whole_cash_benchmark-idle)/SUM(unit_proceeds), conditional excess at
rho=1, and adverse rho=.99. Those are supplied worlds, NOT a USD/USDC peg,
future executable sale/settlement price, a forecast or actual PnL. Include the
residual coin exposure; do not silently assume D=0. Cash benchmarks3/5% are fixed
scenarios, not current guaranteed available T-bill/USDC yield. Idle earns0 here.
Current top-depth/zero-fee controls and same-capital cash are controls, not proof
of risk equivalence to unhedged passive coin or another strategy.

Actual future sale ratio and executable expected net stay None in every row;
no bootstrap/CI/p-value from a single batch, no uncertainty calibration claim.
Fee/access/custody, latency/partial hedge, source effective time, margin,
delivery/TWAP/FX/bid-depth and default risk remain binding. Report current cost
and break-even amount with these limits; positive conditional arithmetic alone
does not establish positive expected net or activate any candidate.

PARTIAL component verdict at most; retain economic negatives, data failures,
inactivity and NULLs. No new prospective strategy-day: fresh current input is
not on-time prospective trading PnL. New prospective scoring requires its own
frozen finite strategy protocol, qualified new input stream and truthful missed
observation journal. No order/money/secret, PR merge/closure, duplicate queue,
panel, scheduler, permanent process or guaranteed-delivery claim. Keep all old
provenance/frozen parents and Claude R337/forward claims untouched. Extend only
M244's existing note after results; append R343 via registry helper.
