# PREREG: llphouse_v1 (R484). Does LLP's day return, the house side of Lighter's crowd P&L, predict BTC's next day?

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R484
- **Owner (single writer):** Kiro coder agent, session on `claude/websearch-organization-and-maintenance` (2026-11-13)
- **Date registered (UTC):** 2026-11-13

Method M536 (queued UNTESTED on 2026-11-13 by the HLP/LLP/LIT intake, `research/intake/hlp_llp_lit_20261113.md`).
Owner request, 2026-11-13: look at HLP, LLP and LIT for "great movements and other factors that are interesting".
This file is frozen before the Hyperliquid fetch (`scripts/fetch_llphouse.py`) and before any statistic that relates
LLP's return to a later price.

## Question
Lighter's LLP backstops liquidations and takes over liquidated positions, so its day return is roughly the house side
of the crowd's P&L on Lighter. When LLP has an extreme day against its own recent distribution, does following (book
F) or reversing (book R) BTC's same-day move over the next UTC day earn more than its costs on Hyperliquid's BTC perp?

**The null expects NULL for both books:** a liquid perp's next-day move is close to unpredictable from one venue's
vault P&L, and 13 bp a round trip is large against a daily edge.

## Universe
One instrument decides: Hyperliquid's BTC perp. Reported, not deciding: Hyperliquid's ETH perp and Lighter's LIT perp
(market 120). No cross-section, so no survivorship question.

