# R325 conditional cost peer review

Independent bounded financial/source-interpretation review only. No network, agents, fresh market capture, real quote values, outcomes, production search or edits outside this cache. Root owns implementation and integration. This review is not whole-system, acquisition/runner/audit, frozen-family, exchange-deployment, fill, funding or profitability certification.

## Exact read and execution scope

Read complete `lab/spot_quote_costs.py` first at SHA256 `62a134a268f67142172b4b34842ffb65ba7bccfae424be63219355977654c6dd`, then complete root-patched version SHA256 `e7f2eac8ef47a91d3d1ea181a7500ca5c4a709564cea8615f48af37c3e552dc9`. Read supporting `Receipt`, `RestBook`, `positive`, `_aggregate`, `mexc_book`, `walk`, `receipt_quality` in `lab/executable_quotes.py` (SHA256 `8b71cc4e1922fdb40399ca162e7bcf91ab41d835cbaa8ba2ce9b9ec5fd46688d`), and relevant DepthLevel / MEXC quantity parser definitions. Helper-file hashes recorded during read: `lab/microstructure.py` `80e67c0a2a508e1c662050dc1fa3f923408584e6e653ac7858c381f56fa5f11f`; `lab/mexc_depth.py` `3d6d7084f45b01e9e24669ec9914673cde56ca04cadea5cfe01ef22072f404bb`. Those whole files were not all reviewed.

