# Organisation, operations and sustainability review (reviewer B)

Read-only review, 2026-11-16. Evidence: the fact pack, AGENTS.md, README.md, docs/ROOM.md, HANDOVER.md, OPERATIONS.md, guides/OPERATIONS.md, handover/SCHEDULED_CHECKS.md, loop/STATE.md, heads of DIRECTION.md and PANEL.md, .github/workflows/, registry/rounds.csv and `git log`. Speculation is labelled.

## 1. The actual operating system

**Writers.** Commits in the last 7 days: github-actions[bot] 225, Claude 163, Kiro Agent 38, SaikiK12 3, openhands 2 (`git log --since='7 days ago'`). Bots are the largest writer, ahead of every agent. The 27 scheduled workflows in `.github/workflows/` (29 have `workflow_dispatch`) are the only durable runner. They write recorder data to `claude/*-data` branches and journals to the default branch `claude/yo-9a1k5w`. Four Codex `quant-*` workflows write to `codex/quant-runtime-state`.

**Where state lives.**
- Decisions and science: `registry/rounds.csv` (275 rows), `registry/methods.csv` (444 rows), frozen PREREGs and FINDINGS under `experiments/`.
- Live data and journals: data branches and `codex/quant-runtime-state`.
- Coordination: issue #7 (88-line ROOM.md protocol, 600+ comments), plus issue #71 and PR #8.
- Narrative state: about 10 docs that each claim to describe "now" (see section 2).

**Single points of failure.**
1. **Ephemeral containers.** `docs/HANDOVER.md` says "the chat container sleeps between sessions, so no recorder or daemon runs in between". `docs/DIRECTION.md` records a roughly 3.1-day outage on 10-30 to 11-02. Any lane whose writer was a container daemon has no writer now.
2. **One scheduled operator who is gone.** README.md still calls Codex "the single scheduled writer". `docs/OPERATIONS.md` and `docs/HANDOVER.md` say the owner reported on 2026-11-09 that Codex is unavailable, and that its dispatch ends 2026-11-19 00:00 UTC. In three days the R420, R429 and R428 runtime workflows stop with nobody assigned. This is the nearest hard cliff.
3. **Default branch equals the bot's push branch.** `claude/yo-9a1k5w` is the default branch and every recorder pushes to it. This caused the email flood (PR #1 head = default branch) and the 17 `action_required` CI runs. Closing PR #1 fixed that symptom. The structural cause remains: any future PR opened from the default branch, or any notification rule, reproduces it. About 88 bot commits in 48 hours also make the default branch hard to review.
4. **GitHub Actions.** It is the only durable runner, and the roughly 300 runs a day are an estimate from the crons. Quota, secret changes, a scheduled-workflow auto-disable after 60 days of repo inactivity, or an owner account problem would silence all forward evidence at once. Check the 60-day rule; I am working from general knowledge.
5. **Owner attention.** The owner is non-technical, French-speaking, and gets email for pushes. Notification volume is the main attention drain. There are two ways to fail: the owner mutes everything and misses a real decision, or the owner is asked to check things they cannot judge.
6. **Claude cloud sessions.** The hourly wake-up is paused. Duties assigned to "Claude when the owner opens a session" (R404 close on 11-18, R392 reads) depend on someone opening a session. The one-shot check-in `trig_014YT...` for 11-16 11:20 is also session-bound.

**Dependency chain (condensed).** frozen PREREG, then a workflow, then data branch or journal, then FINDINGS, then a row in rounds.csv, then a methods.csv status, then panel and README catalogs. The panel is rebuilt by a tick that has stopped (last rebuilt 2026-11-14 05:02), so the tail of the chain is already stale.

## 2. Sources of truth

Documents that claim to say "what is current":

| Document | Last stated date | State |
|---|---|---|
| README.md "Current status" | 2026-11-07 | **Contradicts** OPERATIONS and HANDOVER: still says Codex is the single scheduled writer |
| docs/OPERATIONS.md | 11-07 top, 11-09 patch, file touched 11-12 | Best operational page, but it carries a pending check-in that has now passed |
| docs/HANDOVER.md | 10-29 base, 11-07 and 11-09 overlays | Overlays on a 250-line older doc; the first lines are fresh, the body is historical |
| docs/ROOM.md | 11-07 | Says Codex is operational owner; 88 lines of dated overlays; stale |
| docs/guides/OPERATIONS.md | undated | Duplicates the name and part of the scope of docs/OPERATIONS.md |
| docs/handover/SCHEDULED_CHECKS.md | 11-04 review, 11-07 banner | Marked "inactive historical evidence" but still links as an operations doc |
| docs/loop/STATE.md | 11-12 | 644 lines of tick log; the loop it serves is paused |
| docs/DIRECTION.md | "Now" dated 10-28, 900 lines | Self-declares as a snapshot, but README's start table points to it for priorities |
| docs/PANEL.md | 11-14 05:02 | Generated, stale by 2 days, and says it is rebuilt "at the end of each tick" |
| docs/EDGE_SCOREBOARD.md, GATES.md | R363 / 11-10 | Partial |
| AGENTS.md | 10-24 | Correct and authoritative on rules |

