# Notes: xfund_fwd (R278)

Facts found after the freeze. The PREREG is not changed by them; a fix is a new lane.

## 2026-10-21: a pair forced out by a delisting can be entered again the same day
- **What:** at a live decision, a pair exits (forced) when one of its contracts is missing from its venue's live list
  (Deviation 1). The entry step after it does not read the live lists. A coin whose spread still qualifies and whose
  leg is still fresh can therefore be entered again at once, and forced out again the next day.
- **Cost:** 4 legs a day while it lasts, about 0.7 bp of capital a day at 1x per such coin. The paper book also
  enters a contract a trader could not open (Gate's `in_delisting` contracts are reduce-only).
- **Found by:** `tests/test_carrylane.py`, while writing R279's lane.
- **What is done:**
  - R278 keeps it, as frozen. Its tickets show it: an `exit` with `forced` true and an `enter` of the same coin on the
    same day.
  - Such days are counted when R278 is read.
  - R279 (xfund_kc_fwd, on `lab/carrylane.py`) blocks those entries (its Deviation 7).

## 2026-11-04: the live result so far is mostly one dead-leg windfall (audit F5)
- **What:** a leg whose contract is delisted keeps its stale last trade as its close. The pair's price_pnl then books
  the gap between that stale print and the live leg as profit or loss. Audit F4 verified this on ALPACA in R275's run.
- **Size, recomputed from the journal** ([review](../../docs/reviews/hidden_edge_audit_20261104.md)):
  - PTB alone is 86% of book B's +0.665% to date.
  - Without dead legs, book C's NW t falls from 2.65 to 1.18.
- **What is done:**
  - R278 keeps its frozen accounting.
  - When R278 is read at day 90 and day 180, the decided series is reported next to the same series without the
    dead-leg days. A PASS that rests on dead legs is labelled as such.
  - Delisting-aware exits (close at mark or index on the last trading day) are queued as M470 for a new lane.

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
