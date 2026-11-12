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
- **No local writer.** `lab/operations.py` still lists the tasks R404 (`record_book_costs.py`) and REC_DIGEST. While
  the workflow is the writer, neither may run from a local forward loop: a local run would write its own file for a
  slot the workflow already digested, add a second digest for that path and overwrite `status.json` with a summary
  of other files. Anyone restarting the local loop before 2026-11-18 must leave both tasks out.
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
- **Close.** The frozen rule is unchanged: DATA_PASS at 40 or more snapshots with all three venues in the window,
  otherwise PARTIAL with the count. The status.json history (commits 14a2d3c3 to a60b0082) shows per-venue symbol
  counts for the pooled files only, so it proves all three venues for the first snapshot alone; a later snapshot
  without MEXC would leave those counts unchanged, and the 2026-11-10 06 file has no digest row. The close therefore
  reports the count two ways: (a) the files on `claude/book-costs-data` with rows from all three venues, which can be
  checked file by file; (b) count (a) plus the six lost snapshots, of which only the first is shown to have all three
  venues. The verdict names which count it rests on. If (a) reaches 40, DATA_PASS holds either way; if only (b)
  does, the verdict says that it depends on five snapshots whose venues cannot be checked.
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

## 2026-11-12, workflow checks added after review
- A step after the recorder reads the file the run wrote and fails the job when dYdX, KuCoin or MEXC has no rows in
  it, or when the recorder read nothing. The file and its digest are still committed (a missing venue is a result);
  the red run makes a venue block visible within a slot instead of at the close. The step only reads.
- `digests.csv` and `status.json` are committed to the default branch only after the parquet file is pushed to
  `claude/book-costs-data`, so no digest row describes a file that exists nowhere.
- The data branch is started as an orphan only when origin reports that it does not exist; any other error stops
  the run.
- `claude-clock.yml` also dispatches the workflow at :20 in the first two hours of each slot until 2026-11-18 00:00
  UTC, as a second path next to the cron. A dispatch in a slot that already has its file writes nothing.
