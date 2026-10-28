# PREREG: incremental first-seen state without changing economic decisions

- **Registry id:** R360
- **Owner (single writer):** Codex
- **Date registered (UTC):** 2026-10-28
- Existing M409 account/execution-input dependency; consolidation draft PR56.
- Pre-implementation issue7 claim:6466521041. Claude R355/R356 stays read-only.

## Question and binding constraint

R359 issued four original controls on actually received public frames. Its exit
decision and evaluation required300.983054/348.115149ms of processing/IO and
missed the unchanged250ms issue bound. This is local controller work, not an
isolated exchange delay. Rebuilding all old depth states and serializing old
raw prefixes at every deadline is avoidable work. Does a receive-time state
adapter preserve the exact source/financial contract while reducing deadline
work, and what additional service does it require between deadlines?

R310/R311 remain unchanged:1318actual missing funding events repaired,12models
in calibration,224/273common validation days; the preselected policy loses at
registered2x/3xcosts. No repeat of that incomplete dataset, gap/tradability
relaxation, validation winner selection, leverage-up or new prediction model.
This is necessary implementation and finite economic equivalence validation,
not an alpha search or a replacement for unknown funding/session/access data.

## Immutable inputs and finite budget

Use ONLY the2352sealed R359first-seen frames, original public metadata,
connection/unusable boundaries, clocks, plans, results and journal bytes from
source result commit3a8a0e7121b2bf23d5f3fecf8921ea4b12be0a50 and raw seal
8516653ba8e4c0ec0f5a37f599ebf3752d4f751e. Their exact identities are in the
bound manifest below. Preserve raw sources, frozen code and original outputs.
No future source or newly fetched market input is used by this experiment.

Exactly0new market/source requests,0new collection and0new model downloads.
Historical acquisition remains one accumulated7757/8000requests and reported
229.85/250MiB. R359's closed capture scope cannot be reset or reused. Any later
live capture needs its own finite frozen protocol and declared acquisition.

One scheduled offline run, five paired repetitions of two fixed engineering
profiles, alternating baseline/incremental order by repetition. All runs and
failures retained; no fastest-run selection or repetition after a failure to
improve results. A created run_started.json closes the single run reservation.
Maximum180s measured-run wall budget and655360KiB shared process RSS, checked
between profiles/checkpoints. Full unittest validation is separate from the
benchmark budget. A defect after freeze needs a separately registered correction.

## Implementation contract

The baseline is byte-unchanged R359LivePairControl: rebuild DepthReplay from
the entire then-received prefix on each original stage. The candidate is new
lab/incremental_pair_control.py. Each source receipt is copied into immutable
scalar fields plus exact canonical bytes. Original decoding, atomic nonce/
offset/epoch updates, corruption poisoning and liquidity first-seen clocks
advance once on that source receipt. Capacity remains20000messages and8MiB
decoded raw payload per venue,256KiB per frame; a capacity refusal cannot reset
the prefix. No future queue, historical backfill or new connection epoch in an
existing adapter. Equal clock ties must respect the old canonical sort order.

The frozen control is loaded into an instance-private module namespace and
only its DepthReplay/encoded dependencies bind to owned state/immutable bytes.
The shared module is never monkeypatched. Original financial/action/receipt
methods and R359output identity stay unchanged; an outer R360report identifies
this offline validation. No duplicate accounting implementation or invented
new strategy observations. Callers must deliver then-received frames before
issuing a stage; supplying a frame from the future cannot backdate a decision.

All existing freshness, clock-step, source/receive skew, depth, nonce/epoch,
market/API/activity, minimum/maximum quantity and original first-seen rules
remain. Empty, corrupt, duplicated, invalid, inactive, disconnected and thin
states remain visible. A connection unusable boundary precedes slow close;
it cannot be moved later or reopened. Source/metadata/config mutation after
copy cannot mutate cached input identity. No background process or socket is
started; collectors and Claude forward journals are untouched.

## Fixed semantic and economic comparisons

Use ALL four ORIGINAL R359decision/evaluation clocks, supplied original issued
clocks and final report clock. No outcome-dependent change to entry/exit time,
250ms lateness,300ms minimum modeled delay, capital, instrument, direction,
quantity, fee or risk rule. Actual measured service time is reported separately
from those old source/account clocks. Offline service cannot convert either
late R359exit to on-time evidence. Twelve R359diagnostic variants remain counted
in R359only; this round has0new alpha variants,0new prospective tickets/days.
The two fixed engineering profiles are explicitly enumerated, not hidden trials.

