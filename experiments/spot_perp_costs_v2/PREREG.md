# PREREG: same-data spot/perp numeric compatibility repair

- **Registry id:** R326
- **Owner (single writer):** Codex; one bounded input-bridge reviewer
- **Date registered (UTC):** 2026-10-26

## Exact finite repair

R325 retained22HTTP200responses/13970bodybytes but computed0/108cost tiers:
Decimal JSON prices were refused by its frozen Real/string MEXC reader, and
WIF/SKR explicit minimum baseSizePrecision=0 was refused as notpositive. These
are input-read failures, not zero costs or financial/strategy nulls. Original
freeze aa24350, raw d854aaa and failed outputs dc87e00 stay unchanged.

Before any corrected outcomes, freeze this TWO-MECHANIC bridge: preserve exact
Decimal field text as strings accepted by the old depth decoder; accept explicit
zero base minimum as nonnegative lower bound, never a lot step or zero trade.
Only baseSizePrecision zero changes; missing/negative/bool minimum, other
minimum/cap fields, row schema/order/count/unit validation still delegate to old
checks. No raw data mutation, new market query or interpretation of zero as
unlimited cap. All source/fee/clock/quantity assumptions remain explicit.

## Source/code/same-input identities

- `code_inputs.json`: `eb978122f1f7c1a614feac7a2945be1c9e2d544e975bb49ab7c0bd11521140ca`.
- `inputs.json`: `ca719896c1054393ae2ffab2aac317a754093060a12de6deebe5820dffe62c4c`.
- `fixtures.json`: `8276df1162ee92adc09cbfdf229c1f74fc605f410db8d9c1c44a2406e995d748`.
- `contract.json`: `1df006fb767d94cf0e62a80715da311e579d5ef16ecd8b7a7497754840935742`.
- `sources.json`: `bff4f420cd5a34baf2dd092d167fef3e38f960716015e4f56575dd0a6a773a93`.

Parent raw manifest and all22committed response bytes/clocks are verified through
original R325/R324 input verifier before/after report. Own verify pins this new
code/spec and the parent's failed result. No raw bodies or queues copied. New
report reuses parent ledger/account function and exact finite fixture reference;
its report body only changes input adapters, verification, source path/default
output and registry labels. Parent results/frozen files are never patched.

## Unchanged economic/data contract

EXACT original9pair slots/36profile-fee control cells/108cost tier slots: fixed
BTC/WIF/SKR x3samples,full-five/top-only,zero-charge/public-advertised quote fees,
1x/2x/3x. q remains parent250/maxmid roundeddown to perp and declared spot decimal
grid; not an actual verified spot increment or walked-order cash budget. Same
q across profiles/fees/tiers, no insufficient-depth resize or outcome reselection.
Both advertised statuses/API/sides/market orders, min/max amounts and1e-8rounded
boundary guards unchanged. Parent2s local request/availability,1s receipt skew,
50ms clock-step rules unchanged. Source age/actualpermission still unverified.

Same5000+5000capital, no transfers/FX/leverage-up. Hypothetical same-book four-fill
crossing plus explicit scenario quote commissions, never owner fees. Fixed tiers
scale that hurdle without reoptimization; entry basis is not cash profit. Reuse
SpotCashAccount/PaperAccount; explicit unknown funding keeps fullNAV/netunknown.
Known four-fill price-fee component must equal negative1xcost within1e-8quote.
Retain uncomputed/failure slots, native append-only journals and immutable packs.
Actual eligible pairs0, market expectednet/actualfunding unknown, paperdays0.

No new primary/static/market/history/account/RPC/weight request. Original CURRENT
R325 scope remains22GETs13970acceptedbodybytes; its reservations are not refunded
or renewed. Old historical7757/8000requests and reported229.85/250MiB unchanged;
exact remaining bytes unknown. No orders,money,secrets,large dataset/modelweights,
activation,merge/closure or permanent execution/delivery guarantee.

## Verification and decision

Full1366tests/2skipentries passed190.233s before freeze; two new constructed tests
reproduce Decimal row/contract-size mapping and zero minimum without mutation,
while bool/negative/unknown still reject. Independent reader read exact bridge
dbf2162685740a888e9964ec99e638a07cc8d9b191ed9da6b6413acd21887d34
and reran those same2cases; no current quote values or outcomes read by reviewer.
That does not cover new driver/oracle/full system or authentic source contracts.

After commit only: run corrected finite family; reuse original raw rational oracle
on every computed cash/depth/size/fee/capital tier, check unknown funding and all
journal chains, byte-reproduce compact results in fresh directory. Failure stays;
frozen code cannot be patched. No p-value/CI, calibrated forecast, dependent-null
acceptance or strategy activation. PARTIAL is a conditional-cost input component,
not positive executable expectancy or genuinely new prospective paper evidence.

R325/R326 one input-compatibility decision group,72attempted control cells and
216tier slots on SAME9rawpairs, not18independent market samples.0predictive/
optimization strategy trials added; program entering9478970 unchanged. R311
INCONCLUSIVE224/273/2x3xlosses,R321 NOT_ACCEPTED and owner100frozen coverage stay.
