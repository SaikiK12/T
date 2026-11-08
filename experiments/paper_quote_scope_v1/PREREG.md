# PREREG: native DTB3 source scope and paper continuity

- **Registry id:** R429
- **Owner (single writer):** Codex; native journals only through the selected serialized GitHub Actions writer.
- **Date registered (UTC):** 2026-11-08

## Question

Does requesting exactly the native DTB3 lookback preserve every eligible
date/rate/missingness pair, including the latest usable pair, while allowing
the existing paper rules to continue within their original resource limits?

## Universe

One public FRED series, DTB3, and one source-view comparison. No instrument,
account, return or successful provider selection. The manifest below fixes
all inputs. No cross-sectional universe or delisting comparison applies.

## Data

The held native response is request780 in canonical state
cd469d7d8f4cd426b015d17e9cfd2b3cc3e5b8b7. Its original 301601-byte body
was hashed/decompressed as opaque bytes; only an8192-byte recent tail was
date-filtered. No protected2020 rows were parsed or measured. Original body
hashes, derivation and date counts are in the held-reference receipt.

One ordinary public FRED GET was qualified before registration for status,
schema, clocks, bytes and date counts ONLY. It returned200 and4518bytes,
284 dated rows,2025-10-06..2026-11-05, received2026-11-08T14:28:46UTC.
No rate value, yield comparison or predictive statistic was inspected.
The case fixes the clock at2026-11-08T14:28:45.560594+00:00 and preserves
the original native intraday400-day eligibility cutoff. The HTTP source
view uses its calendar date through today's UTC date (cosd/coed), while
the unchanged native code retains its stricter intraday filter.

These are two provider vintages of the same recent observations, not an
unread trading holdout. Byte/hash identity was permitted source plumbing;
the numerical field-identity check waits for freeze, registry and commit.
FRED publication/revision times beyond these receipt clocks are unknown.
The source does not prove executable Treasury investment, account funding
cash, trade fees, legal access or positive return.

## Feature lineage and point-in-time availability

| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| Native source rows | CSV date and DTB3 string | FRED DTB3; native percent-rate interpretation unchanged, not independently cash-qualified | fixed case clock minus400days; native intraday cutoff | archived request UTC and one later probe receipt | available only after each actual receipt | latest-vintage public series; one held vintage versus one later view | blank/dot remain missing, never zero; invalid/nonfinite/duplicate/out-of-window rows stop |
| Equality and latest usable pair | eligible date/rate/missingness rows | exact Decimal comparison; independent Fraction parser | all dates in union, no outcome-selected exclusions | only after committed frozen protocol | source admission only, no historical trade decision | inherits provider revisions and pair dependence | any unequal/present-only date or latest usable pair fails |
| Runtime resource/health | START/END/CONTENT, native status, manifests | inherited R419/R413/R406 and R428 source-stop state; counts/bytes/UTC | complete inherited prefixes plus later legitimate appends | actual native/source clocks | skips do not refresh data timestamps | forward receipts, not controller success | unknown spend, divergent/cut state or missing receipts stop; no reset/backfill |

## Rule or search space

One primary offline execution of scripts/run_fred_quote_scope.py --run,
followed by one independent offline scripts/check_fred_quote_scope.py audit.
Both are frozen. Default primary invocation is an inactive plan. There is
no date, lag, scale, unit, missingness, fit, fee, parameter or source search.
Every eligible date and exact numerical value/missingness must agree; the
latest nonmissing date and value must also agree. The provider bytes are
not synthesized or reserialized for the native consumer.

Before any value comparison: freeze with lab.prereg.freeze(), append R429
with lab.registry.append, COMMIT AND PUSH the complete input closure.
The sole execution writes an exclusive RUN_STARTED marker first. Failure
is retained and ends this specification; changed code/idea needs a new id.
The independent audit verifies the same result, not another economic trial.

Only a committed primary PASS plus committed independent audit, full tests,
reviewed current-head CI and merge permit the explicit /quant-quote-migrate
command to select R429. No local tick, recorder, daemon or fake Actions
environment. Existing frozen workflows are untouched and share one global
concurrency group. Only the canonical selected contract writes journals.
Migration must publish before preparing source work; the hour checkpoint
must publish before HTTP. Unfinished previous host or source-stop drift
blocks migration. All old native paper algorithms remain unchanged.

