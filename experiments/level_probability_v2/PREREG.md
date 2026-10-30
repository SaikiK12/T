# PREREG: level_probability_v2 (R333). The owner's break-or-rebound model on the top 100 Binance perps (M412)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R333
- **Method M412:** the owner's idea (2026-10-24): when a price sits at a support or resistance level, estimate the
  probability that it breaks through or rebounds, and trade only when that confidence pays the costs.
- **Owner (single writer):** the Claude session that froze it. R333 is claimed on issue #7 before the freeze.
- **Date registered (UTC):** 2026-10-26
- **Code:** `scripts/run_levels_v2.py`. `--run` calls `verify()` on this file first, checks every input's sha256
  against the block below, and checks the data digest below before it computes anything. Tested in
  `tests/test_levels_v2.py` on invented series:
  - barriers, classes and through-direction returns, for both sides, with and without the one-hour delay;
  - one open event per coin; a missing close drops the event and frees the coin;
  - the features at a decision row do not change when anything after that row changes;
  - the walk-forward purge, the quarterly blocks, and predictions only inside test blocks;
  - the four policies, the books' cost charge and the measured lines.
- **Execution mode: API.** Hourly decisions on up to 100 coins exceed the owner's manual limit of about 15 orders a day.
- **Gate: 0, on seen data.** Every hour of 2021-01..2026-09 on these perps was read by earlier lanes.

## Why this lane exists
- **R330** (`experiments/level_probability_v1`, Codex, 6 trials) built the owner's idea on four MEXC coins (BTC, ETH,
  SOL, WIF), one decision per coin a day at 00 UTC, fit on 2025-05..08. Its preselected policy declined all 178
  validation events (NULL_INACTIVE). Its probabilities were slightly worse than the reference (paired Brier +0.0012 on
  177 labels), and every active control lost at 2x and 3x. The sample was too small to say whether the idea works.
- **R306** (M323, plain level rules on 4-hour bars of the top 50, 24 trials) was NULL. Fades lost and breaks earned
  +7 to +9 bp gross per trade in validation, below the 14.4 bp round trip. Levels broke more often than they held.
- **Measure before launching (owner, 2026-10-26):** the owner asked to experiment with other ways and measure them
  before launching any. This lane launches nothing. It is a backtest on seen hours. Next to the lab's costs it reports
  the gross edge, the one-way cost at which the mean trade breaks even, and the books at a zero-fee cost.
- **Why a zero-fee line:** the second Claude session read MEXC's public contract endpoint once on 2026-10-26
  (`reports/Edge leads after the registry map.md`, branch `ccr-23562535-bd0mr3`; not re-read here). It lists 97
  contracts at 0 maker and 0 taker fee, with a median spread of one tick (about 2 bp).
  - Earlier lanes earned gross edges below the lab's round trip. In R306, breaks earned +7 to +9 bp a trade in
    validation, against a 14.4 bp round trip.
  - The coins here are Binance's top 100, not that list. So the zero-fee line is a measurement, not a decision.
- **This lane** keeps R330's level and outcome definitions and gives the idea the sample it needs:
  - every hour of 2021-01..2026-09;
  - the point-in-time top 100 crypto perps by 30-day quote volume;
  - one model across all coins, refit each quarter on events that ended before it;
  - 17 features that describe the level, the approach and the market around it.

## What the author has seen
- **R330's and R306's PREREGs and FINDINGS,** and the results of the other level and chart lanes on these hours: R243,
  R246, R263, R287 and R300 (all NULL).
