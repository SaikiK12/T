# Notes: usopen_fwd (R371)

Facts found after the freeze. The PREREG is not changed by them; a fix is a new lane.

## 2026-11-10: the journal's writer moves to GitHub Actions
- **What:** from 2026-11-11, `.github/workflows/claude-usopen.yml` runs the lane. Weekdays it starts about 30 minutes
  before 10:00 New York and runs the daemon until 6 minutes after. Every day at 00:47 UTC it runs one scoring tick.
- **Why:** the Claude container that ran the daemon is reclaimed while the session is idle. Since 2026-11-02 that left
  5 of 8 tickets missed (written hours late) and none scored after 10-30.
- **Single writer:** the workflow is the only writer of `journal/` from its first run. The local loop no longer runs
  `ensure`.
- **Timing risk:** a GitHub schedule can start late. A run that starts after 10:02 New York writes a `missed` row, as
  the lane's own rule says. Days are never made up.
- **Unchanged:** the rule, the costs and the PREREG. M-book half-spreads still come from the MEXC ticker recorder,
  which stopped on 2026-11-06 with the container and does not run on GitHub. Scoring then uses the rule's frozen
  fallback half-spread (`rule.SPREAD_FALLBACK`) and flags the row, as the code already does.
