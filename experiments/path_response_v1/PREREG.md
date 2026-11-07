# PREREG: path_response_v1 — order and replenishment beyond an OFI baseline

- **Registry id:** R400
- **Owner (single writer):** Codex; Claude operates the unchanged frozen runner against his recordings
- **Date registered (UTC):** 2026-11-03

This file is frozen with `lab.prereg.freeze()` before any market statistic for
this lane. Changes require a new lane. This is an exploratory discovery and
prospectively frozen quote-replay test, not strict on-time paper execution.

## Question and parents

Does a bounded equation using observed price/flow order and same-price displayed
replenishment add prediction and net quote-replay value beyond trade flow,
classical best-quote OFI, recent return, imbalance, spread and depth?

M430/M433 are the existing mechanism parents; no duplicate method id is created.
R367's fixed 100ms selective-maker rule and R386's completed grid remain frozen
and closed. R386 already covers simple return/flow divergence. This lane tests
arrival-ordered representations on raw events, not a rescue of their thresholds.
The author's earlier workbench (#68) used invented values only.

## Data and what has been seen

Fixed universe: Binance USD-M BTCUSDT and ETHUSDT perpetuals, both required.
This two-instrument study is not a cross-sectional survivor-universe test.

Development is **2026-10-29, 13:00-17:00 in the recorder's local UTC-labelled
clock**, and only the four finished parquet files in `training_manifest.json`.
Their byte counts and SHA-256 identities were copied from data-archive's
`files.csv` blob `5f1ac050b43d744c2a220f31057cfda3ae902a51`, before any price
was read here. Exact hashes are checked before training and again before artifact
publication. A different version cannot be silently substituted.

Availability metadata inspected: paths, sizes, hashes, source schema, and
Claude's reported first/last timestamps. Only Oct 29 is a complete archived
window; Oct 30 is partial and Oct 31-Nov 2 have outages/no market window. No R400
price, return, equation score or PnL has been inspected before this freeze.
The calendar overlaps historical prices already used elsewhere in the program;
development/selection results are **not fresh holdout evidence**.

Future evaluation: complete recorded windows Nov 4-10, 2026, 13:00-17:00, from
the same recorder/schema. No interim score and no read before **Nov 11 00:00
UTC**. The selected artifact must be fully published before **Nov 4 00:00 UTC**;
a late or failed preparation cannot catch up after future outcomes exist.

Sources are public websockets captured by `scripts/record_raw.py`. Binance BBO
`t,off,u,bid,sp,bq,aq`; aggregate trades `t,off,a,p,q,m`. Prices are hundredths,
quantities thousandths of a coin; m=1 means buyer maker, hence sell aggression.
Market and publication timestamps are not used to align the streams.

## Feature lineage and availability

All inputs are **forward-captured observations**; true exchange UTC, private
queue state and fills remain unqualified. The historical parser casts `off` to
int32, truncating the absolute wall-minus-monotonic offset. `t-off` is used only
as a **relative receive clock up to an unknown additive constant** within a
stable window; absolute monotonic/UTC is not reconstructed. The same constant
cancels in the anchored decision grid and durations. Encoded-offset steps/wraps
are rejected, not repaired. No cross-day/boot clock alignment is inferred.
The code rejects backwards clocks instead of sorting a broken capture. It
orders the two streams only on that receive clock. Arrival order is not proof
of economic causation; unequal feed-publication delays can affect it.

Every feature uses only `[d-5s,d)`, including the last already observed quote
at its start. Decisions are every 10 seconds on the declared window grid.
Both assets are evaluated together. Events exactly at d are excluded.

