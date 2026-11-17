# carrycost_hist_v1 (R499): superseded by R500 before any cost was read

- **2026-11-17.** The fetcher kept every raw Gate hour file. The session's disk allowance ran out: about 1 GB was free
  for about 3 GB of raw hours. The fetch was stopped after 137 Gate hours and 91 Binance first hours.
- **No walk, spread or cost was computed** from those files, and `run` was never called.
- R499's frozen script cannot change, so [`carrycost_hist_v2`](../carrycost_hist_v2/PREREG.md) (R500) asks the same
  question with the same rules. It reduces each Gate hour on arrival and reads 15 Binance minutes instead of 60.
- R500 reduced R499's cached files and then deleted them (this session's own cache).
- The R499 row in `registry/rounds.csv` stays as registered (REGISTERED, PENDING, 0 trials). The journal is
  append-only; R500's row records the supersession.
