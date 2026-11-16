# Coordinator's own view (written before reading reviews A-C; D had arrived but was only skimmed)

## What the lab knows
1. Costs decide. Most signals here are real but small (1-15 bp/day gross) against 9-19 bp/day of executable cost.
   The owner's "why do you always talk about fees" has a measured answer: fees + spread + impact are larger than
   almost every edge we found.
2. One structural premium survives unread data: funding carry, a few %/yr, capacity-limited ($1k-$5k per leg at
   measured book cost, OpenHands R495 on PR #100, unmerged). It is a yield, not a trading edge.
3. From France, with public data, ~250 ms latency and no keys, speed games are closed (R347, R349, R367, R431).
4. Social-media claims essentially never survive (every reel lane NULL or untestable).
5. The process works as a filter: it caught a leak (R304 metrics-leak), killed the unlock short on reserved data
   (R286) after it looked like the best edge, and keeps nulls on record.

## What it accumulated without learning
- 444 methods, 67 open rows, 274 lane folders, 62 top-level docs, a 900-line DIRECTION whose "Now" is 10-28.
- 102 registry rows in the first 16 days of November: the rate of starting exceeds the rate of deciding. Forward
  lanes decide in 2027. Each new lane raises the program-trial hurdle every other result is read against.
- Census (scratchpad census.tsv): of 67 RUNNING/REGISTERED/ARMED/PLANNED rows, ~13 Claude rows have had no writer
  since containers died (R224, R266, R268, R270, R272, R286, R355, R364, R369 and older R180/R184/R199), 17 are
  Codex's (R331, R372, R374, R400, R417-R429) untouched since 11-02..11-08, and ~37 have a live GitHub writer.

## Philosophical position
- The question should move from "find an edge" to "what is the best use of a small capital and a scarce owner
  attention, given what we now know?" A defensible answer today: keep capital in bills; let the few live forward
  lanes that test the one surviving premium (carry, at measured cost and small size) finish; stop opening new hunts
  unless they change a binding constraint (cost, size, access) rather than add another signal.
- Pre-registration is a discipline only if decisions arrive. A lane that cannot decide within ~6 months at
  realistic effect size is a monitoring job, not a test; say so at registration.
- More searching under unchanged constraints has low expected value: base rate of forward passes so far is 0. The
  value of new work is in measuring constraints (costs, capacity, access), finishing decisions, and keeping the
  record honest and cheap to maintain.

## Organisation
- Too many "now" pages: README status (stale Codex claim), DIRECTION Now (10-28), PANEL (11-14), HANDOVER,
  OPERATIONS x2, SCHEDULED_CHECKS, loop/STATE, EDGE_SCOREBOARD (through R363), trigger prompt, issue #7 (600+).
  Proposal: ONE dated status page (STATUS.md, short, rewritten not appended) + generated tables; everything else is a
  dated snapshot linked from the README index.
- Writers: Claude sessions, Codex runtime (ends 11-19?), OpenHands drafts (4 unmerged, ids R489/R493-R496 claimed
  off-branch), Kiro, free-ai-agent. Coordination by a 600-comment issue does not scale. Proposal: one integrator
  (this branch), drafts merged or closed within 7 days, ids claimed only when the row lands on the default branch.
- Automation: ~300 runs/day, ~44 bot commits/day to the default branch. PR #1 closed today stops the emails. Longer
  term, journals could move to a data branch, but several workflows/paths are frozen inputs, so that is a new-lane-
  level migration, not a tweak.
- Owner contact: one French note a week, decisions only when theirs, no hourly loops (they paused it).

## Limits I would set
- WIP: at most N live forward lanes (N ~ current live ones); a new forward lane needs (a) measured costs first,
  (b) power to decide within 6 months, (c) a free slot or a lane closed.
- Zombie rule: a RUNNING row with no writer for 7 days gets an honest closing note (ABANDONED/INCONCLUSIVE with
  the gap), or a restart on GitHub Actions under its frozen rule if that is possible without editing frozen files.
- Docs: no new top-level doc without retiring one.