| Feature | Parents and formula | Availability / unknown rule |
| --- | --- | --- |
| flow | signed total trade q / initial mean BBO quantity D0 | Past trades only; clipped +/-20; no empty-flow zero filling |
| OFI | Standard bid/ask price-comparison contributions, summed / D0 | Past quotes; +/-20; both sides' price changes included |
| r5 | 10,000*(last mid / start mid - 1) | Past quotes; +/-50 bp |
| imbalance, spread, depth | Last (bq-aq)/(bq+aq), spread in bp, current mean size / D0 | Past quote; spread [0,20], depth [0,20] |
| coin indicator | ETH=1, BTC=0 | Fixed declared universe |
| area | Half integral of p dq - q dp; p=mid change in bp, q=cumulative normalized flow, anchored at window start | Past events only; +/-100; cross-stream receive ties make the window unknown |
| refill | Positive bid-quantity changes at unchanged bid, minus positive ask-quantity changes at unchanged ask, / D0 | Past quotes; +/-20; not identified additions, order identities or fills |

Past windows need positive nonlocked quotes/quantities and valid aggressor flags,
increasing per-stream ids, quote age/gaps <=500ms, first/last/internal trade gaps
<=1s, and local wall/monotonic offset range <=1ms. Unknown features omit the
decision identically for both models. Sparse activity and disconnections cannot
be distinguished by missing trades, so these are explicit coverage restrictions.

## Closed search and splits

Train on decisions through 14:59:30; select on decisions from 15:00:30 onward.
The 60s purge exceeds lookback and delayed label overlap. At least 100 training
and 100 selection observations, >=80% past-feature coverage per instrument/day,
and >=99% usable labels are required. A QC failure is terminal after first look;
there is no replacement day or retuned coverage gate.

Baseline: intercept + seven fields in the table (flow, OFI, r5, imbalance,
spread, depth, coin indicator), standardized using training means/population
standard deviations; std <1e-8 becomes 1; standardized values clipped +/-10.
Ridge penalty 10 on slopes, zero on intercept. No hyperparameter search.
This comparison is against that fixed linear baseline; superiority to a
nonlinear parent model is not established by this lane.

Equation primitives: standardized/clipped area, refill, flow and constant 1.
Grammar `+,-,*,/`, max 5 nodes, max 2,000 attempted admissions/operations, fixed
factory order. It generates **1,476 attempts: 623 retained forms, 837 proven
duplicate attempts, 16 invalid attempts**. Of the retained forms, 564 require
area or refill. These are not independent hypotheses or globally unique laws.

Each candidate must be finite on all training and selection feature rows, have
nonconstant training values, and use a new primitive. Divisor/guard magnitude
<=1e-6 is unknown. Subtract its training-only linear projection on the baseline;
reject residual std <1e-8. Standardize/clip that residual and add it as one ridge
column. This prevents a duplicated baseline feature from merely relaxing ridge
shrinkage. Rank by selection MSE, then nodes, text and factory index. Select only
if MSE improves by more than 1%; otherwise **NO_NEW_EQUATION**, with no future
data read. Selection is never based on historical trading PnL.

Refit only the selected expression and baseline on combined development rows.
Refit scaling/projection are serialized. If the selected domain becomes invalid
or collapses into the baseline span, preparation fails; no next-best rescue.
The JSON model, its SHA-256, source hashes, runtime versions and a portable
development sample table are written exclusively. No new selection or refit
after the deadline. Sample-table replay is for deterministic auditing only;
it cannot create a second alpha claim or another holdout look.

## Labels, decisions, execution and costs

Target: mid return from the first quote received at/after d+500ms to the first
quote received at/after d+5.5s. Either quote must arrive within 100ms of its target.
Invalid/future-clock-stepped quotes create unknown labels. Every local
UTC-labelled hour boundary is excluded within 30s (including possible funding).

Trade only when abs(predicted bp) >10 bp + current observed spread; side is the
forecast sign. This threshold never uses future spreads, depth or outcomes.
At most one $100 position per coin per 10s slot, held 5s after delayed entry,
fixed $1,000 reference capital, no leverage or compounding. Longs cross entry ask
and exit bid; shorts cross entry bid and exit ask. All four displayed-side sizes
must support $100. Entry/exit capacity is assessed **after the decision**; an
insufficient or missing future execution is unresolved, not a dropped trade.

