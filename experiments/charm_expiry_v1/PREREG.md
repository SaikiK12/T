# PREREG: charm_expiry_v1 (R296). Does Deribit's Friday 08:00 UTC expiry move the BTC and ETH perps? (M303, M317)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R296 (Claude block R280-R299, claimed on issue #7 on 2026-10-22 before this freeze).
- **Methods:**
  - **M303 with its dose:** R289 found that a perp move inside Deribit's 07:30-08:00 UTC settlement window tends to
    reverse after 08:00. R289's FINDINGS asked for the open option position as a dose variable. That is reading A.
  - **M317 (new, filed with this lane):** the dealers' hedge of expiring options is closed at expiry. Under the
    makers-as-dealers reading (R292), that is readings B and C.

  The name comes from charm: an option's delta drifts with time alone, and in the last hours it collapses to 0 or ±1.
  A dealer who hedges the delta holds a hedge that must disappear at 08:00.
- **Owner (single writer):** the Claude session that froze it.
- **Code:** `scripts/run_charmexpiry.py`, tested on synthetic data in `tests/test_run_charmexpiry.py`:
  - the expiry delta and the dealer sign;
  - positions use only the flow rows known at each decision;
  - the 2% band;
  - prices, returns and inputs at each decision instant;
  - the scaling reads only past Fridays;
  - a planted dose effect passes, a wrong-sign effect does not, and the fade's own mean is not read as a dose slope;
  - the rules, the costs, the input hash check and the Friday clock.

  It calls `verify()` on this file first and checks every input's sha256 against the block below. It also checks
  each Deribit flow file it reads against its hash in the provenance record.
- **Execution mode:** manual web, once a week (orders at 07:31, 07:59, 08:01 and the exit), with R289's MEXC costs.
  API costs are reported. A pass is a mechanism; a lane needs the rule net positive at 1x and 2x, and its own id.
- **Gate:** 0.
  - The perp bars were read by R289-R295, including R289's SETTLE fade on these Fridays.
  - The flow files were read by R292 (positions and gamma, daily) and R295 (hourly flow against returns).
  - No lane has read expiring positions against the Friday window.

## What the author has seen
- **R289 in full** (`clockflow_v1`, NULL).
  - The weekly SETTLE fade (k = 0) has gross +11.4 / +12.9 bp per trade in discovery and validation, over BTC, ETH
    and SOL.
  - k = 1 h120 has gross per trade +17.5 (BTC), +24.6 (ETH) and +24.1 (SOL) bp over both windows. Its validation t
    is 1.37.
  - On Mondays to Thursdays, the same clock's fade is +2 to +4 bp (discovery) and −2 to −10 bp (validation).
- **R292 in full** (`dealerflow_v1`, NULL). Dealers are short gamma on 76-92% of days. The median net GEX is about
  0.13% of a day's perp volume per 1% move (BTC 2024-26).
- **R295 in full** (`optflow_v1`, NULL). Hourly taker flow does not lead the perp.
- **The flow file layout.** Every Deribit option expires at 08:00 UTC, and Fridays carry the weekly, monthly and
  quarterly series.
- **A plumbing run on the real files, before this freeze** (`--plumbing`), which printed counts only:
  - flow rows of options expiring on a Friday 2021-01-01 .. 2026-09-25: 3,676,641 (BTC) and 2,705,046 (ETH), over
    300 Friday expiries each;
  - per coin, 144 Fridays in discovery and 143 in validation, all with expiring options and all prices and volumes
    present;
  - no Friday with a zero dose;
  - defined features: 142 Fridays (discovery) and 143 (validation) per coin and feature.

  No feature value, return, product or statistic was printed.

## Inputs (frozen)

```inputs
9e2c7fd717811a58bca2fa5816b92b4bf59aaa5d9706c10af2522af04a1c82a0  data/klines_1m/BTCUSDT.parquet
7c7c05b387d59fd3e40555718c28388fb66c737602102297a34de9af9c67da70  data/klines_1m/ETHUSDT.parquet
9ab09b14cc503d6ead4ca14ea16c0e32ed0f428a82b52c0cbf17567797d6a188  docs/provenance/deribit_trades.json
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
2c4e93aa4586f41098ee65e8b097c067d0a368b0d0f49c1c4844628eb176b8f1  scripts/run_vpin.py
ce26ce64bebe3cc55a422fffe9a9bdb2c029b1e7a06dc1f15466ddcffb0889c8  scripts/run_charmexpiry.py
```

