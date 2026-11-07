# PREREG: fundxs_v1 (R302). Do the perps that pay the least funding beat the ones that pay the most, net of it? (M263)

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R302, in the Claude block R300-R319 claimed on issue #7 on 2026-10-22.
- **Method M263** (`registry/methods.csv`): a cross-sectional Binance funding-level book, net of funding. Long the
  bottom fifth by recent funding, short the top fifth; each leg's return includes the funding it pays or receives.
  - **Source:** R276's reference factor `bn_fund_3d` (below), queued as M263 with the duty to reconcile it with R190's
    carry.
- **Owner (single writer):** the Claude session that froze it.
- **Code:** `scripts/run_fundxs.py`, tested on synthetic panels in `tests/test_run_fundxs.py`:
  - the funding windows inside each perp's history;
  - the quintile legs, their side, the universe and the weekly anchors;
  - the minimum of 30 names and random tie-breaks;
  - an end-to-end run where a planted effect is found and a null is not, with the price and funding parts adding up;
  - the plumbing counts.

  It calls `verify()` on this file first and checks every input's sha256 against the block below. The panel targets,
  the book and the decision rule are imported unchanged from `scripts/run_mlrank.py` (R299, frozen). The report,
  windows and yearly table are from `scripts/run_qbasis.py` (R301, frozen), and the costs and statistics from
  `scripts/run_lotcap.py` (R298, frozen).
- **Execution mode: API.** The top-150 books hold 16-30 names a leg and the top-50 books 6-10. That is more orders than
  manual web's ~15 a day, so API costs apply.
- **Gate: 0, on seen data.** R276 read this factor's book over 2021-2026 in aggregate (below), so neither window is
  unseen. This lane is a screen and a reconciliation. A pass earns a place in a reserved batch or forward days, not a
  confirmation.

## What the author has seen
- **R276 (`xvfac_v1`), the reference `bn_fund_3d`,** over 2021-01..2026-09 in one piece (not split by window), top 150
  by volume:
  - rank IC −0.038 at 168 h (t −6.14, reality-check p 0.0095) and −0.023 at 72 h;
  - 24 h quintile means, net of the funding a long pays, monotone: +13.0 / +11.8 / +3.7 / −0.4 / −3.1 bp/day from the
    lowest funding to the highest;
  - long the bottom quintile and short the top: +10.43 / +4.68 / −1.07 bp/day at 1x / 2x / 3x of 7 bp per side, with
    turnover 0.23 + 0.18 a day. Ties in R276 broke by symbol.
- **R190 / R191 carry** (short the perp, long spot, when trailing 72 h funding is above 20% APR): +35% in 2021, about 0
  in 2022-23, +8% in 2024, about 1%/yr since; R191's holdout passed at 1x only.
- **R301 (`qbasis_v1`), read today:**
  - the quarterly basis has a median daily rank correlation of +0.41 to +0.50 with 3-day funding, on 5-10 large coins;
  - its "level low" books (long the lowest basis, short the highest) grossed +7 to +16 bp/day in 2021-23 and −6 to +3
    in 2024-26.
- **Other funding lanes, all NULL:** R222 (premium net of funding, 7 d), R238 (funding slope), R297 (market-level
  funding as a gate).
- **R299 (`mlrank_v1`)** uses `fund3` and `fund30` (R299's definitions, close to this lane's) among its 27 features.
  It is running at this freeze, and its results were not read.
- **A plumbing run on the real panel before this freeze** (`--plumbing`) printed counts only:

  | Signal, universe | Decision days | Discovery | Validation | Names (min / median) |
  |---|---|---|---|---|
  | fund3, top 150 | 2,092 | 1,087 | 1,003 | 80 / 150 |
  | fund3, top 50 | 2,090 | 1,085 | 1,003 | 32 / 50 |
  | fund30, top 150 | 2,069 | 1,064 | 1,003 | 80 / 140 |
  | fund30, top 50 | 2,064 | 1,059 | 1,003 | 32 / 48 |

  No funding value, return or statistic was read.

## Inputs (frozen)

```inputs
b44a28f0f009b00ce481adf66e6bb0b3fb93981a523fc1eaf4c47fad13ef27f6  data/daily/panel.parquet
96053b6a8ba4e22469acfa4da4fb59f1d56e610e5b18460a50e40e82da8d4a6f  lab/inference.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba  scripts/run_clockflow.py
d3cb4b35879bb491245e94a64931cfda2f9e77a79c781fb45342618cad02a82d  scripts/run_lotcap.py
a96ba3034440e83fb90c3211cef6388229ef4b04af1c6bc93c772672412caca3  scripts/run_mlrank.py
4037fa725c3b53259f8479ddfde00695edb187791a010f2fd9c9f80d40d326a8  scripts/run_qbasis.py
22a1d4461ee18ab771120ff7b61435b1a21fe4efce75bd9a796528fed8fc922a  scripts/run_fundxs.py
```

