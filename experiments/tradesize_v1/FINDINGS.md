# FINDINGS: tradesize_v1 (R226). Do trade count and mean print size rank returns beyond quote volume?

**Verdict: NULL. No book passed discovery.**
- Trade count adds nothing beyond quote volume. Its 24 h surge correlates 0.99 with the quote-volume surge as a book.
- Mean print size, as a level or as a change against the coin's own month, ranks nothing in either direction.
- The holdout was not read for any of these books.

- **Registry row:** R226 (trials: 6). Program trials after it: 9,471,756.
- **Origin:** Codex's call on PR #8 (comment 6275953440), `docs/NEXT_SEARCH_SPACE.md` block C.
- **Reproduce:** prereg sha 1c1b0264, committed in 854fa66 before the run; `python scripts/run_tradesize.py` (about 2.5
  minutes).
- **Window:** discovery 2021-01-01..2023-12-31, 1,095 days. The `_chg` features start on 2021-01-31.

## Coverage
Share of eligible coin-hours (top 50) with a finite feature, over discovery and validation:

| Feature | Rank 1-20 | Rank 21-50 | Listed < 180 d | Listed ≥ 180 d |
|---|---|---|---|---|
| `size_lvl`, `qv_lvl` | 99.8% | 99.9% | 99.95% | 99.8% |
| `size_chg`, `count_chg`, `qv_chg` | 93.8% | 92.9% | 79.6% | 98.1% |

The 30-day features miss a coin's first month, which is the main gap for young listings.

## Numbers
- Books are 72 h spreads: H = long bin 7 and short bin 0; L is the reverse.
- Each has a universe hedge.
- Figures are daily net in bp/day, with NW t at lag 10.
- The residual is the intercept of a regression on the reference book's net in the same window.

| Book | Gross | Cost 1x | Net 1x (t) | Net 2x | Net 3x | Max DD | Corr with ref | Residual (t) |
|---|---|---|---|---|---|---|---|---|
| size_lvl H | -3.1 | 1.4 | -4.6 (-0.97) | -6.0 | -7.5 | 67% | 0.65 | -3.7 (-1.01) |
| size_lvl L | +3.1 | 1.4 | +1.7 (0.36) | +0.3 | -1.2 | 52% | -0.65 | +0.8 (0.23) |
| size_chg H | +6.3 | 2.9 | +3.3 (0.77) | +0.4 | -2.6 | 61% | 0.81 | -0.5 (-0.17) |
| size_chg L | -6.3 | 2.9 | -9.2 (-2.14) | -12.1 | -15.1 | 121% | -0.81 | -5.4 (-1.95) |
| count_chg H | +9.1 | 2.9 | +6.1 (1.13) | +3.2 | +0.3 | 60% | 0.99 | +0.3 (0.24) |
| count_chg L | -9.1 | 2.9 | -12.0 (-2.21) | -14.9 | -17.8 | 142% | -0.99 | -6.1 (-5.46) |

Reference books (H direction, not tested):
- `qv_lvl`: -1.4 bp/day (t -0.31).
- `qv_chg`: +5.9 bp/day (t 1.10).

Totals behind the drawdowns are unit-size sums of daily returns, not compounded.

Net 1x by year, in bp/day:

| Book | 2021 | 2022 | 2023 |
|---|---|---|---|
| size_lvl H | -12.0 | +0.5 | -2.2 |
| size_chg H | +18.6 | -4.5 | -4.2 |
| count_chg H | +17.1 | -9.4 | +10.6 |

## Cost sensitivity
- Costs are 1.4-2.9 bp/day at 1x, so no verdict depends on them. Every book fails on its gross.
- The best gross is `count_chg` H at +9.1 bp/day, t 1.13 at 1x. It is still positive at 3x (+0.3) but is not
  significant at any cost.

## Reading
- **Count is quote volume in disguise.**
  - The `count_chg` H book correlates 0.99 with the `qv_chg` reference, and its residual is +0.3 bp/day.
  - The large negative residual t of the L books (-5.46) is not a signal. Two near-identical books traded in opposite
    directions leave mainly the cost of trading twice. The residual is therefore about -2 x costs, with very little
    noise.
- **The one new piece of information, mean print size against its own month, does not rank returns.**
  - The H book gains +3.3 bp/day, and all of that is quote volume: its residual is -0.5.
  - Its 2021 gain (+18.6) reverses in 2022-23.
- **Big prints carry no direction here.** This agrees with the call's own warning: an unsigned count cannot identify
  the aggressor ([Easley et al.](https://doi.org/10.1111/j.1540-6261.1996.tb04074.x);
  [Clark](https://doi.org/10.2307/1913889)).
- **What would still be new:** signed size, meaning taker-buy quote volume per taker trade. Binance klines carry no
  taker trade count, so that needs the aggTrades archive, a large download. This lane does not propose it.

## Not checked
- Horizons other than 72 h.
- Bins other than the extremes.
- Windows other than 24 h against 720 h (block C's 6 h and 72 h means were not run).
- Validation and holdout, which were never computed because nothing passed discovery.
