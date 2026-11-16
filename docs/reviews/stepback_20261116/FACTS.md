# Fact pack for the 2026-11-16 step-back review (repo: /home/user/T, branch claude/yo-9a1k5w)

Collected by the coordinating Claude session on 2026-11-16 ~15:30 UTC from the checkout and GitHub. Numbers are
measured unless marked otherwise. Paths are relative to /home/user/T.

## The owner's request (translated from a French/English message, 2026-11-16)
"Stop those ticks that went through my mails, and take a step back on our organisation and sustainability on this
project. Don't just work to find things: we first need to be philosophers and figure things out, and only then do
things. Think together with Sonnet or Haiku. Please be autonomous to sustain this whole repo structure."

Earlier owner messages (context): they write in French; they want autonomous work toward a reproducible
net-positive return ("Rien ne dépend de moi, tu dois tout faire"); real money must match paper; they asked "so we
have no mental method to trade, only arbitrary things?" and "why do you always talk about fees, are they really that
big?". On 2026-11-13 they paused Claude's hourly self-wake-up loop (no reason given).

## Standing rules
AGENTS.md (hard rules: pre-register and freeze before measuring; frozen files never edited; append-only journals;
one writer per file; no real orders / money / credentials / deleted data without the owner; real money only after
paper proves a net gain via lab.gate.go_real(); never claim something works without running it; a null is a result).
Owner objective (AGENTS.md, 2026-10-24): reproducible positive net return at executable costs, then genuinely new
prospective paper evidence, within public-data, API, latency, capital and compute constraints.

## Scale of the record (registry/rounds.csv, registry/methods.csv)
- 275 registry rows; ids reach R482 on this branch (other agents claim R489, R493-R496 on unmerged PR branches).
- Status: DONE 201, RUNNING 46, REGISTERED 21, ABANDONED 5, ARMED 1, PLANNED 1.
- Verdict: NULL 128, PENDING 76, PARTIAL 48, CONFIRMED 13, DATA_PASS 10.
- Rows by month: 2026-10: 170, 2026-11 (to the 16th): 102. Program trials: 9,785,313.
- Methods queue: 444 rows. TESTED 159, BLOCKED 120, PARTIAL 72, UNTESTED 51, QUEUED 28, N/A 14.
- 67 lanes are RUNNING or REGISTERED (ids in the registry). Several were run by daemons in containers that no longer
  exist; their rows still say RUNNING.
- No strategy has passed forward paper. No money has moved. The only edge confirmed on reserved (unread) samples is
  perp funding carry (C14 binance+gate +2.86%/yr, R391 long tail +2.48%/yr, R392 +0.73%/yr at 1x only). On
  2026-11-15 another agent (OpenHands, PR #100, unmerged) measured order-book costs and found carry clears cost only
  at about $1k-$5k per leg, not $10k; the R391 long-tail books cost 28-48x the assumed unit on most KuCoin contracts.
  Its summary: "nearly all ~51 nulls are real 1-15 bp/day gross against 9-19 bp/day cost" (the cost wall).
- Forward lanes have decision dates mostly in 2027 (e.g. R474/R479 2027-02-13 and 2027-05-15; R480/R482 final
  2027-11-13; R371 futility at 125 scored days, final at 500).

## Size of the repository (file counts)
experiments 3,974 files in 274 lane folders; scripts 912; tests 736 (~3,300 unittest cases); lab 433; research 365
(research/intake 287); docs 136 (62 top-level .md plus guides/, handover/, loop/, provenance/, reviews/);
.github/workflows 30. Fast test suite baseline: 4 failures + 12 errors in files pinned by frozen lanes (cannot be
fixed without breaking a freeze).

## Who writes here
- Commit authors on this branch (all time): Claude 735, github-actions[bot] 228, a Codex-configured author 209, SaikiK12 88,
  Kiro Agent 38.
- Claude cloud sessions (this one; container is ephemeral; its hourly wake-up is paused by the owner since 11-13).
- Codex (OpenAI) runs four hourly "quant-*" runtime workflows that push to codex/quant-runtime-state; README still
  says Codex is "the single scheduled writer" since the 2026-11-07 transfer; a previous note says Codex's runtime
  ends 2026-11-19.
- OpenHands agents act "on behalf of" the owner: draft PRs #97 (M479 monitor), #98 (AGENTS.md edits), #99 (comment
  cleanup), #100 (R493-R496, value review, cost measurements). All four are unmerged drafts based on claude/yo-9a1k5w.
- A "Free AI Coding Agent" workflow triggers on issue comments.
- Coordination room: issue #7, 600+ comments. PR #8 is a "doorbell".

## Automation
- 30 workflows; roughly 300 scheduled runs a day (estimate from crons: flow-paper 72, xyz-books 72, Codex runtimes
  96, book-costs 24, carry 8, clock 8, plus dailies/weeklies).
- 88 bot commits landed on claude/yo-9a1k5w in the 48 h before 15:00 UTC 11-16 (Flow paper 48, R404 snapshots 17,
  Carry 11, others 12). claude/yo-9a1k5w is also the repository default branch.
- EMAIL FLOOD, diagnosed and acted on today: PR #1's head was the default branch, so every bot commit emailed the
  owner ("pushed 1 commit") and started an approval-waiting CI run (17 `action_required` runs of "Offline lab
  checks" since 06:00 UTC). The coordinator closed PR #1 at 15:2x UTC (reversible; branch, workflows and journals
  untouched). Recorders that push to data branches (claude/*-data) never caused emails.

## Documents that claim to be "current"
- docs/DIRECTION.md: 900 lines, last changed 2026-11-02, "Now" section dated 2026-10-28.
- README.md "Current status": says the 2026-11-07 transfer to Codex made Codex the single scheduled writer.
- docs/PANEL.md: generated, last rebuilt 2026-11-14 05:02 UTC (by a tick that has since stopped rebuilding it?).
- docs/HANDOVER.md (2026-11-12), docs/OPERATIONS.md (2026-11-12), docs/guides/OPERATIONS.md, docs/handover/
  SCHEDULED_CHECKS.md, docs/loop/STATE.md, docs/EDGE_SCOREBOARD.md (current through R363; OpenHands added a stale
  banner on its unmerged branch), docs/GATES.md (2026-11-10).
- AGENTS.md itself says: one authority per fact (methods.csv = queue, rounds.csv = rounds, PREREG/FINDINGS = scope).

## Constraints that do not change by working harder
Owner in France (venue access limited: no Binance futures, etc.); public data only, no keys; latency ~250 ms from the
container; small capital; ephemeral containers; owner attention is limited and non-technical-ish; GitHub Actions is
the only durable runner.
