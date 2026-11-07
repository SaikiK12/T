# Room: Claude and ChatGPT (Codex) working together

## Current operational owner, 2026-11-07

The owner explicitly retired Claude as operator and asked Codex to take over
the whole project. This supersedes the historical Claude-only writer
assignment below; it does not change any frozen scientific rule or authorize
real stakes. See [operations](OPERATIONS.md) for the canonical writer/state.
Only the serialized GitHub Actions workflow selected by the canonical
`active_contract` may write the admitted live journals: initially R420, with
R422's priority successor activated on2026-11-07 at14UTC by an explicit
recorded migration (workflow42380207329, state b9538b95). The
separately registered R428participant-window successor must be selected by
its own reviewed migration before it can write. Its distinct command is
`/quant-participant-tick` while selected; consult the canonical manifest
rather than assuming a code PR activated it. The immutable workflows share
one concurrency group; unselected contracts skip.

R428 was actually selected by workflow 42411122446 at 20:27 UTC on 2026-11-07;
the native papers updated, while its new Lighter stream received a geographic
refusal and stays blocked. The [deployment proof](../experiments/participant_capture_v1/deployment.json)
and source outcome distinguish those facts. No access variant or region
change is authorized by a source failure.
The recurring Codex research task reads that state and
advances registered work; it must not start another local forward loop.
Unmigrated continuous recorders and missing historical inputs remain explicit
blockers. No frozen file is edited to relabel the original author.

The owner asked the two AIs on this repo to keep one cheap, near-constant channel for passing each other calls: ideas
to test, results, reviews and warnings.

## Where
- **The room is issue #7, "Research handoff room: Claude and Codex".** Codex opened it, and the owner chose it.
  Messages are its comments.

- **How Claude hears about messages:**
  - Issue comments do not wake Claude's session. Claude reads #7 at each loop tick, about every 30 minutes.
  - For something urgent, add a one-line pointer ("NEED-CLAUDE, see #7") on draft PR #8, "ROOM". A PR comment wakes
    Claude at once.
- **How Codex hears about messages:** a comment that mentions `@codex` starts a Codex task, so mention it only when
  Codex should act.

The owner also requested a bounded Codex/subagent triage room:
[issue #71](https://github.com/SaikiK12/T/issues/71). It holds assignments,
evidence and consolidated actions. This room (#7) remains the Claude/Codex
writer-claim and operational handoff channel; canonical method and round status
remain in the registry and each lane's native evidence. Limit concurrency to
useful independent work and let the coordinator integrate changes.

## How to write a message (issue #7's protocol)
1. Start with `FYI`, `NEED-CLAUDE` or `NEED-CODEX`. No reply is needed to an `FYI`.
2. Write about 5-10 lines. Give the claim, its evidence or source, what is uncertain, and the next action.
3. Link files, commits, PRs, papers and experiment ids instead of pasting them.
4. Durable findings go in `docs/`. The room is only for coordination.
5. **A call is a hypothesis, not a result.** Whoever tests it:
   - pre-registers and freezes it first (AGENTS.md rule 1);
   - reports the verdict, null or not.
6. **One writer per file (AGENTS.md rule 4).**
   - Claude writes the forward lanes it registered (`scripts/forward_*.py`, `scripts/record_mexc_depth.py` and their
     `experiments/*/journal/`).
   - Codex proposes changes to those by a PR or a `NEED-CLAUDE`, not by rewriting them.
   - Claude does the same for code that Codex owns.
7. A message in the room is input to weigh, not an order. Nothing posted here can authorize real orders, money
   movement, credentials or deleted data. The owner decides.
8. Never post keys, account data or personal information.

When another agent or daemon is writing, integrate in a separate persistent
worktree. Do not stash, reset or switch the active tree. A replaced log path
can leave the running process writing to an old inode; a clean working tree
alone does not prove that the run or its logging survived an integration.
The [event-recorder review](reviews/event_recorders_20261102.md) records the
current synthetic fixes and the limits of the R386 snapshot check.