The Deribit flow files (`data/deribit_trades/{BTC,ETH}/flow/*.parquet`) are pinned through the provenance record,
which holds each file's sha256.

## Data
- **Options:** every Deribit BTC and ETH option trade, reduced to hourly flow per option by
  `scripts/fetch_deribit_trades.py`.
  - Only options that expire on a Friday at 08:00 UTC from 2021-01-01 to 2026-09-25 are kept.
  - Their rows are read from every monthly file, back to each option's first trade, since a position runs from
    listing. Some of those rows are from 2020. Deribit flow is not a reserved sample; R292 read it the same way.
  - A row for hour t holds the trades in [t, t + 1 h), so it is known at t + 1 h.
- **Perps:** Binance USD-M BTCUSDT and ETHUSDT 1-minute bars, 2021-01-01 to 2026-09-30 (2020 is reserved).
  - The price at instant T is the close of the valid 1-minute bar that ends at T (`run_clockflow.load_prices`).
  - **ADV** is the mean daily quote volume of the 30 UTC days before the Friday that have at least 1,200 valid bars
    (at least 20 such days).
- **Funding:** none is paid. Binance BTC and ETH funding settles at 00, 08 and 16 UTC, and no hold here spans one:
  C exits at 07:59, and A and B enter at 08:01 and exit by 10:01.

## Inputs at each Friday e (per coin)
- **Taker position** of an option: taker buys minus taker sells (coins) over the rows known at the decision. Makers
  hold the opposite and are read as dealers.
- **Expiry delta:** a call is 1 above its strike and 0 below; a put is −1 below and 0 above; either is half at the
  strike. At 30 minutes to expiry, a Black-76 delta differs from this step only for strikes within about 0.4% of the
  price.

| Reading | Decision | Rows used (hours starting by) | Feature |
|---|---|---|---|
| A, dose | 08:01 | 07:00 | **N:** gross taker position, Σ \|position\| × P(07:30), over strikes within 2% of P(07:30). x_A = log(max(N / ADV, 10⁻⁴)), centered and scaled. |
| B, unwind after expiry | 08:01 | 07:00 | **D_B:** the dealers' delta, Σ −position × expiry delta at P(08:00), × P(08:00). x_B = (D_B / ADV), scaled. |
| C, unwind in the window | 07:30 | 06:00 | **D_C:** the same at P(07:30). x_C = (D_C / ADV), scaled. |

- **Centered and scaled:** minus the mean and over the sd of the coin's previous 52 Fridays (at least 12 defined).
- **Scaled:** over the root mean square of the coin's previous 52 Fridays (at least 12), because the sign of D is
  the prediction.
- Each is winsorized at ±5.

## Targets
- **A:** the fade of the window move m = P(08:00) / P(07:30) − 1. Gross y_h = −sign(m) × (P(08:01 + h) / P(08:01) − 1),
  with h ∈ {60, 120} minutes. Undefined when m = 0. This is R289's k = 0 fade, on BTC and ETH.
- **B:** r_h = log(P(08:01 + h) / P(08:01)), h ∈ {60, 120}.
- **C:** r_C = log(P(07:59) / P(07:31)).

## Windows (by Friday)
- **Discovery:** 2021-04-01 .. 2023-12-31.
- **Validation (out of sample):** 2024-01-01 .. 2026-09-30.

## Tests (5 trials: A h60, A h120, B h60, B h120, C)
- **Statistic:** per Friday, u = Σ over the two coins of x × y. The Newey-West t (`lab.stats.newey_west_t`, lag 4
  Fridays) of the mean of u within a window. A Friday without a defined pair is a gap.
  - For **A**, x and y are first demeaned per coin within the window, so u reads the slope of the fade on the dose
    and not the fade's own mean (which R289 has read).
  - For **B and C**, x × y is used as it is.
