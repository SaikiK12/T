# R326 — conditional spot/perpetual cost hurdles, no executable edge

**PARTIAL.** The same committed R325 inputs now produce72of108registered cost
tier values.24one-cost account models/48journals/168chained rows match raw rational
cash/depth/fee/capital arithmetic within1e-8quote;4outputs byte-reproduce. The
remaining36tier slots retain insufficient displayed depth. **Actual market net
return and funding cash remain unknown; executable pairs and new paper days0.**

## Economic result on the received books

Fixed BTC control,WIF,SKR;3samples each. q uses the unchanged250max-mid reference
budget and declared decimal/base-quantity convention, with5000spot+5000perp
capital. Same q across full-five/top-only depth, zero-charge/public advertised
quote-fee scenarios and1x/2x/3x. No leverage-up, cheaper size or winner selection.

For full depth, required gross quote gain to cover hypothetical same-book
BUYspot/SELLspot/SHORTperp/COVERperp, in bp of one-leg reference notional:

| Symbol | Full pairs calculable | Zero-charge crossing 1x | Public quote-fee cost 1x | 2x | 3x |
| --- | ---: | ---: | ---: | ---: | ---: |
| BTC control | 3/3 | 0.0137–0.3743 | 14.0153–14.3757 | 28.0305–28.7514 | 42.0458–43.1271 |
| WIF | 3/3 | 11.1763 | 25.1797 | 50.3593 | 75.5390 |
| SKR | 2/3 | 68.6903 | 88.6789 | 177.3578 | 266.0367 |

100bp=1percent. Thus WIF's displayed hurdle is about0.252percent at1x and
0.755percent at3x under advertised-fee assumptions; SKR about0.887percent and
2.660percent. Even zero commissions leave SKR crossing about0.687percent on its
two calculable full samples. Fee removal alone does not remove that quoted
friction. Public spot taker rates were0.0005BTC/WIF and0.0008SKR; these are
unauthenticated metadata, not verified owner rates/assets/tiers or promotions.

Full-depth fixed quantity was0.0031BTC,1390WIF,17800SKR.8/9full pair snapshots
and4/9top-only pair snapshots support the conditional size; all top SKR samples,
two BTC top samples and the final SKR full sample remain insufficient. No
missing row became zero cost or smaller quantity. The all-cash control's known
four-fill price-fee component is0 with the same total10000capital; no realized
risk equivalence or alpha ranking is claimed.

These are **conditional quote hurdles**, not observed execution, future roundtrip
cost guarantees or positive expected returns. Source quantity/base convention,
actual spot increments/ticks, REST quote event age, owner fees/permissions,
latency/partial fills, future exits and actual event-bound funding/fair notional
remain unverified. Every executable admission isFalse. Cost tiers linearly stress
the same quoted crossing+assumed fees; they do not simulate altered real fills.
Entry basis is not futures cash profit; perpetual convergence is not guaranteed.

The accounting projection uses invented clocks/perfect supplied quote fills and
hypothetical quote fees, spending spot principal and reserving futures notional
correctly. It explicitly posts UNKNOWN funding; full NAV/net remains unknown
in every model even after quantities close. Only the known four-fill price-fee
component equals negative1xcost. Fee diagnostics are not subtracted twice.
No actual payment, zero funding, real account balance or tax/fee rounding proof.

## Repair lineage and honest failures

R325 freeze aa24350, source raw d854aaa and failed outputs dc87e00 remain intact.
That pass kept9pair/36control/108tier slots but computed0numeric costs. Decimal
JSON prices failed the old Real/string reader; WIF/SKR public base minimum0
failed a strictly-positive adapter. Its0numeric oracle pass is not cost proof.

R326 freeze5d1256b preceded corrected outcomes; PREREG
12742068be9816c8b7502c8b98b973e5a5d1a6f57bc69491476be8feca5a47c4.
Only two input mechanics change: exact Decimal text to old-parser strings;
explicit zero BASE minimum as lower bound0. No unknown/negative/bool minimum,
zero trade, actual step, cap or metadata/source permission is invented. All
q/cost/clock/receipt/capital controls and source/admission gaps are unchanged.
Original bodies/receipts were neither copied nor overwritten; own code/input
verifier and original committed parent verifier run before/after each replay.

22calculation/import/test files pinned. Full1366tests/2skipentries passed before
commit;2new compatibility tests. Independent reader checked exact bridge
 dbf2162685740a888e9964ec99e638a07cc8d9b191ed9da6b6413acd21887d34
and reran those same2constructed cases; no quote values/outcomes inspected.
This is not independent whole driver/oracle or source authenticity validation.
R325's earlier source/core reviews retain their narrower exact-hash scopes.

Raw independent Fraction oracle checked every72numeric tier,24account models,
48journals/168rows, same quantity policy, four cash amounts, costs/fees, minima,
segregated capital and missing funding. All108slots remain;36uncomputed. Four
compact artifacts reproduce byte-for-byte through:

`python -m lab account --spot-costs-v2 --out /fresh/output`

`python scripts/check_spot_costs_v2.py /fresh/output/results.json`

Native journals remain locally append-only with tracked immutable packs.
Reproduction used0network requests and did not overwrite original outputs.

## Input scope, budgets and limits

One original CURRENT capture,2026-10-26 07:26:37.672459–07:26:54.119016UTC:
22public GETs,13970accepted bodybytes, allHTTP200,0budget violations/pending.
No new acquisition in R326. Parent scope charged22x64KiB=1441792byte reservations
and154cumulative reserved seconds without refund; wall16.447seconds. Request
body receipt clocks include process/startup/transport before parsing. Local
pair checks at receipt epoch are not current report-time or source-clock proof.
Transport/header/proxy/unread buffered bytes remain unknown.

Six bounded static source GETs184953bytes in R325 located eleven enumerated
mechanics, retaining exact read/unread and versions. Documented minimums are not
steps; Java ms example is not deployed matching-engine time; aggregate bootstrap
is not303partial-depth semantics. REST depth's crossed toy sample is rejected.
No new source/market/history/account/RPC/weights request, login bypass or secret.
Original historical7757/8000requests and reported229.85/250MiB stay unchanged;
exact remaining bytes unknown. New current scopes are not historical renewals.

M047/M134 same canonical methods and aliases; no new M-id/queue/panel. Their
exact strategy entries/exits/original outcomes are not tested by these cost
controls. Dated M244/M170/R301 remain distinct. R325/R326 one compatibility group:
72attempted control cells/216tier slots on SAME9rawpairs, not18independent samples.
Program9478970 unchanged,0predictive/optimization strategy trials/new paperdays.
R311 remains INCONCLUSIVE224/273 and negative2x/3x; R321 stays NOT_ACCEPTED.
No p-value/CI, calibrated expectancy, owner100completion, activation, orders,
money,secrets,merge/closure or permanent execution/delivery claim.