The FRED-only encoded-body response cap becomes16384bytes; decoded cap,
source allowlist, other source caps and original native4096calls/16777216
auxiliary bytes remain unchanged. The400-day view matches the native
lookback already used by scripts/forward_lockcarry.py. No source freshness
policy is changed. Baseline793calls/16384014charged bytes is inherited
verbatim, leaving393202bytes; all later legitimate appends, BLOCK events
and unknown reservations are preserved. This is an admission shortage,
not a FRED denial. No denied source is retried or routed around.

R428's Lighter jurisdiction SOURCE_BLOCK is retained exactly; no new
participant/market request, URL variant, region/provider/header workaround
or source child. R419's1351calls/16MiB and Nov14end, dispatcherNov19end,
and64MiB state ceiling are unchanged. No coverage through December/2027
settlements is promised. No original allowance is renewed or refunded.

The source plumbing reserved1call/16385bytes inside the SAME historical
allowance. Cumulative7907calls/262112395bytes leaves93calls/31605bytes
under the original8000calls/262144000bytes. The entire reservation remains
charged. Native runtime spend remains a separately recorded original cap.

The distinct workflow requests minute47 and accepts /quant-quote-tick
only after actual missing-hour/pending-job checks, at most one manual
request/hour. A predecessor's actual paper attempt in the same UTC hour
blocks another attempt EVEN IF IT FAILED. Therefore migration can succeed
without new paper rows until the following hour. No fake gap or paper day,
and controller success alone cannot prove native recovery.

## Splits and cost

No return test or trading split; lab/config.py is inherited unchanged.
**Costs1x/2x/3x: N/A, not zero.** Synthetic fixtures exercise source bytes,
denial persistence, accounting, native append prefixes and migration only.
Full-suite proof before freezing is in prevalidation.json. New source
plumbing and old status inspection are not new profitable paper evidence.

## Gates

Primary gate:100% of union dates have matching presence, exact numerical
value and missingness; latest usable date/value equal; at least1date.
Independent checker must reproduce all comparisons and report digest.
Any mismatch/source error blocks deployment. Additional live operational
acceptance requires real new native receipts/status updates after selection,
verified manifest/content hashes, preserved journal prefixes/spend/blocks,
and no duplicate hour. A skipped or green controller is insufficient.

## Null

No predictive SIGNAL/NOISE decision, stochastic null or seed. Report source
PASS, source mismatch or source failure honestly. A source failure is not
an economic NULL, and source equality cannot admit a trading strategy.

## Multiplicity

0predictive/economic trials. One source pair and one independent audit;
program9784361before registration, read again through program_trials at
execution. The program sum is bookkeeping, not an independent-test count
or across-family significance correction. No unseen outcomes are claimed.

## Evidence lineage and admission (future lanes only)

Operational method M480; parent R420/R422/R428 runtime and R413/R406 paper
rules, R419 acquisition. This feeds source admission only. Prior prices,
paper outcomes and R424/R426 nulls stay unchanged. Fresh sample is only
future actual receipts; the held recent series is NOT out-of-sample alpha.
The frozen gates_at_registration.md hash is included in inputs.json.
Funding unit/cash, own fills, margin, France eligibility, economic costs,
dependent-null control, on-time clocks,10-day trimming, leave-two-coins-out
and80%-power requirements are not fulfilled here. No economic admission,
across-family control, reserved-batch read or real-money authority follows.

## Stop rules

Stop on primary/audit failure, invalid schema/state, provider refusal,
unfinished attempt, inherited source block, unknown spend, original
call/byte/storage ceiling or original end date. Keep all failures/gaps.
No rerun, provider/source substitution, budget reset, expired-window
extension, frozen edit, protected2020/MEXC/reserved read, paid/large pull,
account, credentials, orders, money movement or subagents. Owner places
any future real money only after the unchanged go_real gate; no stakes now.

## Frozen input manifest

f828b079c7277bf5b3524e9aeefc74f3dfe81ba81d9b4873f4028ad84f9fe9c3  experiments/paper_quote_scope_v1/inputs.json
