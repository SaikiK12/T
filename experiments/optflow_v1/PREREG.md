# PREREG: optflow_v1 (R295). Does signed Deribit option flow lead BTC and ETH perp returns over the next 1-24 hours? (M311, M313)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R295 (Claude block R280-R299, claimed on issue #7 on 2026-10-22 before this freeze).
- **Methods:**
  - **M311:** Deribit block trades as crypto's dark-pool prints. Signed, delta-weighted block notional leads the perp.
  - **M313:** QuantData's net drift, crypto version. Signed option premium by aggressor leads the perp.

  Both are from the owner's term list (`docs/AUCTION_AND_FLOW.md`, `docs/QUANTDATA.md`). They are run as one family
  on one data set.
- **Owner (single writer):** the Claude session that froze it.
- **Code:** `scripts/run_optflow.py`, tested on synthetic data in `tests/test_run_optflow.py`:
  - the signs of calls, puts, blocks and out-of-the-money options;
  - a flow row is known only after its hour;
  - the z-score reads only the past;
  - non-overlapping rule trades and their costs;
  - a planted lead is found at its signal and horizon only, and a lead with the wrong sign is not a pass;
  - the input files are hash-checked and only the window's months are read.

  It calls `verify()` on this file first and checks every input's sha256 against the block below. It also checks
  each Deribit flow file it reads against its hash in the provenance record.
- **Execution mode:** API (hourly decisions; holds of 1-24 h). A pass is a mechanism. A trading lane needs the
  reported rule to be net positive at 1x and 2x, and then its own id.
- **Gate:** 0.
  - The perp bars were read by R289-R293.
  - R292 read the Deribit flow files for dealer gamma (positions and IVs, daily). No lane has read the flow's
    direction against returns.

## What the author has seen
- **R292 in full** (`dealerflow_v1`, NULL). Dealer gamma from the same flow files does not explain next-day
  volatility or the sign of next-day hourly autocorrelation. Hourly returns mean-revert a little on every kind of day
  (mean ac −0.01 to −0.04).
- **R289:** a Friday move inside Deribit's 07:30-08:00 UTC settlement window reverses. **R291:** VPIN adds nothing
  beyond volume. **R293:** the first UTC hour reverses (post hoc, M315).
- **The flow file layout** (column names) and the block file layout.
- **A plumbing run on the real files, before this freeze** (`--plumbing`), which printed counts only:
  - flow rows from 2021: 4,926,124 (BTC) and 3,827,847 (ETH);
  - hours with trades: 50,370 and 50,369;
  - hours with a block trade: 32,216 and 24,258;
  - share of traded amount that is block trades: 37% (BTC) and 27% (ETH);
  - share of traded amount without a delta (no IV or at expiry): 0.2%;
  - missing price instants: 5 and 4;
  - per horizon and window, the decision hours with both x and r defined: about 24,100 per coin in each window.

  No signal value, return, product or statistic was printed.

## Inputs (frozen)

```inputs
9e2c7fd717811a58bca2fa5816b92b4bf59aaa5d9706c10af2522af04a1c82a0  data/klines_1m/BTCUSDT.parquet
7c7c05b387d59fd3e40555718c28388fb66c737602102297a34de9af9c67da70  data/klines_1m/ETHUSDT.parquet
9ab09b14cc503d6ead4ca14ea16c0e32ed0f428a82b52c0cbf17567797d6a188  docs/provenance/deribit_trades.json
6ca16dedc98b89f2dfee199c2f06936db2b16005aac65493a500f20797ab5abe  lab/exposure.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
7df0959df85c12323c948e6301b3a5d7f1a05c4464e534197fa546f800a8c665  scripts/run_optflow.py
```

The Deribit flow files (`data/deribit_trades/{BTC,ETH}/flow/2021-01 .. 2026-09.parquet`, 138) are pinned through the
provenance record, which holds each file's sha256.

## Data
- **Options:** every Deribit BTC and ETH option trade (inverse options, one coin per contract), reduced to hourly
  flow per option by `scripts/fetch_deribit_trades.py`.
  - A flow row for hour t holds the trades in [t, t + 1 h), so it is known at t + 1 h.
  - Each row has taker buy and sell amounts (coins), the block amounts by side, the amount-weighted IV (percent), the
    premium paid (coins) and the last index price.
  - Only rows from 2021-01-01 are read. Pre-2021 option flow is not needed and stays unread.
- **Perps:** Binance USD-M BTCUSDT and ETHUSDT 1-minute bars, 2021-01-01 to 2026-09-30 (2020 is reserved).
  - The price at instant T is the close of the valid 1-minute bar that ends at T (`run_clockflow.load_prices`).
  - A missing bar leaves that price undefined.

