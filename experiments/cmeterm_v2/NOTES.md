# cmeterm_v2 (R504): superseded by R505 before any settlement was pulled

- **2026-11-17.** R504's frozen `fetch` stopped after the rank map (9,809 intervals) and the 67 quarterly definition
  snapshots ($0.0123).
  - Cause: 2010 definition rows of the NYMEX and COMEX roots carry no unit of measure, and `float(None)` raised.
  - A later check found 145 grains and livestock rows with a unit of zero. Under R503's rule those would divide by zero.
- **No settlement was pulled, and no statistic was computed.**
- **What replaces it.** R504's script cannot change. [`cmeterm_v3`](../cmeterm_v3/PREREG.md) (R505) keeps R503's rule
  unchanged and adds guards:
  - the CME contract unit when a definition's unit is missing or not positive;
  - dropped incomplete settlement rows;
  - resuming from a raw file already on disk.
- R505 reuses R504's rank map and snapshots in `data/databento/cmeterm_v2/`, pinned by hash. Each snapshot is checked
  against R504's manifest.
- The R504 row in `registry/rounds.csv` stays as registered: the journal is append-only, and R505's row records the
  supersession.