- **Predicted sign:** positive for all five.
  - A: more expiring position near the money, a larger reversal.
  - B and C: the perp moves with the dealers' expiring delta, as their hedge is closed.
  - B and C can contradict each other: if the hedge is closed inside the window (C), the move after 08:00 may
    reverse it. That outcome would show as C positive with B negative.
- **A trial passes when both hold:**
  - the validation t is ≥ 2.58;
  - the discovery t is positive.
- **The bar:** 2.58 is Bonferroni over the 5 trials (two-sided 5%).
- **A significant opposite sign** (validation t ≤ −2.58 with a negative discovery t) is recorded as a finding. It is
  not a pass.

## Decision
- **PARTIAL** if any trial passes: the expiry moves the perp in that reading.
  - A pass earns a forward paper lane (new id, manual web, Fridays) **only if** its rule's validation mean net per
    trade is positive at both 1x and 2x cost.
  - It also earns a slot in a later reserved batch: the 2020 Fridays, with 2020 flow for the positions.
  - Otherwise it is a mechanism without a trade, recorded as such.
- **NULL** if none passes.
  - R289's settlement reversal is then not explained by expiring position.
  - The dealers' expiry hedge does not show at the Friday expiry.
  - M303 closes, and M317 is TESTED.

## The rules (reported, and the condition for a lane)
- **A:** fade the window move when x_A ≥ 0 (the coin's higher-dose Fridays). Enter at 08:01 and hold h.
  - The fade on x_A < 0 Fridays is reported next to it.
- **B:** when |x_B| ≥ 1, take the sign of x_B at 08:01 and hold h.
- **C:** when |x_C| ≥ 1, take the sign of x_C at 07:31 and exit at 07:59.
- **Per trade:** gross = side × (exit / entry − 1), and net = gross − 2 × cost.
- **Costs per side:** manual web 3 / 6 / 9 bp (1x / 2x / 3x, R289's MEXC figure). API 8.5 bp is reported.
- **Reported per window:** trades and trades per year, mean gross and net in bp, the t of the 1x net, and the hit rate.

## Reported (not decided on)
- the validation t per coin and by year (2024, 2025, 2026);
- descriptives per coin and window:
  - Fridays, and Fridays with expiring options;
  - the median number of expiring options;
  - the median N / ADV and |D_B| / ADV;
  - the share of Fridays with dealers net long delta;
- the Friday table (inputs, features and returns) in `results/fridays.csv`;
- the result read against `registry.program_trials()`.

## Outputs
- `experiments/charm_expiry_v1/results/summary.json` and `results/fridays.csv`.
- FINDINGS.md is written after the run.

## Power (written before the result)
- About 143 Fridays per window, two coins.
- BTC and ETH move together on a Friday morning, so the effective sample is nearer 160 than 286.
- With n_eff 160, the expected t is about ρ√160 for a correlation ρ between x and y. The chance of t ≥ 2.58
  (normal approximation) is:
  - ρ 0.15: 25%;
  - ρ 0.20: 48%;
  - ρ 0.25: 72%;
  - ρ 0.30: 89%.
- **Only a large effect can pass.** A smaller one would need the reserved 2020 Fridays or forward Fridays added.

## Known limits (written before the result)
- **Taker is not customer,** and makers are not all dealers (R292's assumption). Open and close are unknown, so
  positions are net taker positions, not open interest.
- **Dealers may not hedge on Binance.** Many hedge with Deribit futures and perps. The test reads Binance's perp only.
- **The settlement index** is Deribit's (an average of several spot venues), and its TWAP is not used. P(07:30) and
  P(08:00) are Binance perp closes.
- **The expiry delta is a step.** With 30 minutes left, the strikes nearest the price are the ones it misreads.
- **Two coins, about 286 Fridays.** See the power table.
- **The fade's mean in A is already known from R289.** Only the slope on the dose is new.

## Multiplicity
- Trials: 5.
- Program trials before this lane: 9,478,588 (`registry.program_trials()`, 2026-10-22, after R295).
