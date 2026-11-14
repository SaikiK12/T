# PREREG: vrpsell_v2, sell the crypto variance risk premium with delta-hedged weekly straddles on Deribit

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R409
- **Owner (single writer):** Claude (session claude/yo-9a1k5w); claimed on #7, comment 6668804543
- **Predecessor:** R408 (`experiments/vrpsell_v1`), frozen 2026-11-05 and abandoned before any statistic: its runner
  crashed on the tuple returned by `lab.stats.newey_west_t`. This file is R408's PREREG with only the id, the claim,
  this line, the runner name and its hash changed.
- **Date registered (UTC):** 2026-11-05
- **Method:** M477 (`docs/IMPROVEMENTS_20261105.md`, items 41-50)

## Question
Does selling one at-the-money BTC (or ETH) straddle each Friday on the next weekly Deribit expiry, delta-hedged every hour
on the perp and held to expiry, earn a positive net return after the measured bid-ask spread, the listed fees and the
hedge costs, on 2021-01 to 2026-09?

## Why now
The lab has never tested an option premium as a trade. Implied volatility on BTC is above realized volatility on most
days: R209 found DVOL above the trailing 30-day realized volatility on 82% of BTC days, by 8.6 vol points on average.
The equity version is real on average and is paid for its tails (R239, VIX). A premium that is paid to sellers would be
a new family, not a refinement of the price-signal families that failed at taker cost.

## Data and prior reads (gate 0)
- **Option prices:** `data/deribit_trades/<CUR>/flow/<YYYY-MM>.parquet` (`scripts/fetch_deribit_trades.py`). One row
  per hour and instrument, with the amount-weighted IV of all trades in that hour and the last index price. Every file
  read is checked against `docs/provenance/deribit_trades.json`.
- **Hedge prices:** Binance USDT perp 1-minute closes (`data/klines_1m/BTCUSDT.parquet`, `ETHUSDT.parquet`), taken on
  the hour.
- **Funding:** Binance funding (`data/fundingRate/BTCUSDT.parquet`, `ETHUSDT.parquet`).
- **Window:** Fridays 2021-01-01 to 2026-09-18, so the last expiry is 2026-09-25. Nothing before 2021 is read; 2020 is
  reserved.
- **Prior reads.** This is gate 0: the data are seen, and only the question is new.
  - R209 read DVOL minus trailing realized volatility as a direction timer.
  - R292, R295, R296 and R307 read these flow files for dealer gamma, signed flow, expiry and the 25-delta risk
    reversal, including option IVs.
  - No lane has computed the P&L of selling options.
- **Plumbing, before this freeze, counts only:** all 299 Fridays have a two-legged at-the-money strike on the next
  weekly expiry in the 08:00 UTC hour, for both BTC and ETH. No P&L, IV level or realized volatility was computed.

## Rule (scripts/run_vrpsell2.py)
- **Entry.** On each Friday D:
  - **Expiry:** E = D + 7 days, 08:00 UTC.
  - **Hour:** the first hour starting at 08:00, 09:00, 10:00 or 11:00 UTC whose flow rows hold both the call and the put
    of one strike for E, each with an IV between 10 and 300.
  - **Strike:** among those, the strike nearest the perp price at the start of that hour.
  - **Sale:** at the end of that hour, at volatility (call IV + put IV)/2 minus m x the half-spread, priced by
    Black-Scholes with zero rates and the perp price as forward.
- **Hedge.** At the end of each hour until E, hold 2N(d1) - 1 coins long on the perp. d1 uses the mid IV (not scaled),
  the current perp price and the time left. The hedge is closed at E.
- **Settlement.** The payoff is |S_E - K|, where S_E is the perp price at 08:00 UTC on expiry day. This is a proxy for
  Deribit's 30-minute index average.