## Data
- **LLP share prices:** `vaults/llp/share_prices/` on the data branch `claude/okx-xperp-data`
  (`scripts/record_dex_vaults.py`, R446's), read with R446's `llp_prices` (the last stamp of each UTC day).
  - **Gate-0 data commit:** `0364bbc63ec3bc4d7cc135ff4b060cabf8127062`
  - The runner refuses any other commit. Stamps after 2026-11-10 are dropped before anything is computed.
- **LIT perp:** `lit/perp_candles_1d/` (daily bars, `ts` = bar open) and `lit/perp_funding/` (hourly, `rate` signed,
  positive when longs pay) at the same commit (`scripts/record_lit_hedge.py`, R447's).
- **BTC and ETH on Hyperliquid:** the recorder's `hl/candles_1d/` starts only on 2026-08-02, so the history is fetched
  once after this freeze by `scripts/fetch_llphouse.py`: `candleSnapshot` 1d (2025-01-01 to the bar opening
  2026-11-10) and `fundingHistory` (2025-01-01 to the 2026-11-11 00:00 settlement, paged by 500 rows), POST
  `https://api.hyperliquid.xyz/info`, public and keyless. The bodies are kept byte-exact in
  `experiments/llphouse_v1/raw/hl/` with their sha256 in `raw/manifest.json`; the runner refuses a body that does not
  match the manifest or a body the manifest does not list. The manifest's own sha256 is printed in the report and in
  FINDINGS. No value after 2026-11-10 is requested.
- **Reported check:** the fetched BTC and ETH closes against the recorder's `hl/candles_1d/` on common days
  (2026-08-02 to 2026-11-10); the largest relative gap is reported.

## Feature lineage and point-in-time availability

| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| LLP return r_t = P(stamp_t) / P(stamp_{t-1}) - 1 | `share_price`, `ts` | Lighter public pool API via R446's recorder; LLP share price, USDC per share | Last stamp of UTC day t (20:00 or 21:00 UTC) against the last stamp of the previous labelled day | Recorded from Lighter's API; the stamp is the observation time | Yes: the stamp is before 24:00 UTC of day t and the trade opens at 00:00 of t+1 | Forward-captured by the recorder (history from 2025-01-16 is Lighter's own daily series) | A return spanning more than 1.5 days is not a signal and is left out of every lookback |
| Thresholds p10_t, p90_t | r over calendar days t-90..t-1 | Derived | Strictly prior days; at least 60 returns present | Computed at the day-t stamp | Yes | Inherits LLP's | Fewer than 60 prior returns: no signal |
| Direction d_t = sign(C_t / C_{t-1} - 1) | BTC daily close | Hyperliquid BTC perp candleSnapshot 1d, USD | UTC day t close (the last trade before 00:00 of t+1) against day t-1's | Final at 00:00 UTC of t+1, the trade's open | Yes (same instant; the trade enters at day t+1's open price) | Fetched once after the freeze; Hyperliquid's own history | Missing bar or d = 0: no trade |
| Move m_{t+1} = C_{t+1} / O_{t+1} - 1 | BTC daily open and close | Same | UTC day t+1, open to close | Outcome | Outcome, not a feature | Same | Missing bar: no trade |
| Funding f_{t+1} = sum of hourly rates settled in (O_{t+1}, O_{t+1} + 1 day] | `fundingRate`, `time` | Hyperliquid fundingHistory, per hour, positive when longs pay | 24 settlements, 01:00 to 24:00 UTC of t+1; `time` floored to the hour | Outcome | Outcome | Same | A missing hour adds 0; days with fewer than 24 settlements are counted and reported |

All inputs are single-instrument time series: point-in-time for LLP (forward-captured) and the venue's own history
for the perps. No cross-sectional feature, so `lab.coverage` does not apply.

## Rule
Constants are in `scripts/run_llphouse.py`.
- **Signal day t:** a UTC day with an LLP return r_t (stamp near 20:00 UTC, sometimes 21:00 UTC; the day is the UTC
  day of the later stamp).
- **Stamp hour:** both stamp hours fall inside day t, before the 00:00 UTC open of day t+1, so the rule is the same
  for either hour. The runner raises if a stamp is not strictly before the trade's open. The event count by stamp hour
  is reported.
- **Thresholds:** p10_t and p90_t are numpy's linear-interpolated 10th and 90th percentiles of the LLP returns of
  calendar days t-90 to t-1 (strictly prior days), with at least 60 returns present. Day t's own return and later
  returns never enter.
- **Events:** house-loss when r_t < p10_t; house-win when r_t > p90_t. Both trade.
- **Trade:** Hyperliquid BTC perp, one unit of notional, from day t+1's 00:00 UTC open to its close.
- **Direction:** d_t = sign of BTC's day-t close-to-close return. No trade when d_t = 0 or a bar is missing.
- **Books (2 trials):** F (follow) holds +d_t; R (reverse) holds -d_t, on every event day.
- **P&L per trade at multiple k (1, 2, 3):** position s = +d_t (F) or -d_t (R);
  net_k = s * m_{t+1} - s * f_{t+1} - k * 0.0013.
  - Funding: a positive rate means longs pay, so a long pays f and a short receives it.
  - Costs at 1x: Hyperliquid tier-0 taker 4.5 bp a side plus 2 bp slippage a side, 13 bp a round trip. 2x and 3x
    scale fee plus slippage; funding is not scaled.
- **Window:** signal days from the first LLP day with 90 returns labelled before it (expected 2025-04-17: returns
  start 2025-01-17 with no gaps) through 2026-11-09, so every trade day is on or before 2026-11-10, the seen-data
  cutoff. Nothing after 2026-11-10 is part of this lane.

## Statistics
- Per book: events n, mean net per trade at 1x, 2x and 3x, sd, and t = mean / (sd / sqrt(n)), events treated as
  independent days.
- **Block bootstrap (reported):** moving blocks of 2 consecutive events in date order, 10,000 replicas, seed 536; the
  2.5 and 97.5 percentiles of the 1x mean and the share of replicas at or below 0.
- **Placebo (deciding):** 1,000 books, each on n days drawn without replacement (seed 536) from the pool of every
  eligible signal day in the window (thresholds defined, bars present, d_t not 0), with the same book rule and costs.
  The book's 1x mean must exceed the 97.5th percentile of the placebo means. The book's percentile among them is
  reported.

## Decision (gate 0 on history decides)
Per book: **EARNED** when all hold: n >= 30; 1x mean net per trade > 0 with t >= 2.0; 2x mean > 0; 1x mean above the
placebo's 97.5th percentile. Otherwise **NULL**.
- Registry verdict: PARTIAL if either book is EARNED (history only; a forward lane would have to confirm it before
  anything else), NULL if both are NULL. F and R are near mirror images, so at most one can be EARNED.
- An EARNED book is paper evidence on seen LLP returns only. It admits nothing to real money; `lab.gate.go_real()`
  and the owner decide.

## Reported, not deciding
- House-loss and house-win events separately: n, mean at 1x/2x/3x and t per book.
- Gross mean, mean funding per trade, the all-days mean (every pool day traded) and the pool size.
- ETH on Hyperliquid and LIT on Lighter with the same LLP events, each asset's own day-t direction and the same 13 bp
  costs (Lighter's Standard account charges 0 fees; the 13 bp stand for spread and impact and keep the books
  comparable). LIT trades only from its first bars (2026-01-02).
- Days with fewer than 24 funding settlements, and the fetched-versus-recorded close check.

## Power
About 572 signal days and about 20% events, so about 114 events. With a BTC daily sd near 2.5%, the standard error of
the mean is about 0.23% a trade, so t >= 2 needs a mean net near +0.47% a trade at 1x.

## What the author has seen
- LLP's own returns in full: R446 (`experiments/dexvault_v1`), R447, and the 2026-11-13 intake's tables (largest days
  2025-03-03 -6.73%, 2025-02-26 -6.26%, 2025-10-11 -5.35%, 2025-02-03 +8.92%; 17 of the 20 largest days in
  January to March 2025; monthly returns). So which days are LLP's extremes is known.
- LIT perp's daily path (R447 and the intake: peak 2026-09-24, trough 2026-03-31, largest daily moves, funding by
  month).
- BTC's broad path over 2025-2026 as public knowledge (for example the 2025-10-10 crash). No Hyperliquid BTC or ETH
  bar or funding value was read by this author; the recorder's `hl/` files were listed (names, columns, one header
  line) but no BTC or ETH value was read.
- No statistic relating LLP's return to any later price was computed, by the intake (it states so) or here.
- Because the extreme LLP days are known and some coincide with known BTC crash days, the read is on seen data. That is
  why an EARNED book is only history evidence.

## Trials and reading
- 2 trials (F, R). The program total before this lane is 9,785,286 (after R483), 9,785,288 after it.
- Read against `registry.program_trials()`. One deciding instrument; ETH and LIT are reported and add no trials.

## Limits
- Funding is on the entry notional, not the drifting position value (second order).
- Hourly settlement rates are summed; a missing hour adds 0 and is reported.
- One unit a trade, no compounding, no liquidation (1x notional against one day's move).
- The LLP series starts when Lighter was small (open interest $2m to $80m in early 2025, intake SRC1113-006), so its
  early extremes may say little about BTC.
- Venue risk of Lighter and Hyperliquid is not priced.

## Stop rules
One run. No new thresholds, lookbacks, horizons, instruments or cost levels after seeing results; a change is a new
lane with a new id.

```inputs
0175dc90228817894a416c7754b13993912015fb436d5357e48c066b05ccf12e  scripts/run_llphouse.py
4db0a204d8b31cb3126c0ddd6b9fa2140f05ef55393cb6bbeb79f023980e3d59  scripts/fetch_llphouse.py
cebeec187af86ce6b01d824695bf884204a51a5b3e6ef2f3daf9fe9541e0d8e0  tests/test_run_llphouse.py
a58005353bf406cb84998f12af83384c5b451f72629f5d89356ab651b0903e0f  scripts/run_dexvault.py
c0e956f91ec66c6a48c0b146ab5ee0a69381c150f0cd32325ad85ea16b757184  scripts/run_xperp_carry.py
f1d1258247a5c3f88c797d1f5746d63555d6ea39cb373bafe156db7e7a58ecdf  scripts/record_dex_vaults.py
3ba7069fcd6c96ad6e0b6e1308113804c4142eb4f18ac68cb8ad5f1822fb734e  scripts/record_lit_hedge.py
637797de1f2a504a5ff7e7eac45a0741e571aa46a83a6998db946407be035ffc  research/intake/hlp_llp_lit_20261113.md
e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926  docs/GATES.md
```
