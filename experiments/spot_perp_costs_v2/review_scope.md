# R326 input compatibility bridge — bounded independent review

Read complete `lab/spot_input_bridge.py` at SHA256 `dbf2162685740a888e9964ec99e638a07cc8d9b191ed9da6b6413acd21887d34` and complete `tests/test_spot_input_bridge.py` at SHA256 `a68d430cabcbdc33585783478090dc961374e9d818de8d22bc5dca37db85b534`. Bridge hash matched before/after the test run. This is a same-data compatibility/source-guard review, not a review of new driver/audit/report, corrected outputs or whole-system behavior.

Exactly two existing constructed test methods ran: `PYTHONDONTWRITEBYTECODE=1 python -m unittest tests.test_spot_input_bridge -v`. Both passed; full output is `input_bridge_tests.txt`. No additional constructed cases, current quote values, raw data, financial outcomes, network calls, delegates or frozen-file edits were involved. Earlier supporting decoder/cost reads are described in cost_review.md; no broader dependency review was repeated here. Parent's full suite was not independently rerun or certified.

## Conclusions within this scope

No hidden relaxation of economic/source guards was observed in the bridge.

- Explicit finite numeric zero baseSizePrecision is distinguished from absent/None. The bridge first passes the selected symbol through the original schema validator with that one field represented as missing, then restores minimum_base=Decimal(0). All original identity/precision/status/permission/side/order-type/other-number checks still run. The resulting zero is a lower bound, never a lot step or a zero trade. Missing stays unknown; negative/boolean values reject. Source input is copied, not rewritten. Duplicate/absent symbols and malformed inventories delegate to original behavior.
- Only Decimal elements within list-shaped futures depth rows are converted to their exact decimal string representation. Other types and top-level fields remain untouched. The original futures decoder then handles numeric validity, row meaning, contract-to-base conversion, sorted/uncrossed book, depth clipping and receipt/timestamp requirements. Decimal conversion does not turn booleans into numeric strings or bypass finite/positive/order-count checks. Malformed shapes still reach original validation; this is not a new permissive decoder.
- Neither wrapper changes conditional crossing/fee calculations, fixed capital, quantity-grid convention, permission/state gates, unknown owner fee/asset, missing source quote clock, funding uncertainty, actual fill assumptions or actual eligibility. Accepting an explicitly documented zero minimum removes only a false missing/unsupported-minimum rejection; it supplies no spot increment, quantity-asset or execution proof.

## What the two tests established

1. Explicit zero returns minimum_base0 and no inferred lot step, preserves source text, and still yields positive illustrative q on the established common grid. Missing minimum remainsNone; negative and boolean minima reject.
2. A JSON parse_float=Decimal depth price crosses the legacy type boundary successfully, preserves the constructed price101.25, and still converts10 contracts with contractSize0.001 into0.01 base. The source Decimal remains unmodified. A boolean depth price still raises ValueError.

These checks do not exhaust malformed/hostile payloads, all metadata checks, Decimal edge cases, clipping branches or every downstream guard. Delegation/static reading supports the narrow preservation conclusion; it is not whole-system certification. Exact decimal string handoff also does not remove the original decoder/RestBook/walk float representation and threshold limitations. Source quantity/actual spot increment/owner fee/source-clock/funding gaps remain unresolved, and actual eligibility must stayFalse. No corrected real-data cost result was computed or inspected by this reviewer.
