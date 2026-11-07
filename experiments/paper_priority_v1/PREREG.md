# PREREG: paper_priority_v1, inherited spend and priority native papers

Freeze and commit this closed protocol before activation or any actual HTTP
content experiment. Never edit a frozen file. Changed behavior needs a new id.

- **Registry id:** R422
- **Owner (single writer):** serialized GitHub Actions Priority paper runtime, supervised by Codex
- **Date registered (UTC):** 2026-11-07
- **Claim:** issue7 comment6707586720; follow-up to the observed R420 pilot stop

## Question
Can the native Boros/Deribit paper tasks resume within R420's remaining
auxiliary byte ceiling by ordinary gzip content negotiation, small source
reservations and recorder priority, while preserving previous spend, source
stops and one-writer/host-loss safety?

## Universe
Exactly three native tasks: R419 paired raw capture, R413 Boros paper and R406
Deribit paper. Their scripts, decisions and financial journals remain native.
Broad ticker/7-coin option-chain/Cboe/unlock captures are paused pending a
qualified independent scope: they cannot drain the paper remainder. The whole
task graph and stale lanes remain reported, never called all-project healthy.
`config.json` fixes all tasks, arguments, URLs, caps, state paths and dates.

## Data
No new historical market source. This is an operational transport/migration
study with **0 predictive trials**. The old R420 auxiliary START/END/BLOCK
journal at state commit83e432544fc2e66a6020eb3e623f6f1b4eadff98 is copied
unchanged as `baseline_aux_requests.jsonl`: **190** calls, **14,976,815**
charged bytes. Its hash and original-path provenance are in the baseline
receipt. Counts and resource usage were already admitted by R420; no prices,
returns or new live compression outcome were inspected for this protocol.

The live old ledger must exist, be complete and begin with the exact frozen
baseline. Its full records, including any subsequent appended spend and old
uncertain reservations, precede every new request. There is no fresh zero-based
budget. The native R419 ledger and transport remain unchanged and separate.

## Feature lineage and point-in-time availability

| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| Inherited resource spend | old and new START/END/BLOCK records | local source ledger, wire/client bytes and calls | whole original campaign across migration/restarts | START before HTTP, END after bounded body | dispatch gate only | complete prior prefix plus all new records | missing/cut/divergent ledger blocks; old unknown START retains its original cap |
| Logical native content | exact HTTP wire bytes and Content-Encoding | same frozen public Boros/Deribit/FRED/MEXC routes | one bounded current GET, no retry/fallback endpoint | actual request/response receipt; wire and content SHA256 | native code decides availability | same native source, not a new alpha sample | decode standard gzip only, no JSON reserialization or numeric transform; malformed/error/HTML blocks |
| Native paper decisions | unchanged R413/R406 source content and rules | Boros/Deribit paper, native units | native ticks and settlement clocks | native original journals, not rewritten | native rules only | committed seed plus preserved native outputs; private-host gaps unproved | no invented history, completed day or cash gain |
| Host continuity | canonical manifest, immutable snapshots and prepared-hour checkpoint | one Git state branch and concurrency group | migration then one attempted UTC hour | committed before any HTTP | checked before dispatch | same state lineage, R420 and R422 prefix retained | unfinished old host prevents migration; unfinished new host prevents another attempt |
| Source-health age | native status timestamps and individual child exits | existing lanes, receipt age only | current observation | exact native status time | monitoring only | old seed is not a live heartbeat | stale/error/missing remains explicit even with controller exit0 |

## Rule or search space
One new immutable workflow `.github/workflows/quant-paper-priority.yml`, same
global concurrency group `quant-runtime-single-writer`, no cancellation of an
active writer. Reviewed default branch only. Ordinary cron/owner `/quant-tick`
dispatch requires active_contractR422. The owner's exact `/quant-paper-migrate`
on issue7 permits the initial serialized R420-to-R422 migration after review.
No source request in migration. Restore/check the old completed dispatch,
preserve files and budgets, write migration receipt, selectR422 and publish
the transition before preparing a source hour. Old immutable R420 then skips.

The new adapter explicitly composes R420's unchanged restore/checkpoint/execute
primitives with R422's lane, verifier, child command and HTTP fence. It edits
no imported file. The new phase shares the legacy local writer lock and same
canonical Git state branch. It verifies/publishes its own prepared hour before
HTTP. A successful legacy paper attempt in the same UTC hour is skipped rather
than appended twice; R419's own source-hour guard remains authoritative.

