# R319 — PARTIAL: unfinished execution keeps its exposure and cost

Frozen code/source/spec/fixtures/held identity were pushed in
[`8345586`](https://github.com/SaikiK12/T/commit/8345586) before new outcomes.
PREREG SHA-256:
`659ba380765b239758d7de8f4cea47b53197b88648e12ede240f91b196074fb5`.
Work was completed by Codex alone, without another agent fan-out.

The account now retains both executed quantity and still-possible fills when
one venue rejects, cancels, fills partly or loses its source connection.
Only explicit stable trades post cash; an order label cannot turn a residual
position into zero risk or a completed profitable pair. This is executable
offline engineering and conditional arithmetic, not actual order execution,
new market alpha, authenticated account records or prospective paper evidence.

## Economic constraint at unchanged capital

All144 symbol/grid/deadline/direction rows remain:72 known old deadlines,
two directions,22 available underlying book states yielding44 direction rows
and132 cost tiers. No new book, policy selection or guard relaxation occurred.
All original input/session/fee/index-proof limitations remain. Capital stays
10,000 quote-equivalent,5,000 per venue, with conditional quote-asset parity.

At the original250-unit altcoin size, the unchanged paired crossing-plus10/4bp
reserve requires the following **hypothetical gross funding accumulation**:

| Cost multiplier | Paired hurdle, leg-normalized bp | Days to cover it at assumed10bp/day |
|---:|---:|---:|
|1x|44.89–56.15|4.49–5.61|
|2x|89.78–112.30|8.98–11.23|
|3x|134.67–168.45|13.47–16.84|

The10bp/day value is the inspected source's daily entry-filter threshold,
**not our forecast, realized funding, a guaranteed stable rate or a measured
holding-time return**. Actual expected funding and break-even holding time
remain null. A temporary favorable announced rate cannot by itself establish
that it will cover that many days of cost or survive a forced close.

No eligible held entry-basis illustration is positive after its fixed model
entry cost in either direction/tier. That is a finding on these22 dependent
states, not a rejection of M239/M241 in all markets. More generally, an apparent
positive cross-venue entry notional gap would not be futures profit: a same-book
four-fill round trip realizes only the negative paired spread/depth/fees.
The independent invented large-gap fixture explicitly verifies that distinction.

All792 conditional one-leg failure scenarios are retained: two directions,
three tiers, two filled-leg identities and0/20/50bp adverse future exit shocks.
On altcoin states, one orphan leg's current-book unwind loss at1x is
0.519–0.860 quote units. With a declared50bp adverse exit move it is
1.766–2.111; at3x the latter is2.803–3.831. These values assume the displayed
depth and specified fees; shocks are hypothetical and failure probabilities,
actual future exit prices, impact and fill timing remain unknown. They are not
estimated expected losses. A cancelled/rejected hedge cannot erase that risk.

## Integrated receipt and cash behavior

Sixteen invented source-event paths at1x/2x/3x make48 engineering paths and96
segregated account states. All reproduce after reopening the same journals:

| Final model state | Paths | Meaning |
|---|---:|---|
|flat|3|both actual supplied leg quantities closed; known model cash|
|hedged|6|opposing supplied fills, including exact residual retry/redelivery|
|exposed|15|a rejected or partly closed leg leaves directional base exposure|
|pending orders|3|acknowledgments alone produce no fill, but future fill risk remains|
|unknown|18|source gap/conflict/missing terminal total, bad retry or contradictory receipt|
|inactive|3|explicit flat starting account, no invented trading success|

The model exposes both known received quantity and a possible delta interval
while orders remain unresolved. A cancel request does not stop that interval.
Only a final cumulative quantity matching the individual trades completes the
order accounting. A partial fill followed by rejection retains its filled
position. A retry for the original full size, instead of its remaining fraction,
is refused as a consistent source state and net totals become unknown.

Stable trade ids prevent a new receipt id or restart from duplicating money.
An unexplained overfill is retained as known exposure, not discarded for failing
a model rule. Conflicting terminal totals, economic fills after a terminal
event and unmatched source trades withhold complete delta, cash and net PnL.
Known components remain visible; source gaps never become a known zero return.

The same R318 hash-chained account journal holds lifecycle receipts and financial
posts. A process interruption between them leaves an unapplied-fill join,
blocking complete totals until exact replay joins the original trade once at
its current as-of. The original economic/first-seen clocks stay unchanged.
An exclusive coordinator lease and fixed plan/target/deadline/attempt budget
prevent two writers or a restart from renewing the scope. Attempts include
closing intents; this finite example is not unlimited recovery authorization.
After any exit intent there is no new model entry. A filled small close order
does not imply a larger original position is flat.

All source_reports_authenticated, actual_order_allowed and execution_ready
claims remain false. The new class accepts supplied paper records; it cannot
authenticate exchange reports, place/cancel an order or infer full trade-history
coverage. Missing fees still withhold money even when quantities reconcile.
Actual margin modes, fee debit assets and two-leg executable recovery stay open.

## Previously unread primary code and exact received scope

Inspected official Hummingbot commit
[`9af100d6822da7d2d0291a906c730ef172284ee2`](https://github.com/hummingbot/hummingbot/tree/9af100d6822da7d2d0291a906c730ef172284ee2)
(2026-09-22): arbitrage executor/config, selected position executor routines and
config, shared validation, funding-arbitrage script and Apache2.0 license.
All20 distinct strategy/control/accounting mechanisms, parameters, versions,
hashes and read/unread boundaries are in [sources.json](sources.json), imported
into the existing intake/aliases. These are20 source refinements, not20 completed
owner enhancements or independently tested profitable strategies.

Important porting boundaries: spot sale/purchase cash needs funded inventory;
whole-amount independent failure retry needs residual fill reconciliation;
USD-name/wrapped-token equivalence is only a software policy; default20x
leverage and unknown-connector8h funding cadence are not our validated inputs.
The funding entry's price/fee filter defaults off. All received barrier,
volatility scaling, maker/market hedge, ONEWAY/HEDGE and retained-position
alternatives remain explicit unrun strategy scopes.

The inspected arbitrage percentage expression divides quote PnL by base filled.
A literal units example,4 quote profit/2 base/100 entry price, yields2 quote/base
under that expression versus.02 of entry notional. This is a dimensional
counterexample, not execution of the upstream module, a verified deployed bug
or a trading exploit. Our percentage/return denominators remain capital/notional
with explicit assets. Imported connector/framework guarantees were not audited.

Seven raw staticGETs completed with100,699 bytes in2.183s, no retry/redirect/login.
An initial provider metadata lookup additionally returned137 changed-file patch
entries that were not individually reviewed/mirrored. Its normalized output
was1,145,600characters; that helper could not enforce the intended1MiB per-body
cap. Provider/search wire bytes and combined time are unavailable. The source
budget exception is retained; no claim of a measured combined4MiB limit or full
137-file review is made. No upstream package/code mirror was installed/committed.
No market/account/RPC/history acquisition occurred; the historical accumulated
7,757requests/229.85MiB allowance is unchanged and not renewed.

## Verification, integration and remaining work

**Full suite:1,263 tests,2 skipped, no failures**,171.478s. Fifteen new focused
tests passed in.291s. They cover durable receipt/cash interruption, exclusive
writers, restart/scope reset, terminal quantities, partial-close inventory,
source/fill conflicts, future/regressed clocks, attempt/deadline caps and
duplicate trade ids. The61-file R319 dependency closure retains the original
54-file R318 closure without editing any old frozen file.

The independent standard-library adapter uses the reviewer-origin Decimal
oracle on reported fills to verify all48 paths/96 account states and finite
state expectations. It checks132 immediate-close identities and792 failure
scenario sign/unknown-probability boundaries; it does not independently decode
raw market frames or numerically reconstruct every failure shock/fee formula.
No final independent code sign-off is claimed. The production formulas are
frozen and explicit in PREREG; no Hummingbot module or original strategy runs.

All five outputs (results, compressed observations, HTML, text and audit)
reproduce byte-for-byte. Exact verification and preservation hashes are in
`verification.json`. The one account command supports both protocols:

```sh
.venv/bin/python -m lab account --out /absolute/new-R318-output
.venv/bin/python -m lab account --lifecycle --out /absolute/new-R319-output
.venv/bin/python scripts/check_paired_account.py /absolute/new-R319-output/results.json
```

The R319 view retains R318 fee/funding/acquisition controls with their original
invented/evidence scope and adds paired exposure; reused tests are not new
market evidence. M239/M240/M241/M245 remain untested source-strategy scopes,
M409 remains partial; no queue duplicate, policy selection or activation.

Verdict **PARTIAL**, zero predictive trials, program trials9,478,782 and zero
new prospective days. R311 remains INCONCLUSIVE and selected policy negative
at2x/3x. Actual authenticated complete fills/cancel/position reports, sessions,
owner fees/permission, funding event index/fair values and account liquidation/
financing are still required before a new frozen on-time paper PnL experiment.
The original100-enhancement list is not in this checkout; do not invent its
numbered completion count from these source/control records.