- **The plumbing run of this script** (`--plumbing`, 2026-10-26): event counts by variant and year, the support share,
  each feature's missing share, and the data digest. It computes no class, no return and no model.
  - **Coins:** 623 columns (crypto perps ever in the top 100), 50,376 hours.

    | Variant | Candidate hours | Events | Dropped (gap in the path) | Coins | Support share |
    |---|---|---|---|---|---|
    | V0 | 952,303 | 212,227 | 102 | 622 | 53.9% |
    | V1 | 952,303 | 200,931 | 109 | 622 | 53.8% |
    | V2 | 2,011,739 | 358,934 | 293 | 623 | 52.2% |
    | V3 | 535,427 | 126,872 | 34 | 621 | 54.4% |
    | V4 | 952,303 | 171,485 | 99 | 622 | 53.2% |

  - **V0 events by year:** 2021 34,367, 2022 37,716, 2023 36,592, 2024 37,775, 2025 37,413, 2026 28,364 (to 09-30).
  - **Missing features (range over variants):** major 5.4-6.0%, fund 0.4-0.5%, prem 0.7%; none for the others.
    `major` is missing for coins with fewer than 720 prior closes.
- **A first plumbing run** read the `data/research` cache, whose eligibility is the top 50: V0 had 103,481 events on 470
  coins, and 69 were dropped. Its counts were seen. The universe was then rebuilt as in Data, and the run above
  replaces it.
- **Never computed before the freeze:** a class share, a return, a payoff or a probability of any event.

## Inputs (frozen)

```inputs
c321eaa0779d676851d2e1cb36538dcf49da7d1d52f848b0bcce5e962da49e20  data/klines_1h/manifest.json
4599f9d4b7de402778a7f46e90652229206d1c5537a98ea69479893b481c925a  data/fundingRate/manifest.json
c1cba8a31b72d1418134c415ed9662234602442a99521c7f078685571789a5aa  data/premiumIndexKlines_1h/manifest.json
55e45182aade91c169b5a58b94ea9c831a64bc7753828fd276b7c94ed26e8de6  docs/provenance/klines_1h.json
84a3aadbf5ac0439b99209714c85ab0484b775f1258701835a64029c1ec3e4de  docs/provenance/fundingRate.json
b393a5e3ffa81a1877ce59222cef5b9909e9e1db9f972552689e7922abeb3838  docs/provenance/premiumIndexKlines_1h.json
af7b1a0fbf99471720f765ece0b16734b88247aa84feb7f21137103500d983ea  experiments/venue_gap_v1/results/tradfi_symbols.json
a32e993454728aa37e52559d798406ee64bffdcd9196b183ec908addd63b5dbe  lab/data.py
66ac88bdf3034e11401d18e1dac09e7379d59cbb0654332e4d1458200fca0a27  lab/engine.py
e48dc4a377846fa3a09ab71f6e7a3ceb5a4a2cba7ceb75368f9c065222a6fe31  lab/features.py
fee9835bcc73e14ec277c93d0edf2a1b3f6f1ad739b15e1895dec28a4a186db6  lab/panel.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
7925aa5c0e308c2e4d5ec2c94012242310313846fcdf5cacac2b5c5b669bf1cb  lab/research.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
7c2a0c95c997545d3ee0ed01c7766227ce8e187e4f18a73bece89dd52a8fc711  scripts/run_levels_v2.py
848a5cc24c900bf375a342a55ae142d19662956c8d6d136779c083d4e81ca0f5  tests/test_levels_v2.py
```

- **Data digest:** `0374bd1c296a27684f6350d53fdab58b9ee865c053e1d8200150024cb2e6cbe5`
  (`digest()`: sha256 of the symbol list and every array the run reads; from the plumbing run, checked by `--run`).
- **Libraries:** scikit-learn 1.9.1, numpy 2.5.3, pandas 3.0.5, numba 0.68.0 (this venv).

## Data
- **Universe:** the point-in-time top 100 Binance USD-M crypto perps, built by `load()` as `research.make_universe`
  builds the lab's universes:
  - every file in `data/klines_1h` (900 USDT perps), less the 215 TradFi perps listed in
    `experiments/venue_gap_v1/results/tradfi_symbols.json`, removed before ranking;
  - hourly rows from 2021-01-01 00:00 to 2026-09-30 23:00 UTC;
  - rank: trailing 30-day mean quote volume over bars through hour i (`panel.liquidity_rank`: 720 hours, at least
    180);
  - **eligible at hour i:** rank ≤ 100 at hour i. Delisted coins are included while they were eligible.
  - **Why not the `data/research` cache:** its columns are the coins ever in the top 50 (`scripts/build_views.py`), so
    its ranks 51-100 would hold only coins that reach the top 50 at some time, which is a selection on the future.