Primary cost scenario: **5 bp per taker leg**, not a verified owner fee. Total
cost = mid-return minus crossed-quote return + fees on entry/exit notionals.
Report 1x/2x/3x this entire cost, with the same 1x action threshold. Actual fills,
book walking, impact and fees are not established by public BBO replay. No MEXC
profit or execution claim follows from this Binance-source scenario.

Unknown selected features at forward time mean abstention, not zero-valued
measurements. Unknown labels remain unknown. Any unresolved placed trade prevents
a positive verdict and prevents reporting an aggregate total PnL as known.

## Null, multiplicity, decision and stops

Registry trial charge: **1,478** (all 1,476 raw factory attempts, baseline and
one final refit), including algebraic duplicates, invalid and unfit candidates.
Record every retained form's disposition and score; do not reduce old program
trials through deduplication. There is no program-wide adaptation correction.

Future statistics pool both coins into common local UTC-labelled hourly blocks.
No binomial trade-count inference. Resample whole blocks 2,000 times, seed 400
(401 for MSE), keeping unequal observation counts in the ratio estimator.
Report percentile 95% intervals for selected-minus-baseline hourly 2x PnL,
baseline-minus-selected MSE and selected hourly 2x PnL. The null is no incremental
benefit; intervals assume representative, sufficiently independent hourly
clusters, which this study does not prove. No shuffled-trade independence claim.

At least five of the fixed seven complete forward days and 20 hourly blocks are
needed. All available declared days are used; QC failure cannot be selectively
ignored. Missing/unresolved executions, <99% label coverage or inadequate data
give INCONCLUSIVE/refusal, never a positive result. EXPLORATORY_SIGNAL requires
all three lower bounds >0 and >=99% defined selected forecasts. Otherwise NULL
when sufficient; >1% undefined forecasts cannot pass. No extension or new look.

Power cannot be certified before an effect-size/variance estimate. At most 28
hourly clusters exist here; there is no 80%-power or small-edge exclusion claim.
These are lane-native exploratory outcomes, not gate admission. Strict on-time
predictions, qualified UTC, execution/fill calibration, 10-day trimming,
leave-two-coins-out (impossible with two coins) and across-family control are
unmet. `gate_eligible` is always false; no reserved sample or real order authorized.

## Exact implementation and source reading

The inputs block below binds all new implementation, contracts, source parser,
manifest, dependency lock and the current GATES document. Runner verifies it
before QC or fitting. First-look claims are exclusive and survive failures.

Primary reading: Cont, Kukanov & Stoikov, [The Price Impact of Order Book
Events](https://arxiv.org/pdf/1011.6402), v3, section 2.1's quote-event definition
and OFI sum, plus previously read section 2.3. This supplies the classical
baseline; its contemporaneous NYSE relation does not demonstrate crypto
forecasting or profits. The symbolic/path sources and exact bounded scopes are
in [the engineering note](../../research/discovery/README.md). No new mathematics
or exhaustive worldwide novelty search is claimed.

```inputs
0a41205ce7f82b25e741a8cd2ee69237f15a92f9d30e372f4fdb2889c6c587bc lab/path_response.py
022fa8ed34a688c8b1ea25c4c2accf1a01cf905489b75f1fa02454c0110265a1 lab/formula_space.py
b5479e187e363d5ded08ea25bd8289ea39b4f59f789a9ae1921c3e5610274211 scripts/run_path_response.py
1e730b44af064ed1d150a4d306fd84465413831428ff24a03ea113104dab3b4c scripts/record_raw.py
e678b46a6491d5edb766b08cad59f38dfe1cf659afd8de15a9a22161f9e16025 tests/test_path_response.py
a1002cd1a696fd9aaaf73ddf365b1238c6a983be9fa900ded846dad9456c013f experiments/path_response_v1/training_manifest.json
4cf65930e08965601cefe33b1785271bb024d22f39eac22582e5fd393bb2b466 requirements-test.lock
e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926 docs/GATES.md
```
