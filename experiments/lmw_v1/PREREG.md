# PREREG: lmw_v1 (R251). Lo-Mamaysky-Wang kernel chart patterns on daily crypto, forex and indices

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R251
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_lmw.py`. It reuses `resample()` from `scripts/run_chartist.py` (R243) and `bars()`, `book()` and
  `row()` from `scripts/run_chartxm.py` (R247), unchanged.
- **Queue:** M201 (LMW kernel chart patterns)
- **Gate:** 0 (screen).

## What the author has seen
- R243 and R247: indicator rules (Supertrend, MACD, oscillators, Ichimoku, pivots) on the same markets, all NULL.
  Pivot breaks reversed in discovery and failed unseen (R248).
- **Lo, Mamaysky and Wang (2000):** on US stocks 1962-96, the patterns change the distribution of later returns, but
  that is not shown to be a profitable rule.
- No pattern detector of this kind has been run in this lab.

## Detector (daily closes)
- **Window.** For each asset and each daily bar t, take the window of the last W = 38 closes, ending at t.
- **Smoothing:** Nadaraya-Watson regression with a Gaussian kernel, fixed bandwidth h = 2.0 bars (LMW used 0.3 times
  a cross-validated bandwidth). It is a fixed 38 x 38 linear smoother with each row normalised.
- **Extrema:**
  - Interior points k = 1..36 of the smoothed series m where m_k > m_{k-1} and m_k >= m_{k+1} (maximum), or the
    mirror (minimum).
  - Each extremum's price is the highest (lowest) close among bars k-1..k+1.
  - Two consecutive extrema of the same kind are merged into the more extreme one.
- **Recency.** Take the last five extrema E1..E5 in time. The window counts only if E5 sits at window index 30..34,
  i.e. 3-7 bars before t. This is LMW's d = 3 confirmation lag, plus a 5-bar tolerance.
- **Patterns, tested in this order (first match wins).** near(a, b, x) means |a - b| <= x times their mean.
  - **HS:** E1 a max; E3 > E1; E3 > E5; near(E1, E5, 1.5%); near(E2, E4, 1.5%).
  - **IHS:** E1 a min; E3 < E1; E3 < E5; near(E1, E5, 1.5%); near(E2, E4, 1.5%).
  - **BTOP:** E1 a max; E1 < E3 < E5; E2 > E4.
  - **BBOT:** E1 a min; E1 > E3 > E5; E2 < E4.
  - **TTOP:** E1 a max; E1 > E3 > E5; E2 < E4.
  - **TBOT:** E1 a min; E1 < E3 < E5; E2 > E4.
  - **RTOP:** E1 a max; E1, E3 and E5 each within 0.75% of their mean; E2 and E4 each within 0.75% of their mean;
    min(E1, E3, E5) > max(E2, E4).
  - **RBOT:** the mirror of RTOP, with E1 a min.

## Trading rule
- A TOP pattern (HS, BTOP, TTOP, RTOP) detected at bar t gives s = -1; a BOT pattern gives s = +1.
- The state is held for H = 5 bars on the asset's own calendar. A newer detection replaces it.
- The REV2 books use only HS and IHS.

## Markets and books (6 trials)
- **CRYPTO-1d:** top-50 perps, UTC daily bars (`resample(.., 24)`), detection on eligible coins only.
  - Position s / (eligible coins) from the day's last hourly row to the next day's, as R243.
  - `slices.run(hedge=False)` with tier costs and funding. Alpha against the equal-weight market.
- **FX:** R247's 11 pairs.
- **IDX:** R247's 10 indices.
- For FX and IDX, the R247 construction applies:
  - union calendar, with the state carried over holidays;
  - w = s / N_d, where N_d counts assets with a detector defined (38 bars of history);
  - 1 bp one-way at 1x;
  - alpha against the group's equal-weight buy-and-hold.
- **Books:** ALL8/CRYPTO-1d, ALL8/FX, ALL8/IDX, REV2/CRYPTO-1d, REV2/FX, REV2/IDX.

## Stages
- **Crypto:**
  1. Discovery 2021-01..2023-12. Pass if 1x NW t >= 2, 2x mean > 0 and alpha > 0.
  2. Validation 2024-01..2025-06. Pass if mean > 0, t >= 1.5 and alpha > 0.
  3. No holdout.
- **FX and IDX:**
  1. Discovery 2001-12. Pass if alpha t >= 2, 2x alpha > 0 and 1x net > 0.
  2. Validation 2013-19. Pass if alpha > 0 with t >= 1.5.
  3. Holdout 2020-01..2026-10-19, read once for validation passers. Pass if alpha > 0 with t >= 2.

## Reported (not decided on)
- **Detections per pattern** per market in discovery.
- **The mean raw 5-bar forward close-to-close return after each pattern** in discovery, with its count (descriptive;
  the sign is not applied).
- **Book statistics at 1x, 2x and 3x, per window reached:**
  - mean, t, gross and cost;
  - alpha, beta, per year.

## Multiplicity
- Trials = 6.
- Program trials before: 9,471,991 (after R250).

## Expectations
- **Detections:** the 1.5% and 0.75% tolerances are tight for crypto's 3-5% daily moves, so HS, IHS and rectangles
  will be rare there. Broadening and triangle patterns will dominate.
- **Prior studies:** LMW found information but not profit. Later work (Savin, Weller and Zvingelis 2007) found HS
  predictive power in US stocks, weak and pre-2000.
- **Most likely:** NULL in all six books. Any discovery signal in IDX/FX most likely comes from 2008.