- **Per coin and hour,** all known at the close of hour i:
  - the close (log price) and quote volume and taker buy quote volume, from `data/klines_1h`;
  - the one-way cost tier of the rank (`engine.cost_matrix`);
  - the next-bar return net of the funding a long pays (`engine.forward_returns`);
  - the last settled funding rate, from `data/fundingRate`, carried forward;
  - the premium index close, from `data/premiumIndexKlines_1h`.
- **Reserved rows:** none. `panel.load_panel` refuses rows before 2021-01-01, and the panel ends on 2026-09-30.

## Events
For each coin, hour i, and variant (lookback L, horizon N, delay D):
- **Volatility:** sigma12 = sqrt(12 × the mean of the last 72 squared hourly log returns).
- **Levels:** resistance = the maximum of the L closes before hour i; support = their minimum. The decision close is
  excluded.
- **Candidate:** the coin is eligible at i; the close, sigma12 and both levels are valid; and the last 72 hours all had
  positive quote volume. The close is within 0.25 sigma12 of the nearer level, measured in log price. A tie goes to
  support.
  - **Side:** +1 at resistance (its breakout is up), -1 at support.
  - A close already beyond its level qualifies when it is within 0.25 sigma12 of it.
- **One open event per coin:** candidates are walked in time order. A new event may start only at an hour after the
  previous event's exit.
