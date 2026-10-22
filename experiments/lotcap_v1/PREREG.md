# PREREG: lotcap_v1 (R298). Can a protective cover on the short leg harvest the lottery cluster's median? (M276)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R298 (Claude block R280-R299, claimed on issue #7 on 2026-10-22 before this freeze).
- **Method M276,** queued by R282's FINDINGS (`experiments/pitfac_v1/FINDINGS.md`, "The lead this leaves").
  - Young, small, heavily traded coins (the "lottery" cluster) do worse than the rest on a typical day: rank IC t 10-16.
  - R282's quintile books earned nothing: a few squeezes in the short leg cancel the median.
  - M276 shorts that side with a cap on each coin's loss, against the long side.
- **Owner (single writer):** the Claude session that froze it.
- **Code:** `scripts/run_lotcap.py`, tested on synthetic data in `tests/test_run_lotcap.py`:
  - the scores' percentile ranks and their direction;
  - the legs and the rebalance times;
  - reserved rows dropped on load;
  - the cover: untraded bars never trigger it, and the exit is at the triggering close;
  - funding over (entry, exit];
  - turnover and cover exits charged;
  - the window masks;
  - the statistics and the decision;
  - an end-to-end run on synthetic coins.

  It calls `verify()` on this file first and checks every input's sha256 against the block below.
- **Execution mode: API.** Each book holds about 25-30 names per leg, rebalanced daily or weekly, and checks every
  short at each hourly close. That is beyond manual web's ~15 orders a day.
- **Gate: 0, on seen data.**
  - R282 printed the uncovered age and vol_mcap books by year for 2021-2026, so neither window below is blind.
  - The discovery/validation split here is a stability check on a rule chosen after seeing those tables, not an
    out-of-sample test.
  - Only a reserved sample (2020, a later batch) or forward days can confirm a pass.

## What the author has seen
- **R282 in full** (`experiments/pitfac_v1/FINDINGS.md`, `results/`):
  - **The rank ICs:** age +0.053 (t 13.8), vol_mcap −0.068 (t −15.7), size +0.046 (t 10.4) at 24 h, and the same sign
    every year.
  - **The uncovered 24 h quintile books, gross, all days:**
    - age: mean +4.35, median +13.54 bp/day, NW t 0.68, the best 10 days 100% of the sum;
    - vol_mcap: mean +2.66, median +10.18;
    - size: mean −4.74, median +8.94.
  - **The books by year, gross bp/day:**
    - age: 2021 −11.8, 2022 +10.8, 2023 +14.9, 2024 +15.4, 2025 −8.2, 2026 +4.9;
    - vol_mcap: 2021 −13.7, 2022 +0.8, 2023 −9.1, 2024 +18.9, 2025 +3.2, 2026 +20.0.
  - **The factor correlations:** size vs vol_mcap −0.79, age vs size +0.42.
  - **Oi_mcap's book in the other direction** (long high OI/cap): +36 bp/day, a post-hoc observation. Oi_mcap is not
    used here. It covers about 56 names a day and would shrink the cluster's universe.
  - **The four best squeeze days:** ALPACA 2025-04-30, UNFI 2022-06-07, HIFI 2025-09-12, LSK 2026-09-13.
- **R274 (`squeeze_v1`):** the same close-based cover (10 / 20 / 35%) on event shorts. There, "the cover cuts the tail
  and the median with it", NULL. That is why both "no cover" and the three levels are in the family.
- **R280:** carry short legs pumped 95% or more within a day on 155 days.
- **A plumbing run on the real factor table, before this freeze** (`--plumbing`), which printed counts only:
  - 297,093 factor rows;
  - 2,092 decisions from 2021-01-07 23:00 to 2026-09-29 23:00 UTC (bar opens);
  - for each book (discovery / validation decisions, median names per leg, distinct coins):
    - age h24: 1,088 / 1,003, 30, 720;
    - age h168: 155 / 142, 30, 711;
    - cluster h24: 1,088 / 1,003, 25, 408;
    - cluster h168: 155 / 142, 24, 397.

  No return, price, funding or statistic was read.

## Inputs (frozen)

