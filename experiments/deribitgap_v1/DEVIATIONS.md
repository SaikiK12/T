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

## 2026-11-21: Deribit's daily bars close at 08:00 UTC, so the frozen loader misaligned them (plumbing, before any result)
- **What happened.** The first run stopped with no book day. The engine found no eligible pair, because the
  correlation guard failed on every coin.
- **Diagnosis** (structure only; no spread, funding sum or strategy return was computed):
  - ADA's 30-day correlation of daily returns between the venues was 0.13 / 0.31 / 0.11 on three test days.
  - Raw bars show why. Deribit's 1D bars run 08:00 to 08:00 UTC, while Hyperliquid's run 00:00 to 00:00.
  - `load_daily` with `bar_h` 24 puts a Deribit close at 08:00 on the next day. So the two closes sit 16 hours apart,
    and daily returns overlap a third of the time.
- **Fix.**
  - `scripts/fetch_deribit_h1.py` fetches Deribit's hourly candles (resolution 60) with the frozen client.
  - `scripts/run_deribit_gap_h1.py` runs the frozen `StaticBook`, `book`, data checks and `report` unchanged. It
    loads Deribit prices from the hourly bars (`bar_h` 1), so each daily close is the last hourly close at or before
    00:00 UTC, as on Hyperliquid.
  - Funding, the rule, the costs and the decision are unchanged.
- **Read once.** The frozen `run_deribit_gap.py run` wrote no results; the corrected run is the lane's one read.
