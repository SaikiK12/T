# Handover: getting everything back without Claude (2026-10-29)

The owner's ask (2026-10-29): everything must be in the repo, or there must be a way to retrieve it, for the day they lose
access to Claude. This page is that way. It says what is in git, what is not, and the exact command for each part.
Nothing here needs a key except the two marked in section 6, and nothing here places an order.

**Operational takeover, 2026-11-07.** Claude is no longer the designated
operator. Start with [current operations](OPERATIONS.md): one serialized GitHub
workflow owns the admitted live paper/source writes, with durable state on
`codex/quant-runtime-state`. Its first observed cycle and exact blockers are
in [R420 FINDINGS](../experiments/ops_takeover_v1/FINDINGS.md). The old archive,
private-host inventory and recovery commands below retain their dated scope;
do not start a second local loop from them. Missing original private data is
not restored merely by this takeover.

**Owner update, 2026-11-09: Codex is no longer available.** The owner told Claude, in the session of 2026-11-09,
that they no longer have Codex.
- **What keeps running:** the selected GitHub workflow (R420, R429 successor) runs on its own schedule until its
  dispatch ends on 2026-11-19 00:00 UTC. It needs no agent to run, but nobody maintains it.
- **Duties without an owner:** the native duties listed below fall to Claude when the owner opens a session:
  - R392's freeze before 11-17 (its read on or after 11-17);
  - R404's 11-18 close;
  - a registered successor if R406 or R413 locks mature after 11-19.
- **No always-on host:** the chat container sleeps between sessions, so no recorder or daemon runs in between.
- **Check-in:** a one-shot check-in is scheduled in Claude's session for 2026-11-16 11:20 UTC (trigger
  `trig_014YTgYRN5RzBkqzCyaKPoW4`) to prepare R392.

**Update, 2026-11-10: Claude's forward lanes and recorders now run on GitHub Actions, without a session.**
The chat container sleeps when idle, so every paper lane and recorder Claude owned moved to scheduled workflows on the
default branch. Each workflow is the single writer of its files (its own concurrency group) and commits as
github-actions[bot]. None needs a key, and none can place an order.

| Workflow | Schedule (UTC) | Writes |
|---|---|---|
| `claude-carry-paper.yml` | hourly 00:29-07:29 | journals of R278, R279, R294, R390, R440 (carry books), R285 and R415; lane data in the Actions cache |
| `claude-usopen.yml` | 13:01, 13:31, 14:01, 14:31 on weekdays (the daemon starts in the hour before 10:00 New York), 00:47 daily | `experiments/usopen_fwd/journal/` (R371) |
| `claude-cboe-recorder.yml` | 13:12 and 21:33 on weekdays | data branch `claude/cboe-chain-data` (QQQ/SPY/SPX chains) |
| `claude-hlvaults-recorder.yml` | Sundays 09:13 | data branch `claude/hl-vaults-data`: every Hyperliquid vault, closed ones included, and each vault's allTime account value and pnl (M507) |
| `claude-okx-recorder.yml` | 02:37 and 14:37 | data branch `claude/okx-xperp-data`: OKX Europe X-Perps; Hyperliquid perps matching them under `hl/`; Hyperliquid HYPE and Unit spot pairs with their perps under `hl_spot/`; Hyperliquid's HLP and Lighter's LLP vaults under `vaults/`; Lighter's LIT perp funding and LIT candles under `lit/` |
| `claude-xperp-reads.yml` | Mondays 04:23 | status reads of R441-R447, and the frozen decisions of R441, R443, R445, R446 and R447 after 2027-02-08 and 2027-05-09 (R442 and R444 stopped at gate 0) |

- **Check them:** the repository's Actions tab. A red run names the lane that failed; the others still ran.
- **Stop one:** disable that workflow in the Actions tab. Never run the same lane by hand while its workflow is on.
- **Decision dates:**
  - R440: 90 and 180 scored days, 2027-02-09 and 2027-05-10;
  - R441, R443, R445, R446 (each vault on its own) and R447: 2027-02-08 and 2027-05-09, written by
    `claude-xperp-reads.yml` itself;
  - R371: its 125th and 500th scored days.
- **Not covered:** GitHub disables scheduled workflows after 60 days without repository activity. The bots' own
  commits should count as activity; if runs stop, re-enable them in the Actions tab.

