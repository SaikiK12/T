# R321 bounded Lighter funding unit bridge

Verdict: **not verified**. Neither the received historical `Funding.value` model nor the received protocol prefix definitions currently authorizes quote-per-base settled funding cash. The source narrows the gap but does not close it. Do not substitute a trade-close/mark/index proxy, and do not treat protocol source as the deployed API contract.

## Exact equations and what they establish

At prover tree object `16c0f36d75f2306ee242e26e507e4c237f7f4074`, `block_pre_execution_constraints.rs:588-617` defines signed hourly integer H by dividing the clamped absolute rate by8, discarding the remainder and restoring its sign (zero normalized). With stored encoded index I, the funding increment is **dP = H * I** and, only when funding is due and market active, **P_new = P_old + dP**. Same-block oracle updates follow at627 onward. This is already price-weighted; it is not merely a sum of dimensionless rates.

`constants.rs:214,232-233,250-252` establishes T=`FUNDING_RATE_TICK`=1,000,000; one USDC=1,000,000 internal USDC units; `USDC_TO_COLLATERAL_MULTIPLIER`=1,000,000; one USDC collateral=10^12; `FUNDING_RATE_MULTIPLIER`=(10^6/10^6)=1. `USDC_ASSET_INDEX`=3 and `USDC_MARGIN_ASSET_INDEX`=0 at389-390. These are code-level constants, not definitions of the API string units.

Conditional dimensional identity only: if S_price is the as-yet unverified number of encoded index units per physical quote/base, then **dP/(T*S_price) = (H/T)*(I/S_price)** has quote/base dimensions. With an unchanged physical signed base position q, the funding-prose equation would suggest **cash = -q*(P_b-P_a)/(T*S_price)** over the matching prefix interval. This is NOT a verified account-application formula: the received code does not establish the S_price/base-decimal/quote_multiplier mapping, exact funding application rounding/checkpoint behavior, or deployed/API equivalence. Position changes would require the proper position-specific subintervals. No numerical normalized cash coefficient can yet be asserted.

The cached funding prose at lines116-131 states funding = -position * index * fundingRate and positive credited/negative charged. That alone does not define historical `Funding.value` or map raw prefix units to base/USDC units.

## Distinct newly received mechanics

1. Historical `Funding` has `timestamp: StrictInt` and `value`, `rate`, `direction`: `StrictStr` (29-34). `from_dict`85-104 copies those values unchanged; there is no cash/unit conversion, direction enum or event/asset definition. A strict string type does not distinguish raw prefix increment, normalized quote/base, notional cash, magnitude-only, or another value definition. Those remain unknown alternatives, not source claims.
2. SDK `FundingApi.funding_rates`39-99 is cross-venue rates and returns `FundingRates`; its serializer224-277 uses GET `/api/v1/funding-rates` with empty auth settings. This is a different object/path from historical `Funding`; no historical request or response serializer bridge was received. No SDK code was executed.
3. The exact funding tick, USDC, collateral conversion and asset indices above are now read; the old missing-constants uncertainty narrows, while base/price/quote-multiplier application remains unresolved.
4. `AccountTarget.apply_collateral_delta`664-681 gates a supplied signed delta, adds it to margin balance and also to strategy balance for the insurance fund. `get_relevant_usdc_collateral`644-659 chooses insurance strategy versus USDC margin balance. This proves a generic USDC-labelled mutation helper, not that funding calls it or how a prefix becomes its delta.
5. Public-prefix alternative refined: `PublicMarketDetailsTarget`697-727 explicitly allocates/registers prefix, mark and quote_multiplier as public inputs; witness setters754-780 bind those same fields. `PublicMarketDetails::from_public_inputs`649-677 decodes sign0/+1/-1 and four16-bit magnitude limbs plus mark and quote_multiplier. `MarketRiskDetailsTarget.partial_register_public_input`867-887 exposes the same seven-target layout. These are circuit public inputs, not evidence of a freely queryable historical REST/WS prefix field, data availability, authentic proofs, event-time coverage or a deployed version.

## Bounded cache checks and correction to the earlier scope description

The cached `account_position.raw` does **not** contain an identified funding-application function. Full-file function/funding-name searches show fields, init/reset, selection/diff/witness code only. Read ranges:1-278,290-470,478-630; `init_if_empty`205-261 resets the checkpoint on flagged empty/stale initialization, `apply_diff`427-473 generically applies differences, and `calculate_aggregated_usdc`307-320 divides allocated margin by the collateral multiplier and combines signed entry quote. Those are not funding settlement. Lines279-289 and the tiny final witness tail were not audited. The statement in R317 that the funding application function was merely unread in this file should remain corrected to **funding application not located/received**.

All nine `.cache/r316_lighter_source/*.raw` bodies were searched for literal `/api/v1/fundings`, `"Funding"`, `funding_rate_prefix_sum`, and `last_funding_rate_prefix_sum`: zero occurrences. Four endpoint HTML bodies contain only the `fundings` navigation slug, not its endpoint/schema definition. The cached ws_client.py also has none of those definitions. This is a bounded negative search of received files, not a claim about every official source or public endpoint.

## Exact sources, versions and read scopes

New GET receipts are in `receipts.json`; full bodies in this ignored cache only. All HTTP200, complete below the262144-byte cap, no redirects/retries/login. Four requests total;91022 bytes;1.4253 aggregate seconds. No market/RPC/account requests or datasets read.

