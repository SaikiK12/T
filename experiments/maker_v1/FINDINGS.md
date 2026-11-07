# FINDINGS: maker_v1 (R193)

**Verdict: NULL by the frozen rule** (4 cells selected on discovery; their book on validation: +14%/yr, t 0.18). The
descriptive result is the strongest lever found so far: limit-order entries turn most replicated gross edges from
losing to paying per trade, and the signals add more on top of a limit entry than on top of a market entry.

- **Registry row:** R193 (trials: 24,782 = 413 cells x 5 entries x 2 exits x 2 fees x 3 cost multiples + 2 books)
- **Reproduce:** prereg sha dc39e9e7; `python scripts/run_maker.py`; cells = atlas_v1 replicated CGE(all) raw cells.

## Numbers
Per trade, median over the 413 cells, exit at market after h, maker fee 0, taker costs 1x (episode starts only):

| entry | fill rate | gross disc | net disc | gross val | net val | cells net > 0 disc / val |
|---|---|---|---|---|---|---|
| market at the close (taker) | 100% | 11.0 bp | -3.4 bp | 4.6 bp | -9.8 bp | 43% / 27% |
| limit at the close (kappa 0) | 98% | 8.6 | 1.4 | 1.3 | -5.9 | 53% / 34% |
| limit 0.25 sigma below | 77% | 15.0 | 7.8 | 4.1 | -3.1 | 68% / 41% |
| limit 0.5 sigma below | 58% | 19.6 | 12.3 | 7.2 | 0.0 | 77% / 50% |
| limit 1 sigma below | 32% | 30.7 | 23.5 | 18.7 | 11.4 | 83% / 69% |

sigma = std of the last 168 hourly returns; a fill needs the next bar to trade 2 bp through the limit.

**Adverse selection, measured.** A limit with no signal (every tradable symbol and hour) is the baseline. Buying dips
with a limit 1 sigma below the close earns, before costs, +6 bp (h 1), +15 bp (h 4), +40 bp (h 24) in discovery against
+1, +2, +13 bp for market entries; +2, +8, +15 against 0, -1, -7 in validation. Selling rips with a limit does not help
(the short side is worse with a limit at every horizon). Over that baseline, the signals add a median +17 bp per trade
(discovery) and +13 bp (validation) at kappa 1, against +8 and +6 bp over the market-entry baseline: oversold signals
and deep limit entries reinforce each other.

At kappa 1, fee 2 bp, the share of cells with positive per-trade net in BOTH periods is 61% at 1x costs, 49% at 2x and
38% at 3x. By horizon (validation, net median): h 1 -4.9 bp (29% positive), h 4 +9.7, h 12 +17.7, h 24 +34.3,
h 72 +136 (the long horizons carry market drift; cells are 84% long).

**Book (frozen rule).** Cells with discovery daily-sum net t >= 3 at kappa 0.5, fee 2 bp: only 4, all h 24 longs
(ret[1]/ret[3]/ret[6] at 4 h oversold, donch[20] bottom). One position per symbol, 10 slots:

| split | entry | gross / yr | net / yr 1x | t | max DD | 2x | 3x |
|---|---|---|---|---|---|---|---|
| discovery | maker | 87% | 63% | 1.47 | 116% | 44% | 25% |
| discovery | taker | 59% | 16% | 0.34 | 219% | -27% | -70% |
| validation | maker | 40% | 14% | 0.18 | 131% | -6% | -26% |
| validation | taker | 19% | -26% | -0.34 | 157% | -71% | -116% |

Per year (maker, 1x): 2021 +199%, 2022 -96%, 2023 +86%, 2024 +39%, 2025H1 -17%. A long-only book of oversold alts is a
leveraged bet on the market: the drawdowns come from beta, not from the signal.

## Cost sensitivity
Above: per-cell shares at 1x/2x/3x, book at 1x/2x/3x. Maker fee 0 vs 2 bp moves the per-trade median by 2 bp.

## What this does not show
- Fills come from hourly highs and lows: a trade-through is a fill in a price-time book, but latency, partial fills at
  size, and the queue at the close are not modelled. The order is posted at the close of the signal bar and lives one bar.
- The 413 cells were chosen with discovery and validation (atlas_v1), so the per-cell shares are in-sample for selection;
  only the execution effect is new information. Kappa 1 looked best after seeing both periods.
- No hedge: raw cells are directional and mostly long.
- Venue: Binance archive prices; MEXC fees and books differ.

## Next
A pack lane: all cells with a discovery per-trade edge at kappa 1, many at once, market-hedged, judged on the one-shot
holdout, since discovery and validation are both spent for this choice.
