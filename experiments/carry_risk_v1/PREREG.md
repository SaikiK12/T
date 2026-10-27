# PREREG: source-bounded inverse margin and whole-capital marked carry

- **Registry id:** R346
- **Owner (single writer):** Codex
- **Date registered (UTC):** 2026-10-27
- Canonical method M244; existing alias YT26-04-DATED-CASH-CARRY.
- Claim: issue7 comment6442384076, existing consolidation draft PR56.

## Binding question and preserved decisions

R335 reports a useful historical locked-to-expiry proxy but spreads terminal
returns evenly over holding hours. It explicitly did not measure the marked
path. All54 underlying data files are absent across available workspaces.
No historical drawdown replay or new historical download is authorized here.
R340/R341 already cover inverse fee-prefunding identities; R343's original
schema failure and R344's corrected same-data economic worlds remain intact.
This lane adds source-bounded margin and marked-state measurements to those
EXISTING accounts, without replaying their economic experiment or selecting
a better size, fee, venue, model, leverage or historical rule.

R310/R311 read: actual1318 missing funding events repaired,12calibration models
exercised,224/273 common scored validation days; selected2x/3x costs lose. No
rerun, gap/tradability relaxation, validation winner or leverage-up. Claude's
R337, forward scripts/journals and M412 queue row stay untouched.

## Source and input contract

One new official-source web query, maximum3 static documentation GETs,1MiB/body,
3MiBtotal,15s/attempt,60s GETwall were declared BEFORE dispatch. Actual3HTTP200,
266298body bytes,3.379494s GETwall; scope CLOSED, no retry/redirect/login, market,
history, account, private endpoint or order call. Raw HTML remains ignored cache;
exact receipts, body hashes, source reading, query and example checks are pinned.
No reauthorization of any old source/R340/R343 allowance or historical7757/8000
requests and reported229.85/250MiB accumulated spend.

New Oct13/Oct21 documentation was first received12:55UTC, AFTER R343's07:07UTC
prices. It is a POSTHOC current-rule contract; never on-time historical evidence.
Current dated BTC/ETH inverse futures are Tier4, USD-face N, maximum75MUSD,
25x maximum IM leverage through3percent of maximum size=2.25MUSD. EXACT
IM fraction1/25 and MM fraction2/75 follow the formula; rounded2.67percent
is not used as exact. Implement ONLY this flat segment. Above it or maximum
size remains unknown/rejected, without interpolating the nonlinear curve.
The generic N=coin prose has an explicit inverse USD exception in the table.
Do not import stale2025 additive coin-size slopes or apply current rules to
the absent2021-2026 price history.

S:SM segregates BTC and ETH settlement assets. Each purchased coin is the SAME
inverse collateral, not a second deposit. USDC idle cash cannot automatically
cover BTC/ETH requirements. SM margin balance includes futures unrealized and
realized PnL; open-order IM is additional. Available margin differs from settled
cash and spot-spendable/withdrawal balance. Cross collateral/portfolio margin,
haircuts/fees, complete account positions/orders, inverse USD-to-coin conversion
denominator and exact liquidation trigger/engine remain unverified. Last30min
projected-margin convergence is NOT implemented and returns unknown.

Reuse exact R344 committed results/journal pack and the unchanged8 first-seen
R343 raw bodies. Existing first-seen/source clocks, state, units, depth failure,
capital allocation, current book sweeps, fee assumptions and all cost multiples
are inherited. These are old public quotes and HYPOTHETICAL account fills;
no newly current quote, source-effective-age proof or actual fill is inferred.

## Finite implementation and measurement

Freeze and COMMIT this spec/sidecar,69-file local transitive code/test/runtime
closure and exact input identities BEFORE any new market-derived result. Runner
verifies all identities and committed own manifests/spec before/after; parent
verify checks original raw inventory. Fresh output only, no overwriting journal.
An independent stdlib checker imports no production financial/risk/report code.

Reopen copies of all132 original SpotCashAccount/InverseCashAccount journals
through their unchanged native engines. Never post new financial events. Verify
every copied journal remains byte-identical, quote cash/coin ownership matches
parent, no unearmarked coin is added, no pending fee/conflict becomes known.
Preserve all48 parent model cells:4original size/depth portfolios times2fee
controls times2spot-fee assets times1x/2x/3x. No new cash ledger or derivatives
cash denomination. All alternatives have the SAME10000USDC initial capital.

For an inverse account with signed USD face q, coin balance B and reciprocal
entry a, calculate UPL_coin=q*(a-1/M), E_coin=B+UPL_coin. A short can also be
written E_coin=D+Q/M, D=B-Q/F_harmonic. Convert total E_coin to USDC ONCE using
the supplied spot midpoint S. Do not add original spot holdings again or realize
UPL into cash. Whole NAV = idleUSDC + sum(E_coin*S), without compounding,
external deposits, liquidation fills or hypothetical interest credits.

Report original-snapshot marked views with explicit conversion controls INDEX,
FUTURE_MARK, and UNKNOWN. These are conditional denominators, not an assertion
that either is the venue's actual convention. Per-coin IM/MM is Q/denominator
times the exact fraction, with zero additional paper-subaccount obligations.
Actual complete account and mode remain unknown. A conditional >= comparison
is not the source's unspecified liquidation trigger or account admission.
Preserve UNKNOWN when aggregating unknown per-coin margin states; a known
shortfall is false. Missing full parent input keeps full NAV/frontier unknown,
even if a known partial leg can be shown. No partial portfolio rescue.