Old-version execution stopped at its initial SHA guard after root changed the file; no old-version arithmetic cases executed. Exactly eight constructed cases then passed against patched e7f2eac8…52dc9, whose SHA was checked both before and after execution. Reproduction: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python .cache/R325-ws-source/cost_handchecks.py`. Inputs/assertions are retained there; complete constructed outputs are in `cost_handchecks.json`. Root's separate tests were not independently rerun or certified here.

## Findings and corrected blockers

Two material issues were reported promptly on initial static reading: public status/API/direction/MARKET issues were flags but did not suppress numeric costs; direct conditional_costs accepted q without validating the advertised perpetual grid or declared spot decimal convention. Root corrected both before these eight cases. The patched reasons include public flags, both q grids, and strict integer futures state/type checks; absent/invalid permissions and the combined invalid test now return costs=None. Actual eligibility was and remainsFalse in both versions.

Within the declared conditional model, checked arithmetic has the correct sign and dimensions: crossing=(spot buy-spot sell)+(perp buy-perp sell), charges=(spot buy+sell)*advertised spot rate+(perp buy+sell)*advertised perp rate. It is a same-snapshot two-leg round-trip crossing/fee requirement, not captured basis profit, carry PnL or measured return. All 1x/2x/3x cases multiply the entire crossing+fee amount. One-leg bp divides by q*mean(spot mid,perp mid). Since total capital is fixed10000, cost dollars and cost-on-total-capital bp are numerically equal; that equality would cease to hold if capital changed, and the API rejects another capital value.

Minimum source quantities are kept distinct from grids: minimum_base is checked with q<minimum, while the illustrative spot decimal convention and actual published perpetual volUnit*contractSize form the common grid. The minimum0.03 in case1 does not become a0.03 step. Quote-amount minimum/maximum checks use the hypothetical walked buy and sell cash, rather than q*max_mid. Unknown required minima/maxima produce blockers; unknown advertised fees block advertised_quote_fee but intentionally do not invalidate the separately declared zero_charge counterfactual. Factory number/type checks and unknown branches were read; exhaustive malformed-metadata fuzzing was not performed.

The models retain base quantities only under an explicit unverified spot-base assumption. Public commission metadata is an advertised quote-fee scenario, not owner fee-rate/fee-asset proof. No base-fee inventory adjustment, funding receipt/payment, leverage accounting, genuine exit, fill latency, source-event age or net market return is inferred. Both actual_order_allowed and executable_pair_eligible areFalse, and net_market_return isNone in every checked case.

## Eight constructed hand cases

1. Spot bid99/ask101 and perp bid98/ask102, spot precision2, minimum base0.03, perp contractSize0.1*volUnit1. Shared step0.1, fixed250/maxmid100 gives q2.5. Four cash values252.5,247.5,255,245 give crossing15, one-leg reference250, cost600/1200/1800bp for1/2/3x, and capital costs15/30/45bp.
2. Same q/books with public quote-charge rates0.001/0.002: spot roundtrip charge500*0.001=0.5 and perp500*0.002=1.0, total charge1.5; break-even16.5 and660bp at1x. The control does not alter q.
3. Two levels each side, top size1 and second size2, still q2.5: walked cash255.5,244.5,258,242; crossing27, common capacity3.
4. Exact same q and books, top_only: common shown capacity1, insufficient shown depth, costsNone. Separately inside this clipping case, mexc_book with marketOrderMaxLevel1 clips both futures sides to one level; discarded levels cannot supply shown capacity.
5. Minimum market amount250: midpoint notional250 passes the sizing proxy, but spot sale247.5 fails actual walked quote minimum and suppresses costs.
6. q50 on large shown books: spot entry buy5050 exceeds its segregated5000 cash allocation; costsNone, with no cross-leg cash netting.
7. Spot offline/API-disabled/closed direction/no MARKET, futures API-disabled/bool stateFalse, q1.055 off both perp0.1 and spot0.01 grids: all five public flags plus both grid reasons are blockers, costsNone.
8. Constructed3s request interval and1.99s cross-leg receive skew: both local blockers appear and suppress costs. Good local pairs still have source-event age/fill eligibility unresolved.

## Boundaries parent must retain

- The fixed250 leg budget is a **maximum-mid notional sizing budget**, not a guarantee that walked entry cash is<=250. Case1 deliberately shows buys252.5 and255. Direct conditional_costs itself enforces5000/5000 reservations, not250; its frozen caller must invoke the sizing helper with the registered250 default and preserve the same q across all controls. No runner/collector code was reviewed here.
- receipt_quality is evaluated asof=max(two receive times), so it evaluates relative first-seen pair availability at that receipt epoch. It is not a report-time staleness check and cannot establish source quote age. Preserving original receipts and the explicit unresolved source-clock guard remains essential.
- Supporting RestBook/DepthLevel/aggregate/walk pass through floats; walk returns float before conversion to Decimal. Hand arithmetic above is exact for these chosen inputs, not a proof of exact decimal source-cash preservation or boundary rounding on arbitrary metadata. Near-min/max/cash thresholds therefore retain numerical precision limitations.
- Direct construction/replacement of SpotRules bypasses its parser's complete number/type validation; intended metadata intake must use spot_rules. Sparse absent fields block or raise rather than supplying guessed limits, but exhaustive arbitrary-object API hardening was outside these eight checks.
- The actual spot lot/tick increments and quantity-asset contract remain unverified; decimal precision is a declared diagnostic convention only. A field called baseSizePrecision is a source minimum, never a published lot step. Official source evidence and sample ms semantics do not certify matching deployment, owner fees, fresh executable liquidity or whole-system correctness.

No remaining blocker was observed for the narrower checked conditional arithmetic after root's correction, provided these caller/source boundaries are retained. No real capture or outcome was computed by this reviewer.

## Final prefreeze boundary-guard recheck

Root's final prefreeze module SHA256 is `bc682b8dcc1153ed66125e21aa202c5783a59c66d9b393e4c5c41ca911231e95`. This follow-up is limited to reading the changed minimum/maximum quote-amount and segregated-cash guard region (lines142 onward), plus exactly two constructed local boundary cases. The new guards conservatively append unknown-boundary reasons whenever float-derived quote amounts are within1e-8 of the minimum/maximum or5000 cash/reservation threshold; ordinary below/above-range blockers remain. This mitigates the earlier threshold-rounding caveat while retaining the underlying float representation limitation.

Both cases passed with the bc682b8d…1e95 SHA checked before and after execution. For q1, spot bid99/ask101 and perp bid98/ask102: minimum market amount99 produces costsNone with `spot_minimum_quote_rounding_boundary_unknown`; minimum98.9999999 is1e-7 away, exceeds the1e-8 guard margin, and retains numeric crossing cost6 with no calculation reasons. The reproduction and complete constructed outputs are `cost_boundary_handchecks.py` and `cost_boundary_handchecks.json` here. No extra cases or current-data calculations were performed.

Version scopes remain separate: the complete patched-module review and eight earlier constructed cases apply to e7f2eac8…52dc9; these two cases and changed-region read apply to bc682b8d…1e95. The earlier eight-case script intentionally pins its old version and was not rerun on the new one. Other boundary branches were read, not independently exercised in this limited follow-up. Parent's focused/full suite and new collector/runner/oracle remain outside this peer review. Source quantity/actual lot/owner fee/source-clock/funding gaps, actual eligibilityFalse and the earlier caller/sizing limits remain unchanged.
