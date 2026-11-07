# PREREG: maker_pilot_v1, two-sided quote and inventory diagnostic

Freeze with lab.prereg.freeze and commit before actual fill/PnL calculation.
Frozen inputs never change; changed rule or sample needs a new id.

- **Registry id:** R426
- **Owner (single writer):** Codex, codex/atomic-route-screen-20261107
- **Date registered (UTC):** 2026-11-07
- **Method:** M474; issue7comment6709701086

## Question
Can the small recovered source fragment support consistent two-sided maker
fill/inventory accounting after explicit costs? This is a conditional
execution diagnostic, never reliable high returns or a recurring income proof.

## Universe and data
All3fixed Lighter commodity markets: WTI145, NATGAS158, BRENTOIL159. No coin
selection from returns. NATGAS has no trade file: NO_TRADE_FILE, not0trades.
The exact5eligible quote/trade Parquets are in cases.json. Other15archive
members, including R367HFT parts, remain opaque bytes; no reserved row read.

Source: public owner archive commit2011de73, chunk00006. One bounded restore
read1407398client bytes; all20original sizes/hashes matched. WTI has2803BBO
updates/102trade rows, BRENTOIL2806/32, NATGAS120quotes/no trade file. Counts,
schema, timestamps and current-grid validity only inspected before freeze;
no fill, markout or PnL. Source floats already lost original decimal-string
precision; do not reconstruct or fit a correction from later prices.

Fixed coverage-only common replay: **2026-10-29T01:31:45..01:35:30UTC**,
225seconds after30second warm-up, with5seconds for late reports. These dates
were already seen by R348/R386 and other microstructure research. No OOS,
new independent day or prospective score. Exact access dates, URLs, hashes
and read scopes are in the frozen source SOURCES.md and receipt files.

Three current metadata GETs atNov7 16:23UTC qualify symbol/id/status,
lot/tick precision and minima, not old contract equivalence or owner fees.
Fee hypotheses reuse R317's conditional primary extraction ofOct25:
Standard0/0 and Premium0.4/2.8bp maker/taker. Current market-level0strings
are not account entitlement. Fresh doc-reader attempts failed/redirected;
no newly verified complete current fee document is claimed.

## Feature lineage and point-in-time availability

| Feature / formula | Parent fields | Provider/units | Window/availability | Vintage and missing rule |
|---|---|---|---|---|
| Touch quotes | bid/ask, sizes and local receive t | Lighter own BBO, native quote/base | latest receipt<=decision, age<=1second | actualOct29capture; stale/zero-size skipped, invalid/off-current-grid fails |
| Fixed quantity | initial mid,100or1000notional, current lot/minima | fixed native base Q | computed once at start, floored tolot | currentNov7metadata hypothetical historically; below minimum stays unqualified |
| Post-only acceptance | past chosen price, BBO at arrival | own market price | assumed arrival=decision+1second | future arrival BBO only models acceptance, never quote selection; no private ack |
| Fill candidates | px/sz, maker_ask, liq, tx_us, local t | actual public trade and source clock | ordinary contra price strictly through quote; source matching time inside live order interval, receive>=arrival | clock alignment uncalibrated; no touch fill, old/bootstrap excluded, partial<=printvolume floored tolot |
| Cancel exposure | decision and fixed1second delay | local/matching microseconds | old quote remains live through cancel flight | source clocks and private cancellation not certified; old orders retained for late reports |
| Inventory/cash/fees | signed fixed-base fills and profile costs | quote-currency account, totalcapital10000 | known fill inventory only; ownmarket allocation10000/3 | no transfer, leverage, free exit, resizing or missed-loss recovery |
| Terminal mark/unwind | last BBO and shown touch size | own quote/base units | terminal BBO age<=1second; flat requires no mark | unpriced/stale/depth-incomplete exit gives no liquidatable PnL; funding unmeasured |

No participant alpha, forecast, optimized spread/clock, flow threshold or
source-trader fee is used. No whole-universe or current-owner access claim.

## Rule and closed search space
One symmetric touch-joining rule, fixed15second decision grid,100/1000quote
notional and two fee hypotheses. **3markets ×2sizes ×2profiles=12arms**,
all retained at1x/2x/3x costs=36cases. Same fixedQ at all costs. Inventory
cap±2Q; totalcapital10000 divided equally across the3markets. No leverage,
constant-notional accounting, cross-wallet rescue or early-exit fitting.

