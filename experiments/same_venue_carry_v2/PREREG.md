# PREREG: exact same-input spot-contract metadata correction

- **Registry id:** R344
- **Owner (single writer):** Codex
- **Date registered (UTC):** 2026-10-27
- Claim: issue7 comment6435949011; existing draft PR56, canonical M244.

## One source-schema correction, before recalculation

Parent R343 freeze555add4/raw4cb12cd/failure93df894 stay immutable. All8 public
GETs succeeded /6609 accepted bytes, but the adapter's spot contract_size=1
constraint failed both BTC_USDC and ETH_USDC. Both original sealed metadata
records explicitly give0.00000001. R329-S39 says this field is base coin and is
NOT the amount increment; it never said its value must be1. This was an
incorrect inference by Codex. Preserve all8preparation failures,48model cells,
432incomplete worlds, original4190check oracle and byte-reproduced journals.

New lab/venue_carry_v2.py is EXACTLY the frozen parent module with ONE literal
substitution: rational(contract_size)!=1 becomes !=Fraction('0.00000001').
Never multiply or divide shown spot amounts by contract_size; quantities remain
base coin, min_trade_amount remains minimum AND increment, inverse amounts stay
USD face. Require this exact observed literal rather than accepting arbitrary
positive contract sizes. Old1 and1000 fixtures must fail. No weaker lot, price,
depth, state, availability, clock, gap, fee or custody rule.

Separate runner/oracle bind new registry/lane/module identities and point to
the ORIGINAL parent evidence directory; no duplicated market dataset or new
collector. All three joined capture/budget paths also use that directory.
Original R343 budget scope stays R343. Code substitutions and peer-review scope
are pinned. No runtime monkeypatch or edit of a frozen module.

Raw quote values were already visible while diagnosing the schema failure;
this is a transparent same-snapshot compatibility continuation, NOT untouched
validation, fresh prospective PnL or an independent new quote batch. No economic
parameter/strategy is selected or optimized after seeing prices. Source and
payoff assumptions remain the original R343 finite contract except that literal.

## Frozen identities

- code_inputs.json SHA256 c2d5626a41f4248d8ac867631c5061386bdf5912f9084af3a213e7e106da2021
- inputs.json SHA256 af1a253269cf350b43dc188be60d354b1af8064f231291e251d368bd9f8358ca
- fixtures.json SHA256 034b6ea6ac2f098b55e7bd51fcf5426de1798f02ff19cab705a7feef5d9439e3
- sources.json SHA256 7dd66c5b7b2d390aedc6d8e6b9bd4854bd6a07b444b70bfb6f0a353e753fb84b

Full1559tests passed in207.203s,3existing skips;20targeted original/new tests
passed. Review and scope_check.json are pinned;27source/evidence/test identities.

Python3.12.14,65local source/test/parent-closure files; original manifests,
specs/source records, raw hashes and preserved failure/result pinned in inputs.
Freeze/commit complete spec/code/fixtures/sources before R344 report; commit own
data_inputs manifest bound to this freeze and the original raw inventory. Raw
inputs already committed4cb12cd. Verify all hashes and committed identities
before/after. Never change parent receipt timestamps or use current clocks to
make the old inputs appear fresh. Original source-time decision anchor remains.

## Identical finite economics, unknowns and counting

Original R343 PREREG defines the unchanged input contract and finite algebra:
ONE10000USDC cash peralternative; BTCthenETH;1000/5000USDface percoin;full/top;
same base purchase sized to3xcrossing and both fee-debit controls;public-standard
floors orzero-charge,1x/2x/3x crossing/fees; no second cash/coin deposit. Actual
wallet/settled collateral fungibility is unknown. Original clock/availability
gates retain2srequest/body/publication,1sjointskew,50msclockstep. No guard rescue.

48models /432conditional worlds are a REPAIRED ATTEMPT of the same finite
matrix on the SAME one eight-request batch, not48newpredictors or432newreturn
observations. Parent incomplete matrix retained separately. Report all economic
negatives, capacity failures, inactivity and unknowns.0newdistinct predictive
strategy trials; program9479013 unchanged. No historical/model refit or rescore.
No selection of a favorable coin/size/debit/depth/terminalworld/cost.

Terminal idle credited once plus common rho*sum[Q*(1-deliveryfee)+D*X]*(1-exitfee),
D=net bought coin-entrycoinfee-sum(face/entry), exactly as parent. Whole-capital
cash scenarios0/3/5% annual simple interest to Dec25,2026 08UTC; idle0. Supplied
X scales1/2,1,2 and rho1/.99 are exogenous conditional worlds, not forecasts or
USD/USDC parity. Minimum exit-ratio hurdle is not executable future proceeds.
Preserve residual coin risk, actual sale/TWAP/FX unknown, delivery/custody/margin
and default/ADL/insurance risks. Public source visibility is not owner access,
actual fills, fee/debit/rounding proof, source engine-age or liquidation immunity.

Independent stdlib raw/financial/journal oracle has its own exact literal
correction; it imports no production financial function. Same full arithmetic
and cash ownership checks; do not upgrade the parent's incomplete-path pass.
Full repository suite before new lab commit, original+new20targeted tests,
fresh-directory byte reproduction of results/journals/audit. Peer review is
limited to source-unit/raw-path/diff preservation, not full system attestation.
Preserve any new failure; do not patch frozen R344 code to make it pass.

PARTIAL component at most. One source batch supports no calibrated uncertainty,
expected net gain, bootstrap confidence/p-value or profit claim. No strategy
activation or newprospective day. Newprospective scoring requires separately
frozen finite protocol and on-time new evidence, retaining missed observations.
No new HTTP/search/static source/history/account/order/chain/model requests;
all closed allowances stay closed, historical7757/8000 and reported229.85/250MiB
unchanged. No secret/money/merge/closure/permanent process/scheduler, no duplicate
queue/panel, no Claude R337/forward edits. Only M244 existing note after results;
registry append via helper. Source records remain42historical, not new extraction.
