# R344 bounded source-unit/reuse review

Scope: pre-freeze read-only review of finite R344 diffs, scope_check.json, original sealed metadata/identity and preserved R343 failure. No network, finite reporter/oracle invocation, market outcomes, financial-path arithmetic, extra agent or tracked edit.

Issue found and fixed by root before freeze:
- Three incomplete EVIDENCE migrations initially still pointed to the new lane: runner capture.json, oracle capture.json and budget.jsonl. The new lane intentionally has no evidence directory, so these would fail with FileNotFoundError. All three now point to original EVIDENCE; static recheck passed.

Checks actually performed:
- Confirmed lab/venue_carry_v2.py is byte-for-byte old module with exactly one literal substitution: contract_size validation1 -> Fraction("0.00000001"). Original module still matches555add4.
- Inspected original BTC_USDC and ETH_USDC metadata only: contract_size=1e-8 BASE, independently min_trade_amount=1e-8 in each captured record. R329-S39 supplies BASE units, not a universal size1 assertion. The new literal is pinned to these fixed instruments/record identities; it is not a universal spot rule.
- No quantity conversion was introduced. Source shown amounts still enter walk(...unit="base"); trade step still comes from min_trade_amount. The contract_size value is only validated, never multiplied/divided into displayed amounts or holdings. Inverse books remain USD face with existing sum(face/price) arithmetic untouched.
- Static exact-rewrite assertions passed for the full new runner and oracle. Runner changes are registry/lane/module identity plus all raw inventory/capture/body reads through original EVIDENCE. Oracle changes are registry/lane identity, the same independent literal correction, and original EVIDENCE paths for inventory/capture/budget/bodies. Original R343/one-same-venue-current-capture budget-scope assertion remains unchanged.
- All10 original evidence files (eight raw bodies, capture.json and budget.jsonl) exactly match both4cb12cd and currentHEAD. No v2 evidence directory or collector exists. Original scope remains8GET,512KiB reserved,56s reserved,8charged,6609accepted bytes; unused allowance closed. Historical spend7757requests / reported229.85MiB unchanged. No new acquisition is introduced by either driver.
- R343 results still contain all8 original spot metadata identity failures and unknown actual expected net in every recorded model. Original failure remains frozen; this correction is one reuse of the same current batch, not new independent or prospective evidence.
- scope_check.json agrees with inspected finite changes. Financial rules, capital, symbols, sizes, depth, clocks/state/gaps, fees/debits, terminal worlds and unknown execution fields have no implementation diff.

Limits: reviewed R344 files are UNFROZEN at review time. New protocol/code/runtime/input identities must still be frozen and committed before economic outcomes, binding the exact original ten-file raw inventory without copying/resetting its budget. This review does not rerun the full suite, validate profitability, certify actual fees/access/margin, or make future sale/settlement/FX known. No remaining issue found in this finite source-unit/reuse diff after path fixes.

Reviewed local file identities:
- lab/venue_carry_v2.py sha256 1cca0cd2071f56c4e0a38e61e025640a66678d6757034844a609253d8fef3523
- scripts/run_same_venue_v2.py sha256 bedf391e0a69bf8c6921aa67e004b1a1eb9be38d1d7f4aec638fb3195db12c0b
- scripts/check_same_venue_v2.py sha256 e263fa748961582657e69fe25d2e22f96eb339ee59622cf637f80d8a6a0b18c6
- experiments/same_venue_carry_v2/scope_check.json sha256 8958204ea07a744b2f0a442d5b2982475a4bb8c95179046db19305b21d136a84
