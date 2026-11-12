# Current operator and durable paper runtime

On **2026-11-07**, the owner said Claude would no longer operate and instructed
Codex to take over the whole project. Issue [#7](https://github.com/SaikiK12/T/issues/7)
records the transfer. Frozen strategy definitions, source rules, unread samples,
existing journal history, acquisition limits and **no real stakes** remain.

**Owner update, 2026-11-09: Codex is no longer available.** The owner told Claude, in the session of 2026-11-09,
that they no longer have Codex.
- **What keeps running:** the selected GitHub workflow (R420, R429 successor) runs on its own schedule until its
  dispatch ends on 2026-11-19 00:00 UTC. It needs no agent to run, but nobody maintains it.
- **Duties without an owner:** the native duties listed below fall to Claude when the owner opens a session:
  - R392's freeze before 11-17 (its read on or after 11-17); done early: frozen and read on 2026-11-10 by the
    owner's 2026-11-09 decision, PARTIAL (`registry/rounds.csv` R392);
  - R404's 11-18 close; its recorder runs from `.github/workflows/claude-book-costs-recorder.yml` once that is on
    the default branch (2026-11-12); DATA_PASS needs >= 40 snapshots with all three venues in the window. The
    close reports two counts: three-venue files on branch `claude/book-costs-data`, and that count plus the six
    lost local snapshots in `experiments/recorders/journal/digests.csv` (only the first proven to have all three
    venues; `experiments/book_costs_v1/DEVIATIONS.md`). Do not run the local task graph's R404 or REC_DIGEST
    tasks while the workflow is the writer (a second writer for the same slots);
  - a registered successor if R406 or R413 locks mature after 11-19.
- **No always-on host:** the chat container sleeps between sessions, so no recorder or daemon runs in between.
- **Check-in:** a one-shot check-in is scheduled in Claude's session for 2026-11-16 11:20 UTC (trigger
  `trig_014YTgYRN5RzBkqzCyaKPoW4`) to prepare R392.

## Research objective clarified by the owner, 2026-11-07

The owner wants substantial net gains and recurring opportunities, with strong
evidence of reliability. A low single-digit annual yield is a benchmark, not
the intended discovery. The owner has not specified a precise monthly target
or loss budget; do not invent either or turn leverage into a claimed edge.
No strategy currently has prospective evidence certifying reliable high gains.

Research prioritizes mechanisms with an economic payer and realistic repeated
execution, including liquidity provision and mechanically constrained cash
flows. Keep full fees, inventory/tail losses, total cash and missing data in
the result. Distinguish a token-balance/revert condition, an observed fill,
positive expected net, opportunity frequency and confidence of profit. None
proves the others. Do not annualize a short pilot or equate a high win rate
with a safe account. Existing frozen papers remain intact as measurements;
new ideas require fresh registered tests and new prospective evidence.

## One selected writer, independent of the chat container

### Native FRED source-scope successor, 2026-11-08

[R429](../experiments/paper_quote_scope_v1/FINDINGS.md) repairs a source
admission shortage: R413/R406 stopped overnight while the controller stayed
green. The original auxiliary allowance still has393202bytes, but the old
full-history FRED reservation needs393217. The native consumer already uses
only400days. One frozen, committed source check passed284/284date/rate/
missingness pairs and its latest usable pair, independently reproduced.

The [successor workflow](../.github/workflows/quant-quote-runtime.yml) was
selected by owner comment6723421811/workflow42495486811, after CI42494500508
and mergec5133669. State62236577 selects R429; its
[selection proof](../experiments/paper_quote_scope_v1/deployment_selection.json)
verifies1298manifest hashes and preserved spend/source blocks. Both papers
skipped the already-attempted15UTC hour; this snapshot proves selection,
not fresh paper data. Canonical manifest.active_contract decides the writer. Its
distinct command is `/quant-quote-tick`, requested cron minute47, report
`data/operations/quant_quote_scope_v1/latest.json`. Earlier immutable
workflows then skip under the same global concurrency group. Never start
a second local loop or infer activation from a code merge.

