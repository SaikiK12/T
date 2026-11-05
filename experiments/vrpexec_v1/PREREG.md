# PREREG: vrpexec_v1, R409's weekly short straddle with a maker sale, a band hedge and a maker-first hedge

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R410
- **Owner (single writer):** Claude (session claude/yo-9a1k5w); claimed on #7, comment 6669179798
- **Date registered (UTC):** 2026-11-05
- **Method:** M477 (`docs/IMPROVEMENTS_20261105.md`, items 11 and 42)

## Question
Does R409's trade earn a positive net return when it is executed with three cost levers together, on 2021-01 to
2026-09?
- **The trade:** sell one at-the-money BTC (or ETH) straddle each Friday on the next weekly Deribit expiry, delta-hedge
  it on the perp, and hold it to expiry.
- **The levers:**
  1. a maker sale at the ask in place of a taker sale at the bid;
  2. a no-trade band of 0.10 coins of delta around the hedge target;
  3. maker-first hedge orders.

## Why, and what was seen (gate 0, post-hoc)
This lane is designed after R409's result, and that is disclosed here.
- **R409 (NULL):** −12.2 / −18.0 bp a week at 1x for BTC / ETH; gross +44.0 / +40.8.
- **R409's post-hoc cost split** (`experiments/vrpsell_v2/results/cost_decomposition.json`):
  - the hourly taker hedge fee was about 39 bp a week, two thirds of the 1x cost;
  - the option spread was 10-12 bp and the option fees 6 bp.
- **What the levers cut, roughly:** a band and maker hedge orders cut the first; a maker sale cuts the second.
- **The data:** the option prices, the perp prices and R409's gross series are all seen. Only these are new: the raw
  trades of the two legs on each Friday morning, and the execution model.
- **The primary cell** was chosen before any cell below was computed, from this reasoning. A band of half-width b cuts
  a hedge's turnover to about s²/(2b) per hour, where s is the hourly move of the target. It adds a residual delta that
  is uniform on ±b. At b = 0.10 that is about 3 coins a week against 7.8. The residual adds about 0.5% of notional to
  the weekly standard deviation, against about 1.65% for R409's weekly r. At b = 0.20 the residual doubles.
- **A PASS here is gate 0 on seen data.** It earns only forward paper evidence on fills and spreads (R412), not a
  real-money step.

## Data
- **Straddle legs:** `data/deribit_trades/<CUR>/atm_windows.parquet`, written by `scripts/fetch_deribit_atm_windows.py`
  on 2026-11-05 from Deribit's public history server.
  - Each Friday D gives every trade of the two legs from D 00:00 to 12:00 UTC: price, mark price, IV, index, taker
    direction and amount.
  - The legs are the strike `scripts/vrpexec_rule.pick_strike` names, point in time: both legs traded in the 24 hours
    before 08:00, and the strike is the one nearest the perp price at 08:00 (ties: the lower).
  - Hashes are in `docs/provenance/deribit_atm_windows.json`, and the runner checks them.
  - BTC: 299 Fridays, 40,693 trades. ETH: 299 Fridays, 32,960 trades. Each coin took 598 requests, and every Friday
    had a strike.
- **Plumbing before this freeze, counts only** (`plumbing.log`): 292 BTC weeks and 289 ETH weeks have every
  reference and a complete perp path.
  - BTC skips: 3 no reference, 4 no price path. ETH skips: 7 no reference, 3 no price path.
  - The full pipeline was also dry-run once on synthetic random-walk prices to catch crashes. Its outputs are noise
    by construction and were not kept.
- **Perp:** Binance USDT perp 1-minute bars (`data/klines_1m/BTCUSDT.parquet`, `ETHUSDT.parquet`):
  - closes on the hour, for the path, the hedge and settlement;
  - each hour's lowest low and highest high, for maker hedge fills.
- **Funding:** Binance funding (`data/fundingRate/*.parquet`).
- **Window:** Fridays 2021-01-01 to 2026-09-18, as R409. Nothing before 2021 is read; 2020 is reserved.

## Rule (scripts/vrpexec_rule.py, scripts/run_vrpexec.py)
- **Reference IV of a leg at instant t:** the Black-Scholes IV of the mark price on that leg's last trade before t, with
  zero rates and forward = the trade's index.
- **Taker sale.** Both legs are sold at D 09:00, at reference IV − m × half-spread, priced at the perp. The hedge starts
  at 09:00.
- **Maker sale.**
  - At D 08:00 each leg posts a resting sell at its reference IV + one half-spread, priced at the perp, in coin units,
    rounded up to the tick (0.0001; 0.0005 above 0.005).
  - The order is never repriced.
  - It fills at its limit if a taker buy on that leg prints strictly above the limit before 12:00. The premium is
    converted to USD at that trade's index.
  - A leg still open at 12:00 sells at taker, as above, at 12:00.
  - The hedge starts at 12:00, so a leg filled earlier is unhedged until then.
- **Hedge.**
  - **Target:** 2N(d1) − 1 coins long, at the hedge-start reference IV (the mean of the two legs).
  - **Rebalancing:** hourly to the target, or with a band b only when |target − held| > b, to the band's near edge.
  - **Taker orders** pay the taker fee at the hour close.
  - **Maker-first orders** post at the hour close and fill at that price if any 1-minute bar in the next hour trades
    through it: a low below the price for a buy, a high above it for a sell. They then pay the maker fee. Otherwise
    they cross at the next hour close at the taker fee.
  - The hedge is closed at E at taker.