- https://raw.githubusercontent.com/elliottech/lighter-prover/16c0f36d75f2306ee242e26e507e4c237f7f4074/circuit/src/types/constants.rs — SHA256 `2245c914875768a63f2c0c1de542076815be57762edeb001fcf8fbaba75525ee`;30784 bytes; lines205-272,382-398,438-452 plus targeted-name search. Blob SHA1 `d7606ef5735127873b8fb1af4f7bd5b1b18e1d7f` verified against cached tree.
- https://raw.githubusercontent.com/elliottech/lighter-prover/16c0f36d75f2306ee242e26e507e4c237f7f4074/circuit/src/types/account/account.rs — SHA256 `25a4c2deee0d235c7b76848e68a6c13454a30478745ddb11ef3b34a0e059a4c8`;46477 bytes; lines1-80,620-715 plus full-file funding-name search (none). Blob SHA1 `9fcc5fdaa786bc40facd8dd91f9c6a6c2da13931` verified against cached tree. Rest unreviewed.
- https://raw.githubusercontent.com/elliottech/lighter-python/a7a9ba88514d38a863a33642acd41f8adf442e5c/lighter/models/funding.py — SHA256 `29715b2d22bb7b23dc400f911df6e26a5a90463c5d43725ea89f07286daadeed`;3280 bytes; full106-line generated model.
- https://raw.githubusercontent.com/elliottech/lighter-python/a7a9ba88514d38a863a33642acd41f8adf442e5c/lighter/api/funding_api.py — SHA256 `4237e4d54620aff181ad585aebb14793fce45e14561edb94ae22913c641bca00`;10481 bytes; full279-line generated client. Historical FundingsApi not received.

The prover pin is a **tree object resolved from main**, as recorded in R317; it is not here verified as a commit, deployed circuit or historical deployment. SDK pin is the official commit inherited from R316 receipts; no deployment linkage verified.

Reused exact URLs under the same prover tree pin:
- `circuit/src/block_pre_execution_constraints.rs`: SHA256 `38aeef836aa8e4be6d2973523fa2f50f87c8aa38dc8cf778722eff4012f7dce6`; read1-65,349-380,525-640,882-884 in this pass. Earlier R317 had read the full pre-execution body. No imported arithmetic helper audit/proof execution.
- `circuit/src/types/account_position/account_position.rs`: SHA256 `a025a517b908e249c960151cc1fe6df1a47101c3aeafe86a38539ca5a9a8caf1`; ranges/search as above.
- `circuit/src/types/market_details.rs`: SHA256 `bfda0e2d630fb3034362715e16d5eba72807f621e93614348ec62e78b37ccf00`; lines620-784,800-900 and funding-name index. Remaining selection/hash code not audited.
- `circuit/src/block_pre_execution.rs`: SHA256 `ee1a0cbd73623a5e508092c49c5239df15c433c11a58508cd08a04bc8e68911a`;145-205 only this pass (root/public-input context, not complete parser).
- Cached tree URL https://api.github.com/repos/elliottech/lighter-prover/git/trees/main?recursive=1 — SHA256 `9807f913c32e3c96f09933a3de1b481b6b0a02ad411b11457cb3dce52056005b`; path metadata searches only, no new tree fetch. `circuit/src/tx_constraints.rs`(187132 bytes) and `circuit/src/types/risk_info.rs`(55453 bytes) are **unreceived path candidates**, not read funding implementations.
- Cached funding prose URL https://docs.lighter.xyz/trading/funding — original received body SHA256 `19d8250454f4ac429146dc39e64b174f4e9a5e5afab75a6aa791ca3cc15b889c`; extracted text SHA256 `679edf18a63d3d9c303de9aeb40ccbf17eb862c199bb592cdb72e79477adf430`; only116-133 reread here. No new GET.
- Cached official HTML URLs searched: https://apidocs.lighter.xyz/reference/orderbookdetails , https://apidocs.lighter.xyz/reference/priceoracleinfo , https://apidocs.lighter.xyz/reference/marketpricecharts , https://apidocs.lighter.xyz/reference/funding-rates . Body hashes/version receipts remain `.cache/r316_lighter_source/receipts.json`; this pass only searched for the literal historical/prefix definitions above, not full pages. `info_doc.raw` is the earlier302 body, not read as an endpoint definition.

## What exactly still blocks the bridge

A. Historical endpoint/server contract: definition of `Funding.value`, scale, settlement asset, relation to `rate`/`direction`, sign/magnitude conventions, timestamp unit and event/publication/revision semantics; no historical FundingsApi/OpenAPI definition received.
B. Protocol-to-cash application: actual code multiplying position by the market/checkpoint prefix difference, all base/price/quote_multiplier conversions, rounding, checkpoint advancement, cross/isolated/strategy routing; imported arithmetic helpers and call sites unread.
C. Deployment/API binding: which deployed historical protocol revision generated the public API fields; no deployment hash proof or API server serializer maps this tree to those strings.
D. Prefix alternative data binding: public, authentic, event-aligned prefix endpoints/records, market/decimal epochs and interval completeness. No actual proof/public input record was acquired or verified. A circuit-public field is not by itself a public-history access contract.

Weak alternatives remain open: `Funding.value` might eventually supply normalized per-base cash, or authentic public prefix differences might avoid separate event index observations, once A-D are established. Neither is denied or promoted to usable settled cash here. No economic statistics, orders, account access, profitability claim or production/docs/intake edit.
