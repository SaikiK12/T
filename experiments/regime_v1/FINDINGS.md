# FINDINGS: regime_v1 (R233). Trading the flow books only in some market regimes

**Verdict: NULL.** The test did not find a regime in which to switch the flow books off.
- **Gates:** in discovery, A, B and X2 each made money at 2x costs in all four trend x volatility regimes. So the frozen
  rule selected no gate for any book, and G-A, G-B and G-X2 end without a computed variant.
- **MIX** (the "hyper-agent": hold X2 in three regimes, B in falling low-volatility markets):
  - It raised validation Sharpe by 0.12 against X2 (1.80 vs 1.68). The bar was 0.15.
  - Its drawdown was the same, and at 2x costs it earned less than X2.
- The holdout was not read for any variant.

- **Registry row:** R233 (trials: 4). Program trials after it: 9,471,893.
- **Origin:** the owner's MacroHFT paste (sub-agents per trend x volatility regime, mixed by a hyper-agent).
- **Reproduce:** prereg sha 0087630d, frozen in commit 6e193c8 before the run; `python scripts/run_regime.py` (about 30
  seconds).
- **Parity:** the runner rebuilds R217's books. Their constant-size daily nets equal R217's `daily.npz` exactly (max
  |diff| 0) for A, B and X2.

## Regimes
- **Trend:** the sign of the equal-weight crypto index over the last 30 days.
- **Volatility:** HIGH when the index's 30-day volatility is at or above its own median to date.

Share of days in each regime:

| Window | UL | UH | DL | DH | warm-up |
|---|---|---|---|---|---|
| Discovery 2021-23 | 35% | 3% | 29% | 13% | 20% |
| Validation 2024-25H1 | 24% | 21% | 12% | 42% | 0% |
| Holdout (market data only) | 52% | 0.4% | 32% | 16% | 0% |

- UH had only 35 discovery days.
- Validation spent 42% of its days in DH, three times the discovery share.

## Numbers
Discovery mean daily net by regime, in bp/day, at 1x / 2x / 3x costs, with NW t at 1x:

| Book | UL | UH | DL | DH |
|---|---|---|---|---|
| A | 13.2 / 9.8 / 6.5 (t 1.49) | 17.9 / 14.0 / 10.2 (t 2.08) | 13.2 / 8.9 / 4.7 (t 1.96) | 17.0 / 13.2 / 9.5 (t 2.20) |
| B | 0.7 / 0.1 / -0.6 (t 0.16) | 7.0 / 6.0 / 5.1 (t 1.58) | 11.1 / 10.3 / 9.4 (t 3.68) | 2.0 / 1.5 / 1.1 (t 0.86) |
| X2 | 21.7 / 17.6 / 13.6 (t 1.76) | 23.7 / 18.9 / 14.1 (t 2.09) | 14.4 / 9.3 / 4.1 (t 1.75) | 22.6 / 18.2 / 13.8 (t 2.57) |

Every 2x mean is above zero, so every gate set is all four regimes, which is "no gate selected".

**MIX against its control X2** (the best book over discovery at 2x):

| Window | Cost | MIX bp/day (t) | X2 bp/day | Sharpe MIX / X2 | Max DD MIX / X2 | Paired diff bp/day (t) |
|---|---|---|---|---|---|---|
| Discovery | 1x | +13.8 (2.94) | +15.5 | 2.01 / 1.96 | 21.7% / 24.6% | -1.7 (-0.82) |
| Discovery | 2x | +10.7 | +11.9 | 1.56 / 1.50 | 31.6% / 36.6% | -1.2 |
| Discovery | 3x | +7.5 | +8.2 | 1.10 / 1.05 | 41.8% / 48.6% | -0.7 |
| Validation | 1x | +19.8 (2.28) | +19.7 | 1.80 / 1.68 | 27.4% / 27.5% | +0.1 (0.03) |
| Validation | 2x | +12.1 | +12.8 | 1.09 / 1.09 | 28.8% / 38.3% | -0.7 |
| Validation | 3x | +4.3 | +5.8 | 0.39 / 0.50 | 32.2% / 50.4% | -1.5 |

- MIX per year at 1x: 2021 +1.0, 2022 +8.0, 2023 +32.3, 2024 +15.6, 2025H1 +28.3 bp/day.
- Drawdowns are unit-size sums of daily returns, not compounded.

## Cost sensitivity
- At 1x, MIX and X2 are even in validation.
- At 2x and 3x, MIX trails X2 by 0.7 and 1.5 bp/day. Switching between books each time the regime changes adds
  turnover.
- MIX has a smaller drawdown at 2x-3x (28.8% vs 38.3% at 2x), because it holds B in DL. That is the only benefit, and
  the frozen rule does not count it.

## Reading
- **The flow books are not regime-bound in the way MacroHFT assumes.** A and X2 earn in every regime, slightly more
  when volatility is high.
- **Top-vs-crowd alone (B) earns almost only in falling, low-volatility markets.** In DL it made +11.1 bp/day with t 3.68
  in discovery. In UL it made +0.7. This is a description of discovery, found after looking; it is not a test result.
  - A lane that trades B only in DL would be a new id. It would need validation and forward days, because this split
    was chosen with the data in view.
  - It fits the crowding-unwind story in the PREREG, but in low volatility rather than high.
- **The "hyper-agent" adds no edge over the best single book.** This matches R228, where static mixtures of A, B and X2
  did not beat X2 either.

## Not checked
- Other regime definitions (BTC instead of the index, other windows, terciles).
- Other books, including carry.
- Learned (RL) agents. The paste's sub-agents are DDQN policies at minute frequency, and this lab has no minute data
  or order-book history.
- The holdout, for any variant.