It inherits ALL spend/source stops, same4096calls/16MiB auxiliary ceiling,
R419Nov14/dispatcherNov19 and64MiB state cap. Only the FRED400-day source
query and its16KiB reservation change. Lighter's jurisdiction block stays.
A prior actual paper attempt in the current UTC hour, including a failure,
prevents another attempt until a fresh hour. Observe new native rows and
receipts after selection before claiming recovery; no old gap is filled.
The baseline seven stale lanes and no proven settled income stay visible.
At16UTC the [actual native audit](../experiments/paper_quote_scope_v1/observations/20261108T16.json)
verified state9632578e/1362manifest hashes/44new wire-content pairs. R413
and R406 genuinely updated at16:01:25/16:01:32UTC, with zero settlements;
R419 captured12GET/173279bytes. Five legacy lanes remain stale. Auxiliary
cumulative837calls/16428076bytes leaves349140 of the original16MiB; this
finite recovery does not renew limits or guarantee subsequent observations.
The [Treasury source note](../research/intake/treasury_benchmark_20261108.md)
distinguishes the frozen DTB3 reference from an investable cash benchmark;
do not label a mean discount quote as the owner's realized T-bill return.

### Bounded participant-source successor

**Observed activation:** reviewed merge b4063110 was activated by workflow
42411122446. Canonical state 34bed188 selects R428; [deployment proof](../experiments/participant_capture_v1/deployment.json)
verifies 656 file hashes and actual 20:00 UTC R419/R413/R406 receipts. Papers updated
at 20:27 UTC, with zero settlements. The Lighter qualification returned a
jurisdiction refusal (HTTP 400/code 20558), with 0 stream frames; SOURCE_BLOCK prevents
future acquisition attempts. Its raw refusal/reservation remains. Do not
try alternate query/region/header/provider/REST access around that refusal.
Other native papers continue under their original finite limits; this is
not all-project recovery or proof of paper income.

[R428](../experiments/participant_capture_v1/PREREG.md) adds a finite raw
Lighter WTI/Brent ticker/trade campaign for M441/M474. Its source-only
windows are Nov7qualification65seconds and Nov8/9/10observations180seconds
each, at the first selected cycle inside the frozen eligible start windows.
These are short observations, not full trading days or R367coverage. Raw
source strings, account before-state and original receive clocks are kept;
no markout/return/PnL is scored by this collector.

The [new workflow](../.github/workflows/quant-participant-runtime.yml) stays
inactive until the reviewed owner command `/quant-participant-migrate`
selects R428 in the canonical manifest. While R428 is selected, its operational
report is `data/operations/quant_participant_v1/latest.json` and its distinct
manual command is `/quant-participant-tick`; the earlier workflows skip.
Its requested cron minute37and the unchanged global concurrency group
reduce overlap. GitHub delay, pending replacement or source failure can still
leave a gap; actual receipts remain the evidence.

Existing papers retain their native scripts/journals, actual prior-hour
attempt guards, all old source blocks and original16MiB auxiliary ceiling.
The new source separately reserves the entire32calls/8MiB within the original
historical allowance, conservatively7851calls/259609578bytes including all
old reservations. It cannot renew that grant, the native R419Nov14end, the
dispatcher Nov19end or the64MiB state cap. No source is activated or paper
income proved by a green code test alone. The canonical active_contract,
last_report and native source receipts decide which of these contracts is
actually operating; default-branch journal copies remain historical seeds.

The canonical `manifest.json` on `codex/quant-runtime-state` selects the
**active_contract** and **last_report**. Read those fields for the current
writer and its native receipt. R420 was the first deployed contract. Its
[R422 priority successor](../experiments/paper_priority_v1/FINDINGS.md) was
activated on2026-11-07 at14UTC through
[Priority paper runtime](../.github/workflows/quant-paper-priority.yml).
The transition is published in state b9538b958fcc901604a759855afd3895ffd0932b;
R420 now skips source work and only R422 writes. Both immutable workflows use the same
global concurrency group; no second local loop.

R422 admits only R419/R413/R406 and retains the original16MiB auxiliary byte
ceiling, all old spend/blocks and native R419 limits. Smaller per-endpoint wire
reservations and standard gzip content negotiation protect paper work from
the paused broad recorders. Its newly frozen4096total-call limit includes the
old calls; this is no budget reset. Gzip decoding has its own4MiB limit and
records both wire/content hashes. The remaining original bytes can still bind.

