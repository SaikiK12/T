# FINDINGS: carry_v1 (R190)

**Verdict: CONFIRMED in-sample (SIGNAL and VALIDATED by the frozen rule).** A hedged funding carry on liquid Binance
perps earned after costs, with a very low drawdown, but almost all of it in high-funding periods.

- **Registry row:** R190 (trials: 12)
- **Reproduce:** prereg sha fc712ae1; `python scripts/run_carry.py`; spot pairs in data/spot_pairs.json.

## Numbers (primary: enter above 20% APR trailing 72 h funding, exit below 10%, spot 10 bp, 1x tier costs)
| split | net / yr | Sharpe | NW t | max DD | funding / yr | basis / yr | cost / yr | invested |
|---|---|---|---|---|---|---|---|---|
| discovery 2021-2023 | +12.7% | 5.7 | 3.80 | 0.8% | 15.9% | +0.4% | 3.5% | 46% |
| validation 2024-2025H1 | +5.9% | 5.5 | 2.82 | 0.8% | 9.4% | +0.4% | 3.9% | 57% |

Per year: 2021 +35.0%, 2022 -0.1%, 2023 +3.3%, 2024 +8.1%, 2025H1 +0.8%. Returns are on capital per leg; holding the
spot leg plus perp margin needs about 1.3x that capital.

## Cost sensitivity
2x costs: +9.2% (discovery), +2.0% (validation). A 10% entry threshold trades too often and loses at 2x; 20% and 40%
stay positive in both splits at 1x.

## What this does not show
The basis is the premium index, not the traded spot-perp spread; legs are assumed filled together at the hourly close;
no exchange, custody or liquidation risk on the short perp during squeezes; no reverse carry (needs borrowed spot).

## Next
One-shot holdout (R191).