- **Costs at m = 1, 2, 3.** Everything is scaled by m except funding.
  - **Half-spread:** 0.9 vol points for BTC and 1.1 for ETH. These are the medians of the 6 nearest-the-money
    13NOV26 quotes per coin on 2026-11-05 20:4x UTC (`costs_measured_20261105.json`).
  - **Option fee:** 0.03% of the underlying per leg, capped at 12.5% of the leg price. Deribit lists `taker_commission`
    0.0003 for options.
  - **Delivery fee:** 0.015% of the underlying on the leg that finishes in the money, capped at 12.5% of its payoff
    (assumed from Deribit's fee schedule).
  - **Hedge fee:** 5 bp of notional on every change in the hedge, including its opening and closing. Deribit lists
    3.5 bp for its perp, so this is conservative.
  - **Funding:** Binance funding, paid by a long hedge when the rate is positive. It is not scaled.
- **Unit.** One straddle on 1 coin. The weekly return r is the net P&L divided by the entry perp price (fraction of one
  coin's notional).

## Decision
- **Trials:** 2 (BTC, ETH). The read is against `registry.program_trials('registry/rounds.csv')`.
- **PASS for a coin** needs every one of these:
  1. mean weekly r at 1x > 0;
  2. Newey-West t (lag 2) at 1x >= 2.24 (one-sided 1.25%, Bonferroni over 2);
  3. mean at 2x > 0;
  4. mean at 1x > 0 in each half: weeks entered 2021-01-01 to 2023-12-31, and 2024-01-01 to 2026-09-30;
  5. the 5%-trimmed mean at 1x (both tails) > 0;
  6. the mean at 1x without the 10 best weeks > 0.
- **Otherwise NULL** for that coin.
- **Reported, not decided on:** 3x; the gross (m = 0) and unhedged series; mean IV minus realized volatility over the
  hold; worst week, maximum drawdown, hit rate and annualized mean; entries per hour bucket and skipped weeks.
- **What a PASS earns.** A forward paper lane on Deribit's live books, with bid prices from the order book and its own
  frozen protocol. A PASS is not a real-money result. Margin, path risk on the short legs and Deribit account access
  are not tested here.

## Known limits (stated now)
- **IV is a proxy for the price.** The amount-weighted IV of the trades in an hour is mid-like. The sale is priced at
  that IV minus one measured half-spread from a single snapshot; spreads in stress weeks were wider. 2x and 3x stand for
  that.
- **Settlement is approximated.** The perp price at 08:00 UTC stands in for Deribit's 30-minute index average.
- **Hedge and risk are simplified.** The hedge uses the mid IV and fixed hourly rebalancing. A short straddle has large
  tail losses; the worst weeks and the drawdown are reported with the verdict.
- **One strike.** There is no strangle, no wing protection and no position sizing. A PASS would be the premium's
  existence at executable cost, not a finished book.

## Inputs frozen with this file
```inputs
e3f3fd9aa244be01311755fe971b8091bd36f8bd2ee3b88ffe33e3d730a1821d  scripts/run_vrpsell2.py
7df0959df85c12323c948e6301b3a5d7f1a05c4464e534197fa546f800a8c665  scripts/run_optflow.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
bdd8db8ac836de24f67f4cc796ea483a552bccc36c2ba37ebe0cbc0c686ec742  experiments/vrpsell_v1/costs_measured_20261105.json
9ab09b14cc503d6ead4ca14ea16c0e32ed0f428a82b52c0cbf17567797d6a188  docs/provenance/deribit_trades.json
9e2c7fd717811a58bca2fa5816b92b4bf59aaa5d9706c10af2522af04a1c82a0  data/klines_1m/BTCUSDT.parquet
7c7c05b387d59fd3e40555718c28388fb66c737602102297a34de9af9c67da70  data/klines_1m/ETHUSDT.parquet
b1cb8c15d60cc2495a8215e9c081e196c069ebf9a324f0e164a69ebdf2536ae3  data/fundingRate/BTCUSDT.parquet
3b640724ed7ed8985b3b8ce41d5ffb6b3eaea7a6b399389ee50ceb91ef2b2e89  data/fundingRate/ETHUSDT.parquet
```
