# Notes: xfund_bg_fwd (R390)

Facts found after the freeze. The PREREG is not changed by them; a fix is a new lane.

## 2026-11-10: the journal's writer moves to GitHub Actions
- **What:** from 2026-11-10 the lane is ticked by `.github/workflows/claude-carry-paper.yml` (hourly 00:29-07:29 UTC),
  not by the Claude container. The container is reclaimed whenever the session is idle and the session itself will end;
  a GitHub runner does not depend on either.
- **Single writer:** the workflow is the only writer of `journal/` from its first run. The local loop no longer ticks
  this lane (its wake-up prompt and `docs/loop/STATE.md` say so).
- **Data root:** `data/<lane>/` lives in the Actions cache. On the first run it is rebuilt from the public APIs from the
  warm day, not seeded from the archive (the runner has no archive). Days already in the journal are not re-decided,
  and positions are rebuilt from `journal/tickets.csv`, so the change touches only the data of later decisions. Those
  read the last 14 to 30 days, which the API serves and which a tick re-fetches anyway (two-day overlap).
- **Reachability (probe run 42863150912):** every venue endpoint the lanes use answers from a GitHub runner, Binance
  through www.binance.com (fapi.binance.com returns 451 there and is not used).
- **Rule, costs and accounting:** unchanged. The PREREG is not edited.
