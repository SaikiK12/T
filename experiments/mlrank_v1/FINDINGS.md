# FINDINGS: mlrank_v1 (R299). The GBM ranker passed its rule, then the audit found that three of its inputs know which coins will die

**Verdict by the frozen rule: PARTIAL (gate 0). Not trusted: its inputs leak survival.** Nothing from R299 is a
candidate. R304 (`mlrank_v2`) reruns the family without the leaking features.
- **Trials:** 12, gate 0 on seen data.
- **Read:** frozen PREREG 140faf4d, run 2026-10-22 08:00-09:25 UTC with `scripts/run_mlrank.py`. All 6 inputs
  matched their frozen hashes.
- **The pick passes all three checks.** The pick is gbm h7 pit: each week, long the top fifth of a gradient-boosted
  ranking of 27 point-in-time features, and short the bottom fifth.
  - Discovery net 1x +35.2 bp/day (t +6.31).
  - Validation net 1x +55.4 bp/day (t +4.02), +53.3 at 2x.
- **That is too good to be true:** a market-neutral book with a daily rank IC of 0.155 in discovery and 0.189 in
  validation. Single crypto factors in this lab reach 0.03-0.08.
- **The audit found why.** Three inputs, `n_venues`, `fund_gap7` and `kimchi7`, come from venue histories that were
  fetched only for markets live at download time. A coin that later dies has almost none of them.

## Result

**The pick: gbm h7 pit (bp/day; t is Newey-West)**

| Window | Weeks | Gross | Net 1x / 2x / 3x | t at 1x | Median week, 1x (bp) | Without best 10 (bp/week) | Sharpe (1x) | Long leg (bp/week) | Short leg (bp/week) | Rank IC (t) |
|---|---|---|---|---|---|---|---|---|---|---|
| Discovery 2022-23 | 104 | +37.8 | +35.2 / +32.5 / +29.9 | +6.31 | +272 | +174 | 4.27 | +120 | +145 | 0.155 (14.5) |
| Validation 2024-26 | 142 | +57.5 | +55.4 / +53.3 / +51.2 | +4.02 | +499 | +258 | 2.38 | +280 | +122 | 0.189 (16.9) |

- **The checks:**
  - t ≥ 2.0 at 1x: passes (+4.02);
  - a positive 2x mean: passes;
  - a positive mean without the 10 best weeks: passes.
- **SPA:** p 0.000 in both windows.

**All 12 books, validation (bp/day)**

| Book | Gross | Net 1x (t) | Rank IC |
|---|---|---|---|
| ridge h1 pit / all | +0.7 / +2.5 | −10.7 (−0.94) / −8.8 (−0.81) | 0.103 / 0.104 |
| ic h1 pit / all | −14.1 / −12.8 | −20.8 (−1.75) / −18.7 (−1.53) | 0.101 / 0.104 |
| gbm h1 pit / all | +62.9 / +66.3 | +49.7 (+5.20) / +52.9 (+5.89) | 0.122 / 0.122 |
| ridge h7 pit / all | −15.2 / −11.3 | −17.2 (−0.94) / −13.3 (−0.76) | 0.146 / 0.147 |
| ic h7 pit / all | −22.4 / −19.6 | −24.2 (−1.34) / −21.1 (−1.22) | 0.146 / 0.151 |
| gbm h7 pit (pick) / all | +57.5 / +60.6 | +55.4 (+4.02) / +58.5 (+3.92) | 0.189 / 0.188 |

- **Only the GBM earns.** The linear books have rank ICs of 0.10-0.15 and lose money. A high IC with a losing top and
  bottom fifth means their ranking is right in the middle of the universe and wrong at the extremes.

## The audit
**1. Timing: clean.** The audit checked the code paths:
- Row D holds only hourly bars that ended by 00:00 UTC of day D: `lab/daily.py` assigns a bar to the row of its end
  time.
- Funding settles onto the row at or after its time.
- Targets start at row D's close.
- The walk-forward trains only on decisions whose hold ends at least a day before the predicted month (as tested).

