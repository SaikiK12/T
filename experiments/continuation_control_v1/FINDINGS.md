# R323 — PARTIAL: finite carry continuation and fixed-policy paper accounting

Freeze **9b6ec00e6be3e3a36c7b1a51bc2f94be1d06f51f** was pushed before the full constructed-family
diagnostics. PREREG SHA256 **b12ba992cce6afbda81cf3ab1cbbc968728c717ededb97aec446b7609cf52643**.
Canonical M410 now has a conditional implementation; its empirical forecast,
execution and prospective admission requirements remain unfulfilled. No old
R310/R311/R320/R321/R322 result is rescored, relabeled or activated.

The controller chooses entry,hold,reduction,flip or closure under an absolute
deadline. It accounts for old inventory's price/funding changes, each venue's
own marked capital, depth capacities/minimums, fees and terminal liquidation.
It uses the EXISTING PaperAccount and the same operational command:

```sh
.venv/bin/python -m lab account --continuation --out /tmp/R323-reproduction
.venv/bin/python scripts/check_continuation_control.py --directory /tmp/R323-reproduction
```

Use a fresh directory. This is offline; no market cache, network or secret is
needed. Existing observations and append-only journals are never overwritten.

## What was implemented and checked

Four registered controls share capital/exposure/loss constraints: full-horizon
Bellman, causal one-period myopic choice, cash and maximum-exposure long hold.
They have32reference plans across8fixed invented families. Each plan is chosen
at the preselected2x cost, then its IDENTICAL node actions are replayed at1x/2x/3x.
No cheaper-tier winner, larger leverage or new action is selected to rescue a
negative/infeasible stress. Actual tier-specific guards can reject an action;
the failed path remains unscored with its inventory and known losses visible.

At every modeled node, both INCOMING and outgoing inventory must fit each
venue's own1x notional plus1% capital buffer and2% cumulative loss limit. The
buffer reserves capital; it is not another cash charge. An immediate close
cannot erase an incoming margin breach. Intraperiod exchange liquidation is
not established by this discrete-time model. No cross-venue transfer/pooling.

Funding is a declared normalized quote/base amount on the OLD position. A raw
rate or historical Funding.value string is not converted to cash by guessing.
Unknown candidate values prevent declaring a flat optimal winner. All positive-
probability branches remain; a missing1e-6 tail is not dropped/renormalized.

Explicit bid/ask top-level capacities, base/notional minimums and open/closed/
unknown sessions gate nonzero trades. Stressed half-spread and fee RATE scale
by1x/2x/3x; fees are paid on stressed fill notional. Crossing is embedded in
the fill and not subtracted again. The final trade and its cost are mandatory;
a closed terminal market never receives an invented midpoint exit.

## Conditional economic controls, not measured market gains

All inputs below were constructed: some signs and boundary behavior are known
by design. The model supplies price/funding paths, probabilities, fees and
perfect bounded taker fills; it does not predict them. Total quote-equivalent
capital is10000 with declared USDT/USDC parity and5000/5000 segregation, except
the registered10/9990 resource case. Maximum size is0.5base. Same ex ante limits
do not establish equal realized risk. No candidate is selected from this table.

| Invented family | Dynamic net1x/2x/3x | Myopic net1x/2x/3x |
|---|---|---|
| Zero edge |0 /0 /0|0 /0 /0|
| Persistent carry |+0.42 /+0.24 /+0.06|0 /0 /0|
| Delayed trading closure |+0.22 /+0.04 /−0.14|0 /0 /0|
| Funding reversal |+0.77 /+0.59 /+0.41|+0.64 /+0.28 /−0.08|
| Branched basis reversion |+0.22 /+0.04 /−0.14|0 /0 /0|
| Unbalanced capital |0 /0 /0|0 /0 /0|
| Unknown funding tail |unknown /unknown /unknown|unknown /unknown /unknown|
| Terminal session closure |+0.42 /+0.24 /+0.06|0 /0 /0|

All96case/tier records and120alternative-world paths are retained. Cash is0
throughout, representing inactivity. Fixed maximum long hold matches dynamic
in persistent carry,delayed closure and reversal; it loses0.18/0.36/0.54 in the
zero-edge/basis cases, and fails/incompletes under unbalanced capital,unknown
funding or terminal closure. No known failure or simple matching control is
hidden. Dynamic itself loses at3x in two supplied families; the2x plan stays fixed.