## Data
- **Panel:** `data/daily/panel.parquet`. Row D is the decision at 00:00 UTC of day D. Columns used:
  - `close` (the USD-M perp's close at 00:00);
  - `fund` (the funding rates settled in the 24 h ending at row D, summed; positive means longs pay);
  - `rank_qvol30` (the perp's rank by trailing 30-day quote volume on row D, among Binance perps; 1 is the most
    traded).
- **Reserved rows:** the panel holds none before 2021-01-02 or after 2026-09-30.

## Signals (per perp and day D)
- **fund3:** `fund` summed over rows D−2..D.
- **fund30:** `fund` summed over rows D−29..D.
- A signal exists only when the perp has a close on row D and on the window's first row. A missing `fund` inside the
  window counts as 0.

## Books
- **Universe:** the perps with `rank_qvol30` ≤ 150 (or ≤ 50) and a close on row D.
- **Eligible:** universe perps with the signal. Fewer than 30 means no book that day.
- **Legs:** sort by the signal. Ties break by a seeded random order (seed 302), never by symbol.
  - **Long** the lowest fifth (floor(n / 5) perps), **short** the highest fifth.
  - **One side only:** R276's direction, which M263 names. The reverse side is not a trial.
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

## The family (8 trials)
signal {fund3, fund30} × hold {1 d, 7 d} × universe {top 150, top 50}.

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
  - a place in a reserved batch after batch 1 (Binance's 2020 funding covers about 80 perps);
  - a forward paper lane with its own id and PREREG, on MEXC prices.
- **A NULL** closes M263 in this form. R276's reference number is then explained by the parts below, not traded.

## Reported (not decided on)
- **Hansen SPA and White's reality check** over the 8 books, per window, with p-values against cash.
  - Each book's net 1x is summed onto weekly anchors (every 7th day from 2021-01-02).
  - Stationary bootstrap, 2,000 draws, mean block 4 weeks, seed 302.
- **Per book and window:** the long and short legs' means and the turnover.
- **Per book and calendar year:** gross and net 1x bp/day.
- **The reconciliation with R190: price and funding parts.** Per book, window and year, in bp/day:
  - the price part (the same legs with funding set to 0);
  - the funding part (the rest): what the short leg receives and what the long leg pays.
  - R190 earns only funding, hedged with spot, on high-funding coins. The short leg's funding is the comparable
    number; R190 is not re-run here.
- **R276 parity:** the daily fund3 top-150 book over every period at R276's 7 bp per side, against its +10.43 bp/day.
  The universe, ties and turnover rule differ slightly, so this is a check, not a test.
- **Ties at the base rate:** per signal, universe and window, the median share of the universe at the day's most
  common value, and the share of days where that tie is larger than a fifth (so a leg holds randomly chosen tied
  perps).
- **Leg volume ranks:** the mean `rank_qvol30` of the long and the short leg per book and window. Is it a size bet?

## Outputs
- `results/summary.json` (every number above and the inputs' hashes);
- `results/periods.csv` (every book's periods: gross, price-only gross, legs, names);
- `run.log`, and FINDINGS.md with 1x/2x/3x costs read against `registry.program_trials()`.

## Power (written before the result)
This uses the normal approximation, with validation of 2.75 years and the 2.0 bar.

| Annual net Sharpe of the pick | Expected validation t | P(t ≥ 2.0) |
|---|---|---|
| 0.5 | 0.8 | 12% |
| 1.0 | 1.7 | 37% |
| 1.5 | 2.5 | 69% |
| 2.0 | 3.3 | 91% |

- 30 names a leg diversify the idiosyncratic moves, but the legs differ in beta: high-funding perps are the market's
  leveraged longs. A market move is then a large part of each day's spread.

## Known limits (written before the result)
- **Seen data.** R276 read the daily fund3 top-150 book over both windows together. A pass here is weak evidence; the
  test is the reserved batch or forward days.
- **Ties at the base rate.** Many perps sit at the default 0.01% per 8 h. In calm periods a leg may hold tied perps
  picked at random.
- **Settlement intervals.** Perps that settle every 4 h or 1 h sum more settlements a day; `fund` is the daily sum
  either way.
- **Prices.** Binance USD-M prices and funding; MEXC is not checked here.
- **Short-side capacity.** The highest-funding perps are often small and crowded; shorting them at size is not
  checked.

## Multiplicity
- Program trials before this lane: 9,478,613 after R298, plus R299 (12), R300 (24) and R301 (16) when their rows are
  appended: 9,478,665.
- 8 trials, one pick, one validation read. One registry row with 8 trials.
- The result is read against `registry.program_trials()` in FINDINGS.
