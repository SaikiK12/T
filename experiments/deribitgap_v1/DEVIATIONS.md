# DEVIATIONS: deribitgap_v1 (R519)

## 2026-11-21: the frozen fetch stops on an instrument that is not open (data only, before any read)
- **What happened.** `scripts/fetch_deribit_perps.py` stopped at its 13th instrument, ANTH_USDC-PERPETUAL.
  - `get_instruments` (expired=false) lists that perp.
  - But `get_funding_rate_history` answers error -32602, reason "instrument is not open", every time.
  - The frozen client exits after five retries, before it writes `manifest.json`.
- **Nothing was read.** The run stopped at the manifest check, before loading any data. The 13 partial files were
  never opened. The session read only the API's error object (`code`, `data.reason`).
- **Fix.** `scripts/fetch_deribit_perps_open.py`:
  - it calls the frozen module's own `get`, `perps`, `funding` and `candles`, unchanged;
  - it probes each instrument once and skips only the "instrument is not open" error, listed in
    `skipped_not_open.json` and in the manifest;
  - it rewrites the whole folder.
  The frozen fetch and runner are not edited.
- **Effect on the question.** None intended. An instrument that is not open cannot be traded and has no funding.
  The universe is the open ones.
- **The partial folder.** The 13 partial files, written by the failed fetch minutes earlier and never read, were removed before the re-fetch so that the manifest covers one complete pull.