The useful mechanism is cost coupling: multiple future payments may cover one
round trip while isolated one-period entries do not; a small temporary adverse
payment need not justify another exit/reentry. A mandatory deadline/session can
change that decision. In the simple stationary0.5base fixture, conditional gross
funding0.60 less0.18/0.36/0.54 friction yields0.42/0.24/0.06. Future funding and
quotes are ASSUMPTIONS here, not evidence that this hurdle can be cleared live.
There is no scientific basis to activate M410 or raise leverage from these cases.

## Independent arithmetic, tests and reproducibility

- Required full unittest discovery: **1326tests,2skip entries**,187.544s;22new
  predetermined financial hand checks. Skipped fixtures are not claimed executed.
- The frozen rational oracle independently enumerates **7000** complete root
  contingent-action policies for the8dynamic models. It matches the Bellman
  optimum/root action and reconstructs32reference policies, all96cost replays,
 120paths, capital denominators and1032journal-chain records exactly. It uses
  separate cost/risk/cash arithmetic; the generator is shared only to check
  input genealogy. It does not independently verify forecasts or market truth.
- The common account's reopen result matches each original path. Alternative
  worlds use the SAME initial capital, not120simultaneously funded portfolios.
  Failure/unknown paths withhold expected return rather than being omitted.
- **Five packed artifacts** byte-reproduce through the shared CLI, including
  all120journals. Raw append-only files stay in ignored caches; immutable packed
  copies preserve every byte. No archive/deletion of old frozen journals.
- A separate reviewer found the incoming-margin bypass and rechecked its fix
  at the earlier kernel hash recorded in review_scope.json. Later capacities,
  fixed-policy bridge and full oracle are not independently peer signed off;
  a follow-up hit a usage limit. No full review approval is invented.

## Primary-source scope and remaining admission

One bounded author-hosted Boyd GET received756268bytes, identical to the old
version hash. Newly close-read §5 terminal benchmark/cost/state-approximation
sections are distinguished from received-but-unread pages. Cached March2012 GP
§4/Eqs18–21 adds persistent-impact state D; that uncalibrated extension is
enumerated but excluded from R323. Source public process/control theory is not
a private institutional strategy or proof of alpha. Exact URLs, versions,
access restrictions and five distinct mechanics are in sources/source_review.

M410 still needs causally calibrated transitions/forecast errors, actual first-
seen executable depth after latency, owner fees/permission/sessions, event-bound
funding values/units, contract epochs, margin/liquidation/recovery, and a separate
frozen on-time prospective protocol. Those inputs remain unknown, not zero.
R321's failed calibration is not overridden by exact conditional tree arithmetic.

Count **32diagnostic trials**:4controls×8families, plus96linked cost replays.
The7000internal solver-verification assignments are explicitly reported, not
independent empirical strategies/samples. Program total becomes9,478,970.
New market strategy runs0,prospective days0,actual order permission alwaysfalse.
Market net expected return remains UNKNOWN at all1x/2x/3x tiers. Owner100 frozen
coverage is not relabeled as100completed improvements by adding this component.

All407old intake objects, old alias bytes and journal prefixes stay intact;
only the canonical method/intake receive exact supplementary tested/open scope.
Zero market/history/account/RPC requests. Cumulative historical approval remains
7757/8000requests and reported229.85/250MiB spent. No orders,funds,secrets,weights,
paywall/login bypass,merge/closure,remote upload or permanent execution claim.

## Post-freeze input-contract clarification

A separately declared source-only follow-up read the previously unreceived
pinned SDK CandlestickApi.fundings and public `/reference/fundings` contract:
2GETs/298440bytes within2GET/1MiB/768KiBbody/30s. This is not part of the frozen
R323 measurement/input closure; no controller/account outcome was changed.
The historical client is now located:GET `/api/v1/fundings`, maximum750events,
count_back semantics and1h/1d document resolutions. SDK/request validation differs
from the document's schema; examples do not define clock or cash semantics.

Most importantly,the public Funding schema gives `value`/`rate`/`direction` as
strings and examples, with NO unit/asset/sign/effective-event definition. The
client transports those fields rather than supplying a cash conversion. Thus
the narrower request-client gap is closed, while the server cash-unit/deployment
bridge remains unverified. No API value is promoted to paid cash by inference.
Exact hashes/read-unread scopes and all five distinct mechanics are retained in
api_cash_contract_followup.json. Raw bodies stay ignored. No market/history/
account/RPC request, extra trial, allowance reset or prospective observation.
