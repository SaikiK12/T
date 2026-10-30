# FINDINGS: carrycrash_v1 (R207), does high market-wide carry predict BTC crashes?

**Verdict: NULL, with the sign reversed.** On Binance 2021-2026, days when market carry is in the top decile of its
past year were followed by *fewer* BTC crashes than average, and shorting BTC on them lost -74% in-sample (t -2.06).
High carry marked bull phases (2023-2024), not tops.

- **Registry row:** R207 (trials: 4)
- **Reproduce:** prereg sha 6875765c; `python scripts/run_carrycrash.py`.
- **Source claim:** `docs/CLAIMS.md` C08 (Schmeling, Schrimpf, Todorov 2023).

## Numbers (BTC short overlay, weight 1; NW t lag 10; days without a position count as 0)
| signal | hold | window | days in position | episodes | total 1x | bp/day 1x | t | total 2x | total 3x | max DD |
|---|---|---|---|---|---|---|---|---|---|---|
| **q90 (primary)** | **7 d** | **in-sample 2021-01..2025-06** | **172** | **7** | **-74.3%** | **-4.5** | **-2.06** | **-75.1%** | **-76.0%** | **84%** |
| q90 | 7 d | holdout 2025-07..2026-09 | 40 | 3 | -3.0% | -0.6 | -0.54 | -3.3% | -3.6% | 8% |
| q90 | 30 d | in-sample | 298 | 5 | -36.7% | -2.2 | -0.84 | -37.3% | -37.9% | 53% |
| q90 | 30 d | holdout | 71 | 2 | -8.6% | -1.9 | -0.85 | -8.8% | -9.0% | 13% |
| q80 | 7 d | in-sample | 308 | 10 | -69.6% | -4.2 | -1.55 | -70.8% | -72.0% | 70% |
| q80 | 7 d | holdout | 86 | 6 | -14.7% | -3.2 | -1.20 | -15.4% | -16.1% | 21% |
| q80 | 30 d | in-sample | 484 | 5 | -97.0% | -5.9 | -1.76 | -97.6% | -98.2% | 108% |
| q80 | 30 d | holdout | 163 | 3 | -17.6% | -3.8 | -0.64 | -17.9% | -18.2% | 39% |

Totals are sums of daily returns at weight 1 (not compounded), so a "drawdown" above 100% is possible.

Crash frequency, P(BTC's minimum close over the next 30 days is at least 20% / 10% below the day's close):

| signal | window | signal days | -20%: signal | -20%: all days | -10%: signal | -10%: all days |
|---|---|---|---|---|---|---|
| q90 | in-sample | 130 | 0.0% | 15.2% | 17.7% | 44.3% |
| q90 | holdout | 8 | 0.0% | 17.3% | 0.0% | 29.5% |
| q80 | in-sample | 228 | 1.8% | 15.2% | 27.2% | 44.3% |
| q80 | holdout | 29 | 0.0% | 17.3% | 3.4% | 29.5% |

Market carry (median annualized 72 h funding over the top 50): mean 21% in 2021, 1% in 2022, 9% in 2023, 16% in 2024,
4% in 2025, 2% in 2026. The 365-day threshold needs 180 days, so the 2021 peak only set the bar: the first signals
are in 2023. The losses come from Jan-Feb 2023 and Nov 2023-Mar 2024, the start of the ETF rally.

## Cost sensitivity
1x / 2x / 3x primary in-sample: -74.3% / -75.1% / -76.0%. A position on BTC that changes a few times a month costs
little; the verdict is about direction, not costs.

## Reading
- On these data, high aggregate carry is a **momentum state**: crowded longs paying high funding were followed by
  further rises, not crashes. The BIS paper's crash link (monthly data, mostly 2017-2022) did not show on Binance
  perps after 2021, though the evidence is 7 episodes in-sample and 3 out, clustered in two rallies: very little
  power either way.
- The reverse rule (long BTC on high carry) was chosen after seeing this and its holdout is now read (+3% over 40
  days in position): it is not a lane.
- For the lab's carry book (R190/R191): high carry did not precede crashes, so a crash overlay would not have helped.

## What this does not show
Crashes before 2023 (2021 May and 2022 happened before any signal could fire); other assets than BTC; a
cross-sectional version (coins with the highest own carry), which carry_v1 already trades in hedged form.