- **Entry:** at the close of hour e = i + D.
- **Barriers:** ± sigma12(i) around the entry's log close, read on the closes e+1 .. e+N.
  - The first close on or beyond a barrier decides the class: **through** (the side's way), **away**, or **timeout** at
    e+N.
  - Only closes are read; the hourly bars carry no path inside the hour.
- **Through-direction return:** side × the sum of the next-bar returns net of funding over e .. exit−1. A position
  that trades through (+1) earns it; a position that trades away (-1) earns its negative.
- **Dropped:** an event whose path has a missing close or return. The coin is free again from the next hour. Counted.

| Variant | Lookback L | Horizon N | Delay D | Role |
|---|---|---|---|---|
| V0 | 72 h | 12 h | 0 | primary (lab convention: enter at the decision close) |
| V1 | 72 h | 12 h | 1 h | R330's delay |
| V2 | 24 h | 12 h | 0 | shorter levels |
| V3 | 168 h | 12 h | 0 | weekly levels |
| V4 | 72 h | 24 h | 0 | longer horizon |

## Features (17, at the decision close)
All are signed by the side, so a positive value points the breakout's way unless stated.
- **dist:** side × (level − log close) / sigma12. Positive while the level is not yet crossed.
- **app24, app4:** side × the 24-hour and 4-hour log return / sigma12 (the approach).
- **age:** hours since the level's close was printed, divided by L.
- **touches:** how many other of the L prior closes were within 0.25 sigma12 of the level.
- **range:** (resistance − support) / sigma12.
- **major:** 1 if the level is also the extreme of the prior 720 closes, else 0; missing when 720 closes are not valid.
- **volr:** the standard deviation of the last 24 hourly log returns divided by that of the last 72.
- **vsurge:** log(mean quote volume of the last 4 hours / that of the last 72).
- **taker:** side × (2 × taker buy quote volume / quote volume − 1), over the last 4 hours.
- **fund, prem:** side × the last settled funding rate; side × the premium index close.
- **btc:** side × BTC's 24-hour log return / BTC's sigma12.
- **lrank:** log of the coin's volume rank.
- **hsin, hcos:** the hour of day on a circle.
- **side.**

Missing values stay missing. The model handles them natively.

## Model and walk-forward
- **Classifier:** scikit-learn `HistGradientBoostingClassifier` with learning rate 0.05, 300 iterations, 31 leaves,
  at least 500 events a leaf, L2 1.0, no early stopping, random state 0. Three classes: through, away and timeout.
- **Test blocks:** calendar quarters from 2022-01-01 to 2026-07-01 (19 blocks).
- **Training for a block:** every event of the variant whose exit close is at least 24 hours before the block starts.
  The window expands. There must be at least 1,000 events.
- **Per block, from the training events only:**
  - the climatology (the share of each class);
  - the payoff of each class (its mean through-direction return in sigma12 units);
  - the 90th percentile of the model's |expected| on its own training events.
- **Expected through-direction return** of a test event: sigma12 × Σ p(class) × payoff(class). The same from the
  climatology gives the CLIM control.

## Policies, books and controls (11 trials)
- **The policies** turn an event's expected return into a trade: through if positive, away if negative, else none.
  - **P1:** |expected| > 2 × the round trip (4 × the one-way cost).
  - **P2 (R330's rule):** |expected| > 2 × the round trip + 0.25 sigma12.
  - **P3:** |expected / sigma12| ≥ the training 90th percentile, and P1.
  - **P0 (zero-fee, measured):** |expected| > 4 × 1 bp, the 2x round trip at the zero-fee cost.
- **Books:** V0 with P1, P2, P3 and P0; V1, V2, V3 and V4 with P1. **8 books.**
- **Controls on V0:** **3 trials.**
  - CLIM: P1 on the climatology's expected return;
  - THROUGH: every out-of-sample event, through;
  - AWAY: every out-of-sample event, away.
- **Placebo** (not a trial): V0P1's trades with random sides, 1,000 draws, seed 333. Reports the share of draws at or
  above V0P1's 1x mean per trade.
- **Net per trade:** the side's return − 2 × multiple × the one-way cost of the coin's tier at the decision hour.
  - The tiers are 6 bp (top 20), 8 bp (21-50) and 12 bp (51-100), from `engine.cost_matrix`.
  - The multiple is 1x, 2x and 3x.
- **Day series:** each entry day's mean net per trade. Days with no trade are missing. The window is 2022-01-01 to
  2026-09-30. The t-stat is Newey-West, lag 3.

## Decision
- **The primary is V0P1,** fixed now. No other book can be picked.
- **It passes** only if all five hold, over 2022-01-01..2026-09-30:
  1. the 1x day series' Newey-West t ≥ 2.0;
  2. the 2x day mean is positive;
  3. the 1x day mean without its 10 best days is positive;
  4. the 1x day mean is positive in both halves (2022-2023 and 2024-01..2026-09);
  5. the model's log loss beats the climatology's on V0's out-of-sample events. This is the day series of (model −
     climatology) mean log loss, Newey-West t ≤ −2.0.
- **Verdict:** PARTIAL (gate 0) if all five hold, else NULL.
- **What a PARTIAL earns:**
  - a forward paper lane for V0P1, with a new id, frozen before its first forward day;
  - a place in reserved batch 2.
  It is not a gate-1 pass. These hours were seen, and 9.48 million program trials stand behind any t of 2.
- **What a NULL means:** the owner's level probability idea, as built here, does not pay API costs on the top 100
  Binance perps. M412 is NULL at this scope, with no retuning on these data. A new idea (other features, other
  levels, intrabar paths) is a new lane.

## Reported (not decided on)
- **Measured lines, for every book and control:**
  - gross: the book with no cost;
  - zero-fee: the book at a flat 1 bp a side (half of a one-tick spread of about 2 bp);
  - break-even: the one-way cost at which the mean trade nets zero (half the mean gross trade).
- **Per book:**
  - 1x, 2x and 3x: trades, days, bp per trade, bp per day, Newey-West t, hit rate, and bp per day without the 10 best
    days;
  - the halves at 1x;
  - bp per trade by year at 1x;
  - the share of trades taken through the level.
- **The controls** at 1x, 2x and 3x, and the placebo.
- **V0's probability skill:**
  - log loss and Brier score, model against climatology;
  - reliability by decile of the predicted through and away probabilities.
- **Per variant and fit:** candidates, kept and dropped events, out-of-sample events, and per block the training size,
  the climatology and the class payoffs.
- **The V0 out-of-sample events** (`results/v0_oos_events.csv.gz`): symbol, time, exit, class, return, sigma12,
  cost, side, the three probabilities, the expected return and P1's side.

## Power
- **Events:** 177,860 V0 events in the test window (2022-01-01..2026-09-30, 1,734 days), about 103 a day.
- **One trade's spread:** about one sigma12, since exits sit at ± sigma12 or at the horizon's close. sigma12 on these
  coins is mostly 2-5%; take 3.5%.
- **A day's mean:** with n trades a day whose signed returns correlate at ρ, its standard deviation is about
  3.5% × sqrt(ρ + (1 − ρ) / n). For n = 10 and ρ from 0.1 to 0.3 that is 1.3-2.0%. ρ is not measured before the
  freeze.
- **Detectable edge:** over about 1,700 trading days, an expected t of 2.8 (80% power for t ≥ 2) needs a 1x mean of
  about 9-14 bp per trade. With the 1x round trip of 12-24 bp, that is a gross edge of about 21-38 bp per trade.
- **What it cannot see:** a real net edge of 3-5 bp per trade would most likely read as a positive mean with t below
  2, and so as NULL.

## Multiplicity
- **This lane:** 11 trials (8 books and 3 controls). The placebo, the halves and the skill diagnostics are not trials.
- **Program trials so far:** 9,478,976 (`registry.program_trials('registry/rounds.csv')` on 2026-10-26).
- **Reading:** this is a gate-0 screen. Even a t of 4 on seen hours is a reason for forward paper evidence, not a
  claim of an edge.

## Evidence lineage and admission
- **Canonical method:** M412. Related: M323 (R306), M011 and M010 (R246), and the chart families of R243 and R263.
- **Parent rounds:** R330 (6 trials; MEXC BTC, ETH, SOL and WIF hourly closes, 2025-05..2026-09, daily decisions).
  - **Overlap with R330:** those 4 coins' Binance hours in 2025-05..2026-09 are here too, decided hourly instead of
    daily. They are a small part of 623 coins over 5.75 years.
- **Decision group:** M412 and level probability. A pass feeds one forward lane and reserved batch 2.
- **Samples seen by parents and searches:** every hour of 2021-01..2026-09 on the Binance top 50, by many lanes (among
  them R243, R246, R263, R287, R300 and R306); ranks 51-100 by fewer, at daily resolution (R299, R304 and R305 on the
  top 150).
- **Fresh sample:** none here. Fresh evidence would be forward paper days or reserved batch 2.
- **docs/GATES.md sha256:** e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926.
  - Gate 0 asks for a frozen PREREG, a 1x/2x/3x report and a registry row.
  - Not met: gate 1's unread sample, the strict on-time forward clock, and leave-two-coins-out. These block admission
    beyond gate 0 whatever the verdict.
- This section authorizes no reserved read and no real order.

## Known limits
- **Seen data:** every hour was read before.
- **Closes only:** barriers are read on hourly closes. A barrier touched inside an hour and left before the close does
  not count. This is R330's rule.
- **Costs:** the lab's API tiers, not measured fills. Entry at the decision close (V0) assumes an order right at the
  close; V1 measures what one hour of delay costs.
- **Overlapping events across coins:** coins move together, so events on the same day are correlated. The day series
  and Newey-West lag 3 take some of this into account; the cross-section's correlation is not modelled further.
- **No capital model:** the day series averages the trades of each day. It is not a portfolio with sizing and margin.

## Stop rules
- Run once after the freeze. No new feature, variant, policy, block, threshold or cost after any result.
- An error in the code found after the run is reported in FINDINGS with its effect. A fix is a new lane.

## Outputs
- `results/summary.json`: every book, control, placebo, skill diagnostic, fit and check, the verdict, the input
  hashes, the data digest and the library versions.
- `results/v0_oos_events.csv.gz`
- `run.log`
- `FINDINGS.md` with 1x/2x/3x costs, read against `registry.program_trials()`, and the registry row (11 trials).
