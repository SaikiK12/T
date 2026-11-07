# R427: recorded Lighter trade-role contract through base-position identities

- **Registry id:** R427
- **Owner (single writer):** Codex; isolated lighter-source-contract worktree, no subagents.
- **Date registered (UTC):** 2026-11-07

## Question

Which, if either, of the two named interpretations of the retained Lighter
`is_maker_ask` field is exactly consistent with signed base-position changes
reported for recurring market/account pairs, without prices or PnL?

## Universe

Only WTI and BRENTOIL Oct29 trade fragments already restored for R426:
102 and32rows, hashes fixed by `cases.json` and the input manifest. NATGAS
has no trade file and cannot join this source test. No coins/accounts are
selected by a return, markout, position difference or consistency outcome.
All account identities in each eligible file are retained. The other15
archive members remain opaque: no HFT/R367 or protected-sample read.

## Data

The original recorder copied raw ask/bid account IDs, maker boolean,
source/local clocks, quantity and maker/taker pre-trade positions. Its old
float conversion is not repaired. Only the11explicit columns in the frozen
runner are decoded. Price/entry-quote/fees are not loaded or scored.
Plumbing already established schema,134rows, unique IDs, receipt bounds,
nonnegative transaction clocks,35/14account IDs and14/0consecutive-ID steps.
WTI87/Brent31ID gaps have unknown counter scope; no completeness conclusion
or position-identity statistic was computed from them.
Counts-only field qualification also found no missing/nonfinite positions or
quantities, no off-current-grid values and no invalid boolean encodings.
This does not compare one trade's position to another or identify a side.

Current Lighter metadata from R426 supplies size decimals3/4. Equivalence to
the Oct29 grid is an explicit unproved assumption. The source receipts bind
primary agent-kit/SDK wording and retained prover blobs; public funding
issue182 still has no maintainer cash-unit answer. Static source reading is
not proof of the deployed Oct29 serializer/circuit version.

No new market requests. Four tiny static-document GETs read25490bytes; their
whole294916byte reservation is additionally charged conservatively to the
unchanged original historical ceiling. Cumulative proof7819calls/251220970
bytes under8000calls/262144000bytes. Old worst reservations and uncertainty
are retained; no fresh allowance, denied source retry or large pull.

## Feature lineage and point-in-time availability

| Feature / formula | Parents | Source / units | Window / order | Publication / receipt | Decision availability | Vintage / revision / missing rule |
|---|---|---|---|---|---|---|
| Account occurrence and fixed order | trade_id,ask_acct,bid_acct,tx_us,T,t | retained public Lighter WTI/Brent trades; IDs, source/local clocks | whole named files; tx_us then trade_id | original local receipt and source timestamps retained | ex-post contract check, no trading decision or calibrated cross-clock delay | previously seen short fragment; invalid IDs/clocks/booleans or reversed source ordering fail closed |
| Signed position before account trade | tpos,mpos,maker_ask,ask_acct,bid_acct | recorder's stored floats, interpreted as signed base quantities | both declared mappings, all occurrences | published in trade report, known only after receipt | cannot act at the earlier fill time | exact original values, no future substitution or account selection; no unsigned-to-signed fitting |
| Integer lot recovery | sz,tpos,mpos,current size precision | base units times10^3or10^4 | per value before identity arithmetic | computed once after committed freeze | source qualification only | nearest integer only within fixed10^-6lot float-serialization allowance; otherwise fail; no residual tolerance |
| Consecutive-account identity | prior pre-position,prior bid/ask side,prior quantity,next pre-position | ask subtracts quantity, bid adds quantity; integer lots | adjacent appearances of same account/market, reset at every liquidation | later pre-state is an ex-post witness | not a prospective signal or actual own fill | no dropped mismatch, lag/scale scan, gap imputation, missing-fill repair or completeness assertion |

## Rule or search space

Two interpretations, named before reading position relationships:
- H0 `true_is_maker_ask`: true assigns mpos to ask account and tpos to bid;
  false assigns mpos to bid and tpos to ask. This is existing tape/R426 code.
