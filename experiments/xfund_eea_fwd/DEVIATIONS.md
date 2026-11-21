# Deviations: xfund_eea_fwd (R509)

## 2026-11-19: the read script fails on a journal with no scored day; nothing decided is affected
- **What.** `scripts/read_xfund_eea_fwd.py` (fixed at the freeze) raises `KeyError: 'day'` when the journal has no
  scored day yet. That was true on 2026-11-19, after the first live decision and before its interval closed: `series()`
  sorts an empty frame by a column it does not have.
- **Effect.** None on any decision. The looks need 90 and 180 scored days, and `series()` is correct once one exists
  (`tests/test_forward_xfund_eea.py`, Read).
- **What is done.** The fixed file is left as frozen. R510's fast read (`scripts/read_xfund_eea_fast.py`) treats that
  error as "no scored day".

## 2026-11-20: day 2026-11-20 decided late (execution only)
- The carry workflow's cron fired once, at 07:32 UTC. R509 decided at 08:20, so the day is `late`.
- Its 1 entry and 1 exit have no book record and are charged 21 bp a leg-side, as the frozen read says.
- From 2026-11-21 the clock chain dispatches the workflow at 00:31 and 02:31 UTC (commit 59499b2).

## 2026-11-21: the clock fix holds
- The clock chain dispatched the carry workflow at 00:31 UTC (run 44856336907's predecessor 44844345655, success).
  The 2026-11-21 decisions were made at 01:18-01:19 UTC, `ontime`.
- **One label to read carefully.** The day row labelled 2026-11-21 scores the interval decided on 2026-11-20, so it
  carries that decision's `late` kind (`lab/carrylane.py`, the day row takes the previous decision's kind). From the
  row labelled 2026-11-22 on, days decided on time are scored `ontime`.
- No result was read for this check: only the `day`, `kind` and `run` columns.