At least five documents give an operator or "what's next" answer, and three of them (README, ROOM, HANDOVER top) disagree with the most recent owner fact (Codex gone, 11-09). Two files are both called OPERATIONS.md. AGENTS.md already defines the right principle (one authority per fact) but the narrative layer does not follow it.

**Minimal authority set (proposal).**
1. `AGENTS.md`: rules and autonomy limits.
2. `registry/rounds.csv` and `registry/methods.csv`: science state (already authoritative).
3. One new short generated file, `docs/STATUS.md` (about 40 lines): who writes, which workflows are live, which dates are coming, last verified time. Built from rounds.csv, the workflow files and a small hand-set field "operator". It replaces README "Current status", the top of ROOM, OPERATIONS and the panel header.
4. Per-lane PREREG and FINDINGS.
5. Issue #7 as a conversation log only, never as the state.

Everything else (DIRECTION, loop/STATE, SCHEDULED_CHECKS, HANDOVER body, the 40-odd research and audit docs) is labelled "historical evidence". They are not moved or deleted: frozen links stay valid. A banner or a README pointer is enough.

## 3. Growth versus maintenance

**What one lane costs to keep alive** (my estimate from the repo layout):
- A workflow file: 1 per forward lane family (30 now), with a cron, a concurrency group and data-branch push logic.
- A frozen PREREG plus inputs, and a journal that must be append-only and verified.
- A rounds.csv row, a methods.csv row, and sometimes aliases.
- Mentions in generated catalogs (README folders, experiments/README, PANEL).
- A decision date that someone must read on that day. The dated list is long: 2027-02-01, 02-08, 02-13, 05-15, 11-13, and R371's 125-day futility read.
- Tests (736 test files, about 3,300 cases). Four failures and 12 errors in the fast suite are pinned by frozen lanes. That baseline noise hides real regressions.

Rough cost per lane: 4-6 files created, 1 scheduled job, and 1-3 future human or agent reads. At 67 open lanes in 4 weeks of high output (170 rows in October, 102 in the first 16 days of November), this exceeds what the owner and the remaining agents can read. The program counter shows 9.8M trials, so the multiplicity accounting matters more as the number of lanes grows.

**Is 67 sustainable?** No, not as a count of "things that need attention". It is probably sustainable as a count of passive recorders, since most are bot-run. The real problem is that RUNNING and REGISTERED mix very different things:
- (a) lanes with a live GitHub workflow writer;
- (b) lanes whose daemon died with a container (the fact pack says several);
- (c) lanes registered but never started;
- (d) lanes whose result is already decided but whose row was not closed (the 11-09 hunt-mode wave closed rows by orchestrator hand, which is fragile).
- The registry has no field for "who or what writes this lane today".

**Process to close or sleep lanes without breaking freezes** (not verdicts):
1. Add, append-only, a `liveness` journal (new file `registry/lane_liveness.csv`, one row per lane per audit date: writer = workflow name or none, last data timestamp, next decision date). Never edit old rounds rows.
2. For each RUNNING row run a mechanical test: does a workflow named in the PREREG exist, has it produced data in the last N days. A row with no writer and no data for 14 days gets an appended status event "DORMANT, writer lost" in the journal and is excluded from the "open lanes" count. The frozen PREREG is untouched; a successor lane id is needed only if someone wants to restart it with a changed rule (AGENTS.md rule 2).
3. A lane whose decision date has passed without a read gets an appended "EXPIRED UNREAD" event. It keeps its data but stops counting against attention.
4. The owner's own rule "a null is a result" applies: DORMANT and EXPIRED are operational states, not verdicts, and a null verdict still needs the frozen read.

Whether these appended events satisfy rule 3 (append-only journals) is the one point I could not confirm from the rules text alone; the safest design is a new journal rather than touching rounds.csv. Flag this to the owner as a rule interpretation.

## 4. Multi-agent coordination

Issue #7 as the live coordination channel is not sustainable. 600+ comments cannot be read, and the real claim state is inferred by each agent from the tail. Evidence of the failure: ids R489 and R493-R496 are claimed on unmerged branches while this branch is at R482; four OpenHands drafts (#97-#100) sit on claude/yo-9a1k5w; PR #98 edits AGENTS.md, which the lab treats as the highest-authority file and which should never be changed by an unreviewed agent draft. Several agents (Claude, Kiro, OpenHands, the "Free AI Coding Agent" trigger) can write at once, and four of them cannot see each other's un-pushed work.

