# Deviations: xfund_eea_fwd (R509)

## 2026-11-19: the read script fails on a journal with no scored day; nothing decided is affected
- **What.** `scripts/read_xfund_eea_fwd.py` (fixed at the freeze) raises `KeyError: 'day'` when the journal has no
  scored day yet. That was true on 2026-11-19, after the first live decision and before its interval closed: `series()`
  sorts an empty frame by a column it does not have.
- **Effect.** None on any decision. The looks need 90 and 180 scored days, and `series()` is correct once one exists
  (`tests/test_forward_xfund_eea.py`, Read).
- **What is done.** The fixed file is left as frozen. R510's fast read (`scripts/read_xfund_eea_fast.py`) treats that
  error as "no scored day".
