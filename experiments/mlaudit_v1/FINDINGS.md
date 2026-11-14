# FINDINGS: mlaudit_v1 (R305). R304's pick is not age, not low risk and not market beta: label "unexplained"

**Label by the frozen rules: `unexplained`** (gate 0, on seen data; nothing is promoted). The PREREG sends an
unexplained pick to the next batch as frozen, with a forward paper ticket, and keeps the audit open.
- **Trials:** 7 (6 books here, plus the lag-test book run before the freeze), gate 0.
- **Read:** frozen PREREG 1152e416, frozen and pushed in d398f0f before the run. Run 2026-10-22 12:26-12:41 UTC with
  `scripts/run_mlaudit.py`; all 8 inputs matched their frozen hashes.
- **Parity:** the rebuilt pick matches R304's validation net 1x (+58.9165 bp/day) within 0.01. The labels stand.

## Result (bp/day; t is Newey-West; validation 2024-01..2026-09, discovery 2022-23)

| Book | Discovery net 1x (t) | Validation net 1x / 2x / 3x (t at 1x) | Long / short leg, validation (bp/week) | Rank IC (valid) |
|---|---|---|---|---|
| R304 pick (24 clean features) | +36.0 (5.99) | +58.9 / +56.8 / +54.6 (4.21) | +310 / +117 | 0.190 |
| `gbm no-age` (23) | +37.7 (6.68) | +56.1 / +53.9 / +51.6 (4.06) | +279 / +130 | 0.187 |
| `gbm risk-only` (6) | +7.2 (1.12) | −15.7 / −17.4 / −19.1 (−1.02) | −7 / −92 | 0.137 |
| `gbm no-risk` (18) | +38.6 (6.47) | **+62.4** / +60.0 / +57.6 (**5.42**) | +272 / +182 | 0.182 |
| `composite` (fixed low-risk score) | −2.0 (−0.23) | −21.3 / −22.8 / −24.3 (−1.25) | −13 / −125 | 0.148 |
| `lowvol` (fixed) | −2.2 (−0.25) | −10.9 / −12.0 / −13.1 (−0.80) | −12 / −57 | 0.130 |
| `old` (fixed) | +2.2 (0.39) | −6.9 / −7.6 / −8.3 (−0.43) | +20 / −64 | 0.115 |

**The labels:**

| Label | Rule | Value | Set? |
|---|---|---|---|
| `age_carried` | `gbm no-age` < 29.46 | +56.1 | no |
| `risk_carried` | `gbm risk-only` ≥ 41.24 | −15.7 | no |
| `known_anomaly` | `composite` ≥ 41.24 | −21.3 | no |
| `beta` | alpha t < 2.0 against the equal-weight universe or BTC | 4.22 / 4.11 | no |
| `unexplained` | none of the above | | **yes** |

- **The leg profile was a correlate, not the driver.** The pick's long leg is old and calm and its short leg young
  and volatile (the pre-freeze look). But the six risk features alone lose, and the book without them earns more
  (+62.4, t 5.42). A fixed low-risk score with the same signs loses in both windows. Its 2024-26 years are −40 and
  −30 bp/day.
- **What is left carries it:** momentum and reversal, volume and its trend, taker share, trade size, funding,
  premium, basis, spot share, open interest and positioning (18 features). The linear rankers on the same inputs
  lose (R304), so the GBM's edge sits in their interactions.

**Beta (per weekly rebalance, net 1x, OLS)**

| Window | vs equal-weight universe: alpha bp/day, beta (alpha t) | vs BTC: alpha, beta (t) |
|---|---|---|
| Discovery | +35.7, −0.09 (5.86) | +36.3, −0.16 (6.09) |
| Validation | +58.4, −0.29 (4.22) | +58.8, +0.02 (4.11) |

- **The long leg holds the alpha.** Against the equal-weight universe in validation, the long leg earns +45.9
  bp/day (beta 0.88, t 8.81) and the short leg +14.6 (beta −1.16, t 1.43).

**The short leg's squeeze tail**

| Window | Weeks | Share with a short name up > 50% | > 100% | Largest 7-day move of a short name |
|---|---|---|---|---|
| Discovery | 104 | 23% | 6.7% | +222% |
| Validation | 142 | 49% | 15.5% | **+1,850%** |

- **The squeezes are real, not data errors.** The largest 7-day moves in the universe since 2022 are COAI (2025-10,
  up 15-26x), ALPACA (2025-04), MYX (2025-08/09) and RAVE (2026-04).
- At 1/30 of the short leg, a +1,850% week costs about 62% of that leg's capital in one week. The mean stays
  positive only because such weeks are rare. A leveraged account would have been liquidated on it.
- **Any tradable version needs a squeeze cap on the short leg, or the long leg alone against a hedge.**

**By year (net 1x, bp/day):** the pick earned +35.7 (2022), +36.3 (2023), +52.0 (2024), +56.7 (2025) and +71.5
(2026). `gbm no-risk` earned +37.1, +40.1, +44.6, +83.8 and +57.5.

## Costs
- **Levels:** API, 8.5 / 17 / 25.5 bp per side on each weekly rebalance's turnover.
- **At 1x/2x/3x** the pick nets +58.9 / +56.8 / +54.6 in validation. Cost does not decide any book here.

## Read against the program
- **Program trials:** 9,478,690 after R304. With R305's 7 it is 9,478,697 (`registry.program_trials()`).
- **These are diagnostics on windows R299 and R304 already read.** `gbm no-risk`'s t of 5.42 is not a new
  discovery. It is one of 6 refits chosen to explain a known result.

## What this does and does not show
- **It shows:** the pick is not an age artifact, not the textbook low-risk anomaly and not a market bet. Its long
  leg beats the equal-weight universe by about 46 bp/day with t 8.8, on features of flow, funding, open interest
  and positioning.
- **It does not show** why. "Unexplained" is the frozen label, not a pass. Three things remain unchecked:
  - **Survival in Binance's metrics archive:** OI and positioning are missing for about half the rows, at similar
    rates for survivors and later-delisted coins (R304's PREREG). Not checked: whether missingness itself predicts
    returns (a missing value ranks 0, and a tree can split on it).
  - **Execution:** the long leg's names at the rebalance and their MEXC books. Not checked.
  - **Capacity and fills:** not checked.

## Next (fixed by the PREREG for `unexplained`)
- **Forward paper ticket:** the frozen pick, weekly on MEXC prices, from the first free day. It needs a live feature
  pipeline; Binance metrics are archived daily, so the panel's recent rows can be built. The lane gets its own frozen
  PREREG (next Claude id). Two forward variants are added as separate lanes, chosen now from this audit:
  1. the long leg alone, hedged with the equal-weight universe;
  2. the pick with a protective cover on each short (R274/R298 semantics).
- **Batch 2:** the frozen pick is listed. The 2020 sample has no OI or positioning (`metrics` start 2021), so the
  batch PREREG must say how the model scores rows without them. Otherwise the read tests a different model.
- **Audit, still open:** missingness of OI and positioning as a feature (refit with a missing-flag and with rows
  without metrics dropped), as a new frozen lane.
