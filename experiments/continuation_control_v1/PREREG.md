# PREREG: finite-deadline carry inventory and common-account cost sensitivity

- **Registry id:** R323
- **Owner (single writer):** Codex; one bounded primary reader/limited reviewer
- **Date registered (UTC):** 2026-10-26

## Question, scope and evidence lineage

Implement canonical M410's previously unrun continuation controller. Under an
EXPLICIT supplied scenario tree, can exact Bellman choices respect segregated
resources, normalized funding cash, paid entry/resize/exit costs and an absolute
terminal deadline, and match an independent contingent-policy enumeration and
the existing PaperAccount? This is a conditional implementation/economic-control
study, not evidence that the supplied forecasts or favorable payments occur.

R310/R311 tested twelve myopic market-proxy rules, not this controller; no old
market data, held labels or validation winners are reused. R311 remains
INCONCLUSIVE224/273 and negative2x/3x; R321 remains NOT_ACCEPTED. R318/R319/R322
account/source work stays frozen. All eight constructed fixture families and
some signs/boundary results are known by design, not fresh empirical discoveries.

## Finite input/code/source identities

- `code_inputs.json`: `2b33d4e2cc0618d05e154e1f102fd1a3073896e90ffe32feb945157dca64866a`.
- `inputs.json`: `f226abd738dc8fa137ceda9d0d1e707f75531a2362f19e8830ab1c3732d82a4e`.
- `fixtures.json`: `26fd57381d72d2a8f81ce97782a6e70bbb59fcd65be875a4ee6c1b7de9d44f45`.
- `sources.json`: `07defdf43105b04c6dae9b1074e1c5877cfdbedc3745335fa275fb45daa4bca1`.

Eighteen pinned calculation/test/verification files; shared CLI dispatch is
excluded from the calculation closure and is exercised separately. Exact public
versions/URLs/body hashes, received/read/unread sections and review limitations
are retained. Boyd's terminal benchmark trade cost is a source fact; an all-cash
absolute deadline, separate wallets and exact state cash accounting are our
extensions. GP's persistent-impact state is read but excluded/unfitted; no
quadratic-cost partial-adjustment formula is used for proportional fees.

## Closed decision and execution contract

At every node use old paired inventory q and TWO marked equity balances.
Choose q from{-2,-1,0,1,2}, each unit=0.25 declared common base. MEXC holds+q,
Lighter−q. Each edge applies price changes and normalized funding quote/base to
the inventory held BEFORE its child-node trade. Missing funding is unknown for
nonzero inventory; a supplied flat model position has zero exposure. A raw rate
or unscaled Funding.value cannot be substituted for normalized cash.

The absolute horizon is3 decision periods. Terminal q MUST become0 and pay
the remaining close; no receding-horizon postponement or terminal midpoint fill.
The objective is expected terminal combined model equity, with actual costs in
each state. At EVERY modeled node incoming AND outgoing inventory must fit each
venue's own1x reference notional plus1% capital reserve; each marked balance
must also remain at least98% of that venue's initial capital. Reserves are
feasibility constraints, not extra cash charges. Opposite-leg gains cannot fund
another venue. Intraperiod liquidation/margin is not certified by this model.

Explicit bid/ask top-level capacities, base/quote minimums, fees and open/closed/
unknown session states are required for a nonzero trade. Common lot and all
book/cash scales are DECLARED fixtures, not authenticated venue metadata. Unknown
required values are not turned into zero costs or infinite capacity. All positive-
probability children count. Unknown candidate values prevent declaring a flat
optimal winner. Runtime/data failures never become successful inactivity.

Register FOUR controls: dynamic full-horizon Bellman; causal rolling ONE-period
myopic choice with next-period close; cash; fixed maximum long inventory until
the true terminal close. Ties prefer minimum change, then minimum absolute
position, then signed q. Capital and ex ante exposure/loss constraints match
across controls; realized risk equivalence is not asserted. The passive control
uses maximum positive units, not a smaller comparison exposure.

## Fixed scenarios, costs and capital

fixtures.json enumerates exactly8 families: zero edge,persistent carry,delayed
known trading closure,funding reversal,branched basis reversion,unbalanced
10/9990capital,unknown funding in a positive1e-6 tail,and terminal session closure.
All other cases have5000/5000 model capital, total10000. USDT/USDC parity is a
declared quote-unit assumption, with no collateral transfers. Prices,funding,
branch probabilities and perfect bounded taker fills are supplied assumptions.
They are not calibrated forecasts, actual execution, an unseen sample or alpha.

Build ONE reference policy per family/control at the preselected2x cost.
Replay its IDENTICAL node actions at1x/2x/3x; no cost-tier reoptimization,
post-validation winner or size/leverage rescue. Stress quote HALF-SPREAD and
fee RATE by the tier; fee is paid on stressed fill notional. This is not a
linear scaling of a precomputed cash total. Spread embedded in fill prices is
not separately booked again. Replay guards can reject a now-infeasible fixed
action; record the failure without silently selecting a smaller action.

32reference plans,96fixed-tier replays,120alternative-world paths. Branches are
alternative worlds using the SAME initial capital; never sum their capital/NAV.
No dropped or renormalized tail. Missing/failed paths withhold expected return;
known losses and unclosed inventory remain in diagnostic records. Separate
common-account append-only journals are retained in ignored raw caches and
immutable packed copies. Reopening must match; outputs never overwrite originals.

## Verification, trial count and stopping

Full required unittest discovery and22predetermined financial hand checks precede
commit. A separate reviewer located an incoming-margin bypass and rechecked its
fix at a prior exact kernel hash; later capacities/fixed-policy bridge/oracle
are NOT independently peer signed off. Follow-up was interrupted by a usage
limit. Do not convert that limited review into full implementation approval.

After code/input freeze, independently enumerate all7000root contingent-policy
assignments for the8 dynamic cases and reconstruct fixed reference/control
decisions,96tier replays/120paths/capital denominators and every journal chain.
This oracle shares the frozen model generator only for genealogy, not Controller
or ledger arithmetic. Reproduce packed outputs through the common lab account
command in a fresh directory. Any mismatch is retained; changed frozen code
requires a new lane, not a patched positive result.

Count **32diagnostic trials** (4controllers ×8families);96cost replays reuse those
same reference policies.7000internal optimization-enumeration assignments are
reported as solver verification, not independent market strategy samples.
Program entering this lane9,478,938. Market strategy runs0,new prospective days0.
PARTIAL requires the bounded component checks; every actual market-admission
gate stays blocked. No statistical inference, calibrated uncertainty, general
dependent-null guarantee, reserved sample or positive executable expectancy is
claimed from constructed trees. Market net at1x/2x/3x remains unknown.

One static primary GET756268bytes plus a cached author PDF within declared
4GET/2MiB/1MiBbody/90s scope. No market/history/account/RPC collection, orders,
money,secrets,weights,paywall/login bypass,merge or closure. Historical allowance
remains7757/8000requests and reported229.85/250MiB spent; no reset. No permanent
execution or remote delivery is promised.
