# PREREG: qbasis_v1 (R301). Does the dated-futures basis rank the perps that follow? (M170)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R301, in the Claude block R300-R319 claimed on issue #7 on 2026-10-22.
- **Method M170** (`registry/methods.csv`): a weekly sort of annualized basis on the coins with Binance COIN-M
  quarterlies, traded in the matching USD-M perps, held 7 days.
  - **Source:** Chi, Hao, Hu and Ran (J. Futures Markets 2023), as cited in M170's note: the basis is the strongest
    cross-sectional signal on dated crypto futures. The paper was not re-read for this PREREG.
  - **What this lane tests:** the paper's futures returns include each contract's convergence to spot. This lane
    trades the perps, so it asks only whether the basis predicts the price; the carry a quarterly earns by
    converging is not in these books.
- **Owner (single writer):** the Claude session that froze it.
- **Code:** `scripts/run_qbasis.py`, tested on synthetic panels in `tests/test_run_qbasis.py`:
  - the legs, sides and weekly anchors;
  - the minimum of 5 names;
  - random tie-breaks;
  - the 7-day change;
  - the window masks;
  - an end-to-end run where a planted basis effect is found and a null is not;
  - the plumbing counts.

  It calls `verify()` on this file first and checks every input's sha256 against the block below. The panel
  targets, the books and the decision rule are imported unchanged from `scripts/run_mlrank.py` (R299, frozen); the
  costs and statistics from `scripts/run_lotcap.py` (R298, frozen).
- **Execution mode: API at the decision costs.** The 7-day k = 1 books trade 2 coins a week. That fits manual web's
  ~15 orders a day, so the break-even cost per side is reported for that mode.
- **Gate: 0.**
  - The signal has never been read. No lane has used `qtr_basis_ann` or `data/coinm_1h` (searched across the repo
    before this freeze).
  - The coins' prices and funding have been read by many lanes (R190 carry, R275-R277 cross-venue funding, R276's
    Binance funding factor, R282's factors).
  - So it stays a screen. A pass earns a place in a reserved batch or forward days.

## What the author has seen
- **Funding as a cross-sectional signal:** R276's reference `bn_fund_3d` (rank IC −0.038 at 168 h). M263 is queued
  to test it as a book.
- **R190/R191 carry:** short perp, long spot when trailing funding is high. It earned about 35% in 2021, about 0 in
  2022-23, 8% in 2024 and about 1%/yr since.
- **R299 (`mlrank_v1`)** used the spot basis (perp over spot) among its 27 features. It is running at this freeze,
  and its results were not read.
- **A plumbing run on the real panel before this freeze** (`--plumbing`) printed counts only:
  - 14 coins ever have a quarterly basis: ADA, BCH, BNB, BTC, DOT, EOS, ETC, ETH, FIL, LINK, LTC, SOL, TRX, XRP.
    EOS, ETC, FIL and TRX appear only in early 2021.
  - **level:** 2,094 decision days (1,089 in discovery, 1,003 in validation), median 9 names, minimum 5.
  - **chg7:** 2,083 days (1,078 / 1,003).
- **A coverage count** (no values) showed:
  - 9-10 coins from 2021 to 2025-09-19;
  - then 5 (BTC, ETH, BNB, XRP, SOL) until 2026-09, after Binance stopped listing the other quarterlies.

  No basis value, return, funding or statistic was read.

## Inputs (frozen)

```inputs
b44a28f0f009b00ce481adf66e6bb0b3fb93981a523fc1eaf4c47fad13ef27f6  data/daily/panel.parquet
96053b6a8ba4e22469acfa4da4fb59f1d56e610e5b18460a50e40e82da8d4a6f  lab/inference.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
d3cb4b35879bb491245e94a64931cfda2f9e77a79c781fb45342618cad02a82d  scripts/run_lotcap.py
a96ba3034440e83fb90c3211cef6388229ef4b04af1c6bc93c772672412caca3  scripts/run_mlrank.py
4037fa725c3b53259f8479ddfde00695edb187791a010f2fd9c9f80d40d326a8  scripts/run_qbasis.py
```

