# Deviations: xfund_eea3_fwd (R512)

## 2026-11-20: the first live day was decided late (execution only; the frozen rule applied as written)
- **What happened.**
  - `claude-carry-paper.yml`'s cron (:29, hours 0-7) fired only once on 2026-11-20, at 07:32 UTC. R512 decided at
    08:21, 8.35 h after 00:00, so its first live day is `late`.
  - The 19 inherited pairs, 1 entry and 1 drop have no live fill and no book record.
  - The frozen read charges each of their leg-sides 21 bp (3x the flat cost): about 0.2% of capital once, against
    about 0.15% at the costs measured on 2026-11-18/19.
- **Why.** GitHub started this workflow's cron about once a day, usually after 07:00 UTC. All seven carry lanes were
  late that day.
- **Fix (plumbing).** From 2026-11-20 the clock chain (`claude-clock.yml`, commit 59499b2) dispatches the carry
  workflow at 00:31 and 02:31 UTC, so later days are decided on time. Nothing in R512's rule, read or code changed.
