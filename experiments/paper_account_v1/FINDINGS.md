# R318 — PARTIAL: integrated simulated account works; execution proof remains missing

Code/spec/fixtures/exact already-seen R316 identity were frozen and pushed in
[`9da3582`](https://github.com/SaikiK12/T/commit/9da3582) before the new held-book
calculations. PREREG SHA-256 is
`7d76628ff1b5c7887fca833064b6c2b05d4e72149b51fa639ebe6e7f180e30ef`.

There is now **one offline calculation path** linking positions, cash, price PnL,
fees, funding, liquidation marks, source/session readiness and persistent
quota/budget/recovery state. It has one French HTML/text view. This removes a
real integration gap; it does **not** demonstrate a positive trading edge,
actual paid fees, executable fills or new prospective paper PnL.

## Economic result at fixed capital

Retained all72 dependent book/deadline states and **432 size cases**, including
302 blocked/unavailable cases.130 conditional displayed sweeps yielded390 fixed
1x/2x/3x cost scenarios and1,560 explicitly hypothetical adverse exit quotes.
Those130 sweeps share only22 underlying250-unit eligible states,12BTC and10alt;
they are not130 independent trading opportunities. All72 actual input states
remain execution-ineligible:64 blocked,8 unknown. No session, owner permission,
actual fee or event-bound Lighter index was acquired.

Total cost below is the unchanged10/4bp charge reserve **plus displayed
crossing**, normalized by one leg's midpoint notional. It is not the percentage
of total capital, the owner's fee schedule or earned/lost account money.
Capital stays10,000 quote-equivalent,5,000 per venue, with explicitly assumed
USDT/USD-quote parity. Every size is fixed from the immediate book; delayed
books never rescue an unavailable decision quantity.

| Altcoin leg budget | Eligible states | Crossing alone,1x bp | Reserve plus crossing,1x bp |
|---:|---:|---:|---:|
|25|10|15.63–27.88|43.62–55.89|
|250 unchanged control|10|16.90–28.14|44.89–56.15|
|500|10|18.39–28.89|46.38–56.89|
|1,000|8|18.39–25.63|46.38–53.63|

Smaller notional slightly reduces depth consumption in these states; it does
not remove the spread/fee hurdle. MEGA's displayed1x hurdle rises from43.62bp
at25 units to50.63bp at1,000 units. ROBO's1,000-unit immediate decision exceeds
MEXC **maxVol**, at both deadlines; this is a contract-size restriction, not a
measured depth shortfall. The last table row excludes those two states and
therefore cannot be interpreted as an improvement from increasing size.
No size was selected or optimized from these results.

For the unchanged250-unit altcoin control, reserve-plus-crossing ranges are
**44.89–56.15 /89.78–112.30 /134.67–168.45bp** at1x/2x/3x. Original R316 costs
match all72 held controls exactly;22 available new250-unit costs also equal
the original control dictionaries. At each deadline65 size cases are displayed
fillable, but the0ms deadline is below the declared300ms Lighter minimum.
The65 delayed cases merely meet that minimum; no total order-to-fill latency
or executable fill is observed. Hypothetical20/8bp exit fees,500ms additional
exit delay and0/20/50bp adverse shocks never acquire a future price timestamp.

## Account integration and failures retained

Eight invented account cases cover weighted entry, partial close, reversal,
long bid/short ask liquidation, inactive capital, unknown fees/marks and late
fill reconciliation. Closed-sequence model PnL is **-11.15/-12.30/-13.45USDT**
at fixed1x/2x/3x fees and identical prices/capital. These invented numbers test
accounting only; they are not a historical strategy return or paper evidence.

Opening futures notional reserves model1x capital without debiting its entire
spot purchase value. Closed price PnL, funding and paid/model fees post once.
Spread already embedded in fill prices is a diagnostic, not a second charge.
Open liquidation PnL and future exit fees are separate from realized money.
No cross-venue collateral subsidy or cross-asset aggregation occurs.

A later duplicate notification posts nothing. A conflicting financial revision
or a late fill makes totals unknown pending reconciliation; it cannot quietly
leave a falsely complete result. Missing fee/funding amounts remain pending
while known components stay visible. The exact new receipt resolves a pending
amount by append, retaining the original unknown attempt. Missing/stale/future
or wrong-quantity liquidation marks withhold net equity.

The synthetic funding case derives exposure from the account's accepted fills,
preserves MEXC's whole15s inclusion window and converts.01% explicitly. Its
missing value leaves cash unknown; the supplied bound model later posts+.03USDT
once. The early.02% announcement's error against the original.01% settlement
is-.0001 as a fraction. The corresponding Lighter model requires an explicit
pre-update index declaration, but **source_bridge_verified remains false**.
This does not solve the absent actual event/proof/API-unit bridge.

Fee statements are strictly bounded explicit redacted inputs; no credential
discovery/account query exists. All R318 statements are invented. The test
statement's entry/exit charges flow into the same journal/account; an absent
statement supplies no rate. Promotions reserve both legs, do not renew after
replay/revision/export/instrument changes, and cannot cover an expired exit.
Unsigned owner-supplied statements remain conditional, never authenticated fees.

Streaming tests retain a nonce gap, stale epoch and disconnected transport;
reopening a journal requires a new budgeted transport/snapshot. Dispatch/frame/
restart reservations persist before processing. The illustrative budget retains
a timed-out reservation, refuses redispatch/regrant on reopening and blocks
when exhausted. **No actual network request occurred in R318.** The accumulated
R310/R311 allowance remains7,757requests/229.85MiB. Unknown exact historical
bytes prevent this adapter from inventing a new byte grant.

Twenty-two held-book illustrations link a hypothetical midpoint entry basis to
side-aware displayed close marks. Their entry fees are deliberately unknown,
so every illustrated net cash/PnL/NAV stays UNKNOWN. They are not assumed entry
fills. Existing legacy proxy PnL is never imported as certified account cash;
the strict projection preserves missing inputs rather than rewriting frozen
forward journals or the legacy missing-return convention.

## Coverage of the requested first20 improvements

This is implemented/tested coverage, not another task queue. “External” means
the adapter exists but the required real-world evidence is still absent.

|#|Integrated change|Evidence / practical limit|
|---:|---|---|
|1|One account/journal and report|`paper_account.py`,8 engine cases; simulated linear futures only|
|2|Price/fees/funding decomposition|Independent cash conservation; execution drag non-additive|
|3|Realized vs open money|Bid/ask marks and separate future fees; unknown mark withholds NAV|
|4|Capital across venues|Two separate5,000-unit accounts; no collateral/FX netting|
|5|Optional redacted fee import|Strict64KiB whitelist importer; actual owner fees External|
|6|Promotion quota and expiry|Both-leg reservation, replay and instrument/export reuse; real entitlement External|
|7|Adverse exit scenarios|1,560 hypothetical side-specific exit quotes, not observed future fills|
|8|Lots, minima, affordability|Exact common lattice and actual per-venue buy/sell minima; ROBO maxVol failure retained|
|9|Size/depth/cost relation|432 retained cases at six fixed sizes; no best-size selection|
|10|Comparable capital/risk boundary|Same10,000/5,000-per-venue diagnostic capital; no equal-realized-risk alpha claim|
|11|Collector first-seen clocks|Sealed R316 books/references feed strict readiness and close marks|
|12|Event-bound Lighter index|Typed supplied-index contract tested; actual pre-update proof/API-unit bridge External|
|13|Synchronized paired inputs|Age/skew/identity/sequence guards unchanged;72 actual states remain blocked/unknown|
|14|Collection vs execution delay|Receipt offset, evaluation delay and venue minimum separated; actual fills External|
|15|Sessions and API rights|Unknown/closed/expired/mismatched contracts tested; real sessions/account permission External|
|16|Exact instrument/assets/contract model|Typed identities/units, maxima/minima and unknown class preserved; no ticker-based crypto/settlement guess|
|17|Announced vs settled funding|On-time original-event error with unit/timing/revision guards; synthetic here|
|18|Bounded persistent recovery|Gap, old epoch, crash reservations, restart exhaustion and reopen tested; no live reconnect loop|
|19|Accumulated acquisition budget|Durable scope/limits/baseline and no-refund reservations; old allowance not reset|
|20|Consistent missing-data admission|Strict new account/view withholds unknown cash/equity; frozen proxy histories not migrated/re-scored|

Useful related work is the single offline French account view, explicit blocker
messages and reproducible shared command. No claim that all100 suggestions are
implemented, that every first20 external input is available, or that adding
documents completes an improvement.

## Verification and reproduction

- **1,248 full tests passed,2 skipped**,182.896s;75 new focused tests passed in
  .079s. Focused feedback does not replace the full commit gate.
- Original financial reviewer supplied the independent Decimal oracle and
  identified notional-as-profit, unknown-mark and durable-reservation hazards.
  Root completed the artifact adapter and final integration review after that
  reviewer became unavailable; do not claim an independent final code sign-off.
- Artifact audit checks8 cases/16 segregated account states,130 displayed costs,
 390 stress costs and22 unknown-fee account links. Maximum reported quote
  arithmetic difference **4.67e-13**. Its arithmetic uses reported model
  postings/sweeps; it is not a second independent raw-market decoder.
- `results.json`, compressed observations, HTML, text and audit byte-reproduce
  in a fresh output directory; exact hashes are in `verification.json`.

```sh
.venv/bin/python -m lab account --out /absolute/new-empty-output
.venv/bin/python scripts/check_paper_account.py /absolute/new-empty-output/results.json
```

Open `account.html` locally; it is offline, contains no scripts or order controls,
and shows supplied figures without recomputing/adding balances. One maintained
canonical queue row M409 records this input/engineering scope. No new queue,
strategy catalog, source scrape, market acquisition or activation was added.

Verdict **PARTIAL**, zero predictive trials, program trials9,478,782, zero new
prospective days. R311 remains INCONCLUSIVE and its preselected policy negative
at2x/3x. Actual sessions/owner fees and permission, event-bound fair/index
notionals, executable paid fills, margin/liquidation and two-leg recovery still
block a newly frozen prospective profit test. No validation winner or leverage
change rescues that missing evidence.
