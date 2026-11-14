# FINDINGS: llphouse_v1 (R484, M536)

**Verdict: NULL for both books.** On the 99 days when Lighter LLP's return fell outside its prior-90-day 10th to 90th
percentile band, following BTC's same-day move over the next UTC day (book F) lost 0.16% a trade at 1x (t -0.64), and
reversing it (book R) lost 0.10% (t -0.39). Before costs both are within 0.03% of zero. LLP's extreme days carry no
usable information about BTC's next day on Hyperliquid at these costs.

- Frozen PREREG sha256 `0e2d35d72743514028824eb0d8c4188f289233528c090e3042c7b87f3667d1be` (commit `2025a9ee`), before
  the Hyperliquid fetch and before any LLP-against-later-price statistic.
- Fetch once after the freeze (commit `28aaf129`): 68 byte-exact bodies, `raw/manifest.json` sha256
  `2a48a12f617daf7e081faff01ec167d6aae7e68f2adc992a8b1c63308897ac27`. BTC and ETH: 679 daily bars 2025-01-01 to
  2026-11-10 and 16,296 hourly funding settlements each (2025-01-01 00:00 to 2026-11-10 23:00 UTC), no gap above one
  hour inside that range.
- The fetch stops one settlement short of the PREREG's "to the 2026-11-11 00:00 settlement": `fetch_llphouse.py`
  sets `endTime` to 2026-11-11 00:00:00.000, and Hyperliquid settles a few milliseconds past the hour (the last one
  fetched is 2026-11-10 23:00:00.008), so the 2026-11-11 00:00 settlement is not in `raw/`. Trade day 2026-11-10
  therefore holds 23 funding hours, not 24 (`short_funding_days` 1 for BTC and ETH in `report.json`). No event trades
  on 2026-11-10 (the last event's signal day is 2026-09-28), so only the placebo pool's last day is affected; a
  Hyperliquid hourly rate is typically about 0.001%, so one missing hour cannot move the verdict. Noted after review (2026-11-13), not re-run.
- LLP and LIT from `claude/okx-xperp-data` at `0364bbc63ec3bc4d7cc135ff4b060cabf8127062`. One run, 2026-11-13
  (`run.log`; `results/events.csv`, `results/report.json`).
- Fetched closes against the recorder's `hl/candles_1d/` on the 101 common days (2026-08-02 to 2026-11-10): largest
  relative gap 0.0 for BTC and ETH.

## Window and events
- Signal days 2025-04-17 to 2026-11-09 (572 days, every one with thresholds and a BTC trade). Trade days end on
  2026-11-10.
- **99 events: 51 house-loss, 48 house-win.** First 2025-04-22, last 2026-09-28. No event after 2026-09-28: LLP's
  October and November 2026 days stayed inside their band.
- Events by year: 19 in 2025 (April to December), 80 in 2026 (8, 14, 8, 2, 8, 12, 13, 6 and 9 from January to
  September). A likely reason, not checked: the 2025 lookbacks held LLP's large early-2025 days, which widened the
  band.
- Stamp hour of the event days: 71 at 20:00 UTC, 28 at 21:00 UTC. Every stamp was before the trade's 00:00 UTC open
  (the runner checks it).
- The predicted event count was about 114 (20% of days); 99 is 17% because percentiles of a 90-day window with ties
  and drift do not give exactly 10% a tail.

## Deciding: BTC perp on Hyperliquid (mean net per trade)

| Book | n | 1x mean | 1x t | 2x mean | 2x t | 3x mean | 3x t | Gross mean | Funding a trade | Placebo 97.5th pct | Book's placebo percentile | Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F (follow) | 99 | -0.162% | -0.64 | -0.292% | -1.15 | -0.422% | -1.67 | -0.032% | +0.003% | +0.326% | 31.8 | NULL |
| R (reverse) | 99 | -0.098% | -0.39 | -0.228% | -0.90 | -0.358% | -1.41 | +0.032% | -0.003% | +0.194% | 68.2 | NULL |

- Gross mean includes funding and excludes the 13 bp round trip. Funding is small: about 0.003% a trade.
- **Block bootstrap (2-event blocks, 10,000 replicas), 1x mean:** F 95% band -0.667% to +0.330%, 74% of replicas at
  or below 0; R -0.590% to +0.407%, 65% at or below 0.
- **Placebo:** 1,000 books of 99 random days from the 572-day pool (seed 536). The pool's own means are -0.086% (F)
  and -0.174% (R; t -1.94 over 572 days, a mild tendency for BTC's day to continue rather than reverse). Neither book
  beats its placebo's 97.5th percentile. F sits at the 31.8th percentile, R at the 68.2nd.
- Every condition fails for both books except n >= 30: 1x mean below 0, t far below 2, 2x mean below 0.

## House-loss vs house-win (reported, not deciding), BTC

| Book | Kind | n | 1x mean | 1x t | 2x mean | 3x mean |
|---|---|---|---|---|---|---|
| F | house-loss | 51 | -0.146% | -0.48 | -0.276% | -0.406% |
| F | house-win | 48 | -0.180% | -0.43 | -0.310% | -0.440% |
| R | house-loss | 51 | -0.114% | -0.38 | -0.244% | -0.374% |
| R | house-win | 48 | -0.080% | -0.19 | -0.210% | -0.340% |

The two halves agree: no side of LLP's extreme days says anything about BTC's next day.

## ETH (Hyperliquid) and LIT (Lighter), reported, not deciding

Same LLP events, each asset's own day-t direction, the same 13 bp costs.

| Asset | Book | n | 1x mean | 1x t | 2x mean | 3x mean | Bootstrap 95% band (1x) | Placebo pct |
|---|---|---|---|---|---|---|---|---|
| ETH | F | 99 | +0.030% | 0.08 | -0.100% | -0.230% | -0.687% to +0.742% | 56.9 |
| ETH | R | 99 | -0.290% | -0.75 | -0.420% | -0.550% | -1.002% to +0.427% | 43.1 |
| LIT | F | 80 | -1.230% | -1.54 | -1.360% | -1.490% | -2.858% to +0.074% | 4.7 |
| LIT | R | 80 | +0.970% | 1.21 | +0.840% | +0.710% | -0.334% to +2.598% | 95.3 |

- ETH: 51 loss and 48 win events. The house-loss half of F was +0.268% (t 0.51) and of R -0.528% (t -1.01); neither
  is far from noise.
- LIT: 80 events from 2026-01-09 (41 loss, 39 win); 9 pool days had fewer than 24 funding settlements. Reversing LIT's
  day after an LLP extreme made +0.97% a trade at 1x (t 1.21, 2x +0.84%, 3x +0.71%), at the 95.3rd placebo
  percentile, below the 97.5th. LIT's daily sd is about 6.5% (intake), so this is one t of 1.2 among four reported
  books; it is not a finding. If it is ever tested, it is a new lane on forward days with its own trials.

## Trials and reading
- 2 trials (F, R). `registry.program_trials()` = **9,785,288** after this round. A NULL at t below 1 needs no
  multiplicity correction to be read as a NULL.

## Costs
1x: 13 bp a round trip (Hyperliquid tier-0 taker 4.5 bp a side plus 2 bp slippage a side) plus hourly funding. 2x and
3x scale fee plus slippage only. Every book is negative at 2x and 3x on BTC; the cost level does not decide the
verdict, because the gross is within 0.03% of zero.

## What this rules out, and what it does not
- Out: using LLP's day return as a one-day directional signal on BTC (follow or fade its same-day move), with this
  10/90 band and a 90-day lookback, on 2025-04 to 2026-11.
- Not tested: LLP's return as a predictor of volatility rather than direction, other horizons, Lighter's
  `exchangeMetrics` liquidation volume (M536's other input, intake SRC1113-006), or HLP. None of these may reuse this
  window as if unseen.
- Seen data: LLP's extreme days were known before the freeze (R446, R447, the intake). That would have favoured a
  hit; there is none.

Paper only. No order, no money, no key.
