# PREREG: R334 opportunity value and one-account allocation diagnostic

- **Registry id:** R334
- **Owner (single writer):** Codex; claim https://github.com/SaikiK12/T/issues/7#issuecomment-6424888355
- **Date registered (UTC):** 2026-10-26

## Question and scope
Can supplied price/funding forecasts be joined to existing first-seen quote cost,
persistent PaperRisk controls and ONE PaperAccount budget without treating a high
probability, an unfilled plan, an unknown payment or reused capital as profit?
This is offline component validation, not a new strategy screen or runtime
allocator. No scheduler, account access, orders, authentication or durable
opportunity reservations are implemented. No concurrent/repeated execution use.

Existing canonical scopes: M409 carry, M410 continuation, M412 level confidence.
Reuse R318 account, R319 lifecycle semantics and R320 threshold/risk components.
Do not alter those frozen files or R310/R311 decisions. R331 remains unfinished
at its calibration artifact; later model-selection/validation labels are unread
in this pass. Claude owns R332/R333 and the live forward journals.

## Frozen inputs and provenance
- code_inputs.json SHA256 2bdc714fd4b2a0edfecd1bcd6430ca545857b4aa7074ec029d78c024a30d61ba
- data_inputs.json SHA256 6b0961cd9a792225fec28d40ec97ee51affa1d20a7a3abf83d677b15c01cf4de
- fixtures.json SHA256 cd52efd8ae13339ef963cf24a7701bf065326d1f27fa5f93e60e34e34dcdf2ce

Sixteen-file local code/test closure and Python version are pinned. Verify all
hashes before and after reporting. Data is the already-seen published R318
72-deadline, six-size derived cost artifact and its original provenance, NOT
newly decoded raw market frames or future returns. Preserve all absent costs.
Parent source/clock/capacity/session/fee/settlement limits remain. Source facts
are reused, not a new web reading. No data downloads or model weights.
Historical acquisition allowance remains7757/8000requests,reported229.85/250MiB;
exact remaining bytes unknown. Zero new requests and no budget renewal.

## Finite rule and economic convention
One supplied forecast has exact venue, symbol, signed BASE quantity, settlement
asset, original first-seen clock, future horizon and at most32 complete outcome
probabilities. Outcome price and funding payoffs are settlement-quote amounts
for THAT quantity, midpoint-to-midpoint and EXCLUDING execution costs. Unknown
positive-mass outcomes stay unknown; zero-mass unknowns do not affect expectation.
No inference converts directional probability, volatility or basis into cash.
The calibration pointer and quote-error allowance are supplied contracts, not
an authenticated calibration or coverage guarantee. No new confidence interval.

Reuse liquidation_quote for the current buy/sell sweeps and fee amounts. Count
same-book round-trip spread/depth plus both-side fees ONCE. Exit remains a proxy;
a separate nonnegative future-exit reserve is mandatory. Source/receive clocks
keep original1s/2s/50ms guards. Missing fee/book/depth remains unavailable.

Reuse entry_threshold at fixed1x/2x/3x: expected(price+funding) minus k times
(current crossing+fees+exit reserve) minus supplied error. Require strictly
positive3x for conditional inclusion; no tier-dependent entry quantities.
This NEW component rule does not change any old strategy's thresholds or fees.

Market, fee, lot, settlement and session contracts need explicit source pointers,
current validity, matching venue/asset/symbol/quantity, linear payout and matching
quote/settlement asset. Check supplied base step/min/max. These declarations are
not owner permissions or source authentication. No automatic USD/USDT/USDC netting.

Obtain a current snapshot and invoke the ACTUAL existing persistent PaperRisk
object on that snapshot. Its anchor and original account balances must match.
Old stops cannot reset. Caller cannot substitute an already-green risk summary.
New plans obey projected registered per-venue and per-symbol gross limits, using max(buy,sell) notional for shorts as well as longs.
One ordered batch consumes per-venue/asset planning capacity from min(available
cash, net liquidation equity minus locked capital), floored at0. Reserve initial
entry notional plus full3x round-trip/exit reserve per included idea. No new
leverage, inter-venue profit offset, capital top-up or unrealized-gain financing.
All tiers share the SAME planned quantity and admission, caller order unchanged.
The financial account/journal must remain identical. Risk observations may append
only to the new scratch risk journal. No plan is a fill or durable reservation;
that runtime/lifecycle bridge is explicitly still required before repeated use.

## Constructed inputs and retained data
Exactly15 invented cases in fixtures.json: high confidence/small gain, positive
conditional forecast, funding+breakout sharing a budget, same cash twice,
uncalibrated, missing funding, fee, session, future book, insufficient depth,
wrong settlement asset, persistent risk halt, short, missing exit reserve and
missing error. Some contain multiple opportunities. Same1000USDT account,
10bp per-side supplied fee,99.5/100.5 book, fixed base quantities1 or6,
12h horizon,2quote error and.5quote exit reserve unless explicitly missing.
These deliberately illustrative payoffs/calibration IDs are NOT fitted to markets.

Every original R318 deadline x six sizes x1x/2x/3x cost cell is emitted, including
missing depth/clock/quantity/costs. Retain original10,000total/5,000per-venue
conditional quote-equivalent capital and fixed sizing. Report each published
paired hurdle before unknown forecast/error; expected gross/net and admissible
opportunities remain unknown/false. No placeholder book or favorable forecast
will be manufactured from aggregate sweeps. No observed future exit or PnL.

## Checks, decision and multiplicity
Run full unittest suite before code commit, including complete invented driver
and independent Fraction oracle plus corruption rejection. Commit frozen spec,
code/input identities BEFORE reading actual held costs for this new diagnostic.
Then run finite report, separate Fraction checker and byte-for-byte reproduction.
The checker imports no production value/financial/selection functions; its scope
is literal invented arithmetic/ordered allocation and parent cost-cell identity,
not raw-source decoding, calibration validity or actual execution.

PARTIAL means verified component behavior with actual net-return evidence still
UNKNOWN; preserve failures and do not edit frozen files to repair them. No
p-value, statistical alpha verdict, holdout read, calibrated error coverage,
strategy candidate, executable expected return or activation follows. Cost
sensitivity is reported for every positive/negative/unknown constructed case.

Predictive strategy trials0 for R334. Basec54872e records9,478,976. Conservatively
register the frozen but unfinished R331 family as14planned/tested variants,
program9,478,990, explicitly without later selection or validation outcomes.
R334 adds0 to that denominator. All dependent repeated cells remain dependent, not
new opportunities or owner-enhancement completion counts. Prospective days0.
No method/coin/fee/threshold selection or discarded nulls after results. Old
registry bytes remain a prefix. Append the previously missing R331 REGISTERED/PENDING row and own R334 row
only; no panel/queue/live-journal
rewrites that overlap Claude. No merge, PR closure, money or secret access.
