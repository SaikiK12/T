# R319: partial fills, residual exposure and the economic cost of an unfinished pair

- **Registry id:** R319
- **Owner (single writer):** Codex alone, `codex/lab-consolidation`, existing draft PR #49
- **Date registered (UTC):** 2026-10-25
- **Canonical scopes:** M239/M240/M241/M245/M409; same single methods queue

Code manifest SHA-256: c64f8b21c94827d9dd685ceb3644188974281ebc8c1f6e052bd79082ea8600c2
Held reported-input SHA-256: 149d07faeccdb894ff46ebbbf3e6ae33118f878e553c5c0e733c8c3421747d36
Invented lifecycle fixture SHA-256: d579ddc6fe38af295b90cc5637a672b90c236d231f6c6eded2e6f9e10eefac9e
Source contract SHA-256: e8e79ec56932072b78231bb182d31960c18a20dea07c8c007965fed9c658ee17

## Binding question and inherited limits

Can one unfinished execution leg leave inventory or missing cash while a model
reports a completed, hedged or zero-PnL pair? Add source-aware receipt tracking
to the existing R318 account and measure fixed hypothetical unwind costs on
the same already-seen displayed books. No new indicator search, strategy
selection or reinterpretation of historical proxy money.

R311 repaired1,318 actual events and exercised all12 models but remains
INCONCLUSIVE on224/273 common days; the calibration-selected policy loses
at2x/3x. Do not rerun it, change the validation winner, loosen eligibility,
increase leverage or convert smaller charges into prospective proof.
R318's fee/session/account/index-proof evidence remains externally incomplete.

Freeze and commit/push this spec,61-file manifest, sources, fixtures and six
exact R318 reported-input identities before new held cost/lifecycle reports.
R318 and all old frozen code/spec/results/journals remain unchanged. Unit
development uses invented facts with predetermined assertions, not market
outcomes. The original account command remains available; --lifecycle selects
this registered integration through the same operational entry point.

## Bounded, previously unread primary source

Official Hummingbot commit9af100d6822da7d2d0291a906c730ef172284ee2, dated
2026-09-22. Read six selected source files plus Apache2.0 license, without
installing Hummingbot, connectors, framework or weights. Exact file hashes,
function scope, all20 distinct received mechanics and unread boundaries are
in sources.json. Generic media claims/corpus introductions are not full source
extraction. The20 records map to existing methods/aliases, not20 implemented
owner enhancements or new successful strategies.

Received mechanisms include pre-funded spot arbitrage, independent full-amount
failure retry, quote/base percentage units, wrapped/USD token equivalence,
daily funding normalization, optional after-fee entry filtering, shared base
quantity, funding/price take-profit and rate stop, maker-then-market hedge,
stop-loss/take-profit/time/trailing barriers, volatility-scaled distances,
activation bounds, ONEWAY/HEDGE close semantics, residual close/cancel, retained
positions, exchange-budget constraints and funding receipt attribution.
Keep all weak alternatives untested. Do not port default20x leverage, USD-name
parity, generic8h funding fallback or spot buy/sell cash as perpetual profit.

Seven raw staticGETs completed,100,699 bytes in2.183s, each<=1MiB, without
redirect/retry/login. Initial provider commit lookup returned137 changed-file
patch entries, not individually reviewed/mirrored, and its normalized return
was1,145,600characters. That connector has no caller-enforced response cap:
the intended1MiB per-response limit was not enforced on metadata. Combined
provider/search wire bytes/time are unavailable; do NOT claim a fully measured
4MiB combined wire bound. Further metadata discovery stopped. Exact limitation
is retained instead of inventing byte accounting. No market/account/RPC/history
request occurred; historical7,757requests/229.85MiB is unchanged, not renewed.

## Finite lifecycle/account integration

Use exactly16 invented fixture paths, each at fixed1x/2x/3x charges: inactive,
acknowledged_without_fills, both_legs_then_exit, first_leg_rejected,
partial_hedge_rejected, cancel_race, residual_retry, oversized_retry,
terminal_total_missing, source_gap, duplicate_trade, unknown_fee,
fill_without_order, fill_after_terminal, entry_timeout, partially_closed.
Total48 dependent engineering paths, not48 market trials. Initial5,000USDT
MEXC and5,000USDC Lighter remain separate; no FX/netting or leverage-up.

Target1BTC base, opposite signs, entry deadline at anchor+10s, maximum3 recorded
orders per leg in this finite example. Both opening and closing attempts count
against that total; this is not an unlimited recovery allowance. Supplied
statuses/trades are invented, not authenticated reports or permission to trade.

