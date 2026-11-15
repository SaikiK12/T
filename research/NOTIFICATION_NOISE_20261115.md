# The bot-commit notification flood: diagnosis and options (2026-11-15)

The owner is receiving one email per `github-actions[bot]` commit ("Carry paper lanes: GitHub tick
…", "Flow paper lanes: GitHub tick …", "R404 book_costs_v1: snapshot …"). This is a diagnosis with
measured numbers, not a change: the noisiest workflows are claimed by an open PR, and notification
settings belong to the owner.

## Measured

From `GET /repos/SaikiK12/T/commits?sha=claude/yo-9a1k5w&per_page=100`:

- **83 of the last 100 commits are `github-actions[bot]`**, spanning 2026-11-13 10:12 → 2026-11-15 14:18
  (about two days), so roughly **40 notification emails a day**.
- Breakdown: **53 Flow paper lanes**, 12 Carry paper lanes, 11 R404 book_costs_v1, 5 R371 usopen_fwd,
  2 R457 usopen_dex_fwd.

## Why it happens

Each recorder/tick workflow commits its journal and pushes **straight to the default branch**:

```yaml
br="${{ github.event.repository.default_branch }}"      # claude/yo-9a1k5w
git pull -q --rebase --autostash origin "$br" && git push -q origin "HEAD:$br"
```

`.github/workflows/claude-flow-paper.yml` runs on `cron: '17,32,47 * * * *'` — **3 runs an hour, 72 a
day**. It only commits when a journal actually changed, which is why 53 landed in two days. The
carry lanes run `'29 0-7 * * *'` (8/day) and the cost recorder is 3-hourly.

The owner is subscribed to the thread that these commits land on. PR #100 also targets
`claude/yo-9a1k5w`, so branch activity surfaces in the PR thread.

**This is not a bug in the lanes.** The strict on-time clock in `docs/GATES.md` requires each hour to
be computed within 60 minutes of its close, and the extra :32/:47 fires exist because GitHub drops or
delays scheduled runs. Removing them would damage the evidence, not just the noise.

## Options, cheapest and safest first

### 1. Owner-side: stop watching the branch (no code change, zero risk) — recommended
GitHub → the repo → **Watch → Custom → uncheck "Pushes"**, or on the PR thread use **Unsubscribe**.
Per-thread unsubscribe is available in the email footer. This silences the flood without touching a
single frozen rule, cron, or journal. Nothing about the lab's evidence changes.

The API cannot do this with the current token: `GET /repos/SaikiK12/T/subscription` returns **403
"Resource not accessible by integration"** — watching is a user-level setting, and changing someone's
notification settings is not the agent's call anyway.

### 2. Filter in the mail client (no code change)
Filter `from:notifications@github.com` **and** subject containing `GitHub tick` or `snapshot` into a
label, skip inbox. Keeps the record, removes the interruption.

### 3. Repo-side: push journals to a data branch, not the default branch (needs a lane owner)
The cost recorder already does exactly this: it pushes to `claude/book-costs-data`
(`.github/workflows/claude-book-costs-recorder.yml:149`). The same pattern would move the flow and
carry journals off the default branch and cut ~65 of the 83 commits from the watched branch.

**Blocked this session, and deliberately not done:**
- `.github/workflows/claude-flow-paper.yml` and `claude-book-costs-recorder.yml` are **claimed by
  open PR #99**. AGENTS.md rule 4 is one writer per file; I did not edit them.
- It changes where the canonical journals live, which `docs/GATES.md`, `lab/operations.py` and the
  forward readers all resolve. That is an operations migration, not a notification tweak, and it
  needs the canonical writer's own reviewed change.
- `claude-carry-paper.yml` and `claude-usopen-dex.yml` are unclaimed, but moving only those would
  remove ~14 of 83 commits while leaving the 53-commit flow lane untouched — not worth a unilateral
  change to the evidence layout.

### 4. Squash or batch the commits (weakest)
Committing once a day instead of per tick would cut emails but break the per-hour audit trail that
the on-time-day count depends on. Not recommended.

## What I did

Diagnosed and measured it, and wrote this note. **No workflow, cron, journal or notification setting
was changed.** The two files that would need editing are another writer's this session, and option 1
solves the owner's actual problem in one click without any of that risk.