- **Settlement:** |S_E − K|, with S_E the perp at 08:00 UTC on expiry day (as R409).
- **Cells:** 2 sales × 6 hedges.
  - Sales: taker, maker.
  - Hedges: hourly, band 0.10, band 0.20, each as taker or maker-first.
- **Primary cell: maker sale, band 0.10, maker-first hedge** (`maker/band10_mk`).
- **Costs at m = 1, 2, 3.** Everything is scaled by m except funding.
  - **Half-spread:** 0.9 vol points for BTC, 1.1 for ETH (as R409, `experiments/vrpsell_v1/costs_measured_20261105.json`).
  - **Maker sale give-back:** a filled maker leg gives back (m − 1) times its distance from the mid. So it is sold at
    the limit at 1x, at the mid at 2x and about at the bid at 3x.
  - **Option fee:** 0.03% of the underlying per leg, capped at 12.5% of the leg price. Deribit lists the same fee for
    maker and taker.
  - **Delivery fee:** 0.015%, capped at 12.5% of the payoff (as R409).
  - **Hedge fees:** taker 5 bp and maker 2 bp of notional. These are Binance VIP0; Deribit's perp lists 3.5 / 1.5 bp.
  - **Funding:** not scaled.
- **m = 0** (reported only): sale at the mid, no fees.
- **Unit:** one straddle on 1 coin. The weekly r is net P&L divided by the perp price at D 08:00.
- **Skips:** a week is skipped in every cell if any leg has no trade before the instant it needs, or if the perp path
  from D 08:00 to E has a gap.

## Decision
- **Trials:** 2 (the primary cell on BTC and on ETH). The read is against `registry.program_trials('registry/rounds.csv')`.
- **PASS for a coin** needs all of R409's six checks on the primary cell:
  1. mean weekly r at 1x > 0;
  2. Newey-West t (lag 2) at 1x ≥ 2.24 (one-sided 1.25%, Bonferroni over 2);
  3. mean at 2x > 0;
  4. mean at 1x > 0 in each half (Fridays 2021-2023, and 2024 to 2026-09);
  5. the 5%-trimmed mean at 1x > 0;
  6. the mean at 1x without the 10 best weeks > 0.
- **Otherwise NULL** for that coin.
- **Reported, not decided on:**
  - **The other 11 cells**, at m = 0-3, each with the same statistics. They show each lever alone. **None is ever
    promoted:** any of them would be a new lane, with its own trials.
  - the 1x cost split of every cell;
  - hedge turnover, and the maker hedge fill rate;
  - maker sale fills: share of legs, both legs, and minutes to fill;
  - skips.

## Known limits (stated now)
- **The maker fill model is a trade-through proxy without queue position.** Our order is assumed filled when a taker
  buys strictly above it. A buyer who lifts a better price would have hit our cheaper order first, but hidden size,
  other makers and the price's own moves are not modeled. R412 measures this forward with the live queue.
- **Spreads came from one 2026-11-05 snapshot.** Stress weeks were wider; that is what the 2x and 3x stresses stand for.
- **The reference IV may be stale** when the last trade before an instant is old. Deribit's mark moves with the
  underlying; ours is held at sticky strike from that trade.
- **Maker hedge fills use Binance 1-minute bars.** A low below our price is a trade-through, but the hedge size is
  assumed to fit; at 1 coin it does.
- **Settlement, margin and the unhedged hours** are simplified as in R409. The worst weeks and the drawdown are
  reported with the verdict.

## Inputs frozen with this file
```inputs
c6aec87fa290dd8606eef4b49c46132385612ebff58617334557b3f7b251eb5d  scripts/run_vrpexec.py
b86232f09023eefe2657deb380cef6030ab37e0a5c28f0db23e705fd5c83c597  scripts/vrpexec_rule.py
e5b6422426e1630719ace1ab71cd70931385fa8fc11c000dd8f05b56e0e260d7  scripts/fetch_deribit_atm_windows.py
e3f3fd9aa244be01311755fe971b8091bd36f8bd2ee3b88ffe33e3d730a1821d  scripts/run_vrpsell2.py
7df0959df85c12323c948e6301b3a5d7f1a05c4464e534197fa546f800a8c665  scripts/run_optflow.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
2f2e4811a85ad142f378a1fc234c0b95b1a45f8fe77e027175ff05ac706d4841  docs/provenance/deribit_atm_windows.json
9ab09b14cc503d6ead4ca14ea16c0e32ed0f428a82b52c0cbf17567797d6a188  docs/provenance/deribit_trades.json
bdd8db8ac836de24f67f4cc796ea483a552bccc36c2ba37ebe0cbc0c686ec742  experiments/vrpsell_v1/costs_measured_20261105.json
9e2c7fd717811a58bca2fa5816b92b4bf59aaa5d9706c10af2522af04a1c82a0  data/klines_1m/BTCUSDT.parquet
7c7c05b387d59fd3e40555718c28388fb66c737602102297a34de9af9c67da70  data/klines_1m/ETHUSDT.parquet
b1cb8c15d60cc2495a8215e9c081e196c069ebf9a324f0e164a69ebdf2536ae3  data/fundingRate/BTCUSDT.parquet
3b640724ed7ed8985b3b8ce41d5ffb6b3eaea7a6b399389ee50ceb91ef2b2e89  data/fundingRate/ETHUSDT.parquet
```
