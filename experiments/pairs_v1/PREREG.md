# PREREG: pairs_v1 (R250). Pairs trading on crypto perps: distance and Engle-Granger selection

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R250
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_pairs.py`, `lab/slices.run` (`hedge=False`: each pair is its own hedge)
- **Queue:** M045 (pairs trading within clusters), M183/M046 (cluster ideas, related)
- **Gate:** 0 (screen).

## What the author has seen
- No pairs or cointegration statistic has been computed in this lab.
- **R238/R245:** one-week cross-sectional spreads and 1-7 day reversal books lost to costs or were flat.
- **R219:** lead-lag between coins at 1 h was +1.45 bp/h before taker cost.
- **Literature:**
  - Gatev, Goetzmann and Rouwenhorst (2006): the distance method on US equities.
  - Crypto studies (Fil and Kristoufek 2020) find pairs profits at high frequency that shrink at daily frequency and
    after costs.

## Universe and timing
- Top-50 eligible perps (`research.load_universe`), hourly closes. Formation uses log prices.
- **Weekly cycle.** Every Monday 00:00 UTC:
  - pairs are formed on the previous 720 hours (30 days);
  - they are traded for the next 168 hours (7 days);
  - every position still open at the end of the week is closed.
- **Candidate coins:** eligible and with a finite close at every hour of the formation window, and eligible at the
  formation time.
  - **TOP20:** candidates with liquidity rank (`u.rank`) <= 20 at the formation time.
  - **TOP50:** all candidates.

## Pair selection (K = 10 pairs per week, a coin may be in several pairs)
- **DIST (Gatev):**
  - Normalise each candidate's price to 1 at the formation start.
  - Rank all pairs by the sum of squared differences of the normalised prices, and keep the 10 smallest.
  - Spread = n_i - n_j (normalised prices continued into the trading week), with the hedge ratio fixed at 1.
- **EG (Engle-Granger, simplified):**
  - For each candidate pair (i, j), with i the more liquid coin, regress log p_i on log p_j by OLS over the formation
    window, giving alpha and beta. Keep pairs with 0.2 <= beta <= 5.
  - **Test:** the Dickey-Fuller t-statistic of the residual: delta e_t = a + b e_{t-1}, with no augmentation lags,
    computed in numpy. statsmodels is not installed.
  - Keep the 10 most negative statistics among those below -3.34 (the 5% Engle-Granger critical value for two
    variables). Fewer than 10 may qualify.
  - Spread = log p_i - beta log p_j - alpha.

## Trading rule (both methods)
- z = (spread - formation mean) / formation std, evaluated at each hourly close in the trading week.
- **Entry:** z > 2 shorts the spread (short i, long j); z < -2 goes long the spread.
- **Exit:** when z crosses 0, at the end of the week, or when either coin leaves eligibility. After an exit, a pair may
  re-enter in the same week.
- **Weights for an open pair:**
  - i gets d / (K (1 + beta));
  - j gets -d beta / (K (1 + beta));
  - d = +1 for long the spread. beta is 1 for DIST.
  - So each open pair has gross 1/K, and the book's gross is at most 1.
- Weights are set at the hourly close and earn the next hour (`slices.run`), with tier costs and funding. No hedge
  basket.

## Books (4 trials)
DIST/TOP20, DIST/TOP50, EG/TOP20, EG/TOP50.

## Stages (as R238)
1. **Discovery 2021-01-01..2023-12-31.** Pass if both hold:
   - 1x NW t (lag 10) >= 2;
   - 2x mean > 0.
2. **Validation 2024-01-01..2025-06-30**, for discovery passers. Pass if the 1x mean > 0 with t >= 1.5.
3. **Holdout:** not read.

## Reported (not decided on)
- Per window reached, at 1x, 2x and 3x:
  - mean, t, Sharpe, max drawdown;
  - gross and cost, gross exposure, per year, trimmed mean.
- Trades, mean holding hours, the share of trades closed by reversion to 0 vs at week end, pairs selected per week
  (EG).

## Multiplicity
- Trials = 4.
- Program trials before: 9,471,987 (after R249).

## Expectations
- Crypto coins share one dominant factor, so many pairs look cointegrated over 30 days and then break.
- Hourly entries at |z| > 2 should trade often, and costs (two legs, both sides) are 4x a single-coin round trip.
- **Most likely:** gross positive for DIST (mean reversion of close substitutes), net negative; NULL.