After successful CI/merge, the operational owner used the exact
`/quant-paper-migrate` comment on issue7 for the initial serialized transition.
That workflow checks the completed old host and publishes migration, then a
prepared hour, before any HTTP. `/quant-tick` subsequently reaches the selected
contract. Never fake GITHUB_ACTIONS locally or write a journal by hand.

At its first completed cycle, R422 verified fresh native R413/R406 statuses
at14:09UTC. Its42new requests used35,139wire bytes, retaining old spend for a
total15,011,954of16,777,216charged auxiliary bytes. The [deployment receipt](../experiments/paper_priority_v1/deployment.json)
binds282file hashes and42wire/content pairs. This is observed source health,
not proof of paper profit, future uptime or all-project recovery.

A later [read-only observation](../experiments/paper_priority_v1/observations/20261107T17.json)
verifies state89cc3a8f after workflow42398223226: all462manifested file hashes
and168wire/content pairs match. Native papers updated at17:50UTC, with
zero settlements; R419 has its17UTC source packet. Cumulative auxiliary
spend is358calls/15117067bytes, leaving1660149bytes of the same original
ceiling. Five legacy lanes remain stale. These are observed source receipts,
not proof that every lane runs or that the account earns money.

The paragraphs below retain R420's original scope/evidence and ceilings.

Originally [Paper lab runtime](../.github/workflows/quant-runtime.yml) was the
sole admitted writer. Its immutable workflow is scheduled at minute17 each UTC hour; `workflow_dispatch` and the
owner's exact `/quant-tick` comment on issue7 use the same concurrency group.
The workflow runs reviewed default-branch code, never an unreviewed PR head.
GitHub Actions serializes runs without cancelling the active writer. No local
cron, second forward loop or daemon is installed by this takeover.

The repository is public, its default branch is `claude/yo-9a1k5w`, and only
standard Ubuntu runners are used. GitHub's [billing documentation](https://docs.github.com/en/actions/concepts/billing-and-usage)
(undated, accessed **2026-11-07**, relevant public-runner clause) states:
“GitHub Actions usage is free for standard GitHub-hosted runners in public repositories”.
No paid runner, owner secret, exchange account, API key or money movement.
The ordinary ephemeral Actions token publishes repository state only.

GitHub's [event documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
(undated, same access, partial schedule/issue-comment sections) warns that cron
can be delayed or dropped under load and public schedules can be disabled after
inactivity. A schedule is not continuous-host proof. Actual receipt times and
missed slots remain visible; no backdating or invented on-time days.

## Canonical operational evidence