For EACH of the ten profile runs require exact original complete result bytes
and all38native/reference-journal and receipt files, including late/inactive/
blocked/unknown outputs and native account reopen/restart identity. Preserve
36cost cells:6symbols x2directions x1x/2x/3xcosts; original fixed inventory,
250quote leg budget,5000USDT MEXC +5000USDC Lighter per alternative. Those
alternatives are not combined into a larger portfolio. Spread is embedded once;
old10/4bp fee reserves are scenarios, not owner entitlements. XPD remains the
metal/session negative control. Reference cash uses the full10000capital.

Independent standard-library Fraction arithmetic checks every complete closed
price-minus-fee component from original book levels, signed original quantity,
fixed1x/2x/3xmid-relative execution stresses, entry/exit fee amounts and native
asset accounts. Also check break-even funding component, exact flattening and
unchanged source/action clocks. These are conditional shown-book model prices,
not actual matching, fills or expected executable returns. Funding_cash,
full_net_pnl/full_account_nav/actual_expected_net stay UNKNOWN. Original explicit
1:1USDT/USDC FX scenario remains a scenario. Session/access, actual account
fees/margin/liquidation, intrahold risk and full funding cash are unqualified.

In addition, fix64evenly spaced frame-prefix counts using ceil(i*2352/64),
i=1..64, including all ties at the selected monotonic clock. At each compare
all6symbols xfull/top_only profiles against freshly reconstructed original
DepthReplay: rows, full returned books, errors and assembly counters. All768
row/book comparisons and128counter comparisons must agree. This is an
equivalence oracle using the same frozen venue parser, NOT an independent
venue parser or predictive validation sample.

## Timing, controls and decision rule

Measure actual perf_counter_ns wall service on this execution environment for
each source receipt, every four-stage call including original journal IO,
constructor, final report and whole run; retain process CPU and shared RSS
high water. File loading/decompression precedes both profiles and is excluded
from stage service. Report all five stage samples, median, nearest-rank p95/
p99 and maximum; report all preprocessing totals/p99/max. Do not hide moved
receive work or claim isolated memory attribution from a shared high water.

Report an OLD-arrival serial-service illustration: start each measured task
at max(old first-seen/stage clock, previous service finish), then add its
measured duration. Retain source-queue lag and stage finish lag. This is a
local capacity diagnostic, not a changed account clock, live schedulability
proof, venue latency measurement or a claim that different live receive work
would have received the same future frames on time. No statistical edge claim
or independent-day confidence interval follows from five hardware repetitions.
Dependent-null/multiplicity and calibrated strategy uncertainty remain required
for any future alpha protocol, rather than being inferred from these controls.

Semantic/account equivalence must pass before considering integration in a
separately frozen future capture. Report whether all measured candidate stage
durations fall within250ms and compare every paired sample; no optional tuning
after measurement. A failure/null is retained and rules stay fixed. Faster
offline work alone authorizes neither activation nor a new strategy paper day.

Before committing new lab code run complete unittest discovery. Twelve invented
tests cover every prefix/noop/idle/profile, corrupt/conflicting/regressing data,
nonce gaps, clock steps, disconnect/epoch refusal, immutable copied inputs,
capacity/backfill refusal, exact journal/money equivalence, thin/missed/late
controls, private-instance isolation, future refusal and an independent money
checker rejecting corrupted invented cash. Record all actual test outcomes.

## Bound direct files

- config.json SHA256:faf28acbffd2831a677cb857fb66aa89b75368e06265f1605c2bbf28a0759350
- code_inputs.json SHA256:6626713d4669bff01446f18ce7986c4bf6bb0d6674e8d96144768c04b2e8de44
- input_identity.json SHA256:e7e2fb869d49fe2beca5548165eb6d14b4cbe8324b6beb86cda6b9186788ab07

Freeze this spec with lab.prereg.freeze(); commit spec, code and manifests
BEFORE the benchmark or its source-state/economic outcome checks. The runner
verifies the frozen hashes and committed input identity before and after work.