Auxiliary **byte ceiling remains16MiB**, including all14,976,815old bytes and
any later old spend. Actual remaining space can be less than a request's
reservation; then the source stops. Total call ceiling is newly frozen at
**4,096**, including old190calls, allowing more smaller public responses inside
the SAME byte cap. This replaces R420's self-imposed512-call limit by a new
registered contract; it resets no count or historical/R401/R402 allowance.
No large object, bulk history, paid endpoint, account or credentials.

Wire reservations per fixed URL prefix, in config: Boros assets32KiB,
markets96KiB, book16KiB; Deribit instruments/books32KiB; FRED/MEXC funding
board384KiB. Maximum decoded content **4MiB** separately. Request header
Accept-Encoding:gzip is ordinary HTTP negotiation, never a browser User-Agent
or denial workaround. Identity responses also work within the same cap.
No fallback request if gzip/identity is unusable. Raw bounded wire bytes are
preserved in an immutable archive; exact wire and decoded content hashes and
byte counts are recorded. Content decoding changes no number/string/row.

Reserve cap+1 before HTTP. Unknown failure keeps that reservation, including
old larger caps from R420. Complete responses charge exact wire bytes. Denied
HTTP401/403/404/429/451, redirects, HTML, invalid JSON and explicit public JSON
errors persist source stops. Prior blocks are inherited. No auth/cookies,
spoofing, redirected request or source outside the fixed public GET scope.
No old denied Binance futures/OKX/One Trading/FairX host is moved to another
region. R419 delegates intact to its native frozen transport and limits.

Source dates remain bounded: **2026-11-07 13:00UTC..2026-11-19 00:00UTC**,
R419 separately endsNov14. The state-size ceiling remains **64MiB**. No
counter, window or allowance is renewed by a later cron/research invocation.
No continuous recorder, missing warm panel or reserved read is supplied here.

## Splits and cost
No predictor, return split, alpha test or financial score. **Costs1x/2x/3x:
N/A, not0** for R422. Native paper rules retain their own frozen financial
fees/decisions. Actual wire/decoded counts are operational evidence, not PnL.

## Gates
Synthetic tests, full repository suite, integrity, staged catalogs and
latest-head CI before merging/activation. Test inherited spend/source stops,
unknown larger reservations, both body-size limits, exact content hashes,
failed/cut/denied bodies, auth/spoof/redirect refusal and a composed synthetic
migration/checkpoint/finish sequence. A real source call starts only after the
protocol/input closure is committed and the reviewed workflow is integrated.
Verify actual migration, checkpoint and per-task receipts; an enabled schedule
or process exit0 is not proof of live paper health or a profitable strategy.

## Null
Failure, budget stop, source denial, malformed state/content or unchanged stale
paper stays explicit. No zero return, fresh day or successful data capture is
substituted. An exhausted remaining pilot can still stop before Nov19; this
protocol promises no indefinite free collection or extra byte grant.

## Multiplicity
**0 predictive trials**; current program total **9,784,345** via
`registry.program_trials('registry/rounds.csv')`. No new paper or strategy
decision opportunity is admitted by this engineering registration. Native
strategy multiplicity remains unchanged; no program-wide statistical claim.

## Evidence lineage and admission
Direct parent R420, with its exact closed input closure; unchanged native R419,
R413/R406 parents. R421's execution costs are not remeasured here. The copied
current GATES is hashed. No on-time alpha days, dependent-null calibration,
trimming/leave-two-out or80%-power calculation: no return series. Source and
legal access, funding units/cash/marks, executable capacity, real money and
missing private-host continuity remain unproved. No account/order gate met.

## Stop rules
No source before committed activation/checkpoint, outside dates or beyond
either accumulated ceiling. No missing-counter reset, duplicate writer/hour,
deleted journal, frozen edit, new source/feature/scope after the outcome or
extra broad recorder. Every source/header/cap/schedule change gets a new id.
Failed source bodies/partial files remain; corruption requires reconciliation,
not a new empty state. Actual findings and blockers live in native FINDINGS.

## Frozen input manifest

df5185176648c04f74593913a195b193df8f357a7c9d431b300814f1b6bfa2e7  experiments/paper_priority_v1/inputs.json
