# PREREG: weekendlink_v1 (R244). Does BTC's weekend move set the direction of US equities on the first session after?

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R244
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_weekendlink.py`. Data: Binance BTCUSDT hourly klines (`data/klines_1h`, 2020-01 to 2026-09)
  and Yahoo daily QQQ and SPY via `lab/markets.py`. The runner records the data sha256.
- **Queue:** M198 (BTC weekend return and the NQ Monday open), restated as a tradeable rule on the ETFs. Yahoo's NQ=F
  and ES=F daily bars are stamped at midnight New York, so their "Monday open" cannot be placed in time (Sunday
  18:00 or Monday 09:30). QQQ and SPY open at 09:30.
- **Gate:** 0 (screen).

## What the author has seen
- R235: SPY/QQQ overnight drift and turn-of-month, 2000-2012. R239 and R241: no BTC-equity link was measured.
- Data structure only: the timestamps of NQ=F/ES=F bars (above) and the BTCUSDT coverage dates.
- No statistic of BTC weekend returns against equity returns has been computed.

## Definitions
- **First session of a week:** each ETF trading day whose previous trading day is in an earlier ISO week. That is
  Monday, or Tuesday after a Monday holiday.
- **BTC weekend move** before that session: `ln(BTC at 09:00 New York on the session day / BTC at 16:00 New York on
  the previous trading day)`, from hourly closes. DST is handled by converting New York times to UTC. The move is
  missing if either hour is missing.
- **Session return:** `adjclose / adj_open - 1` of the ETF on that day (09:30 to 16:00), with adjusted open =
  `open x adjclose / close`.
- **Gap (reported only):** `adj_open / previous adjclose - 1`. It cannot be traded: the open already contains it.

## Rules (two trials)
- **WKND-QQQ** and **WKND-SPY:** at the open of the first session, go long the ETF if the BTC weekend move is positive
  and short if it is negative. Exit at that session's close.
- Costs: 1 bp one-way at 1x, so 2 bp per trade.

## Test and stages
The test is per trade: the mean net return over the first sessions in a window, with a plain t-statistic (trades do
not overlap).
1. **Discovery 2020-01-01..2023-12-31** (about 200 trades). Pass if both hold:
   - 1x mean > 0 with t >= 2;
   - 2x mean > 0.
2. **Validation 2024-01-01..2025-06-30** (about 75 trades), for discovery passers. Pass if the 1x mean > 0 with
   t >= 1.5.
3. **Not read:** 2025-07 onward. That is the crypto holdout, spent at program level, and the BTC data ends 2026-09.

## Reported (not decided on)
- Per window, at 1x, 2x and 3x: trades, mean, t, hit rate, per year.
- The ETF's own first-session mean (always long), for comparison.
- **Gap measurement:** the slope and correlation of the gap on the BTC weekend move. This is the M198 question in its
  original, untradeable form.
- The slope of the session return on the BTC weekend move.

## Multiplicity
- Trials = 2.
- Program trials before: 9,471,951 (after R243's 14).

## Expectations
- The gap probably moves with BTC's weekend move, since both reflect weekend risk news. That is information already
  in the open price.
- What is left for the session after the open is likely nothing. Most likely NULL for both rules.
