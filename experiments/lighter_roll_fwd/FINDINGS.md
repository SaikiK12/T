# FINDINGS: lighter_roll_fwd (R389). Running; no step scored yet

The lane is RUNNING. Its first step window is 2026-11-06 23:29 UTC. This file records facts found after the freeze.
The PREREG and the scorer are frozen and are not changed by these notes.

## 2026-11-04, before any step: the scorer counts out-of-window steps (audit D1)
- **The PREREG says** (Window): the windows stay at UTC 23:29-00:30, and steps that fall outside them are "reported,
  never rescued". From 2027-03-28 London is UTC+1, so the 23:59 London step lands at 22:59 UTC, before the window
  opens.
- **What `scripts/score_lighter_roll.py` does:** it trades every step day from 2026-11 to 2027-05 in the same UTC
  window. April and May 2027 steps (days 5-9 of the month) are therefore traded and counted in the 20, although
  their step is outside the window.
- **When it matters:**
  - Step 1 of each month sets the direction and is never traded, so each month gives at most 4 traded steps.
  - November to March gives exactly 20 only if no step is missing or stale.
  - One missing step puts an April window into the decision, and that window holds no step.
- **Declared now, before any data:** the PREREG's text governs.
  - At the decision, steps dated on or after 2027-03-28 are reported, not counted.
  - If fewer than 20 in-window steps are traded by the end of 2027-05, the lane is INCONCLUSIVE, as the PREREG says.
  - The scorer's own count is printed beside it, so the difference is visible.
  - A DST-aware successor lane (new id, M472) must be frozen before 2027-03-28 to cover summer steps.
- **Found by:** the hidden-edge audit ([review](../../docs/reviews/hidden_edge_audit_20261104.md)).

## 2026-11-09: lane ABANDONED with 0 traded steps (no host can record the windows)
- **No step was ever scored.** The scorer's own summary reads `0 of 20 traded steps` (`results/summary.json`).
- **The first window was missed.** It ran from 23:29 on 2026-11-06 to 00:29 UTC on 11-07, and the chat container
  that ran `record_lighter_index.py` was down from about 21:00 UTC on 11-06 to 16:40 UTC on 11-09.
- **The index files stop on 2026-11-06.** `data/lighter_index` holds BRENTOIL and WTI files for 2026-11-03 to 11-06
  only, all before that first window.
- **No remaining host can record a window.**
  - The project's only paper writer since 2026-11-07 is Codex's GitHub Actions runtime (R420, `docs/OPERATIONS.md`).
  - That runtime is refused by Lighter's WebSocket as a "restricted jurisdiction" (R428).
  - It also runs hourly jobs, not a stream held open across 23:29-00:29 UTC.
- **The decision cannot be reached.**
  - The mechanism stop needs all five November jumps measured, and the 11-06 jump is already lost.
  - The primary decision needs 20 traded steps by the end of 2027-05.
- **What this means.** The lane closes as ABANDONED, with no result either way on M462 (whether Lighter's book lags its
  documented BRENTOIL index step). Running it again would take a new lane id, a host that can reach Lighter and stay
  up across the step windows, and a DST-aware window (M472).
