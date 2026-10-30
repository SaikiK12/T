# PREREG: physical spot, segregated perpetual cash and finite public wire inputs

- **Registry id:** R324
- **Owner (single writer):** Codex; bounded source reader / spot-kernel reviewer
- **Date registered (UTC):** 2026-10-26

## Question and exact method lineage

Supply the missing physical-spot accounting/input component for M047/M134.
Does a buy SPEND principal rather than reserve it, do base/quote fees affect
inventory/cash once, and can the two funded wallets reproduce literal net cash
at fixed costs? Can one short public spot/perp capture establish structural
wire compatibility for fixed BTC/WIF/SKR, retaining failures/absent symbols?

This is NOT a new strategy/backtest, source-defined alpha, funded account or
prospective PnL experiment. M047 premium>cost entry and premium<=0 or72h exit
remain open. M134 original trailing72h funding>20pct APR historical/forward
scope remains unchanged. No M244 dated-futures convergence/maturity is assigned
to a perpetual. R311224/273 INCONCLUSIVE and negative2x/3x, and R321 dependent
inference NOT_ACCEPTED remain unchanged; no old outcomes rerun or winner/size/
leverage rescue. Program entering9478970. No prediction model/search here.

## Finite code/input/source identity

- `code_inputs.json`: `27c92a5a582bdda8dd731ba463b740066deb2f88a1a0ca48bd229ff73b112629`.
- `inputs.json`: `82fb87ae9597dd5d3117f756a3beb974f407114f0cb1fa7a8788af88cff89716`.
- `fixtures.json`: `e370cd2b1bbe4c437aebb3121bd556af7c91e06492a1446bbd8e653dc687dd2d`.
- `contract.json`: `abdef91435beab899733fe8ad02b887836548d1fffe69f48af98e4af7896e504`.
- `sources.json`: `b809051aae6438fa36609422a916996d773f3e802dce5bc3fa29bb55e1725b7f`.

Exact source URLs/tree/two blobs/status/body hashes and read/unread scopes are
retained. Nine separately declared static GETs118731bodybytes, including one503
and two404failures; no more source GETs here. Correct integration/local-book/
market/fee pages remain unread. Root follow-ups supplement the earlier reader
note without rewriting its prior unread scope. A Git tree is not a commit or
proof of current deployment. Source examples give no fee tier or execution proof.
Introduction ms statement applies to SIGNED requests, not WS sendTime.

## Cash, inventory and economic controls

One physical spot account and one linear futures account each receive5000
invented USDT, total10000. Spot buys1gross base at declared ask, SPENDS principal
plus quote commission; base commission instead reduces hedgeable inventory.
No spot borrowing, second principal reservation or collateral transfer. Futures
entry RESERVES1x notional; it does not spend that principal. Opening basis is
not instant cash profit. Exposure is net owned spot plus signed perpetual base.
All capital counts, including both wallets; quote-currency FX is not inferred.

Eight constructed cases only: unchanged basis, convergence, widening, base
commission with net hedge, base commission with gross/orphan hedge, unknown
funding, unknown spot fee and third-token fee. Mid paths and normalized funding
cash are explicit fixtures, favorable cases known by construction. No API
Funding.value/rate/forecast becomes realized cash. Unknown/third-asset fees
block new spot fills; unknown required fee/funding/marks withhold total NAV.
Rejected closes, unclosed inventory, historical deficits and nulls are retained.
All fills are invented bounded perfect taker fills, not observed execution.

24account paths=8cases x FIXED1x/2x/3x cost tiers. Tier stresses half-spread,
quote fee RATE and base/third fee magnitude; quote fees apply to stressed fill
notional. Fixed quantity policy is net owned base or the named gross-hedge
control, never reoptimized from outcomes. Base fees reduce net quantity as
specified, not a leverage/size rescue. Four modeled trades plus explicit funding
per path;48 native append-only journals with immutable packed copies. Cash
reference stays flat with the same10000capital; conditional component arithmetic
is not a risk-adjusted empirical strategy comparison. Mid price PnL + normalized
funding - crossing - commissions must equal literal two-wallet net; spread
embedded in fill prices is not subtracted again. Net divides by total10000.

Separate finite hand/functional cases are implementation checks, not unseen
empirical labels. Count0predictive/optimization trials and report ALL24cost paths.
There is no market sample to calibrate significance or dependently bootstrap;
R321 calibration failure is not bypassed. No genuine prospective strategy day,
market expectancy/activation or100enhancements-completed claim is authorized.

## One finite current-data contract and stop

Commit this spec/code BEFORE current acquisition. No REST metadata/history/
account/RPC request;2public WebSocket handshakes,4subscription messages maximum.
Fixed symbols BTC/WIF/SKR; no replacement for unavailable pairs. Spot limited
depth5 channel and public futures sub.depth.full reuse old transport/constants.
Per connection observe12seconds after open, max3000accepted messages and4MiB
reserved application payload; each message/non101handshake body max128KiB.
Combined max6000messages/8MiB accepted application payload,30seconds overall.
Each handshake attempt durably reserves25seconds/4MiB; sum50seconds reservation
is cumulative across parallel requests, not50seconds wall permission. Stop before
remaining payload headroom<128KiB. No retry, reconnect, redirect or alternate
route on denial. Library/TLS/proxy defaults retained; websockets16.0 only.
Transport overhead and unread buffered/oversize failure wire bytes are unknown;
report accepted application bytes honestly, not invented measured totalwire.

Every raw receipt has original first-seen UTC+monotonic clocks before decoding.
Raw binary messages are preserved in base64. Missing WS sendTime never falls
back to creation/last-order/receive clocks. All source-time units, quantityasset,
complete-snapshot semantics, metadata status/minima/lot, actual fees/permissions,
future exit depth and event-notional funding remain unresolved. Thus EVERY
received packet remains executable_quote_eligible=false;0certified synchronized
executable pairs, market net unknown at1x/2x/3x. Raw observations can establish
wire receipt/structure, not market availability/session or a completed paperday.

Raw inputs/receipts are sealed and COMMITTED before any offline outcome report;
report verifies committed identities. Reproduction cannot collect. Existing
attempt directories/journals/results cannot be overwritten or a budget reset.
Original historical approval remains7757/8000requests and reported229.85/250MiB
spent, exact remaining bytes unknown. This separately declared tiny CURRENT
compatibility acquisition is not a renewal or use of that historical allowance.
No real orders, money, secret values, account access, largehistory/weights,
paywall/login/API-limit bypass, merge/closure or permanent service.

## Verification and bounded review

Required full discovery actually passed1350tests with2skipentries in181.605s;
24new functional tests include fees/principal/hedge/marks/reopen, malformed wire
and mocked denial/no-retry/binary first-seen capture. Independent reviewer checked
spot_cash.py at7ab221fd898cf25ce48c77fb05a16e8a7e445f6b90a65fb34e1be078b53c6a71
and its finite exact financial probes; no concrete blocker found at that scope.
Pair aggregation, wire/collector, full fixture runner and final literal oracle
are NOT fully independently peer-reviewed. Native journal config/chain does not
pin code; external frozen closure here binds replay implementation.

After input sealing: run24fixed accounting paths, independently audit literal
cash/cost/capital and journal chains, and byte-reproduce compact outputs in a
fresh directory via lab account --spot-perp. Any mismatch/failure is retained;
changed frozen code requires a new lane. PARTIAL means bounded component
accounting/compatibility findings only, with no net-market success criterion.
