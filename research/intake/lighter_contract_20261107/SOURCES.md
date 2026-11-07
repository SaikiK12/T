# Recorded Lighter roles: primary source and a closed accounting hypothesis

Accessed 2026-11-07; source reading began at18:53UTC. Exact HTTP clocks and
hashes are retained in [source_receipts.json](source_receipts.json). No
market source was requested. The only market inputs proposed for R427 are
the two already-restored Oct29 WTI/Brent trade files, unchanged from R426.
No prices, position differences, side consistency, markouts or return
statistics were read during plumbing. [Schema/counts](schema_counts.json)
are separate from the proposed position-identity measurement.
Both files have all required position/quantity values finite and compatible
with the declared lot grid, and valid stored boolean encodings. These are
field-availability counts, not cross-trade accounting matches.

## Sources actually read

1. **Primary; partial**, elliottech/Lighter agent kit,
   [read schemas](https://github.com/elliottech/lighter-agent-kit/blob/main/references/schemas-read.md).
   Undated source, accessed Nov7. Its trade example says:
   `"is_maker_ask": false, // false = aggressive buy, true = aggressive sell`.
   The opposite interpretation is registered alongside the existing code's
   interpretation. The funding section describes a different endpoint,
   `/funding-rates`, as "8-hour-equivalent"; that is not a definition of
   `/fundings[].value`. Only these sections were extracted, not the full kit.
2. **Primary; partial**, elliottech/Lighter Python SDK,
   [Trade model](https://github.com/elliottech/lighter-python/blob/main/lighter/models/trade.py).
   Undated, accessed Nov7. It declares boolean `is_maker_ask`, ask/bid account
   IDs, and string maker/taker position sizes before the trade. It gives no
   explicit aggressor-direction definition. No SDK trading code was executed.
3. **Primary source code; partial**, elliottech/Lighter prover,
   [apply_trade.rs](https://github.com/elliottech/lighter-prover/blob/main/circuit/src/apply_trade.rs)
   and [matching_engine.rs](https://github.com/elliottech/lighter-prover/blob/main/circuit/src/matching_engine.rs).
   Retained copies match Git blobs
   `c6eb4735ed1f706490239f2e2835509ebd67c00a` and
   `77d0f0c92b84f3c0296f05faa7f3ccc1d2cf4b50` in tree
   `fa85b33197710ece649739bc38f5e23e816ddbdf`.
   The perps branch says "If is_ask => -1, else 1" and multiplies the signed
   base quantity into the taker's position delta. The other account receives
   the opposite base-position change. Funding changes allocated collateral,
   not this traded-base delta. Read scope: apply_trade.rs320..405 and
   1110..1190, matching-engine maker/taker/ask contexts; **not a full code or
   security audit**. These objects do not prove which circuit/API serializer
   version was deployed on Oct29, nor the public boolean's exact serialization.
4. **Primary location but public-user claims; full issue body and all currently
   returned comments**, [SDK issue182](https://github.com/elliottech/lighter-python/issues/182),
   opened by kfa17 on Oct6, one comment by Locke777pips on Oct23, accessed
   Nov7. The first question asks whether historical `value` is a funding
   charge per base unit; the later comment also asks for deployed versions.
   **No maintainer answer was present in the returned thread.** These are
   questions, not an exchange definition or permission to contact anyone.
   No message was posted upstream.
5. **Secondary; partial**, bond-labs-dev,
   [lighter-data README](https://github.com/bond-labs-dev/lighter-data),
   undated, accessed Nov7. Its funding section claims a nonnegative percent
   per hour, long=payer, and verification against `value/index_price`.
   No underlying live validation trace was verified here. This is a claim,
   not primary cash-unit evidence. Search also found implementations making
   conflicting decimal/percent assumptions; no magnitude was fitted to them.

## Exact question and important limits

For each recorded market/account, adjacent reported pre-trade positions
should differ by that account's preceding signed trade quantity if the
retained prints contain every intervening base-position change. A bidder
adds base quantity; an asker subtracts it. The two boolean interpretations
assign the raw maker/taker pre-position fields to opposite account IDs.
All comparisons and failures must be reported under both hypotheses.

The recorded trade IDs have gaps (WTI87, Brent31 nonconsecutive steps).
Their counter scope is not established; a gap alone is neither proof of a
missing market fill nor proof of complete capture. No comparison is dropped
to obtain consistency. Liquidation records form explicit sequence barriers.
An omitted trade, ADL, grouped pre-state snapshot, unsigned position field,
historical lot change or lost numeric precision can make the model fail.
An exact sampled pass would support only that observed role assignment;
it would not certify a complete feed, all future fields, private order/fill
acks, source clocks, net profit, France access or historical funding cash.

Current metadata's size precision3/4 is borrowed as an explicitly unproved
Oct29 grid assumption. Stored floats are converted to declared integer lots
with a fixed one-millionth-lot serialization allowance; the subsequent
position identities are exact integers, with no fitted residual tolerance.

Four new static-document GETs read25490bytes. The budget proof conservatively
charges their whole294916byte cap as well, retaining all old reservations:
**7819calls/251220970bytes** of the original8000calls/262144000bytes.
This is no new market acquisition, allowance renewal, large download,
account, credential, order, native tick, daemon or protected-sample read.
