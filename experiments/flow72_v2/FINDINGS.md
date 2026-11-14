# FINDINGS: flow72_v2 (R197)

**Verdict: PASS (in-sample design check) -> one-shot holdout earned.** Short the coins whose takers sold the most, or
whose top traders lean short against the crowd, as overlapping 72 h slices hedged with the universe: +42.6%/yr net at 1x
(t 3.25), positive in all five years, still positive at 3x costs. In-sample: the cells were picked with both periods and
the construction after a failed book (R196).

- **Registry row:** R197 (trials: 24 books)
- **Reproduce:** prereg sha 2e8d8172; `python scripts/run_flow72_slices.py`.

## Numbers (2021-01-01 to 2025-06-30)
| book | hedge | net / yr 1x | t | Sharpe | max DD | 2x | 3x | gross | cost | beta BTC |
|---|---|---|---|---|---|---|---|---|---|---|
| combined | universe (primary) | +42.6% | 3.25 | 1.54 | 27% | +26.9% | +11.3% | 57.9% | 15.5% | -0.01 |
| combined | none | +42.4% | 0.72 | 0.32 | 199% | +26.9% | +11.4% | 57.9% | 15.5% | -1.15 |
| top_vs_crowd | universe | +69.3% | 2.64 | 1.18 | 60% | +58.4% | +47.5% | 70.7% | 10.6% | 0.05 |
| taker[24] | universe | +53.6% | 2.95 | 1.26 | 36% | +37.8% | +21.9% | 69.6% | 15.7% | -0.05 |
| taker[4] | universe | +13.0% | 1.52 | 0.67 | 25% | -5.8% | -24.6% | 37.4% | 18.7% | 0.00 |

Primary per year: 2021 +6.2%, 2022 +21.3%, 2023 +92.8%, 2024 +27.3%, 2025H1 +44.1%; discovery +40.1%/yr (t 2.82),
validation +47.6%/yr (t 1.82). Mean gross short exposure 1.31 of capital, matched by the long basket.

Consistency check: 58% gross a year on 1.31 exposure is about 37 bp per unit per 72 h, the size of the atlas all-hours
means (-37 to -57 bp). Costs are 15.5%/yr rather than one round trip per slice because a coin that stays in the bin
opens a new slice as an old one expires, and the two cancel.

## Cost sensitivity
1x +42.6%, 2x +26.9% (t 2.07), 3x +11.3% (t 0.87) for the primary. top_vs_crowd alone is the most cost-robust (+47.5% at
3x); taker[4] alone does not survive 2x.

## What this does not show
- Selected with the data: the cells by atlas_v1 (338,240 cells, replication on validation), the construction after
  R196's diagnostic. Only the holdout can say more.
- The universe hedge is idealized: an equal-weighted basket of the tradable coins whose internal rebalancing is free.
  A BTC or top-10 basket hedge is the practical version.
- Shorting 1.3x of capital in alts needs margin and borrowable perps; no position limits, no liquidation risk in squeezes
  (max drawdown 27% hedged, 199% unhedged).
- Order-flow data are Binance's 5-minute metrics as archived; their timeliness in live trading is assumed.

## Next
One-shot holdout (R198) on 2025-07-01..2026-09-30 with the primary frozen as is.
