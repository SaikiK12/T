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