**Lightweight protocol (proposal).**
1. **Claims live in a file, not in comments.** `registry/claims.csv`, append-only: id range, agent, branch, claimed at, expiry (default 72 h). One agent (or a bot step in CI) allocates R-ids. An id claimed on a branch that is not merged within the expiry is released automatically by a documented rule, so ids cannot be stranded.
2. **One integration worktree and one reviewer role per week.** A single agent merges, in a batch, the compatible drafts (already stated in AGENTS.md: group work in the consolidation review).
3. **Draft PR limit.** At most 2 open draft PRs per agent. A draft with no push for 7 days is closed with a comment, reopenable.
4. **Issue #7 becomes a short weekly digest** (one pinned comment, edited), plus a new closed-by-convention issue per week for chatter. Old comments stay.
5. **Protected files.** AGENTS.md, frozen PREREGs, registry journals and `.github/workflows/` require the owner's explicit approval to merge. PR #98 should not merge on an agent's say-so.
6. **Stop the default-branch push pattern.** Move bot commits to a dedicated `state` branch, or change the default branch to a quiet one, so that no PR head ever equals the branch the bots write to. This is a repo setting plus a path change in about 27 workflows; plan it as one reviewed change, not piecemeal.

## 5. Sustainability charter (proposed)

**Structure.** Keep `experiments/`, `registry/`, `lab/`, `scripts/`, `tests/`, `research/`. Add `docs/STATUS.md` (generated) and a `docs/ARCHIVE_INDEX.md` pointing to historical documents. Do not move frozen paths. Do not add new top-level docs for a new idea: add it to methods.csv, or to the lane's FINDINGS.

**Weekly (agent, about 30 minutes of compute, no owner needed).**
- Rebuild STATUS.md; check that every scheduled workflow ran in the last 48 h and flag silent ones.
- Run the liveness audit (section 3) and list lanes with a decision date in the next 14 days.
- Count open drafts, expired claims, and notification volume (bot commits to default branch per day).
- Run the full tests and compare with the known baseline of 4 failures and 12 errors.

**Monthly.**
- Close or sleep lanes under the section 3 rules, reconcile README and ROOM with STATUS.
- Review the program trial counter against what the lab has measured (`registry.program_trials()`).
- Check Actions usage and the 60-day inactivity rule.
- Short owner summary in French, five lines: money moved (should be none), best candidate, what is waiting for them, what is at risk.

**Limits (proposed numbers, owner to confirm).**
- Active forward lanes with a live writer: at most 20 at a time; a new lane needs another one to close or sleep, or a passing gate.
- Scheduled workflows: at most 30 (the present count, so a freeze on growth), and no cron more often than hourly without an owner note.
- Notification budget: zero emails to the owner from bots; at most 1 owner digest per week; owner pings only for decisions listed below.
- New lane starts per week: at most 5 (October-November ran at 170 and 102 rows per month, about 25-40 a week).
- Draft PRs: 2 per agent; claim expiry 72 h.

**Autonomous (any agent, with claim and tests).** Add a registered lane inside existing data and cost rules; write FINDINGS and close rows by the code that appends; rebuild generated docs; fix README staleness; label documents historical; open draft PRs.

**Needs the owner.** Anything touching AGENTS.md or hard rules; enabling, disabling or retiring workflows that write journals; changing the default branch; real orders, money or credentials; larger data downloads; loosening gates or fees; closing a lane with a verdict; the Codex end date of 2026-11-19 (extend, replace or let lapse).

## Top 5 actions, ordered

1. **Decide the 2026-11-19 cliff.** Ask the owner whether the R420/R429/R428 runtime workflows are extended under Claude's workflow ownership or allowed to lapse. Record the answer in one sentence in OPERATIONS.md. This is the only deadline in the next three days.
2. **Make one STATUS page and fix the contradictions.** Correct README "Current status" and the ROOM top (Codex gone, who writes now) and mark the old operational docs historical. Cost: one small PR; value: every agent and the owner read the same facts.
3. **Move bot writes off the default-branch pattern** or otherwise guarantee no PR can have the default branch as its head; keep PR #1 closed. This permanently ends the email and CI flood.
4. **Run the liveness audit on the 67 RUNNING/REGISTERED lanes** and publish the split (live writer / lost writer / never started / past date), via an append-only new journal, without changing any verdict or frozen file.
5. **Move claims out of issue #7 into `registry/claims.csv`**, triage the four OpenHands drafts (merge the harmless ones in a batch, hold #98 for the owner), and cap new lane starts and open drafts per the charter.

Not checked: I did not read the 600+ issue comments or PR bodies, did not run the audit, tests or any workflow, and the workflow run volume is the fact pack's estimate. The Actions 60-day rule is from general knowledge.
