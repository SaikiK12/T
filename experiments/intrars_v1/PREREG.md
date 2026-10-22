# PREREG: intrars_v1 (R300). Do the day's relative-strength leaders keep leading into 24:00 UTC? (M318)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R300. It opens the Claude block R300-R319, claimed on issue #7 before this freeze.
- **Method M318,** queued from Linda Raschke on Better System Trader 124 (`docs/TRADER_TALKS.md`). On stocks: the
  day's relative-strength leaders keep leading into the close, with an 80% win rate whose edge "might only last one
  day".
- **Owner (single writer):** the Claude session that froze it.
- **Code:** `scripts/run_intrars.py`, tested on synthetic data in `tests/test_run_intrars.py`:
  - the start, entry and end rows of each clock and anchor, and the New York 10:00 anchor (EST, EDT, weekends and
    NYSE holidays);
  - the legs: top-50 eligibility, the n strongest and n weakest, random tie-breaks, the minimum of 30 names;
  - the exit at the last traded close, and funding over (entry, exit];
  - the fade book as the follow book's mirror;
  - the window masks;
  - an end-to-end run where a planted continuation is found and a null is not.

  It calls `verify()` on this file first and checks every input's sha256 against the block below. The bar and
  statistics helpers (`Bars`, `series_stats`, `decide`) are imported unchanged from `scripts/run_lotcap.py`
  (R298, frozen).
- **Execution mode: API.** The book enters 6-10 names at a fixed hour and closes them at 24:00 UTC every day, which
  is 12-20 orders a day. That is beyond manual web's ~15. The break-even cost per side is reported for any other mode.
- **Gate: 0, on seen data.** The atlas (R185) binned the same feature cross-sectionally over both windows (below).
  Neither window is blind. Only a reserved sample or forward days can confirm a pass.

## What the author has seen
- **R185 (`atlas_v1`), read for this PREREG after the family below was fixed.**
  - Its `dayopen[]@1h/xs8` is the move since the UTC day's first open, in 8 cross-sectional bins at every hour
    (not at fixed anchors). It reports gross conditional means, raw and in excess of the universe.
  - The extreme bins point to **reversal, not continuation**. Discovery 2021-23, then validation 2024-01..2025-06,
    excess bp:
    - The weakest bin (0) beats its tier:
      - top 10: +10.9 / +13.5 at 1 h, +23.8 / +33.4 at 4 h, +32.7 / +52.5 at 12 h;
      - rank 11-25: +4.8 / +3.5 at 1 h, +13.3 / +13.7 at 4 h, +27.7 / +29.5 at 12 h.
    - The strongest bin (7) in the top 10 trails: −8.1 / −8.4 at 1 h, −14.2 / −23.7 at 4 h.
    - Over all 50 names the 1 h excess cells did not replicate (validation t 0.2-0.5).
  - The atlas family as a whole: per trade, its replicated cells earn about 5-11 bp gross, under the 12-16 bp
    round trip (R193 `maker_v1`).
- **R245 (`xsrev_v1`), NULL.** 1-day close-to-close reversal inside liquidity terciles lost 13-17 bp/day, mostly to
  9-12 bp/day of cost.
- **R293 (`er_v1`), NULL.** Each coin's own first UTC hour reverses until 24:00 (time series, post hoc). That is M315,
  to be read only on unseen data. This lane's 1 h anchor is the cross-sectional cousin; it is read here on seen data
  and does not spend M315's test.
- **R290 (`auction_v1`), NULL.** Real session anchors were no more structured than random clocks (BTC, ETH, SOL;
  1-minute bars).
- **A plumbing run on the real bars before this freeze** (`--plumbing`) printed counts only:
  - 499 symbols are ever in the top 50, and 2,099 days;
  - each 00:00 UTC anchor (k 1-12) has 2,090-2,091 days: 1,086-1,087 in discovery and 1,004 in validation, with a
    median of 50 eligible names;
  - the New York 10:00 anchor has 1,439 days (749 / 690);
  - the placebo offsets are 1, 6, 8, 11, 12, 14, 15 and 21 h.

  No return, price change, funding or statistic was read.

## Inputs (frozen)

