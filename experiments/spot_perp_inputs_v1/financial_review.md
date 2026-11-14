# R324 spot cash model — bounded financial review

Reviewed `/workspace/T-consolidation/lab/spot_cash.py` in full at SHA-256 `7ab221fd898cf25ce48c77fb05a16e8a7e445f6b90a65fb34e1be078b53c6a71` (17,450 bytes). Hash was rechecked after the hand calculations ran and remained unchanged. Read supporting `number`/`text`, `FrameClock`, `clock_known` and append-only record/locking helpers. No production or canonical files were edited, no network calls made, no agents delegated, and no market or outcome statistics computed. The parent is independently implementing/tests and owns canonical integration.

No concrete financial blocker was found in the reviewed model. This is a bounded code and finite synthetic arithmetic check, not whole-system verification, current exchange contract validation, real account proof or a trading result.

## Accounting reviewed

- Buying base spends `quantity * price + known quote commission` from quote cash. Base inventory receives gross quantity less known base commission. Opening spot principal is not reused as collateral cash and is not reserved a second time.
- Selling requires enough owned base to cover sold quantity plus any known base commission. Sale proceeds less quote commission enter quote cash. The model forbids borrowed base/spot shorts.
- Acquisition cost is pooled exactly; sells allocate average acquisition cost to all base consumed, including sale commission paid in base. A base commission on acquisition reduces inventory while leaving total acquisition cost in the remaining cost pool. This is the model's cost allocation convention; it is not a tax-lot accounting claim.
- In the known ledger component, branch algebra gives `cash = initial cash + external quote flows + realized allocated PnL − sum(cost pools)`. Fees affect cash/inventory once. `fees_by_asset_diagnostic_not_subtracted_again` is diagnostic and must not be subtracted again.
- Missing amount/asset or a third fee token remains pending. Pending fees suppress available cash/inventory and NAV and block later fills. Quote resolution debits cash; buy fees add to cost pool and sell fees reduce realized PnL. Base resolution reduces inventory and, for sells, allocates its original basis. An unfunded base resolution remains pending. Reported amount/asset changes require reconciliation.
- A delayed quote fee can reveal negative historical cash; the model records a risk event and blocks later buys. This flag is not a real-account debit authorization.
- Missing liquidation marks, unknown exit fees, stale/unknown source clocks, wrong consumed inventory, pending fees or reconciliation prevent NAV. Known cash is retained as a component. Full inventory consumed must already include a modeled base-denominated liquidation commission.
- Economic arithmetic uses exact `Fraction`s after finite decimal validation. SpotEvent/from_mapping accept decimal strings, integers or Decimal values; binary floats and fraction-form strings are rejected. Event mapping preserves finite decimal input; rational strings are used in model state/output where appropriate.
- Event identity deduplicates accepted economics independently of receipt clock. A conflicting accepted-event revision requires reconciliation. Journal attempts are hash chained, replayed under a lock, and require the same account config on reopen.
- Accepted events require `simulation_only is True`, journal config and snapshots declare simulation only, and `actual_order_allowed` remains false.

## Actual finite hand checks

The local ignored `.cache/R324-spot-source/math_probe.py` was executed successfully with `PYTHONPATH=.`. The first invocation omitted PYTHONPATH and stopped before importing the model; it was corrected and the actual calculations then passed. The check uses only small declared synthetic numbers, temporary ignored journals, and exact assertions:

| Hand case | Expected and checked result |
| --- | --- |
| Initial100; buy3 at10, zero quote fee | Cash70; inventory3; cost pool30 |
| Sell1 at12 and pay0.1 base | Cash82; inventory1.9; cost pool19; realized1 |
| Sell remaining1.9 at12, quote fee0.2 | Cash104.6; inventory/cost pool0; net PnL4.6; no further liquidation mark required |
| Initial100; buy2 at10, base fee0.2 | Cash80; net inventory1.8; cost pool20. The gross2 hedge is larger than net spot inventory |
| Mark preceding1.8 inventory with proceeds21.6, exit quote fee0.1 | NAV101.5; PnL1.5. Missing mark or unknown exit fee instead yields unknown NAV |
| Attempt to sell2 when only1.8 owned | Rejected; cash/inventory/cost pool unchanged |
| Buy2 at10 with unknown quote commission, then resolve quote fee2 | Pending initially hides cash/NAV and blocks another fill; resolution yields cash78, inventory2, cost pool22; liquidation proceeds24 gives NAV102/PnL2 |
| Repeat original fill and resolution; close/reopen journal | Both repeats duplicate without another debit; reopened full snapshot equals pre-reopen snapshot; initial100-to101 config reset rejected |
| Sell1 at12 with fee initially unknown, later resolve0.1 base | Same cash82, inventory1.9, cost pool19, realized1 as immediate known-base-fee case |
| Commission0.1 in THIRD token | Fee remains pending; resolution in THIRD is rejected as unmodeled; NAV remains unknown |
| Spend all100 buying10 at10, later resolve quote fee1 | Cash−1 and historical risk event; new buys blocked |
| Float0.1, rational string1/3, or simulation_only=False on event input | Rejected |

## Limits and remaining integration obligations

- This checks the stated arithmetic under supplied simulated fills/marks. It does not validate actual MEXC fills, fee asset/tier, base-unit contracts, lot/tick/fee rounding, source timestamp units, market permissions, current inventory, locked balances, wallet transfers, real account reconciliation, tax treatment, or order execution.
- `SpotMark` values and `source_unit_verified` are caller-supplied model assertions. The model does not itself walk a venue book, validate external market provenance, infer a fair exit price or prove source clock units. Its accepted clock skew/freshness bounds are model policy.
- A base-fee buy reduces hedgeable spot inventory below gross purchased quantity. A separate perp controller must size against net owned base and contract units or carry an explicit orphan exposure; this module alone does not establish a balanced pair.
- Third fee assets remain unsupported, including no conversion or third wallet. Conservative blocking is a limitation, not zero fee proof.
- Deterministic journal reopen was tested under the same reviewed implementation. The header pins account config and the record chain, not the model code hash. External preregistration/freeze/version binding must cover replay semantics; this review does not authorize changing a frozen replay implementation.
- This is not a full test suite or an independent source-contract proof. Parent-owned full-suite/integrity work and any exchange/source limitations remain separate. The exact reviewed file hash above bounds this conclusion; later edits need their own relevant validation.
