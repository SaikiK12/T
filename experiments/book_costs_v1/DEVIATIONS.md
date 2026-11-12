# Deviations and fixes: book_costs_v1 (R404)

## 2026-11-12, writer change: GitHub Actions
- **Old writer.** The PREREG runs `scripts/record_book_costs.py` from the local forward task graph
  (`lab/operations.py`, task R404). That graph stopped with the Claude container. Its last R404 commit is a60b0082
  (2026-11-10 08:18 UTC), which wrote the 2026-11-10 06 UTC slot.
- **New writer.** From its first run, the only writer is `.github/workflows/claude-book-costs-recorder.yml`. It runs
  at :11 and :47 in the first hour of each 3-hour UTC slot and at :29 in the second hour. Only the first run in a slot
  writes a file; the later runs find the slot written and add nothing. The workflow runs `scripts/record_book_costs.py`
  and `scripts/record_digest.py` unchanged, so the universe, endpoints, pacing, sizes, bands and the
  one-file-per-slot rule are as frozen. `lab/operations.py` is not changed.
- **Where the files live.** The parquet files are gitignored on the default branch, so the workflow keeps them on the
  data branch `claude/book-costs-data`, at `book_costs/<YYYY-MM-DD>/<HH>.parquet`. Each run copies that tree into
  `data/recorders/book_costs` before the recorder runs and copies it back afterwards. Only
  `experiments/recorders/journal/digests.csv` and `experiments/book_costs_v1/journal/status.json` are committed to
  the default branch. Digest paths keep the old form, `book_costs/<YYYY-MM-DD>/<HH>.parquet`.
- **Window.** Every run at or after 2026-11-18 00:00 UTC exits before it reads anything, so no file from after the
  window is written.

## Missing slots
- No snapshot exists from the slot after 2026-11-10 06 UTC up to the slot of the first GitHub run. These slots stay
  missing. They are not filled in, as the PREREG requires ("Missing slots are missing").

## Files lost with the old container
- The 6 earlier snapshots (2026-11-04 19:56 to 2026-11-10 08:14 UTC; summarised in the status.json of commit
  a60b0082) stayed on the old container's gitignored `data/` and are not on any branch. Five of them survive as
  digests in `experiments/recorders/journal/digests.csv`: 2026-11-04 18, 2026-11-05 15 and 18, 2026-11-06 00 and 12.
  The 2026-11-10 06 file has no digest row.
- From the first GitHub run, `status.json` summarises only the files on `claude/book-costs-data`. The earlier
  summary stays in git history.
- **Close.** The close on or after 2026-11-18 counts the snapshots with all three venues from both sources:
  the earlier rows in `digests.csv` and the status.json history, and the files on `claude/book-costs-data`. The
  frozen rule is unchanged: DATA_PASS at 40 or more such snapshots in the window, otherwise PARTIAL with the count.
  M469 can read the lost files only through the published summary. It cannot recompute them, and must say so.

## Dry run from the review sandbox (not an R404 snapshot)
- On 2026-11-12 at about 22:17 UTC, the unchanged recorder ran in a scratch worktree outside this repository. Its
  files were deleted afterwards and nothing from it was committed or digested here.
- `--limit 3 --force` read 3 books from each venue in 2 s.
- A full run took 2 min 26 s and wrote 1,315 books: dYdX 57, KuCoin 712 and MEXC 546. On MEXC, 40 books failed
  because the reply had no `data` field, which is most likely a rate-limit reply. A second full run in a copy of the
  workflow's steps behaved the same way: 1,311 books, 44 MEXC failures. A third run in that slot found the slot
  written and wrote nothing.
- All three venues answered in every run. The frozen recorder logs a failed market and continues, so a few missing
  MEXC books do not remove MEXC from a snapshot. A GitHub runner may meet stricter MEXC limits, as R220 did
  (`experiments/carry_fwd/DEVIATIONS.md`). The workflow's logs record the per-venue counts of each run.