**2. Survivorship: three leaking inputs.**

| Source | Contracts fetched |
|---|---|
| Binance klines, funding and metrics | every archive perp, delisted included |
| Gate (S3 archive), dYdX | delisted included |
| KuCoin, Kraken | live at download only |
| MEXC | perps listed at download only (from 2025-04) |
| Hyperliquid | listed perps only |
| Upbit, Bithumb | KRW markets live at download only |

Coverage in the top 150 (rows with a close), for the 159 perps whose last close is more than 30 days before the
panel's end, against the survivors:

| Year | KuCoin funding: survivors / later delisted | Upbit price | Mean `n_venues` |
|---|---|---|---|
| 2021 | 53% / 2% | 42% / 5% | 1.29 / 0.49 |
| 2022 | 73% / 5% | 40% / 4% | 1.93 / 0.88 |
| 2023 | 89% / 5% | 40% / 3% | 2.60 / 1.06 |
| 2024 | 95% / 3% | 39% / 3% | 3.73 / 1.51 |
| 2025 | 93% / 0% | 42% / 0% | 4.52 / 1.88 |

- **How the inputs leak:**
  - `n_venues` counts the venues with a price on the row, so a low count marks a future delisting.
  - `fund_gap7` is a mean over six venues' funding gaps, four of them survivor-only.
  - `kimchi7` exists only for coins on Upbit or Bithumb today.
  - A missing value ranks as 0, the middle, and a tree can split on that.
- **Why it pays:** a coin usually falls before Binance delists it. A model that can tell which coins will die
  can short them.
- **Milder gaps, not leaks:**
  - OI and positioning cover 45-54% of survivors' rows and 25-35% of later-delisted coins'. The metrics files were
    fetched for every archive perp, delisted included, and are missing at similar rates (50% against 45%). That gap
    is in Binance's archive.
  - Binance spot coverage falls when a spot pair is delisted. That is public when it happens.
  - The market-cap estimate (R299's vintage set) covers 52-85% of later-delisted coins against 81-91% of survivors.

**3. What is not shown yet:** how much of the +55 bp/day the leak earned. R304 measures it. It runs the same family
on the 24 clean features, plus the GBM on the three leaking features alone, and reports each leg's share of
later-delisted coins.

## What this does and does not show
- **It shows:** a frozen, well-tested pipeline can still pass on a leak that sits in the data, not the code. The
  panel's `pit` label was about timing, not coverage. The same three columns feed R282's `n_venues_7d` and `kr_rel_7d`
  (neither passed there) and every cross-venue lane that ranks coins by venue presence.
- **It does not show** that the clean features are worthless, or that the GBM is. That is R304's question.

## Costs
- **Levels:** API, 8.5 / 17 / 25.5 bp per side on each rebalance's turnover.
- **At 1x/2x/3x** the pick nets +55.4 / +53.3 / +51.2 bp/day in validation. Cost does not decide it, the leak does.

## Read against the program
- **Program trials:** 9,478,613 in `registry.program_trials()`. With R299's 12, R300's 24, R301's 16 and R302's 8 it
  is 9,478,673.
- **The SPA p of 0.000 is not evidence of an edge.** Inputs that know the future pass any multiplicity bar.

## Next
- **R304 `mlrank_v2`:** the same 6 clean books and a leak-only diagnostic. PREREG frozen before its run.
- **Data:**
  - The panel's venue columns are survivor-biased for the venues above.
  - `docs/FEATURE_VINTAGE_INTEGRITY.md` records them.
  - Any lane that ranks coins by venue presence or by a survivor-only venue's values must exclude them or use only
    Gate and dYdX.
- **Fix at the source:**
  - Done: `lab/coverage.py` labels those columns (`survivor_columns`) and measures any column's coverage by survival.
    `lab/daily.py` is a frozen input of four lanes, so the label lives outside it.
  - Queued: refetch KuCoin, Kraken, MEXC, Hyperliquid, Upbit and Bithumb with delisted markets where their APIs allow
    it.