```inputs
deb00da8d4bb62d232091b237bb719c02ac34b1102029466daeebb4e0202539c  experiments/pitfac_v1/factors.parquet
a32e993454728aa37e52559d798406ee64bffdcd9196b183ec908addd63b5dbe  lab/data.py
96053b6a8ba4e22469acfa4da4fb59f1d56e610e5b18460a50e40e82da8d4a6f  lab/inference.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
d3cb4b35879bb491245e94a64931cfda2f9e77a79c781fb45342618cad02a82d  scripts/run_lotcap.py
```

The hourly bars and funding (`data/klines_1h`, `data/fundingRate`, about 720 files) are not hashed one by one. The run
records a sha256 over every grid it loaded (`bars_digest` in the summary), so a rerun can show it read the same data.

## Data
- **The factor table:** R282's frozen `factors.parquet`. It has one row per (decision bar t, Binance perp) for the top
  150 perps by 30-day volume.
  - t is the hourly bar that ends at 00:00 UTC. Values use only what was known by then (R282's audit).
  - Columns used: age (days listed), size (free-float cap, Coin Metrics) and vol_mcap (volume per unit of cap).
- **Bars:** Binance USD-M hourly klines (close, volume) and funding settlements per coin. A bar is traded when its
  close is finite and its volume positive.
- **Reserved rows are dropped on load and never read:** bars and funding before 2021-01-01, and from 2026-10-01
  (post-archive).

## Scores (per decision t, across the coins with a value)
- **lot_age:** the percentile rank of −age. The youngest coin is the most lottery-like.
- **lot_cluster:** the mean of the percentile ranks of −age, −size and +vol_mcap, over coins with all three.
- Ranks average ties. A higher score is more lottery-like.

## Books
- **Legs:** at each rebalance, sort the scored coins by score (ties by symbol). With n ≥ 30 coins, k = floor(n / 5):
  - long the k lowest scores (old, large, low turnover);
  - short the k highest.

  Fewer than 30 coins means no book that day.
- **Rebalancing:** hold 24 h, rebalanced at every decision; or hold 168 h, rebalanced every 7th day from the first
  decision.
- **Entry** is the close of the decision bar (00:00 UTC). A coin whose entry bar is not traded is left out of its
  leg.
- **Exit:**
  - at the last traded close at or before the end of the hold;
  - a coin that stops trading exits at its last traded close.
- **The cover** (shorts only; none, 10%, 20% or 35%):
  - The short closes at the first traded hourly close in the hold that is at least the cover above its entry.
  - The exit is at that close, so a gap through the cover is paid in full.
  - The coin stays flat until the next rebalance.
  - This is qx `leg_stop` semantics (R274). It is executable by an API job that checks each hourly close.
- **Weights:** equal within a leg, 1 unit long and 1 unit short. A covered short's weight goes to cash.
- **Per period:** gross = mean long (return − funding paid) + mean short (−return + funding received). Funding sums
  the settlements in (entry close, exit close].

## Costs (API, per side)
- **Levels:** 8.5 / 17 / 25.5 bp at 1x / 2x / 3x.
- **What is charged:**
  - each period's turnover from the previous period's end weights (a covered short ends at 0);
  - every cover exit;
  - weight drift inside a period is ignored.

## The family (16 trials)
score {age, cluster} × hold {24 h, 168 h} × cover {none, 10%, 20%, 35%}.

## Windows (by decision; a period counts only when its hold ends inside the window)
- **Discovery:** 2021-01-01..2023-12-31.
- **Validation:** 2024-01-01..2026-09-30.

## Statistics
- **Per book and window, at 1x / 2x / 3x net and gross:**
  - mean per period, bp/day and %/yr, median and hit rate;
  - the mean without the 10 best periods and the best 10 periods' share of the sum;
  - annual Sharpe.
- **The t** is Newey-West on a calendar grid of periods (days for 24 h, weeks for 168 h), missing periods as gaps.
  The lag is 5 for 24 h and 2 for 168 h.

## Decision
- **The pick:** among the 16 books, the one with the highest discovery net 1x t, among those with a positive
  discovery mean.
- **The pick passes** only if, in validation, all three hold:
  1. net 1x t ≥ 2.0;
  2. the net 2x mean is positive;
  3. the net 1x mean without its 10 best periods is positive.

  Ten periods are 1% of a daily book's validation and 7% of a weekly one's. This is stricter for weekly books, by
  design: their squeezes would sit in fewer, larger periods.
- **Verdict:** PARTIAL (gate 0) if the pick passes, else NULL. The validation is read once. No second pick.
- **What a pass earns:**
  - **A forward paper lane** with its own id and PREREG, API mode, on MEXC prices where the coins list.
  - **A place in the next reserved batch after batch 1** (batch 1 is frozen), on 2020, through that batch's frozen
    PREREG.
    - lot_age can be computed for 2020.
    - lot_cluster needs 2020 caps, which that batch would have to show it holds.
- **A NULL** closes M276's cover form. The rank-weight form with a per-coin cap, named in M276, would need its own id.

## Reported (not decided on)
- **Covered minus uncovered:** for each score and hold, the paired difference of each cover's net 1x series from
  the uncovered book's, per window (12 series). This is M276's own question: does the cover keep the median and cut
  the tail?
- **Hansen SPA and White's reality check** over the 16 books, per window, with p-values against cash.
  - Each book's net 1x is summed onto the weekly rebalance grid.
  - Stationary bootstrap, 2,000 draws, mean block 4 weeks, seed 298.
- **Per book and window:**
  - the long and short legs' means (bp per period);
  - the price-only mean (no funding);
  - names per leg;
  - covers per period;
  - turnover per period.
- **Parity with R282:** the uncovered age 24 h book's price-only mean over all decisions, against R282's +4.35 bp/day
  gross.
  - R282's book came from qx `factors` on daily panel returns, so the two need not match to the basis point.
  - A gap above 2 bp/day is explained in FINDINGS before the verdict is discussed.

## Outputs
- `results/summary.json` (every number above, the inputs' hashes and `bars_digest`);
- `results/periods.csv` (every book's periods: gross, legs, names, covers);
- `run.log`, and FINDINGS.md with 1x/2x/3x costs read against `registry.program_trials()`.

## Power (written before the result)
This uses the normal approximation, with validation of 2.75 years and the 2.0 bar. The expected t is the annual net
Sharpe × √2.75.

| Annual net Sharpe of the pick | Expected validation t | P(t ≥ 2.0) |
|---|---|---|
| 0.3 (R282's age book) | 0.5 | 7% |
| 0.5 | 0.8 | 12% |
| 1.0 | 1.7 | 37% |
| 1.5 | 2.5 | 69% |
| 2.0 | 3.3 | 91% |

- Only a cover that turns the median into a steady book (Sharpe ≥ 1.5) is likely to pass.
- The bet is that a cover keeps much of R282's median day (+13.5 bp) as the mean while cutting the tail. This
  PREREG does not assume the book's volatility, so it does not claim what Sharpe that would give.
- A NULL rules out a large improvement, not a small one.

## Known limits (written before the result)
- **Seen data.** The rule's family was chosen after R282's tables. See the gate above.
- **Vintage.** size and vol_mcap use the latest-vintage Coin Metrics caps (R282 "Not modelled"). A later revision
  could leak into lot_cluster; lot_age has no such issue.
- **Shorting the squeeze names.**
  - Several of R282's squeezes came around delisting notices, when Binance limits new positions.
  - A paper short is held here; a real one might not have been opened.
  - The cover limits that loss, but cannot tell whether the entry was possible.
- **Cover fills.**
  - A cover pays 8.5 bp per side at 1x, at the triggering close. In a squeeze the real slippage is likely larger, so
    2x and 3x are reported.
  - An exchange stop order would also trigger on intrabar spikes that close below the level. This rule only reads
    closes, and is executed that way.
- **Exits.** A coin that stops trading exits at its last traded close. On Binance, a delisted perp settles near its
  last price.
- **Prices.** The books use Binance prices. Whether every short could be opened on MEXC is not checked.
- **Impact** above 7 bp per side (R262's square-root model) matters only above about $100k per book.

## Multiplicity
- 16 trials, one pick, one validation read. One registry row with 16 trials.
- SPA over the 16 is reported per window.
- The result is read against `registry.program_trials()` in FINDINGS.