**Recovery review, 2026-11-04 (code/metadata only, at `99e9ba1`).** Sizes, host
observations, test failures and scheduler dates below retain their original dated
scope. They are not a current inventory or proof that a daemon, archive or
scheduler is healthy. Start with the [current recovery checks](handover/SCHEDULED_CHECKS.md)
and fresh [writer claims](https://github.com/SaikiK12/T/issues/7). No capture-host
restart, archive pack, full restore or new market read was performed for this review.

**Subsequent bounded recovery, 2026-11-04.** Two local folders missing from the
classification manifest, `m090_content_v2` and `orb_index_pilot`, were classified
as original public captures. Their 54 files were appended to
[`data-archive` at 2011de7](https://github.com/SaikiK12/T/commit/2011de73202cd8733ad8ac029d461e5166c1d086).
The new chunk was retrieved from GitHub and restored into a separate empty
directory; all file hashes matched. No observation row was decoded. This verifies
that subset, not the capture host's full inventory or a complete machine rebuild.
The [receipt and current limits](reviews/project_execution_20261104.md) distinguish
this check from the older recovery exercise below.

## 1. Where the work is
- Repository `SaikiK12/T`. **All the work since the early lanes is on branch `claude/yo-9a1k5w`** (draft pull request #1,
  base `main`). `main` does not hold it until that pull request is merged; merging is the owner's decision.
  `git clone -b claude/yo-9a1k5w https://github.com/SaikiK12/T.git` gets everything below.
- In git: code (`lab/`, `scripts/`, `engine/`, `tests/`), every frozen PREREG and FINDINGS, the registers
  (`registry/rounds.csv`, `registry/methods.csv`), the forward lanes' journals (`experiments/*/journal/`), the
  per-folder data receipts (`docs/provenance/*.json`: every file's size and sha256), and the notes
  (`docs/DIRECTION.md` is the plan, `docs/DATA_SOURCES.md` the data, `AGENTS.md` the rules).
- On the branch `data-archive` (same repository, no code): the packed subset of live recordings. Coverage depends on
  its manifests and packing receipts; the branch does not contain every capture (section 3). The owner chose this
  destination on 2026-10-29.
- Not in git: `data/` (13 GB in the original snapshot, gitignored), the live processes, the two keys, and Claude's own scheduler.
  The Control Room dashboard was published as a Claude artifact, which will not outlive the account; its source is `dashboard/`
  and `scripts/dashboard_data.py` rebuilds its data files.

## 2. Set up a machine
```sh
git clone -b claude/yo-9a1k5w https://github.com/SaikiK12/T.git && cd T
python -m pip install uv==0.12.23
uv venv --python 3.12.14 .venv
uv pip sync --require-hashes --python .venv/bin/python requirements-test.lock
.venv/bin/python -m lab integrity           # registers and frozen specs
.venv/bin/python -m lab check --suite fast  # tests
```
The original host ran Python 3.13 and pandas 3.0 rather than the locked stack and
reported two `test_level_probability` errors. That is a historical host report:
those errors did not reproduce in the later locked environment, and
[PR #74's full CI](https://github.com/SaikiK12/T/actions/runs/41739649035) passed.
Use the pinned environment and retain the exact traceback and versions if a
failure recurs. `requests` is needed by some `fetch_*` scripts and is not in the
test lock; inspect a fetcher's requirements before running it. System Chromium
is needed only for the browser test.

## 3. Data: five classes, one manifest
`registry/data_manifest.csv` lists every `data/` entry with its class and how to restore it, and
`python scripts/handover.py status` checks the disk against it (an unlisted entry is an error).

The sizes in this table are historical estimates, not this checkout's inventory.

| Class | What | Size in the original snapshot | How it comes back |
|---|---|---|---|
| REFETCH | public history (Binance archive, MEXC, Gate, Kraken, Hyperliquid, macro, ...) | 12 GB | `python scripts/handover.py commands --missing`, then the printed command per folder |
| RECORDED | live captures of public streams that no endpoint serves again (tape, hft, rawtape, Lighter trades, commodity perps, option expiry, news, hourly recorders) | 0.24 GB, growing | on branch `data-archive` (not `data/news`, see below): `git worktree add ../T-data-archive data-archive`, then `python scripts/handover.py restore --src ../T-data-archive` |
| DERIVED | rebuilt from the downloads by frozen code | 0.9 GB | the printed command |
| LICENSED | CME trades from Databento | 8 MB | needs the owner's Databento key, about $0.68 (section 6); never committed or archived |
| SCRATCH | logs, locks, third-party forum and video text | 0.2 GB | not kept |

Read these limits before trusting a re-download:
- **A later download is not always the same file.** MEXC and KuCoin history lists only contracts that existed on
  2026-10-20; Kraken funding goes back one year; Hyperliquid hourly candles only a recent window; FRED's high-yield series
  three years; Coin Metrics, DefiLlama and the unlock calendar are the latest vintage, not point-in-time.
  `docs/DATA_SOURCES.md` has the note per folder. Frozen lanes verify their inputs by sha256 and will refuse a file
  that differs, by design. If the original files are lost, such a lane cannot be re-verified: it has to be re-run as a
  new lane with a new id (AGENTS.md rule 2).
- **Unarchived RECORDED data may have only one copy.** What the recorders captured since 2026-10-21 cannot be fetched
  again. The archive uses a 50 MB target chunk size with a sha256 for every chunk and file; it is incremental
  (`pack` again to add what is new) and `restore` rejects a different destination file unless explicitly forced.
  - `sh scripts/archive_recordings.sh` packs what is new into the `data-archive` checkout (default `../T-data-archive`),
    commits and pushes it. **Run it once a day**: git keeps every chunk, so many small runs only add clutter. It stops adding
    chunks at its configured `ARCHIVE_BUDGET_MB` (900 MB by default). Check the agreed current budget and actual
    manifest/receipts; a shell default is not a current capacity report. The first estimate here (25-40 MB a day) was wrong: 190 MB came in the first
    9 days, but once the 100 ms and raw feeds were on, the run of 2026-10-30 00:43 UTC added 8 chunks (about 370 MB)
    for one day, and the branch reached its cap (854 MB of 900) with 695 files (82 MB, mostly `tape/_parts` and the
    newest commodity-perp parts) left out and listed as "NOT ARCHIVED (over budget)". At about 400 MB a day, nothing
    more fit. On 2026-11-02 (`ARCHIVE_BUDGET_MB=1800`) 15 more chunks went in, leaving 1,345 of 1,800 MB, one file over 95 MB
    (`rawtape/kbook/PF_XBTUSD/2026-10-29.parquet`) left out, and room for about one more day at that rate. Those are dated
    receipts, not a claim of current archive coverage. Report each excluded/oversize/over-budget or failed file as
    unprotected until an actual restore/hash check establishes another copy. A larger destination or budget needs
    the owner's choice; do not silently expand it.
  - **`data/news` is not on the branch**: it is third-party headline text and the repository is public. It stays on the
    machine (2 MB); `pack` without `--public` includes it for a private archive. Lighter and Hyperliquid captures carry
    public account and wallet ids, as the exchanges publish them.
  - Files a recorder rewrites (a changed size or mtime) go into a new chunk, so the branch can hold two versions of one file;
    `restore` applies them in chunk order.
- The recorders stop at their caps (`data/commodity_perps` 4,000 MB, `data/rawtape` 4 GB, `data/tape` 3 GB, ...) or
  under 2.5 GB free disk, and say so in their `status.json`.

## 4. Keep the forward lanes and recorders running
They are daemons plus an hourly loop. `python -m lab forward` prints the task graph without starting anything.
Use the launch example below only on the capture host after the current owner has
checked existing processes and the shared notice lock. Keep state outside the
checkout and preserve any existing writer; a development clone is not a recovery
replacement for the host. Prefer the coordinated recovery entry point described
after the example to independent manual launches.
```sh
export FORWARD_STATE_DIR=/absolute/path/outside/the/checkout
setsid nohup sh scripts/forward_loop.sh >/dev/null 2>&1 &   # full tick at :15, R200 alone at :45
setsid nohup sh scripts/notice_loop.sh  >/dev/null 2>&1 &
```
On the capture host, `sh scripts/restart_all.sh` is the existing recovery entry
point: it requests a clock adjustment, starts absent loops, calls daemon `ensure`
and launches a full tick. Coordinate with the current owner and inspect existing
processes/state before using it; executing it is more than an inspection.
The historical claim that it was "safe to run twice" is not a general guarantee
against concurrent invocations. The wrapper's loop checks and the five-minute
notice loop require the [compatibility review](../dashboard/README.md) before
adopting a different scheduler. Never replace a live writer's worktree or assume
newly merged code is already loaded; confirm the executed revision and receipts
after a controlled reload. Do not run the launch commands in a development copy
to stand in for the actual capture host.

On 2026-10-29 the container Claude ran
in restarted six times between 02:44 and 05:48 UTC, and each time every daemon was down until it was run (idle time looked
like the trigger, which is unproven); the recordings have a gap for each, and a forward lane whose decision falls in a gap
writes "missed". The clock is not disciplined either: after the 05:48 restart it ran 99 ppm slow, 1.7 s behind by 10:22.
`python scripts/clock_check.py status` measures it against MEXC, Deribit and OKX and `slew` removes it gradually. Nothing
runs it on a schedule: `restart_all.sh` runs it once, and on 2026-10-29 it was run by hand every 10 minutes. Whoever takes
over needs to run it regularly (details, log columns and the estimated bias in affected data in
`experiments/recorders/README.md`).
The journal's `bound_ms` is half a request round trip, not a verified UTC bound. Keep the raw data;
an estimated historical correction does not establish an on-time observation. A failed read of the
pending kernel correction blocks `slew` rather than replacing an unknown adjustment.
The tick runs `ensure` for every recorder and forward lane, so one loop restarts the rest. `python -m lab status
--state-dir "$FORWARD_STATE_DIR"` shows what ran. The machine must stay on and reach the public exchange websockets;
a gap in a recording is a gap in the evidence, not something to fill later. The forward lanes (R364 settlement scalp,
R369 EIA-release lag, R371 US-open leaders, the carry books, ...) are paper only: nothing in this repo places an order.

## 5. What was scheduled in Claude's account
The reminders copied on 2026-10-29 are preserved as inactive evidence in
[SCHEDULED_CHECKS](handover/SCHEDULED_CHECKS.md), below its current recovery
procedure and one-read guards. They describe R369's first event, the raw-tape
window, R367's originally planned date, R286 and the old hourly housekeeping.
R286 and R391 have already published their one reads; do not rerun them from an
old reminder. R367's coverage-qualified reschedule, R389's first step and R392's
pre-freeze condition are recorded in the current table with their native links.
The session scheduler vanishes with the account; these documents do not install
or establish a durable scheduler on another host.

## 6. Keys (names only; values never go in the repo)
- `/root/.config/databento/env`: `DATABENTO_API_KEY=...` (read by `scripts/fetch_databento.py`). The owner's key was
  pasted into a chat on 2026-10-29: **rotate it on Databento's site** and put the new one in this file. Spend so far:
  $0.6756; every pull is price-checked first and capped at 5 cents, the R370 lane at $2.
- `/root/.config/lse/env`: `LSE_API_KEY=...`, the owner's LSE vault key (`docs/DATA_SOURCES.md` describes the service and
  the one verification fetch made with it). LSE data is never committed.
- Exchange API keys: none are stored or used in this project. No order has been placed.

## 7. Rules that carry over (AGENTS.md has all of them)
Freeze a PREREG before measuring, never edit a frozen file, append to journals only through the code that appends, one
writer per file, no real orders or money movement, a null is a result, report 1x/2x/3x costs and read every result
against `registry.program_trials()` (9,479,189 on 2026-10-29). The honest state on 2026-10-29 (`docs/PANEL.md`): 168
registered rounds (NULL 92, PARTIAL 34, PENDING 28, CONFIRMED 8, DATA_PASS 6), no strict on-time paper day yet, and no
demonstrated net profit. Real money needs gates 1-3 and the owner. `docs/DIRECTION.md` "Now" is the live list of what
could still produce one. Current method status comes from `registry/methods.csv`,
recorded round history from `registry/rounds.csv`, and exact completed scope from
the lane's native PREREG/FINDINGS. Existing round rows remain unchanged:
`lab.registry.append` adds a new id, not a replacement status row.

## 8. What was checked, and what was not
- Checked: `scripts/handover.py` packed the recordings (2026-10-29: 2,564 files, 6 chunks, 190 MB) and pushed them to
  `data-archive`; a fresh `git clone` of that branch restored into an empty tree reproduced all 2,564 files with matching
  sha256, identical to the live copies; `scripts/archive_recordings.sh` ran from scratch (new worktree) and again
  incrementally; 12 tests in `tests/test_handover.py`; the manifest names only scripts and provenance files that exist.
- Not checked: restoring the 12 GB of REFETCH data from scratch (it would take hours and the sources may have changed);
  running the forward loop on a machine other than this container.
- Review on 2026-11-04 checked the recovery text against current code and published
  lane metadata only. Earlier successful restores do not establish coverage of
  later recordings. A new restore exercise must retain its source revision,
  manifest identities, restored hashes and explicit omissions.