## Signals (per currency and flow row hour t, in USD)
With Δ the Black-76 delta (`lab/exposure.py`): F is the row's index price, T runs from the middle of the hour to
expiry (08:00 UTC), r = 0, and σ is the row's IV. A row with no delta is left out of the two delta signals.

| Signal | Method | Per option-hour, summed over options |
|---|---|---|
| `block_delta` | M311 | (block taker buys − block taker sells) × Δ × F |
| `screen_delta` | M311 (the order-book counterpart) | ((buys − block buys) − (sells − block sells)) × Δ × F |
| `drift` | M313 | ±premium × F × (buys − sells) / (buys + sells), + for calls, − for puts |
| `drift_otm` | M313 | `drift` over out-of-the-money options only (call strike > F, put strike < F) |
| `drift_screen` | M313 | ±premium × F × ((buys − block buys) − (sells − block sells)) / (buys + sells) |

- **Net drift** follows QuantData's definition: bullish = call taker buys + put taker sells.
- An option-hour's signed premium is approximated from the hourly total, as M313's note sets out.

## Features (at each UTC hour T, per currency)
- **Window:** the signal summed over the rows in [T − W h, T), with W = h (the horizon). An hour without trades
  counts 0.
- **x_T:** that sum minus its mean over its previous 720 hourly values, divided by their standard deviation (at
  least 500 defined), winsorized at ±5.
- **Target:** r_T = log(P(T + h) / P(T)) of the same currency's perp.

## Windows (by decision hour T; the return must end inside the window)
- **Discovery:** 2021-04-01 .. 2023-12-31.
- **Validation (out of sample):** 2024-01-01 .. 2026-09-30.

## Tests (15 trials: 5 signals × 3 horizons, h ∈ {1, 4, 24} hours)
- **Statistic:** u_T = Σ over the two currencies of x_T × r_T, and the Newey-West t (`lab.stats.newey_west_t`, lag
  max(5, h)) of its mean within a window, over every decision hour.
- **Predicted sign:** positive for all five. Flow that buys delta, or premium on the bullish side, leads a rise.
- **A trial passes when both hold:**
  - the validation t is ≥ 2.94;
  - the discovery t is positive.
- **The bar:** 2.94 is Bonferroni over the 15 trials (two-sided 5%).
- **A significant opposite sign** (validation t ≤ −2.94 with a negative discovery t) is recorded as a finding. It is
  not a pass.

## Decision
- **PARTIAL** if any of the 15 trials passes: option flow leads the perp at that signal and horizon.
  - A pass earns a forward paper lane (new id, API) **only if** its rule's validation mean net per trade is positive
    at both 1x and 2x cost.
  - Otherwise it is a mechanism without a trade at API cost, and it is recorded as such.
- **NULL** if none passes. M311 and M313 are then TESTED for the 1-24 h perp lead.

## The rule (reported, and the condition for a lane)
- **Per currency:** at a decision hour with no open position and |x_T| ≥ 1, take the sign of x_T on the perp for h
  hours. No overlap.
- **Per trade:** gross = side × r_T, and net = gross − 2 × cost.
- **Costs:** API, 8.5 / 17 / 25.5 bp per side at 1x / 2x / 3x (R289's API figure).
- **Reported:** trades, mean gross and net in bp, the t of the 1x net, and the hit rate. Discovery and validation
  are reported separately.

## Reported (not decided on)
- the t per currency in each window;
- the validation t by year (2024, 2025, 2026);
- the descriptives above (block share, hours with blocks, amount without a delta);
- the hourly frame (x and r per currency, signal and horizon) in `data/optflow_v1/hourly.parquet` (gitignored);
- the result read against `registry.program_trials()`.

## Outputs
- `experiments/optflow_v1/results/summary.json`.
- FINDINGS.md is written after the run.

## Known limits (written before the result)
- **Taker is not customer.** Deribit's taker side is the aggressor's, and market makers also take. Blocks are
  negotiated, and which party is the "taker" of a block leg is Deribit's convention.
- **Opening and closing are unknown,** and combos are not separated: a spread's legs are signed one by one.
- **Signed premium is approximate:** the hourly file keeps one premium total per option-hour.
- **One venue:** Deribit's inverse options only. Not covered: USDC options, OKX, Bybit, Binance and CME.
- **Delta** uses the row's index price, the amount-weighted IV and r = 0. Near expiry it is sensitive to both.
- **Hourly sampling:** a lead shorter than an hour is invisible, and a lead inside the first hour is counted only
  from the hour's end.
- **API costs** of 17 bp a round trip dwarf most hourly leads. The test decides on the predictive t, and the rule
  shows whether a pass trades.

## Multiplicity
- Trials: 15.
- Program trials before this lane: 9,478,573 (`registry.program_trials()`, 2026-10-22, after R294).
