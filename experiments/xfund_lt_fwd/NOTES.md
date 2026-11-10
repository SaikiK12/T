# Notes: xfund_lt_fwd (R294)

Facts found after the freeze. The PREREG is not changed by them; a fix is a new lane.

## 2026-10-22: the replay matches the twin under the lane's exit rule; thin Lighter hours force some exits
- **Replay check** (first tick, 2026-10-22 03:03-03:19 UTC, days 2026-08-22..10-22, not scored):
  - `lab/xfund.py`, run on the lane's forward root with the lane's forced-exit rule (Deviation 1: no fresh close on
    either leg in the last 3 days), gives the journal's 80 tickets exactly. The 61 daily nets (close accounting)
    agree within 5e-11.
  - Data: 195 Lighter and 117 MEXC files, none failed. API rows changed no archive value on overlap.
- **Against R288's engine on the same days, the journal differs on purpose.** The engine forces an exit only after a
  leg's last fresh day in the whole file, which looks ahead. The lane uses the 3-day rule.
- **What drives it: Lighter's thin hours.**
  - A close is fresh when the bar ending at 00:00 UTC traded. On Lighter that is the 23:00-00:00 hourly bar, and in
    the replay window 21% of coin-days had none. MEXC had 0%. This is over the 108 coins with both legs loaded.
  - Two of the replay's 30 exits were forced this way:
    - KAITO on 2026-09-05 (no Lighter trade in the last hour of 09-03, 09-04 and 09-05), re-entered on 09-07;
    - XPT on 2026-10-22.
  - Each costs 2 legs, and a re-entry 2 more, at 5.5 bp per leg (1x).
- **What is done:** nothing. The rule is frozen, and R288 used the same freshness definition (its exits wait while
  a leg is not fresh). The count of forced exits is reported when R294 is read.

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
