# Handover: getting everything back without Claude (2026-10-29)

The owner's ask (2026-10-29): everything must be in the repo, or there must be a way to retrieve it, for the day they lose
access to Claude. This page is that way. It says what is in git, what is not, and the exact command for each part.
Nothing here needs a key except the two marked in section 6, and nothing here places an order.

## 1. Where the work is
- Repository `SaikiK12/T`. **All the work since the early lanes is on branch `claude/yo-9a1k5w`** (draft pull request #1,
  base `main`). `main` does not hold it until that pull request is merged; merging is the owner's decision.
  `git clone -b claude/yo-9a1k5w https://github.com/SaikiK12/T.git` gets everything below.
- In git: code (`lab/`, `scripts/`, `engine/`, `tests/`), every frozen PREREG and FINDINGS, the registers
  (`registry/rounds.csv`, `registry/methods.csv`), the forward lanes' journals (`experiments/*/journal/`), the
  per-folder data receipts (`docs/provenance/*.json`: every file's size and sha256), and the notes
  (`docs/DIRECTION.md` is the plan, `docs/DATA_SOURCES.md` the data, `AGENTS.md` the rules).
- On the branch `data-archive` (same repository, no code): the packed live recordings, the only copy of what the recorders
  captured since 2026-10-20. The owner chose this place on 2026-10-29. Section 3 says how to restore it.
- Not in git: `data/` (13 GB, gitignored), the live processes, the two keys, and Claude's own scheduler.
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
The container this was built in ran Python 3.13 and pandas 3.0, not the locked 3.12 stack; two tests of
`test_level_probability` are known to error on pandas 3. `requests` is needed by the `fetch_*` scripts and is not in the
lock. System Chromium is needed only for the browser test.

## 3. Data: four classes, one manifest
`registry/data_manifest.csv` lists every `data/` entry with its class and how to restore it, and
`python scripts/handover.py status` checks the disk against it (an unlisted entry is an error).

| Class | What | Size now | How it comes back |
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
- **RECORDED data is the only copy.** What the recorders captured since 2026-10-21 cannot be fetched again. The archive
  holds it in chunks of at most 50 MB with a sha256 for every chunk and file; it is incremental (`pack` again to add what
  is new) and `restore` never overwrites a different file.
  - `sh scripts/archive_recordings.sh` packs what is new into the `data-archive` checkout (default `../T-data-archive`),
    commits and pushes it. **Run it once a day**: git keeps every chunk, so many small runs only add clutter. It stops adding
    chunks at 900 MB (`ARCHIVE_BUDGET_MB`); 190 MB came in the first 9 days and the 100 ms and raw feeds were added only
    in the last two, so expect 25-40 MB a day (not measured over a longer span): a few weeks. Then the owner has to choose a
    bigger home (a release asset, a private repository or a disk).
  - **`data/news` is not on the branch**: it is third-party headline text and the repository is public. It stays on the
    machine (2 MB); `pack` without `--public` includes it for a private archive. Lighter and Hyperliquid captures carry
    public account and wallet ids, as the exchanges publish them.
  - Files a recorder rewrites (a changed size or mtime) go into a new chunk, so the branch can hold two versions of one file;
    `restore` applies them in chunk order.
- The recorders stop at their caps (`data/commodity_perps` 4,000 MB, `data/rawtape` 4 GB, `data/tape` 3 GB, ...) or
  under 2.5 GB free disk, and say so in their `status.json`.

## 4. Keep the forward lanes and recorders running
They are daemons plus an hourly loop. `python -m lab forward` prints the task graph without starting anything.
```sh
export FORWARD_STATE_DIR=/absolute/path/outside/the/checkout
setsid nohup sh scripts/forward_loop.sh >/dev/null 2>&1 &   # full tick at :15, R200 alone at :45
setsid nohup sh scripts/notice_loop.sh  >/dev/null 2>&1 &
```
After a restart of the machine, `sh scripts/restart_all.sh` does all of it at once: the two loops (only if absent), `ensure`
for every daemon and one full forward tick. It is safe to run twice. On 2026-10-29 the container Claude ran in restarted
five times in 45 minutes, and each time every daemon was down until it was run (idle time looked like the trigger, which is
unproven); the recordings have a gap for each, and a forward lane whose decision falls in a gap writes "missed".
The tick runs `ensure` for every recorder and forward lane, so one loop restarts the rest. `python -m lab status
--state-dir "$FORWARD_STATE_DIR"` shows what ran. The machine must stay on and reach the public exchange websockets;
a gap in a recording is a gap in the evidence, not something to fill later. The forward lanes (R364 settlement scalp,
R369 EIA-release lag, R371 US-open leaders, the carry books, ...) are paper only: nothing in this repo places an order.

## 5. What was scheduled in Claude's account
Reminders, with their exact steps, are copied into `docs/handover/SCHEDULED_CHECKS.md` (R369 first event, raw-tape window,
R367 run on 2026-11-02, reserved batch 1 on 2026-11-03, the hourly housekeeping). They vanish with the account; the file
is a to-do list for a person or another assistant.

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
could still produce one.

## 8. What was checked, and what was not
- Checked: `scripts/handover.py` packed the recordings (2026-10-29: 2,564 files, 6 chunks, 190 MB) and pushed them to
  `data-archive`; a fresh `git clone` of that branch restored into an empty tree reproduced all 2,564 files with matching
  sha256, identical to the live copies; `scripts/archive_recordings.sh` ran from scratch (new worktree) and again
  incrementally; 12 tests in `tests/test_handover.py`; the manifest names only scripts and provenance files that exist.
- Not checked: restoring the 12 GB of REFETCH data from scratch (it would take hours and the sources may have changed);
  running the forward loop on a machine other than this container.