- H1 `true_is_taker_ask`: the opposite account-role assignment, following the
  contrary primary agent-kit example. It is not selected by profit.

Validate all source identities/booleans and signed quantities. Exact duplicate
trade IDs, self-trades, missing/nonfinite/off-grid fields or contradictory
source ordering stop this consumed run with preserved ERROR, never a new try.
Negative pre-positions are allowed; nonpositive trade quantity is not.
Fixed sort is transaction microseconds then trade ID; under that ordering
trade IDs must increase and the source millisecond timestamps must not reverse.
No local/source clock subtraction or actual order latency is inferred.

For each market and hypothesis, walk every ordinary print, mapping pre-state
to ask/bid accounts under that hypothesis. For every subsequent appearance
of an account, test:

`next_before = previous_before + previous_base_delta`,
where previous_base_delta is +qty for a bidder and -qty for an asker.
All arithmetic after lot recovery is exact integers; identity tolerance0.
Report every account/ID pair, both pre-states, delta, expected state, residual
and match flag. A liquidation clears every predecessor state in that market
and is not bridged. ID gaps are not filtered: without a counter-scope/feed
guarantee, omitted executions can invalidate this model.

Per market/hypothesis, require at least8transitions across at least2accounts,
with at least2transitions whose previous side is ask and2whose previous side
is bid. Failure is INCONCLUSIVE_COVERAGE, never a zero or a pass. Sufficient
coverage and all exact matches give SAMPLED_POSITION_CONSISTENT; any mismatch
with sufficient coverage gives POSITION_IDENTITY_MISMATCH.

A market passes only if exactly one mapping is consistent and its opposite
has sufficient coverage and at least one mismatch. Two consistent mappings
are INCONCLUSIVE_NOT_DISCRIMINATING. Whole-lane SAMPLED_ROLE_CONTRACT_PASS
requires both markets to pass with the SAME mapping. Anything else remains
UNQUALIFIED_SAMPLED_ROLE_CONTRACT, with both full outcomes retained.

## Splits and cost

No forecast, return, markout, trading rule, split or financial PnL. This is
conditional source accounting on previously seen dates, not OOS/live alpha.
**Costs1x/2x/3x: N/A, not zero.** R426's three cost cases stay unchanged.

## Gates and null

Full synthetic suite, integrity, staged catalogs, exact frozen input hashes
and a COMMITTED/PUSHED freeze before source quantity/position comparisons.
`RUN_STARTED.json` is exclusively created before those fields are loaded.
One run only; any failure consumes the scope. One frozen independent
Fraction/account-history checker compares every retained identity to the
unchanged native report; it is validation, not a new convention/search.

No financial null or p-value applies. A mismatch can mean wrong side
semantics, incomplete feed, grouped pre-state, stale ordering, wrong signed
position/grid assumptions or serialization changes. It does not prove no
trading edge. A sampled pass supports only observed role consistency under
the stated assumptions; it cannot certify complete capture, global API
semantics, production deployment vintage, private ack/queue, clocks, funding
cash, fee entitlement, capacity, access from France or a profitable method.

## Multiplicity and evidence lineage

**0 predictive/economic trials**, program total9784361via
`registry.program_trials('registry/rounds.csv')` before this registration.
Two semantic hypotheses on two dependent market fragments are all reported;
identity counts are not independent trading bets. M474/R426 is the affected
execution pilot, M441 the untested participant-flow family. No gate1, real
stake or rewriting of any earlier frozen lane follows from this test.

## Stop rules

No new market, account, row, time order, sign convention, grid, threshold,
serialization allowance or mismatch exclusion after the result. Do not rerun
R426, edit a frozen parser, tune quotes/markouts on this fragment or infer a
strategy winner from source identities. New ideas need new registered input
scope and evidence. No native tick/recorder/daemon, account/credential/order,
money movement, paid source, protected2020/MEXC/reserved read, denied endpoint
retry, private data, subagent or allowance renewal.

## Frozen input manifest

d4a35a23c301f6dfaa2ceb20764718913ccd94a970b03a59f986a4e26c11c265  experiments/lighter_trade_contract_v1/inputs.json
