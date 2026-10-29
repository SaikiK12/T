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
| RECORDED | live captures of public streams that no endpoint serves again (tape, hft, rawtape, Lighter trades, commodity perps, option expiry, news, hourly recorders) | 0.24 GB, growing | `python scripts/handover.py pack --out DIR` makes the archive, `... restore --src DIR` puts it back |
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
- The recorders stop at their caps (`data/commodity_perps` 4,000 MB, `data/rawtape` 4 GB, `data/tape` 3 GB, ...) or
  under 2.5 GB free disk, and say so in their `status.json`.

## 4. Keep the forward lanes and recorders running
They are daemons plus an hourly loop. `python -m lab forward` prints the task graph without starting anything.
```sh
export FORWARD_STATE_DIR=/absolute/path/outside/the/checkout
setsid nohup sh scripts/forward_loop.sh >/dev/null 2>&1 &   # full tick at :15, R200 alone at :45
setsid nohup sh scripts/notice_loop.sh  >/dev/null 2>&1 &
```
The tick runs `ensure` for every recorder and forward lane, so one loop restarts the rest. `python -m lab status
--state-dir "$FORWARD_STATE_DIR"` shows what ran. The machine must stay on and reach the public exchange websockets;
a gap in a recording is a gap in the evidence, not something to fill later. The forward lanes (R364 settlement scalp,
R369 EIA-release lag, the carry books, ...) are paper only: nothing in this repo places an order.

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
- Checked: `scripts/handover.py` packed the 240 MB of recordings into 4 chunks (139 MB), and a restore into an empty
  tree reproduced all 2,222 files with matching sha256; 11 tests in `tests/test_handover.py`; the manifest names only scripts
  and provenance files that exist.
- Not checked: restoring the 12 GB of REFETCH data from scratch (it would take hours and the sources may have changed);
  running the forward loop on a machine other than this container.
