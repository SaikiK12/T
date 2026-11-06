# PREREG: gexfilter_v1, S&P 500 dealer gamma (free SqueezeMetrics GEX) as a volatility filter for BTC and ETH

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R416
- **Owner (single writer):** Claude (session claude/yo-9a1k5w)
- **Date registered (UTC):** 2026-11-06
- **Method:** M486, the owner's reels of 2026-11-06 and the instruction "trouve ces gamma gratuit toi même". The free
  history found is SqueezeMetrics' daily S&P 500 GEX. Per-strike maps (the "660 node") have no free history; they are
  recorded from today by `scripts/record_cboe_chain.py`.

## Question
Does the S&P 500 dealer gamma exposure known after the US close predict BTC and ETH realized volatility over the next
US session, beyond VIX and the coins' own recent volatility? Low gamma should mean more volatility (c < 0).

## Data
- **GEX:** `data/squeezemetrics/DIX_20261106.csv`, SqueezeMetrics' public file (`docs/provenance/squeezemetrics.json`),
  3,903 US trading days from 2011-05-02 to 2026-11-05.
- **Coins:** Binance USD-M hourly bars, `data/klines_1h/BTCUSDT.parquet` and `ETHUSDT.parquet`, read from
  2021-01-01 00:00 UTC only. 2020 is reserved and never read.
- **VIX:** `data/cboe/VIX.parquet`, daily close.

## Rule (scripts/run_gexfilter.py)
For each US trading day d in the GEX file with a next trading day d':
- **Window:** W = [d' 12:00 UTC, d' + 1 day 12:00 UTC). It covers d''s US session. GEX(d) is about 15 hours old at its
  start. SqueezeMetrics does not state its publication time, so a one-day-later signal is reported as a check.
- **y:** log realized volatility over W, sqrt of the sum of 24 squared hourly log returns; at least 22 bars.
- **Controls, all known at the start of W:**
  - x1 = log RV over the 24 hours before W;
  - x2 = log(RV over the 168 hours before W / √7);
  - x3 = log VIX at d's close.
- **Signal:** the rank of GEX(d) among the 252 values ending at d, a fraction in (0, 1]. A rank uses past values only.
- **Model:** y = a + b1 x1 + b2 x2 + b3 x3 + c × rank, OLS. Newey-West t (Bartlett, lag 10) in trading-day order.
- **Windows by d':** IS = 2021-01-08..2025-06-30 (1,123 days in the plumbing); HOLD = 2025-07-01..2026-09-30 (314
  complete days). The holdout is unread for this family.

## Decision
**Trials:** 2 (BTC, ETH). Read against `registry.program_trials('registry/rounds.csv')`.

**GEX_FILTER for a coin** needs both:
1. IS: c < 0 with t ≤ −2.5;
2. HOLD: c < 0 with t ≤ −2.0.

**Otherwise NULL** for that coin.

**Reported, not decided:**
- the volatility ratio between rank 0.9 and rank 0.1, exp(0.8 c);
- R² with and without the signal;
- the signal one trading day later (`rank_lag`);
- a negative-GEX dummy instead of the rank;
- the model without VIX;
- mean |coin return| over W on days with rank ≤ 0.2 against the rest;
- an S&P 500 self-check: log |S&P 500 return on d'| on log VIX and the rank. This is the equity mechanism itself.

**What GEX_FILTER means:** a risk input. The lab could cut size or widen stops when the S&P 500 gamma is low. It is not a
direction signal and not a trade.

## What was seen before this freeze
- **The file's head and tail rows:** 2011-05-02/03, and 2026-11-04 (GEX 5.46 bn) and 2026-11-05 (1.84 bn). The S&P
  500 close went from 7,688.62 to 7,353.73, −4.4%. So GEX was high the day before the 5 November drop. That is one day,
  outside both windows.
- **Plumbing counts:** GEX < 0 on 153 IS days and 9 HOLD days.
- **Earlier crypto gamma tests:** R292 NULL (Deribit dealer gamma and next-day RV) and R295 NULL (option flow blocks).
- **BTC and ETH volatility** over these years has been read by many lanes; GEX has never been read by this lab.

## Limits (stated now)
- **SqueezeMetrics' own estimate:** its dealer convention and method are its own and not replicated here.
- **Overlap:** equity and crypto volatility share macro shocks. VIX and the coins' own lagged RV are the controls, but
  a common shock after d's close can still pass through.
- **No costs:** a volatility forecast, not a trade.

## Inputs frozen with this file
```inputs
a790ffa3748e6f59cc42092eec45f955f9022e043ee63ea38642917fbb091055  scripts/run_gexfilter.py
e673452733f27c90bc5634c302f1c5143bfc41c52a18cbfc4dbf4aceac6c1785  tests/test_run_gexfilter.py
17763aa98650afc11086245d477d8c07a429287b9316bc3197494c961b896f0e  data/squeezemetrics/DIX_20261106.csv
ee2577fa45bdbb6b8582ab86c63958bf53717db638ae2fe4a76d32000f45cb3b  data/klines_1h/BTCUSDT.parquet
071f96b6f779a6a69a08610ccf21e14905466a9941b14f3bcbdaaf192409fbb5  data/klines_1h/ETHUSDT.parquet
6c5a1e1ad3982bd90928f92968b65e62b0771874c17de77f7191c685ced11c91  data/cboe/VIX.parquet
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
```