## Data
- **Panel:** `data/daily/panel.parquet`. Row D is the decision at 00:00 UTC of day D. Columns used:
  - `close` (the USD-M perp's close at 00:00);
  - `fund` (funding settled in the 24 h ending at row D);
  - `qtr_basis_ann`: the nearest COIN-M quarterly with 7 or more days left over the COIN-M perp, minus 1, at the
    last hour with both. It is annualized by 365 / days left (`lab/daily.py` `_quarterly`, point in time).
- **Reserved rows:** the panel holds none before 2021-01-02 or after 2026-09-30.

## Signals (per coin and day D)
- **level:** `qtr_basis_ann` on row D.
- **chg7:** `qtr_basis_ann` on row D minus its value on row D−7. Across a quarterly roll, this compares two
  contracts' annualized basis.

## Books
- **Eligible:** coins with the signal and a close on row D. Fewer than 5 means no book that day.
- **Legs:** sort by the signal. Ties break by a seeded random order (seed 301), never by symbol.
  - **side high:** long the k highest, short the k lowest;
  - **side low:** the reverse;
  - k is 1 or 2.
- **Holds:**
  - 1 day, rebalanced every day;
  - 7 days, rebalanced every 7th day from the panel's first day (2021-01-02).
- **Entry and exit:** entry at row D's close. The exit is at the last close in rows D+1..D+h (none: return 0).
  Funding is the sum of rows D+1..D+h. These are R299's `targets`.
- **Weights:** equal within a leg, 1 unit long and 1 unit short.
- **Per period:** gross = mean long (return − funding) + mean short (−return + funding). This is R299's `book`.

## Costs (API, per side)
- **Levels:** 8.5 / 17 / 25.5 bp at 1x / 2x / 3x.
- **What is charged:** each rebalance's turnover from the previous period's weights (R298's `costed`).
- **Break-even:** the gross per period divided by the turnover per period is reported.

## The family (16 trials)
signal {level, chg7} × side {high, low} × hold {1 d, 7 d} × k {1, 2}.

Both sides are in the family. In commodity futures, high carry (backwardation) earns. Crypto contango may instead
mark crowded leveraged longs. This PREREG takes no side.

## Windows (by decision; a period counts only when its hold ends inside the window)
- **Discovery:** 2021-01-01..2023-12-31.
- **Validation:** 2024-01-01..2026-09-30.

## Statistics
- **Per book and window, gross and net at 1x / 2x / 3x:**
  - mean per period and bp/day, median, hit rate;
  - the mean without the 10 best periods and their share;
  - annual Sharpe.
- **The t** is Newey-West on a calendar grid of periods (days or weeks), with lag 5 for daily books and 2 for weekly
  ones. These are R298's `series_stats`.

## Decision
- **The pick:** the book with the highest discovery net 1x t, among those with a positive discovery mean (R299's
  `decide`).
- **The pick passes** only if, in validation, all three hold:
  1. net 1x t ≥ 2.0;
  2. the net 2x mean is positive;
  3. the net 1x mean without its 10 best periods is positive.
- **Verdict:** PARTIAL (gate 0) if the pick passes, else NULL. Validation is read once. No second pick.
- **What a pass earns:**
  - a forward paper lane with its own id and PREREG on MEXC prices (all ten coins list there);
  - a place in a reserved batch after batch 1. Binance's COIN-M quarterlies started in 2020, so the 2020 sample
    needs that batch to show it holds them.
- **A NULL** closes M170 as a perp signal. Trading the quarterlies themselves (with their convergence) would be a new
  lane, and needs COIN-M access the owner does not use.

## Reported (not decided on)
- **Hansen SPA and White's reality check** over the 16 books, per window, with p-values against cash.
  - Each book's net 1x is summed onto the weekly anchors.
  - Stationary bootstrap, 2,000 draws, mean block 4 weeks, seed 301.
- **Per book and window:** the long and short legs' means and the turnover.
- **Per book and calendar year:** gross and net 1x bp/day.
- **Leg membership** for the side-high k = 1 books: how often each coin is the highest or the lowest. Does the signal
  just pick BTC or one alt every day?
- **Basis against funding:**
  - the median daily cross-sectional rank correlation between the basis level and the perp's last 3 days of funding
    (is the quarterly basis just funding?);
  - the mean annualized basis by year.

## Outputs
- `results/summary.json` (every number above and the inputs' hashes);
- `results/periods.csv` (every book's periods: gross, legs, the coins in each leg);
- `run.log`, and FINDINGS.md with 1x/2x/3x costs read against `registry.program_trials()`.

## Power (written before the result)
This uses the normal approximation, with validation of 2.75 years and the 2.0 bar.

| Annual net Sharpe of the pick | Expected validation t | P(t ≥ 2.0) |
|---|---|---|
| 0.5 | 0.8 | 12% |
| 1.0 | 1.7 | 37% |
| 1.5 | 2.5 | 69% |
| 2.0 | 3.3 | 91% |

- A one-against-one book of large coins has a daily volatility of 2-4%.
- With 5-10 names, the legs are one or two coins, so idiosyncratic moves dominate.
- A NULL rules out a large, steady effect only.

## Known limits (written before the result)
- **A small, shrinking universe:** 9-10 coins until 2025-09, then 5. In 2025-09..2026-09 the k = 2 books trade 4 of
  the 5 coins.
- **Short-dated basis is noisy.** Annualizing a basis with 7-14 days left magnifies small gaps.
- **Rolls.** chg7 compares two contracts across a roll.
- **Prices.** Binance USD-M prices; MEXC is not checked here. All ten coins trade on MEXC.
- **Costs.** API 8.5 bp per side is conservative for BTC and ETH, and close for the alts.

## Multiplicity
- Program trials before this lane: 9,478,613 after R298, plus R299 (12) and R300 (24) when their rows are appended:
  9,478,649.
- 16 trials, one pick, one validation read. One registry row with 16 trials.
- The result is read against `registry.program_trials()` in FINDINGS.
