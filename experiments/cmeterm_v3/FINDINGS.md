# FINDINGS: cmeterm_v3 (R505). Commodity carry on 13 CME roots, 2010-09..2026-10

**Verdict: CARRY_NULL.**
- The primary book nets **−0.76%/yr** (gross −0.31%/yr, Newey-West t −0.31) over 16.2 years.
- It is negative at 1x, 2x and 3x costs. Costs are small (0.44%/yr at 1x): the gross is what is missing.
- No forward paper lane and no capital study are earned.

- **Registry row:** R505 (trials: 0; R503 counted this rule's one trial). Program trials at the read: 9,785,747
  (R506's 432 included).
- **Reproduce:**
  - PREREG sha256 `9a1049a5…`;
  - code commit `307e9d1` (`scripts/run_cmeterm_v3.py`, R503's rule imported from `scripts/run_cmeterm.py`);
  - `data/databento/cmeterm_v3/manifest.csv` sha256 `cb4368c1…`;
  - `reduced.csv` sha256 `e9d35356…`, 221 root-years.
- Run on 2026-11-18 by `scripts/run_cmeterm_v3.py run`. The PREREG and its six input hashes were verified first.
- Results: `results/report.json`, `results/daily.csv` (one row per settlement day), `results/months.csv` (one row per
  decision).

## Data
| Item | Value |
|---|---|
| Settlement days in the calendar | 4,135 (4,074 with a book) |
| Settlements read | 162,379 |
| Settlement rows dropped as incomplete | 0 |
| Definition rows using the fallback unit (no or zero unit in the data) | 395 |
| Definition rows whose unit disagreed with the fallback table | 0 |
| Mapped contract-days without contract details | 1,761 (those roots are skipped on those days) |
| Databento spend for R505's settlements | $2.78 quoted over 221 pulls (manifest; cap $4.00) |

**Sanity check.**
- On 2020-04-20, the open-interest leader in CL was the June contract, settling at 20.43. That matches the published
  settlement.
- The May contract's −37.63 settlement that day was not the leader, so it never enters the book.

## Cost sensitivity (primary: inverse-volatility, k = a third of the valid roots, entry the next settlement day)
| Costs | Net %/yr | Gross %/yr | Cost %/yr | NW t | Sharpe | Max drawdown |
|---|---|---|---|---|---|---|
| 1x | **−0.76** | −0.31 | 0.44 | −0.31 | −0.07 | −60.3% |
| 2x | −1.20 | −0.31 | 0.89 | −0.49 | −0.12 | −66.6% |
| 3x | −1.65 | −0.31 | 1.33 | −0.68 | −0.16 | −72.8% |

Annualized volatility is 10.3%. Drawdowns are on the running sum of daily returns (R503's engine), not compounded.

## Sub-periods (1x)
| Window | Net %/yr | NW t | Max drawdown |
|---|---|---|---|
| 2010-09..2018-06 | 1.03 | 0.35 | −33.8% |
| 2018-07..2026-10 | −2.44 | −0.64 | −45.3% |
| 2024-01..2026-10 | 6.09 | 1.18 | −9.5% |

| Year | Net %/yr | NW t | | Year | Net %/yr | NW t |
|---|---|---|---|---|---|---|
| 2010 (from 09-01) | 21.23 | 2.17 | | 2019 | −4.08 | −0.38 |
| 2011 | 8.15 | 1.15 | | 2020 | −11.32 | −0.80 |
| 2012 | 4.23 | 0.59 | | 2021 | −4.10 | −0.38 |
| 2013 | −1.59 | −0.27 | | 2022 | 4.80 | 0.64 |
| 2014 | −20.92 | −2.28 | | 2023 | −4.06 | −0.42 |
| 2015 | 5.42 | 0.69 | | 2024 | −0.54 | −0.08 |
| 2016 | −7.00 | −0.62 | | 2025 | −3.11 | −0.46 |
| 2017 | 10.71 | 1.76 | | 2026 (to 10-30) | 25.29 | 2.35 |
| 2018 | −16.89 | −1.15 | | | | |

## Where the gross sits (full sample, %/yr of the book)
| Sector | Gross | Roots |
|---|---|---|
| Grains | **+1.70** | ZC +1.01, ZW +0.43, ZS +0.26 |
| Metals | +0.39 | HG +0.44, GC +0.20, SI +0.13, PL −0.39 |
| Energy | −0.51 | HO +0.68, CL +0.37, NG −0.75, RB −0.82 |
| Livestock | **−1.89** | LE −1.06, HE −0.83 |

**The bad years, split by sector.** Computed here from the frozen engine on sub-windows; not a pre-registered cell.
| Year | Energy | Grains | Livestock | Metals | Worst roots |
|---|---|---|---|---|---|
| 2014 | −10.8 | −2.8 | −6.9 | 0.0 | HE −4.9, RB −4.3, HO −3.1 |
| 2018 | −14.2 | +2.1 | −2.1 | −2.1 | NG −7.8, LE −3.7, HO −3.4 |
| 2020 | −22.2 | +12.4 | −2.9 | +2.0 | HO −9.2, RB −7.9, LE −6.7 |
| 2026 | +32.2 | −2.4 | −1.5 | −2.7 | best: HO +15.1, CL +10.4 |

- The book's big moves are energy. It was long backwardated energy into the 2014 and 2020 oil collapses, and the
  curve flipped against it. 2026's gain is the same exposure the other way.
- Livestock loses in most windows. Its curves are seasonal, so its carry ranks follow the calendar, not scarcity.

## Book diagnostics
| Item | Value |
|---|---|
| Decisions / with a book | 194 / 194 |
| Mean valid roots | 12.9 of 13 |
| Roots skipped for lack of a rank | 19 root-months (no other skip occurred) |
| Mean carry spread between the legs | 42.7%/yr |
| Holdings within 60 days of expiry | 315 of 1,552 (20%) |
| Minimum capital for whole contracts | median $1.06M; last month $1.70M |

- **How often each root is long or short.** Shares of the 194 months:
  - mostly short: ZW (short 71%), NG (59%), HE (54%), ZC (53%);
  - mostly long: RB (long 66%), CL (52%).
- The 42.7% spread is inflated by seasonal curves (NG, livestock, grains near harvest). It is the annualized log
  slope between the two most-held contracts, not an expected return.

## Variants (reported, never chosen)
| Variant | Net %/yr | NW t |
|---|---|---|
| Equal weights | −0.61 | −0.22 |
| k = 3 | −1.36 | −0.48 |
| Entry at the decision day's own settlement (no lag) | −1.38 | −0.56 |
| 12-month mean carry (de-seasoned) | **+1.13** | 0.43 |

The de-seasoned signal is the only positive variant, and it is far from significant. R506 counts it, and many others,
as trials.

## What this says, and what it does not
- **The published commodity carry premium is not visible here at a usable size.**
  - Koijen, Moskowitz, Pedersen and Vrugt (2018) and Gorton, Hayashi and Rouwenhorst (2013) report Sharpe ratios
    around 0.6 for broad commodity carry, mostly before 2012 and on 20-30 roots.
  - This book has 13 roots and 2010-2026. Its Sharpe is −0.07 with a standard error of about 0.24. A true Sharpe of
    0.4 or more is unlikely here (one-sided p ≈ 0.02); 0.5 gives p ≈ 0.008 and 0.6 gives p ≈ 0.002.
- **Costs are not the problem.** They are 0.44%/yr at 1x. The gross is about zero.
- **The minimum capital (about $1M) excludes the owner's stake anyway.** Micro contracts exist for CL, GC, SI and HG
  only, so a $10k version is a different, smaller book.
- **Not checked:**
  - measured CME spreads (one tick assumed);
  - first notice and delivery dates beyond the 40-day rule;
  - a larger universe (softs, other metals and energies) or 1990s-2000s data, where the published edge mostly lives.
- **Days, not years.** Sixteen years of settlements answered this for about $2.9 of data across R503-R505.

## Lineage and process
- R503 froze the rule; its fetch was cut before any statistic (`../cmeterm_v1/NOTES.md`).
- R504 replaced the plumbing; it stopped on 2010 definitions without units (`../cmeterm_v2/NOTES.md`).
- R505 added only guards. The rule, cells and verdict are R503's, imported from R503's frozen script.
- The container was replaced mid-fetch on 2026-11-17 and the background job hit its time limit twice. The fetch is
  resumable by design: every root-year was re-checked on restart, and none was read before the run.
- The registry row stays REGISTERED/PENDING: rewriting journal rows is not allowed. The verdict lives here and in
  `registry/methods.csv` (M549).
- R506 (`../cmeterm_grid_v1/`) reads the same data with 432 cost- and confidence-aware variants and a walk-forward
  selection. It was frozen before this run.

## Next
- No forward lane. The rule stops here.
- R506 decides whether any managed variant has an out-of-sample edge.
