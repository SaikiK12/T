# FINDINGS: gap_breadth_v1 (R525). Every floorless × floor pair pays; their portfolio earned +7.8%/yr at Sharpe 5.5 over 5.7 years

**Verdict: PASS.** The equal-weight portfolio of all 12 pairs passes every check:
- NW t 11.96;
- +6.70%/yr at 2x costs;
- halves +8.7 and +6.9 %/yr.

- **All 9 new pairs pass R391's rule on their own.**
- **Registry:** R525, 9 trials. Program trials become 9,785,781.
- **Reproduce.** The PREREG (sha 3c21e235) was frozen in commit 244dae9a before any new pair was computed.
  `run_gap_breadth.py run` ran once on 2026-11-23 (2 min 45 s).

## The portfolio (equal weight over the pairs live each day), 2021-01-22..2026-09-30
- **Return:** 2,078 days; +7.77%/yr at 1x and +6.70%/yr at 2x.
- **Risk:** Sharpe 5.5, NW t 11.96, max drawdown −0.73%.
- **Live pairs:** 7.1 a day on average. Pairs join as their venues' data begin: Bitfinex 2021, Deribit 2022,
  Hyperliquid 2023, Kraken 2025-12.

| Year | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (to Sep) |
|---|---|---|---|---|---|---|
| %/yr at 1x | +13.7 | +4.1 | +9.4 | +8.6 | +2.2 | +9.5 |

- **Every year positive.** 2025 is the weak year, as in R507.

## The 12 pairs (R275's L14d th5% K20 on `xfund_v2`; %/yr on book capital)
| Pair | New | Verdict | 1x | 2x | 3x | NW t | Max DD | From |
|---|---|---|---|---|---|---|---|---|
| kraken+binance | yes | PASS | +32.4 | +30.7 | +28.9 | 7.34 | −1.66% | 2025-12 |
| kraken+gate | yes | PASS | +31.4 | +29.7 | +27.9 | 7.59 | −1.44% | 2025-12 |
| kraken+kucoin | yes | PASS | +31.0 | +29.2 | +27.4 | 9.45 | −1.03% | 2025-12 |
| kraken+hyperliquid | R508 | PASS | +22.0 | +20.2 | +18.5 | 7.05 | −0.69% | 2025-12 |
| deribit+gate | yes | PASS | +7.0 | +6.0 | +4.9 | 6.53 | −0.99% | 2022-03 |
| deribit+binance | yes | PASS | +6.8 | +5.8 | +4.7 | 6.53 | −1.06% | 2022-03 |
| deribit+kucoin | yes | PASS | +6.0 | +4.9 | +3.7 | 6.33 | −1.08% | 2022-03 |
| deribit+hyperliquid | R519 (reported) | PASS | +4.4 | +3.4 | +2.3 | 6.69 | −0.85% | 2023-05 |
| bitfinex+kucoin | yes | PASS | +6.7 | +5.5 | +4.3 | 7.27 | −3.79% | 2021-01 |
| bitfinex+hyperliquid | yes | PASS | +5.3 | +4.2 | +3.2 | 4.02 | −5.80% | 2023-05 |
| bitfinex+gate | yes | PASS | +4.3 | +3.3 | +2.3 | 5.11 | −8.06% | 2021-01 |
| bitfinex+binance | R507 | PASS | +3.5 | +2.3 | +1.1 | 2.95 | −6.85% | 2021-01 |

- **Correlations on common days:** median 0.17, minimum −0.05, maximum 0.94. Pairs that share a floorless venue
  move together: the Kraken pairs trade the same thin Kraken coins.
- **Bitfinex+Binance's** +3.5%/yr differs from R507's +5.2% because this round uses the `xfund_v2` engine and R437's
  loader (marks and notional at entry). R507's frozen read stands.

## What it means
- **The faille is a property of venue design, not of a pair.** Every floorless × floor combination the lab holds
  pays after 3x costs, over 1-6 years.
- **The framework is the product.**
  - Across all pairs, the portfolio's drawdown is −0.73% in 5.7 years at 1x, so leverage is limited by venue margin
    (`docs/reviews/stake_dhl_20261123.md`), not by market risk.
  - At about 2.5x that is roughly +19%/yr in sample.
- **The largest piece is Kraken's thin coins** (about +31%/yr against any floor venue), with small capacity (R508).
  The broadest piece is Deribit (liquid coins, +6-7%/yr).

## What this does not show
- **In sample.** The known pairs' venues were read before. Only forward days confirm: R509, R512, R520 and R524 run,
  and R523 combines two of them.
- **Kraken's window** is only 10 months (2025-12..2026-09).
- **Capacity and costs.** Thin Kraken and new Deribit books may cost more than 7-21 bp.
- **Venue risk:** five venues to fund and watch. MEXC was not in the map.
- **Correlated legs.** Pairs sharing a floorless venue are near-duplicates, so the effective breadth is closer to the
  three floorless venues than to 12 pairs.

## Addendum, the same day: a Millikan audit of this pass (post hoc, descriptive; the verdict stands)
- **Why.** Feynman, read 2026-11-23 (`docs/METHOD_LIBRARY.md`): hunt bugs in a pleasing result as hard as in a
  failing one.
- **Lookahead check.** Every pair was rerun with a one-day decision delay: decide on day d−1's windows, act at day d.

  | Pair | Base %/yr | With a one-day delay | Kept |
  |---|---|---|---|
  | kraken+binance | +32.4 | +30.6 | 94% |
  | kraken+gate | +31.4 | +28.4 | 90% |
  | kraken+kucoin | +31.0 | +26.0 | 84% |
  | kraken+hyperliquid | +22.0 | +21.1 | 96% |
  | deribit+binance / gate / hyperliquid / kucoin | +6.8 / +7.0 / +4.4 / +6.0 | +6.3 / +6.4 / +4.0 / +5.3 | 87-93% |
  | bitfinex+binance / hyperliquid / kucoin | +3.5 / +5.3 / +6.7 | +2.9 / +5.6 / +6.6 | 82-105% |
  | **bitfinex+gate** | +4.3 | **−11.4** | — |

  - 11 of 12 pairs keep 82-105%, so there is no sign of lookahead.
- **What broke bitfinex+gate under the delay: LUNA, May 2022.**
  - The delayed book entered LUNA (long Gate, short Bitfinex) on day 499. The legs diverged by about 34x before the
    daily blowout check closed it the next day. One trade lost −3,449% of a leg's notional, and the worst day was
    −85.9% of book capital.
  - The undelayed book missed LUNA by one day. That is luck, not design.
- **Bitfinex's thin pairs also show stale-looking legs.** SAND, COMP and ALGO lost 64-84% of a leg's notional on
  price, which two live venues on one coin cannot do. A Bitfinex series probably stopped printing while Gate's moved.
- **What it means.**
  - The design gap's return is robust to timing.
  - Its tail is the hedge breaking on a collapsing or halted coin, which a daily check cannot catch. The live book
    needs:
    1. an hourly divergence stop on each pair (close both legs if the ratio moves more than about 10% from entry);
    2. a cap of about 5% of book capital per coin;
    3. no entry on a coin with a venue halt, delisting notice or a dead series;
    4. a minimum printing activity on both venues before entry.
  - Bitfinex's numbers are the least trustworthy of the three floorless venues. R524 (Bitfinex + Binance forward)
    should be read with that in mind.
- **Not yet done** (breakthrough review, item 0): a funding timestamp-convention check per venue, a PnL decomposition
  of Kraken's +31%/yr by liquidity, and an exact reproduction of R507/R508 under this engine.