Live state is persisted on branch
[`codex/quant-runtime-state`](https://github.com/SaikiK12/T/tree/codex/quant-runtime-state),
through `manifest.json` and `state/<original repository-relative path>`.
R420's controller receipt is
`state/data/operations/quant_takeover_v1/latest.json`; R422 uses
`state/data/operations/quant_priority_v1/latest.json`. The manifest's current
`last_report` is authoritative. Each per-hour run directory
holds source task logs. Native paper journals retain their original schemas.
Code-branch journal copies remain the historical seed, not a live heartbeat.
The methods queue and round registry on the default branch remain canonical.

The first actual cycle, [42337055267](https://github.com/SaikiK12/T/actions/runs/42337055267),
completed on **2026-11-07 04:08 UTC** and published both its before-HTTP
checkpoint and final state. The [native deployment receipt](../experiments/ops_takeover_v1/deployment.json)
binds the state commit, verified hashes and individual source outcomes. R419,
R413/R406 and MEXC/Deribit captures produced native output; Cboe skipped its
closed window; DefiLlama exceeded its response cap and remains stopped.
This is one observed cycle, not proof of future schedule execution or a full
private-container recovery. `manifest.meaning` retains its bootstrap text;
use the current native report and `bootstrap` flag for deployment status.

A new runner restores the manifested state before any source call. Missing or
corrupt state fails closed rather than resetting budgets. Hashes, append-only
prefixes, path safety and immutable raw captures are checked before copying.
Original cache mtimes are preserved. Bootstrap T-bill caches are conservatively
aged so a Git checkout cannot masquerade as a fresh FRED response. Only the
native scripts write their financial journals. State publication uses normal
fast-forward Git pushes; a competing remote writer causes a publish failure.

`HOUR_ALREADY_RESERVED` consumes an attempted UTC hour even after a crash. The
transport fence reserves bytes before network, retains uncertain crash spend,
preserves response bodies unchanged and records their byte hashes. Denied
sources persist across runs. Authentication, browser-UA spoofing, redirects,
HTML/bot responses and unregistered endpoints stop the child before legacy
retry handlers can repeat them. Known denied Binance futures/OKX/One Trading/
FairX hosts are not moved to GitHub's region as an access workaround.

## Finite scope and current blockers

[R420](../experiments/ops_takeover_v1/PREREG.md) admits the unchanged R419 paired
capture, R413 Boros paper locks, R406 Deribit paper locks, current MEXC ticker,
Deribit option-chain, Cboe pre/post-session and DefiLlama calendar recorders.
Its closed config names every task and preserved state prefix. R419 retains
its own Nov14 end and native caps; additional external guards can only stop it
earlier. Auxiliary sources share **512 calls / 16MiB client-body** across the
whole takeover campaign, not per hour; each response has a **2MiB** ceiling.
The first cycle consumed about6.2MB of that auxiliary byte allowance, including
the over-limit calendar debit. These are finite pilot ceilings and may halt
sources after only a few cycles. No schedule or later research turn renews them.
This actually bound by the12UTC observation on Nov7:190calls and14,976,815bytes,
with native paper status last updated08:08UTC. R422's successor preserves that
spend and the same byte ceiling; it does not make the old papers continuous
through their missed observations.
R419's admitted native ceiling is **1,351 calls / 16MiB**, with **1MiB** per
response; its own frozen transport and stricter source caps run intact. Stored state is capped
at **64MiB**. R420 dispatch ends **2026-11-19 00:00 UTC**; only health reporting
continues after its source window. No historical budget is renewed.

Before any market request, a prepared-hour reservation is pushed to the
canonical branch. A lost predecessor therefore blocks a later host even when
its final publication never arrived; unknown spend is not reset. Partial files
and cut journals are preserved and require reconciliation. The canonical
active_contract marker allows a reviewed successor to retire an immutable old
workflow without editing frozen files.

The controller inventories the whole existing task graph. Missing warm
datasets, unsafe legacy transport, unqualified whole-universe capture volume
and continuous-recorder requirements stay `BLOCKED`. In particular R285/R415
cannot gain a fresh account day from absent upstream family data. An hourly
ephemeral job cannot replace the continuous tape required by R367 or the
event-time daemons. Restarting those needs their state and an appropriate
qualified host/source contract; recorded gaps cannot be repaired into live data.

The old archive index contains HFT paths predominantly for Oct29, plus fragments
around it. It does not establish the three usable full days R367 requires.
Downloading its large chunks blindly is not a solution. The indexed archive
does not contain `daily_v2`, `metrics_full` or `fundingRate`, and the inspected
index has no `recorders/book_costs` files. Recheck actual newer source metadata
before any minimal, explicitly authorized large recovery. Do not silently
recreate a warm historical panel through thousands of API requests.

Native duties remain: R367's Nov8 end; R392 batch3 freeze **before Nov17** (its
missing registration/spec was flagged); R404's Nov18 close before M469; M486
needs about120 sessions, and R416 is not retested. The existing hourly
`Quant research loop` task was updated, not duplicated. It resolves these
dependencies and advances reviewed registered successors, without writing live
journals outside this workflow or launching subagents.

## What success means

A green workflow means the controller finished and persisted its state. Each
task has its own exit result and each lane its own receipt-age assessment.
`all_project_lanes_running` remains false while dependencies are blocked.
No controller status admits alpha, capacity, a paper gain or real-money use.
The native strategies report their own frozen costs and decisions; R420's
engineering costs1x/2x/3x are N/A, not zero. Changes to a frozen source, budget,
code or idea require a separately registered successor.
