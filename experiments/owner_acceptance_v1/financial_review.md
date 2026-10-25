# Bounded independent financial review of paper controls

Reviewed `lab/paper_controls.py` and `tests/test_paper_controls.py`, with relevant `PaperAccount.snapshot`, liquidation-mark, clock and paired-snapshot semantics. No production edits, network, market data, orders, publishing or freezes. Findings apply to the reviewed implementation, not to future revisions.

## Blocking findings

1. **Changed contract rules can bypass the persistent guard.** `paper_controls.py:100` compares two arguments supplied to the same call; neither expected nor observed contract version is pinned in the policy header or persisted observation. On one risk journal, accept `contract_version='one', expected_contract_version='one'`, then call with both equal to `'two'`. Both observations return `MODEL_WITHIN_LIMITS`. Thus a caller that refreshes the expected version along with changed source metadata avoids the changed-rule stop. Persist an immutable expected source/rule identity in the journal and reject or halt drift. A version mapping may be needed for distinct venue/contracts.

2. **Omitted exposure is accepted as complete zero exposure.** Lines 122/134 use `a.get('positions', [])`; remove `positions` from an otherwise valid nonempty account snapshot and observe with complete/session/fee flags true. Result: `MODEL_WITHIN_LIMITS`, gross notional `0`, and `gross_notional_complete=True`. Separately, observe two venue/asset accounts, then pass only the first account on the same risk journal. The omitted account is silently absent and the result again permits entries. `_state` already remembers prior account identities but `observe` does not enforce their continued presence. Require an explicit positions list and the established complete account identity set (or an explicit reconciled account-universe transition). A missing account must halt rather than disappear from risk coverage.

## Reproducer outline

Use `tests.test_paper_controls.snapshot`, `clock`, `ANCHOR` and a temporary `PaperRisk(..., RiskPolicy('p'), ANCHOR)`. Call `observe` with asof/clock `clock(1)`, mode `fixture`, all three completeness/session/fee flags true and equal contract-version arguments.

- Missing positions: `s = snapshot(); del s['accounts'][0]['positions']`.
- Missing established account: first append a second account with `venue='lighter', asset='USDC'`, observe, then observe the original one-account snapshot.
- Changed rules: observe once with both version strings `one`, then with both `two`.

These counterexamples were executed with invented quantities; no real-market outcome was calculated.

## Checked behavior and limits

`python3 -m unittest tests.test_paper_controls -v`: all 7 tests pass. Invented counterexamples above reproduce both blockers. Existing tests exercise strict gross settlement-quote forecast/error tagging, absent calibration/error, the exact 1x/2x/3x arithmetic, persistent loss/drawdown stops after reopening/deposits, currency separation, hedged gross concentration, missing marks/fees/session/rules and future receive clocks, and retained positions without invented closes.

Financial arithmetic examined: `gross - multiple*(cost + extra_reserve) - error` subtracts supplied costs once and scales cost/reserve once; the caller must supply a gross forecast and nonoverlapping cost/reserve inputs. `nav - initial_cash - external_capital_flows` preserves economic loss across deposits. Reconstructed PnL high-water marks persist. Position notional `entry + sign(quantity)*liquidation_pnl` matches the frozen account's price-PnL definition, with `max(entry, liquidation_notional)` providing conservative gross exposure. Exit fees remain in NAV and execution drag is not separately subtracted here.

This is a bounded review of conditional paper accounting/controls, not validation of supplied forecasts, error calibration, source authenticity, every risk dimension, all owner requirements or any profitable strategy. It does not change R311's INCONCLUSIVE result or the selected model's negative 2x/3x result, and authorizes no activation or real order.

## Targeted revision recheck before freeze

Both blocking findings above are resolved in the reviewed revision. The constructor now pins the contract version and exact initial venue/asset balances in the journal header. Both supplied version IDs are checked against the pinned version. Missing/extra accounts halt; registered missing accounts remain visible with unknown NAV/gross totals, and a missing explicit positions list halts with `gross_notional=None` and `gross_notional_complete=False`.

Validation rerun: all **8** `tests.test_paper_controls` tests pass. Independent invented fixtures additionally checked initially allowed state, both version IDs changing together, persistent stop after reopening with the original header, refusal to reopen with changed rules or balances, omission after observing both accounts, extra account, retaining a known account's gross component alongside an unknown missing account, missing positions on a fresh unstopped journal, and persistent halt after restoration/reopening. All assertions passed; actual-order and automatic-flatten flags remain false with exposure retained.

**Remaining limits:** no unresolved blocker within these two corrected cases. This recheck is limited to the two prior findings and the current two files; it does not broaden the original scope, authenticate caller data, validate future risk forecasting/error calibration, validate other risk dimensions, assess all owner requirements, establish positive returns, or authorize activation/orders. No future revisions have been reviewed. R311 remains INCONCLUSIVE and the selected model remains negative at 2x/3x.
