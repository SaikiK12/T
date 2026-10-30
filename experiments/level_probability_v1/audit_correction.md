# R330-AUDIT-SIGN1: audit-only unsigned entry-notional correction

The original frozen independent checker failed before completing its audit:
it compared signed `q * price` to positive500. Every short open fails that
magnitude guard although `abs(q * price)` is500. Parent failure record/log hash
and original checker are retained. No original PASS is claimed.

This new named checker copies the parent body with ONLY the unsigned notional
guard `abs(abs(q*p)-500)` replacing `abs(q*p-500)`, plus its function/CLI name.
A literal text-equivalence unit verifies that exact scope. An entire invented
four-asset/two-stage long/short export makes the old checker fail and the new
checker pass all36accounts. TWO new tests pass before this audit-only freeze;
the actual historic results have NOT been passed through the corrected checker.

New audit code/input identity `9ca1e60858741616b1a6a853fb6f3245b24fe3e2bf37bb19b11a327a690c45be`. This spec and identity are committed
before invoking the corrected historical audit. Wrapper verifies own/new code,
old frozen research/code/input identity and exact original result SHA before/
after. Original results are already computed from frozen code c4893c0 after
training-only model commit caf9343; neither is recalculated, tuned or changed.
No result/financial formula/source/position/fee/quantity/cost/decision repair.
No new trial, market/history request, paper day or restored acquisition budget.
This validates conditional research arithmetic, not executable fills, funding
fair-notional, market calibration, true expected profit or strategy activation.
Original checker failure and narrow pre-freeze26-case review remain explicit.
