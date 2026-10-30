# PREREG: seesaw_v1 (R219), do the big coins' last hours predict the altcoins?

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R219
- **Owner (single writer):** the session that froze it
- **Code:** `scripts/run_seesaw.py`, `lab/slices.py`
- **Sources:** the owner ("other cryptos' charts could lead"); `docs/ALTCOIN_LEADS.md` item 1 (Jia, Wu, Yan & Liu
  2023 seesaw effect; Guo et al. 2024 cross-crypto predictability at minute horizons; Kurihara & Matsumoto 2026, BTC
  leads small alts); `docs/NEXT_SEARCH_SPACE.md` block A3 (catch-up).

## What the author had seen
No coin-level beta, lead-lag or catch-up feature has been computed in this lab (checked in code by the search-space
review). The atlas found short-term reversal in a coin's own returns before costs and nothing net. The published
effects are at minute horizons; hourly bars test only what is left after an hour.

## Data and signal (all known at the close of row t)
- lr[t, s] = log(close[t] / close[t-1]) (the bar ending at row t's close).
- **Leaders** at t: the 5 most liquid eligible crypto contracts (liquidity rank 1-5). **Alts**: eligible crypto contracts
  of rank 6-50. TradFi contracts are excluded (R216's list).
- D[t] = mean of lr over the leaders at t.
- **F1, lead-lag:** g[t, s] = OLS slope of lr[tau, s] on D[tau - 1] over tau in t-719..t (at least 500 pairs);
  score S1 = g[t, s] x D[t], the predicted next-hour return.
- **F2, catch-up over L hours:** b[t, s] = OLS slope of lr[tau, s] on D[tau] over tau in t-719..t (at least 500
  pairs); score S2 = b x (sum of D over the last L hours) - (sum of lr[., s] over the last L hours). A positive score
  means the alt lagged the leaders' move.

## Books
- Every hour, the alts are cut into cross-sectional quintiles of the score (at least 15 alts with a score). Top
  quintile opens a **long** slice, bottom quintile a **short** slice, each held H hours.
- Slice size 1 / (H x K), where K is the mean number of alts per quintile per hour on 2021-01..2023-12. Gross is about
  2, net about 0. Universe hedge, tier costs, funding included in returns.
- Variants (the trials):
  - F1 with H = 1;
  - F1 with H = 4;
  - F2 with L = 1, H = 4;
  - F2 with L = 4, H = 4;
  - F2 with L = 24, H = 24.

## Stages (per variant)
1. **Discovery** 2021-01-01..2023-12-31: pass if the daily net at 1x has mean > 0 and NW t (lag 10) >= 2.
2. **Validation** 2024-01-01..2025-06-30, discovery passers only: pass if mean > 0 and t >= 1.5.
3. **Holdout** 2025-07-01..2026-09-30, validation passers only, one shot (unread for this family): **CONFIRMED** if
   mean > 0 and t >= 2.

## Reported (not decided on)
- Gross and cost per day, and 2x/3x net, for every variant and every window it reaches.
- The long and short legs' gross separately.
- Mean score-quintile spread of next-hour returns (gross, before slicing).
- A one-hour-delay version (signal at t, slice opens at t + 1) for every variant reaching validation: the hourly lead
  may die inside the hour, and live signals arrive minutes after the close.

## Multiplicity
Trials = 5. Program trials before: 9,471,729.

## Expectations
- Hourly lead-lag is mostly arbitraged within minutes. F1 and the short-horizon F2 variants should show small gross
  spreads that tier costs on 1-4 h slices (rank 6-50 pay 8-12 bp one-way) wipe out.
- F2 at 24 h is the one with a chance to survive costs.
- Guess: all NULL at 1x; F2(1, 4) gross positive.