Every model gets FIXED5x5x2=50 stress states,2400total:
- Common coin/index/spot scale lambda in .25,.5,1,2,4.
- Common future-mark-only factor beta in .9,1,1.02,1.1,1.25.
- Both explicit INDEX and FUTURE_MARK denominator controls.

M_i = originalM_i*lambda*beta; S_i = originalS_i*lambda;
index_i = originalIndex_i*lambda. Original spot/index quote ratios are retained,
not silently assumed equal to USD/USDC1. No new stablecoin FX distribution.
These are independent STATES, not a sampled/observed price path. Mark/index
ratios outside the source's adjustable default10percent band are flagged;
they are outage/adverse-scenario controls, not asserted reachable venue marks.

Retain the full-capital10000 cash control and a matched-deployment spot-only
control: same initial bought coin/spot commissions and idle cash, no inverse
fees/UPL. These compare arithmetic exposure, not demonstrated equal realized
risk. Do not adopt a winning control or alter size/cost by its outcome.

For each model/5coin scales/3loss floors2,5,10percent,720frontiers are predefined.
Write NAV(beta)=idle + lambda*R + H/beta, where R=sum(D_i*S_i) and
H=sum(Q_i*S_i/M_i) at original prices. Solve the exact beta threshold for NAV
>=10000*(1-loss). If the constant part already covers the floor, retain the
unbounded flag. Incomplete inputs withhold the boundary. These are conditional
capital-loss budgets, not chosen trading stops, loss probabilities or CIs.

Primary ILLUSTRATION is the same5000full/public-standard/base-debit case as
R344, showing ALL1x/2x/3x; all other original cells remain. The static price
scales, basis widening and margins do not forecast returns, select a strategy,
make current costs/owner fee entitlement known, or activate a paper lane.

## Checking, uncertainty, accounting and decision

Meaningful tests cover signed payoff, daily settlement without duplicate PnL,
fee debits, same-coin margin, no USDC rescue, unknown mark/fee/denominator,
tri-state aggregation, flat-segment boundary, expiry exclusion and exact loss
frontier. Independent prefreeze source reviewer reproduced8published examples
and checked13invented financial/state identities. One UNKNOWN-to-FALSE bug was
found, corrected and rechecked BEFORE freeze; original failure receipt retained.
Full unittest discovery is required before committing lab code.

The independent post-freeze checker reconstructs native journal chains, every
coin/cash state and marked NAV/IM/MM, all2400worlds and720boundaries, with exact
Fractions. It checks complete versus unknown totals, no second collateral,
unchanged journals and source identities. Fresh run must reproduce compressed
results/journal pack/audit bytes. Failures are retained and never overwritten.

0new predictive trials: this is a fully enumerated engineering/risk diagnostic
on old sources and parent allocations, not a new return hypothesis sweep.
Program9479022 unchanged; R335's6strategy trials remain counted. No invented
independent samples, p-value, bootstrap, dependent-null significance or
calibrated future-loss probability from these deterministic worlds. Historical
proxy profits, old nulls and missing data retain their original status.

Verdict PARTIAL if conditional risk/capital arithmetic is reproducible while
owner/account/margin/execution evidence is absent; never DATA_PASS or activation
from a finite scenario. Outputs retain actualrisk=false and actualexpectednet
unknown. New prospective strategy days0. No orders, money, secrets, merge/close,
permanent daemon, current market acquisition or historical/model download.
Integrate exact results/source scopes into existing M244/intake and append a
registry row using its helper. PANEL is unchanged generated information.

## Frozen identities

- code_inputs.json SHA256 66c01e58165fa4c6be9031ede834feabf85d4c85cf009f126684c07b8040fc0d
- inputs.json SHA256 f96787bb23116eb1005927db04ecef8a50110e74033ec684c97e2af7724ea9e5
- fixtures.json SHA256 31037eca081442b75a7d1f63cb4478e73d7634598c311beb7444ff855090307c
- source_review.json SHA256 659b31edb0bdfc60080e05f9f805554b5faed92277d59d12b10acbbef01b866d
- margin_contract.json SHA256 0aa11ebb2e7364e0cea838218a31dd4e0f6cbf6f4f4f79d2a3685c50c6a74e52
- source_receipts.json SHA256 bbcdfacb1fca4764155afc521162aef6e4391e4ccd6eb8967f8e012d206aa40c
- source_search.json SHA256 19bbbb44ee0da068c860782aabec8bea9fe4f427c06586ba0a82ebced2e79d87
- sources.json SHA256 56eebcc337cf1fce11c0fd2330654bf111bb3591ff6390cc9f7fb80cb98446f3
- historical_availability.json SHA256 5431b4871a607756647bdb1883a7a352b6b37ad7e30a9f5fcef282e13a57679b
- tests_before_freeze.json SHA256 52abe4e35f98468c91bcc6d096c59db7148556831291d93d198ef367814a4049
- implementation_review_before_fix.json SHA256 9385c6315d9127aa1162b9c47824d5b64f9ead2013d357a11d9941878811a9c3
- implementation_review_after_fix.json SHA256 8f96e70b7ff053f1dab07103a87ce444b67c8c039b086e5990c4af070378d006
- source_formula_examples.json SHA256 7119b903f9056b939dc33cc1397f412ed908ccf7a0b0090dfde72293e21df786

Full1580tests PASS,3existing skips,207.242s. Input manifest36files.