Only explicit per-trade base fills change inventory and the frozen account's
cash. Submission/acknowledgment/cancel request cannot stand in for a fill or
terminal cumulative quantity. Rejecting/cancelling after a partial fill does
not erase it. Residual entry equals target minus all observed entry fills;
unresolved orders forbid a new model entry, and retries cannot re-use the full
original size when only a fraction remains. After any close intent, no new
entry; closure of a smaller order never flattens a larger position by label.

Stable trade ids deduplicate redeliveries even with a new receipt id. A source
gap, unmatched order, conflicting trade or terminal totals, future/regressed
clock, oversized retry, order-limit violation or unexplained overfill makes
complete exposure/cash/PnL unknown. Preserve known received inventory and cash
components separately. Pending quantities retain a possible delta interval;
unbounded/mismatched source state cannot become a known zero interval.

Persist source receipts before financial posting in the same account journal.
If interrupted between them, expose an unapplied financial join, withhold totals
and allow exact stable-trade replay to join at its current as-of without
rewriting the original receipt. An exclusive coordinator lease prevents two
writers. Reopening never resets the plan, target, deadline or attempt counts.
Actual provider/account/margin/order permission remains unverified and every
actual_order_allowed/execution_ready flag remains false.

All final fixture snapshots use the declared12s invented bid99/ask101 close
marks; estimated exit fees10/4bp times the tier remain future model fees,
separate from supplied paid/model entry/close fees. No missing fee becomes0.

## Fixed held economics and controls

Use72 exact already-seen R318 book/deadline rows, original250-unit quantities
and10,000 total/5,000-per-venue quote-equivalent capital. Original source age,
skew/sequence/session failures are unchanged. Evaluate both long-MEXC/short-
Lighter and opposite directions:144 retained descriptive rows, including nulls.
Use only R318's reported sweeps/costs; this runner/checker is not an independent
raw-market decoder or a new synchronized capture. Quote parity is conditional.

For each available row, retain all three original cost tiers. Compute midpoint
basis minus tier*entry crossing/charge cost as an **entry basis illustration**,
not realized cash. An immediate same-book four-fill perp round trip realizes
only negative tier*(paired crossing+fees); the initial cross-venue notional
gap cancels and cannot itself create perpetual money.

For each direction/tier, consider exactly two filled-leg identities and adverse
future exit shifts0/20/50bp: up to2,592 conditional failures. Base one-leg loss
is tier*(buy-sell+(buy+sell)*fee). For a long's adverse lower sell price, add
close_notional*shock*(1-tier*fee); for a short's higher buyback, add
close_notional*shock*(1+tier*fee). These are source-labelled hypothetical
stress costs, not observed future exits or estimated failure probabilities.

The source's daily entry filter0.001 supplies one explicit10bp/day gross-funding
HYPOTHESIS ONLY. Compute hurdle/(mean leg notional*.001) as break-even days.
Actual expected funding, holding-time profitability and failure probability
remain UNKNOWN. Do not assume a constant forecast survives that many days,
choose a route/size, rescue R311, or activate M239/M241/M267 from the arithmetic.

## Verification, outputs and decision

One combined results.json/account.html/account.txt reuses R318 fee/funding/
budget evidence with its original scope, adds the48 lifecycle paths and144
held directions, and preserves inactive/failed/unknown states. It is not a
second panel/queue. Keep compressed observations and independently audit
reported fills with the reviewer-origin Decimal oracle; independent raw-book
decoding, Hummingbot runtime execution and final independent code sign-off are
not claimed. Own oracle/adapter checks all48 paths and finite known states.

Include one literal units counterexample:4 quote profit,2 base filled,100 entry
price gives2 quote/base under the inspected source formula versus.02 of entry
notional. No upstream method is executed and this is not an empirical return.
Report a dimension problem, not a verified exchange trading exploit.

Run the complete required suite before committing lab code;15 focused tests
give development feedback. Byte-reproduce all outputs in a new directory and
preserve every old source object/alias/journal byte. Reconcile the exact20 new
source records into the single canonical intake and existing queue scopes.

Verdict may establish PARTIAL mechanics, never profitable alpha. Zero predictive
trials and new prospective days; program trials9,478,782 unchanged. No inference,
SPA, calibrated uncertainty or multiplicity claim from these dependent already-
seen diagnostics. Actual sessions, owner fees/permission, full fills/cancel
reports, event-bound index/fair values, margin/financing and a new on-time frozen
paper protocol are still required for prospective net-return evidence.
