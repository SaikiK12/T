# FINDINGS: listings_v1 (R188)

**Verdict: NULL by the pre-registered rule (|t| >= 3 not reached), with a consistent sign.** New USDT perpetual
listings trailed the market in every year 2021-2025H1, but squeezes kept the significance below the bar.

- **Registry row:** R188 (trials: 24)
- **Reproduce:** prereg sha 8f6f0f1e; `python scripts/run_listings.py`; data manifests as in atlas_v1.

## Numbers (primary: entry 24 h after listing, hold 14 days, excess vs the top-50 market, no volume filter)
| split | listings | mean excess | clustered t | median | share negative | largest squeeze | net short mean (t) |
|---|---|---|---|---|---|---|---|
| discovery 2021-2023 | 184 | -3.7% | -1.94 | -8.9% | 64% | +170% | +3.0% (1.56) |
| validation 2024-2025H1 | 227 | -5.0% | -1.38 | -10.4% | 64% | +161% | +4.3% (1.17) |

Per year (mean excess): 2021 -5.0%, 2022 -6.9%, 2023 -2.1%, 2024 -1.7%, 2025H1 -9.6%. All 48 configurations (delay
24/72 h, hold 7/14/30 days, market or BTC benchmark, volume filter on/off) had a negative mean except two near zero;
the best combined evidence was delay 24 h, hold 7 days, market, volume >= 10 M (discovery t -3.06, validation t -1.52).
Hedged short book (primary): discovery +18.8%/yr net (Sharpe 0.63, max drawdown 31%), validation +67%/yr (Sharpe
1.09, max drawdown 43%). Late baseline (same coins 180 days after listing): -1.6% (t -1.9) in discovery, +0.8% in
validation, so most of the effect belongs to the first weeks.

## Cost sensitivity
One round trip per event on both legs (about 25-80 bp) against moves of 5-15%: costs are not the binding constraint
here; the right tail is.

## What this does not show
Listing time is the first archived hour, not the announcement. No borrow or margin limits on shorting very new perps,
no position limits, no funding caps; squeezes on thin books would cost more than the tier model says.

## Next
The strongest configuration went to a one-shot holdout (R189).
