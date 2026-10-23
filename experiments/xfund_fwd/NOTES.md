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