```inputs
21e8ee4b665d0177eff6eee53bfbc640e80407d33b90131a102590385477a8c0  data/research/meta.json
2f3a43047a900ca85f63afd136459c825c657a4b67e74b7c10e9cf8ed1cb4c35  data/research/rank.npy
1acee88308164de0f3a03d3833ef03cc33b54c177a3f430ac45cf1c579cb5108  data/research/t.npy
a32e993454728aa37e52559d798406ee64bffdcd9196b183ec908addd63b5dbe  lab/data.py
96053b6a8ba4e22469acfa4da4fb59f1d56e610e5b18460a50e40e82da8d4a6f  lab/inference.py
831fe1dfa2c794bc0467137bb10f9395895ecddecfffcbc860b2c6273faae18d  lab/sessions.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
4db33b243bf832e0d4b0356a92cf103eed282241d10b1d8a3b1bfdadfa742eb6  scripts/run_intrars.py
d3cb4b35879bb491245e94a64931cfda2f9e77a79c781fb45342618cad02a82d  scripts/run_lotcap.py
```

The hourly bars and funding (`data/klines_1h`, `data/fundingRate`, 499 coins) are not hashed one by one. The run
records a sha256 over every grid it loaded (`bars_digest` in the summary), so a rerun can show it read the same data.

## Data
- **Bars:** Binance USD-M hourly klines (close, volume) and funding settlements per coin, loaded by R298's `Bars`. A
  bar is traded when its close is finite and its volume positive.
- **Universe:** `data/research/rank.npy` (`scripts/build_views.py`). This is the trailing 30-day mean quote-volume
  rank among all Binance perps trading at that hour, from bars through that hour (`lab.panel.liquidity_rank`).
- **Reserved rows are never read:** bars and funding before 2021-01-01, and from 2026-10-01 (post-archive). The grid
  is [2021-01-01, 2026-10-01).

## Books
- **The clock.** Day i of the real clock starts at 00:00 UTC. The start price is the close of the hourly bar
  ending then.
- **The decision.** At the close of the bar ending k hours later (k in {1, 2, 4, 8, 12}), or at 10:00 New York on
  NYSE trading days ("us10": 14:00 UTC in EDT, 15:00 UTC in EST; no book on other days).