Each decision uses only fresh received BBO and already-received fill inventory.
Omit buy if knownposition>=Q, sell if<=−Q. Quotes arrive1second later; current
BBO at that arrival models a post-only rejection if crossed or stale. Old
orders are scheduled tocancel at the next refresh+1second, at the same time
neworders arrive, bounded by terminaltime. This keeps oldquote exposure during
cancel flight and nonoverlapping same-side intervals. No actual latency/ack
measurement or arrival acceptance proof.

An ordinary contra print must be **strictly beyond** the limit; equal-price
touch never fills. At most its printed size fills our remaining quantity,
rounded down tolot. Both local receive>=arrival and source tx_us inside the
order's [arrival,cancel) interval are required. A receive after cancel may
still report a pre-cancel matching event: keep the old order rather than
deleting that loss/exposure. Liquidation prints are excluded. Price priority,
negligible counterfactual impact and matching/local clock alignment are
assumptions; no actual queue position or fill/inclusion proof follows.

Every fill changes signed cashflow, fixed-base inventory and notional fees.
If |inventory|>2Q, fill-time marked equity<=0 or marked inventory notional
exceeds allocatedcapital, stop at the breach and suppress terminal PnL.
Never count later recovery. Reported minimum equity is at fill times only,
not maximum drawdown or intrahour solvency. Unknown real margin rules remain.

Terminal inventory closes at observed bid/ask only if the last BBO is fresh
and its shown quantity covers all of it. Otherwise no liquidatable PnL;
mark-only equity is separate. No free close beyond shown depth. Flat positions
need no terminal mark. Nominal individual quote/cancel actions are<=48/min
for3markets before terminal/connection actions; weighted rate credits,
nonce/gateway/account eligibility remain unverified, not approved throughput.

## Splits and cost
No discovery/validation, statistical significance, Sharpe, annualization,
monthly income, win probability or confidence-of-profit from this fragment.
**All reported monetary PnL is BEFORE UNMEASURED FUNDING**, not certified net.
No zero-filled funding, guessed cap or claimed broker cash. Fee/profile/tick
and current/historical minimum equivalence remain conditional.

Costs1x/2x/3x multiply maker fees and terminal taker fees bym. Residualinventory
crosses the actual BBO spread once; extra(m−1)copies of its mid-to-touchcost
stress it. Standard0fees stay0, while adverse selection remains in cash/price
paths. No maker touch fills, queue certainty or guessed favorable owner tier.

## Gates and null
Full synthetic suite, integrity, staged catalogs and committed exact closure
before actual source fills/PnL. Exclusive RUN_STARTED before loading values,
one invocation. Invalid inputs consume ERROR; no repair/rerun. Missing source,
minimum, arrival/exit or guard failure stays unqualified, not0return.

Native verdict always **PARTIAL_EXECUTION_DIAGNOSTIC_ONLY**, regardless of
profit sign. Source clock/ack/queue/funding/profile/legal access/capacity and
adequate independent days are not certified. No positive cell may be promoted
to reliable gains. A negative cell rejects only this model/fragment, not all
market making. Independent Decimal cash/inventory/fee/exit display identities
use fixed1e-8quote-currency rounding tolerance, never fitted fill tolerance.

## Multiplicity and evidence lineage
M474, related M058/M433/M441.12economic arms including missing/failed cases
count in registry; cost tiers are sensitivities. Program before9784349,
after9784361, reported by registry.program_trials. No independent-test-count
or program-wide significance interpretation. Parent dates already seen; no
fresh heldout or reserved read. Directional maker dips R193/R194were NULL;
this is a separate two-sided inventory/execution diagnostic.

Copied GATES SHA e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926. Dependent null, strict on-time future days,
trimming, leave-two-out and80%power are unmet, not waived. No gate1/real
admission, calibrated probability or whole-capital monthly yield.

## Stop rules
One fragment/window/touchrule/timing/candidate list. No post-result market,
fee, clock, size, source, spread or horizon adjustment; changes need new ids.
No HTTP in runner, native tick/recorder, real order/account/credential,
protected/reserved row, paid/large acquisition, denial bypass or subagent.
Original accumulated allowance conserved:7811calls/249746402conservative
bytes including RPC403, bounded archive restore and3metadata calls; no reset.

## Frozen input manifest

7ae9f3481ebcdf4ff8cf0c1d587f75f67d16c2cf971e5061172dba8b13a0d51a  experiments/maker_pilot_v1/inputs.json
