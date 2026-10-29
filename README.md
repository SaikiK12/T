# data-archive: the live recordings that cannot be downloaded again

This branch holds only packed copies of what the lab's recorders captured from public exchange streams since
2026-10-20 (tape, 100 ms feeds, raw-event tape, Lighter trades, commodity perps, funding/ticker/wallet/notice/unlock
snapshots, top-trader ratios, MEXC contract lists). No code lives here: the code is on `claude/yo-9a1k5w`.

Left out on purpose: `data/news` (third-party headlines; this repo is public), all licensed CME/Databento data, keys,
logs and anything a running recorder was still writing (younger than 15 minutes).

Files: `chunk-NNNNN.tar.gz` (at most 50 MB each), `chunks.csv` (sha256 of every chunk), `files.csv` (path, size, mtime and
sha256 of every file). The archive is incremental: later chunks add new files or newer versions of a file.

Restore (from a checkout of `claude/yo-9a1k5w`):

    git worktree add ../data-archive data-archive
    python scripts/handover.py restore --src ../data-archive

`restore` checks every chunk and file sha256, rejects any member outside `data/`, and never overwrites a file that
differs unless `--force`. `docs/HANDOVER.md` on the code branch has the rest.