- **Eligible coins:** in the top 50 by rank at the decision bar, and traded at the start and decision bars.
- **The signal:** each coin's move from the start close to the decision close.
- **Legs:** with at least 30 eligible coins, sort by the move. Exact ties are broken at random (seeded): a draw of
  10⁻¹² is added to each move, below any real difference.
  - **follow:** long the n strongest, short the n weakest;
  - **fade:** the reverse;
  - n is 3 (Raschke's "the 3 strongest") or 5 (the top tenth of 50).

  Fewer than 30 eligible names means no book that day.
- **Entry** is at the decision close.
- **Exit** is at the last traded close at or before 24:00 UTC (the close of the bar ending then). A coin with no
  traded bar after its entry exits at its entry.
- **Weights:** equal within a leg, 1 unit long and 1 unit short.
- **Per day:** gross = mean long (return − funding paid) + mean short (−return + funding received). Funding sums the
  settlements in (entry close, exit close]. A settlement exactly at the entry close is not charged.

## Costs (API, per side)
- **Levels:** 8.5 / 17 / 25.5 bp at 1x / 2x / 3x.
- **Turnover:** the book is entered and closed every day. That is 4 units a day: 2 to enter and 2 to exit. So the
  daily cost is 34 / 68 / 102 bp at 1x / 2x / 3x.
- **Break-even:** the cost per side at which the book's gross mean is zero (gross / 4) is reported.

## The family (24 trials)
anchor {k1, k2, k4, k8, k12, us10} × n {3, 5} × side {follow, fade}.

- follow and fade are exact mirrors in gross, so at most one of each pair can earn net.
- Both are in the family because Raschke (follow) and the atlas (fade) point in opposite directions.

## Windows (by day; a day counts only when its hold ends inside the window)
- **Discovery:** 2021-01-01..2023-12-31.
- **Validation:** 2024-01-01..2026-09-30.

## Statistics
- **Per book and window, gross and net at 1x / 2x / 3x:**
  - mean bp/day and %/yr, median, hit rate;
  - the mean without the 10 best days and the 10 best days' share of the sum;
  - annual Sharpe.
- **The t** is Newey-West, lag 5, on the calendar grid of days, missing days as gaps. These are R298's
  `series_stats` with hold 24.

## Decision
- **The pick:** among the 24 books, the one with the highest discovery net 1x t, among those with a positive
  discovery mean (R298's `decide`).
- **The pick passes** only if, in validation, all three hold:
  1. net 1x t ≥ 2.0;
  2. the net 2x mean is positive;
  3. the net 1x mean without its 10 best days is positive.
- **Verdict:** PARTIAL (gate 0) if the pick passes, else NULL. Validation is read once. No second pick.
- **What a pass earns:**
  - a forward paper lane with its own id and PREREG, API mode, on MEXC prices where the coins list;
  - a place in the next reserved batch after batch 1, on 2020, through that batch's frozen PREREG.
- **A NULL** closes M318 in this form on Binance's top 50. The atlas's per-tier fade (top 10, rank 11-25) would be a
  new lane with its own id.

## Reported (not decided on)
- **Placebo clocks.** Eight offsets o drawn once (seed 300, without replacement, from 1-23 h): 1, 6, 8, 11, 12, 14,
  15 and 21.
  - Each clock runs the 20 k-anchored books with the day starting at o:00 UTC.
  - For each clock: its highest discovery net t, its pick (the same rule) and that pick's validation net t and
    bp/day.
  - The real clock's rank among the 9 on both is reported. This is R290's question: is 00:00 UTC special for this
    rule?
- **Hansen SPA and White's reality check** over the 24 books, per window, on net 1x daily series.
  - Days without a book count as 0.
  - Stationary bootstrap, 2,000 draws, mean block 10 days, seed 300.
- **Per book and window:**
  - the long and short legs' means;
  - the price-only mean (no funding);
  - the equal-weight eligible basket's mean, and each leg's excess over it (does the edge sit in the leaders or in
    the laggards?);
  - median names;
  - the break-even cost per side.
- **Per follow book and calendar year:** gross and net 1x bp/day. The fade books are their negatives in gross.

## Outputs
- `results/summary.json`: every number above, the inputs' hashes and `bars_digest`.
- `results/days.csv`: every follow book's days, with gross, legs, basket, names, and the symbols in each leg. The
  fade books are the mirror.
- `run.log`, and FINDINGS.md with 1x/2x/3x costs read against `registry.program_trials()`.

## Power (written before the result)
This uses the normal approximation, with validation of 2.75 years and the 2.0 bar. The expected t is the annual net
Sharpe × √2.75.

| Annual net Sharpe of the pick | Expected validation t | P(t ≥ 2.0) |
|---|---|---|
| 0.5 | 0.8 | 12% |
| 1.0 | 1.7 | 37% |
| 1.5 | 2.5 | 69% |
| 2.0 | 3.3 | 91% |

- A 3-vs-3 alt book held for 12-23 hours has a daily volatility of several percent.
- A net edge of 10 bp/day at 4% daily volatility is a Sharpe of about 0.5.
- So only a large, steady spread passes. A NULL rules out that, not a small edge.

## Known limits (written before the result)
- **Seen data:** the atlas read the same feature on both windows. See the gate.
- **Costs dominate.** 34 bp a day at 1x on a book that turns over fully twice a day. The atlas's fade cells, if they
  carry over, are about this size in gross.
- **Fills at the close.** Entry and exit are at hourly closes, as a market order placed at the hour would get, plus
  the cost. Gaps inside the hour are not modelled.
- **Shorting.** Pumped coins can be hard to short. Delisting-notice coins may block new positions on Binance; a paper
  short is held here.
- **Prices.** Binance prices. MEXC listing of each coin is not checked here.
- **Impact** above 7 bp per side (R262's square-root model) matters only above about $100k per book.

## Multiplicity
- Program trials before this lane: 9,478,613 after R298. R299 `mlrank_v1` (12 trials) is running and is appended
  first.
- 24 trials, one pick, one validation read. One registry row with 24 trials.
- The placebo clocks (160 books) are controls, never picked, and not counted as trials (as in R290).
- SPA over the 24 is reported per window. The result is read against `registry.program_trials()` in FINDINGS.
