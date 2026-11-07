# PREREG: tradesize_v1 (R226). Do trade count and mean print size rank returns beyond quote volume?

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R226
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_tradesize.py`; it reuses `lab/flowfeat.load`, `lab/features.bins_xs`, `lab/slices.py` and
  `lab/research.load_universe`.
- **Origin:**
  - Codex's call on PR #8 (comment 6275953440).
  - `docs/NEXT_SEARCH_SPACE.md` block C.

## Why
- Binance hourly klines carry `count`, the number of trades in the hour.
- The lab loads `count` (`lab/panel.FIELDS`), but no view, book or lane has read it.
- Quote volume divided by count is the mean print size. Larger prints may mark informed or institutional activity
  ([Easley et al., JF 1996](https://doi.org/10.1111/j.1540-6261.1996.tb04074.x)).
- `count` is unsigned. It cannot identify the aggressor or a unique order, and activity can stand in for volatility
  rather than direction ([Clark, Econometrica 1973](https://doi.org/10.2307/1913889)).
- So these are activity features, not signed flow, and the test asks only for information beyond quote volume.

## What the author has seen
- Every result of `volz` (quote volume against its own trailing mean, in atlas_v1 R185 and the context atlas R192).
- No statistic computed from `count`. The holdout (2025-07-01..2026-09-30) is unread for count-based features. Its
  calendar has been read for other books.

## Features
All features are computed at hour t from 1 h bars through t only, at the same timing as every atlas view. Let
`Q_n` = the sum of `quote_volume` over the last n bars, and `N_n` = the sum of `count` over the last n bars. A
feature is NaN when either sum is ≤ 0 or a bar in the window is missing.

| Name | Definition | Role |
|---|---|---|
| `size_lvl` | log(Q_24 / N_24) | tested: mean print size, level |
| `size_chg` | log(Q_24 / N_24) - log(Q_720 / N_720) | tested: mean print size against its own 30-day mean |
| `count_chg` | log(N_24) - log(N_720 / 30) | tested: trade-count surge |
| `qv_lvl` | log(Q_24) | reference for `size_lvl` |
| `qv_chg` | log(Q_24) - log(Q_720 / 30) | reference for `size_chg` and `count_chg` |

Each feature is binned cross-sectionally into 8 bins among eligible coins (top 50 by liquidity; `features.bins_xs`).

## Books
- **Spread book per feature:**
  - **H** = long the slices opened in bin 7 plus short the slices opened in bin 0.
  - **L** = the reverse: long bin 0 plus short bin 7.
  - Both directions are tested, because an unsigned feature has no prior sign. That gives 2 books per tested feature.
- **Slices:**
  - Each slice is held 72 h.
  - Unit size is 1 / (72 x K), where K is the mean number of slices opened per hour in bins 0 and 7 together over
    discovery.
  - Positions are summed before costs (`slices.positions`, then `slices.run`).
  - Universe hedge, tier costs and funding, as in R197 and posfam_v2.
- **Reference books** use the same construction on `qv_lvl` and `qv_chg`, in the H direction. They are controls, not
  tested.

## Stages (the decision)
Each book's daily net is regressed on its reference book's daily net in the same window. The **residual** is that
regression's intercept, with an NW t at lag 10.

1. **Discovery, 2021-01-01..2023-12-31.** A book passes when all three hold:
   - its 1x daily net has NW t (lag 10) ≥ 2;
   - its 2x mean is positive;
   - its residual has NW t ≥ 2. This is the "beyond quote volume" condition.
2. **Validation, 2024-01-01..2025-06-30.** Only stage-1 passers run. A book passes when:
   - its 1x mean is positive with NW t ≥ 1.5;
   - its residual is positive.
3. **Holdout, 2025-07-01..2026-09-30.** Only stage-2 passers run, in the same run, with slices warmed up from 72 h
   before. **CONFIRMED** when its 1x mean is positive with NW t ≥ 2.

Books that fail a stage are not computed on later windows.

## Known boundary
As in every earlier slice lane, `ret[t]` uses the close at t + 1. So the last hour of validation earns the first
holdout bar. That is 1 hour of 13,128. It is stated here rather than fixed, to keep the construction identical to R197
and R211.

## Reported (not decided on)
- 2x and 3x costs.
- Gross and cost per day, max drawdown, and per-year means.
- Each book's correlation with its reference book.
- **Coverage** of each feature among eligible coin-hours over discovery and validation (requested by the call):
  - by liquidity tier, rank 1-20 and 21-50;
  - by listing age, under 180 days and 180 days or more since the coin's first bar in the panel. Coins already trading
    on 2021-01-01 count their age from that date.
- **The first 30 days of 2021 have no `_chg` value.** The panel starts on 2021-01-01, so discovery for those features
  effectively starts on 2021-01-31.

## Multiplicity
- Trials = 6 (3 features x 2 directions). The two reference books are not tested.
- Program trials before: 9,471,750.

## Expectations
- **Most likely outcome: NULL.**
  - `count_chg` is close to `volz` and should mostly duplicate `qv_chg`, so its residual is expected near zero.
  - `size_lvl` is likely a size or liquidity effect within the top 50.
- **`size_chg` has the best chance.** A day of unusually large prints relative to the coin's own month is the one new
  piece of information.
- **If a book confirms:**
  - a forward twin needs Binance live klines for `count`, which `lab/live.py` maps;
  - fills would be on MEXC, whose klines have no trade count;
  - that is the same arrangement as R215.
