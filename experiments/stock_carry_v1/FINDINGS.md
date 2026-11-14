# R436 stock_carry_v1: NULL

Shorting the MEXC US-stock perps with the highest trailing funding, each hedged
with the cash stock, does not beat the T-bill. The hedge works: the two price
legs cancel to +$8. The trouble is the funding. It does not last after
selection: 55%/yr at entry, 15%/yr while held. Costs then take 45% of what is
left. Even before costs the book earns 4.10%/yr on capital, about the T-bill
(4.07%).

- Registry R436, method M493. 12 trials (L ∈ {7, 14} d × K ∈ {3, 5, 10} ×
  τ_in ∈ {10, 20}%/yr). Program total 9,784,969.
- Run once on 2026-11-10, 03:12:08-03:12:27 UTC (20 s, exit 0), by the frozen
  `scripts/run_stock_carry.py` (sha e0704cf5…).
- PREREG sha 99687671… was frozen and committed in 33cef0d before the run.
  Before the run, `prereg.verify` passed and all 10 frozen inputs matched.
  All 962 MEXC funding and kline files also matched `inputs/mexc_files.json`.
- The Yahoo inputs (`cash_daily.parquet`, `cash_events.parquet`) stay on disk
  but are gitignored. Their hashes are in the PREREG's inputs block.
- Outputs:
  - `results/cells.csv`: all 12 cells at 1x, 2x and 3x.
  - `results/positions_primary.csv`, `results/weekly_primary.csv`.
  - `results/summary.json`.
  - `run.log`.

FINDINGS was written by the orchestrator from the lane agent's text. The harness does not let subagents write it.

## Verdict

**NULL.** The primary cell is L = 14 days, K = 5, τ_in = 20%/yr, leverage 2,
$10k of capital. The window has 66 Wednesday rebalances, 2025-07-23 to
2026-10-21. The universe is 381 survivor-only contracts (324 stocks, 57 ETFs).

The T-bill is the mean ^IRX close with a 2-day lag, 4.07%/yr.

| Cost | Net on capital (%/yr) | Excess over T-bill (pts) | Net USD |
|---|---|---|---|
| 1x | +2.31 | -1.76 | +292.7 |
| 2x | +0.52 | -3.55 | +66.2 |
| 3x | -1.27 | -5.34 | -160.3 |
| 1x, MEXC API taker 8 bp | +1.76 | -2.31 | +223.0 |

Leverage views at 1x (not trials):
- leverage 1: +1.57%/yr (-2.51 pts);
- leverage 3: +2.68%/yr (-1.39 pts).

| Gate | Value | Pass |
|---|---|---|
| 1. Excess at 1x ≥ +2.0 pts | -1.76 | no |
| 2. Excess at 2x > 0 | -3.55 | no |
| 3. Bootstrap 2.5% point of the weekly mean > 0 | -0.043%/wk (95%: -0.043 to +0.144; mean +0.044) | no |
| 4. Sum without the 5 best weeks > 0 | -1.33% of capital | no |
| 5. No within-week perp high ≥ 45% above the mark | 47.7% (BNCSTOCK, held 09-09 to 09-30) | no |

The bootstrap uses 4-week circular blocks, 10,000 reps, seed 436.

34 weeks held a position, which is at least 26, so the result is not
INCONCLUSIVE. Other statistics:
- Newey-West t (lag 4): 0.94.
- Positive weeks: 21 of 66, or 21 of 37 counting from the first entry.
- Worst week -0.92% of capital, best week +2.19%.
- 43 positions in 37 names.

### Grid (excess over the T-bill, pts)

| L | K | τ_in | 1x | 2x | 3x | Held weeks | Positions |
|---|---|---|---|---|---|---|---|
| 7 | 3 | 10% | -1.71 | -4.36 | -7.02 | 36 | 44 |
| 7 | 3 | 20% | -2.10 | -4.71 | -7.32 | 33 | 43 |
| 7 | 5 | 10% | -1.23 | -4.43 | -7.63 | 36 | 75 |
| 7 | 5 | 20% | -1.20 | -4.18 | -7.17 | 33 | 70 |
| 7 | 10 | 10% | -2.57 | -6.34 | -10.11 | 36 | 131 |
| 7 | 10 | 20% | -1.53 | -4.96 | -8.38 | 33 | 119 |
| 14 | 3 | 10% | -2.70 | -4.72 | -6.73 | 36 | 34 |
| 14 | 3 | 20% | -1.88 | -3.65 | -5.42 | 34 | 30 |
| 14 | 5 | 10% | -1.93 | -4.15 | -6.36 | 36 | 53 |
| **14** | **5** | **20%** | **-1.76** | **-3.55** | **-5.34** | **34** | **43** |
| 14 | 10 | 10% | -2.03 | -4.61 | -7.19 | 36 | 90 |
| 14 | 10 | 20% | -1.22 | -3.21 | -5.19 | 34 | 70 |

All 12 cells are below the T-bill at every cost level; the best is -1.20 pts
at 1x. All 12 also fail gate 5:
- 9 cells hit a 99.0% within-week high (SNXX_USDT, 2026-07-29 to 08-05, in
  cell 7/3/10%).
- The three L = 14, τ_in = 20% cells hit BNCSTOCK at 47.7%.

## Why it fails

These diagnostics describe the primary positions. They were not decision cells.
They come from a post-run read of the frozen functions; the diagnostic scripts were kept outside the repo.

**Decomposition** (USD on $10k, 1x):

| Funding | Perp leg | Stock leg | Dividends net of 15% | Costs | Net |
|---|---|---|---|---|---|
| +500.1 | -1,435.6 | +1,443.8 | +10.9 | -226.5 | +292.7 |

- **The hedge holds.** The two price legs net +$8.1, and the median entry
  |perp/cash − 1| is 0.12%.
- **Funding mean-reverts after selection.**
  - The median entry score is 55%/yr. Realized funding over the 130 held
    slot-weeks is 15.0%/yr on held notional.
  - 16 of 43 positions paid funding while held.
  - The worst cases are flips: FCX entered at a 40%/yr score and paid $49.6 in
    one week; SBUX entered at 76%/yr and paid $39.7.
- **Costs take 45% of the funding** ($226 of $500).
- **Slots sit mostly empty.** 130 of 330 slot-weeks were filled (39%). Gross
  before costs is 4.10%/yr on capital.
- **Idle weeks do not explain the NULL.** Counting only from the first entry
  (2026-02-11, 37 weeks), net is 4.12%/yr against a T-bill of 4.07%: +0.05 pts,
  far from +2.0.
- **High funding is recent.**
  - No eligible name cleared 20%/yr before 2026-02-11.
  - The supply arrived only in the last two months: 32 eligible names cleared
    20%/yr on 2026-09-16 and 55 on 2026-10-14.

Eligibility funnel at L = 14. Names pass each filter in order, left to right.

| Date | Priced | ≥ 14 d funding | Ratio/split | Perp ≥ $100k/d | Cash ≥ $5M/d | Also ≥ 20%/yr |
|---|---|---|---|---|---|---|
| 2025-08-20 | 10 | 10 | 10 | 2 | 2 | 0 |
| 2025-11-12 | 23 | 23 | 23 | 16 | 16 | 0 |
| 2026-01-07 | 39 | 39 | 39 | 22 | 22 | 0 |
| 2026-03-04 | 55 | 50 | 50 | 40 | 40 | 4 |
| 2026-05-27 | 98 | 88 | 85 | 84 | 84 | 16 |
| 2026-07-22 | 226 | 203 | 201 | 201 | 200 | 2 |
| 2026-09-16 | 308 | 298 | 297 | 290 | 290 | 32 |
| 2026-10-14 | 358 | 339 | 337 | 315 | 314 | 55 |

**Capacity** does not bind at $10k. A slot is $1,333, at most 1.3% of the
$100k/day perp turnover floor.

## Read against the program

The primary alone decides this 12-trial family, and it is NULL. No other cell
comes close. Against a program total of 9,784,969 trials, nothing here needs a
correction or earns a forward lane. The stop rule ends the lane: one run, no new
cells.

## Limits

- **Survivor-only universe:** MEXC listings as of 2026-10-22. Stock perps
  delisted earlier are absent, and the direction of that bias is unknown.
- **Spreads are declared, not measured:** 5 bp per side on each leg. The
  EUR/USD conversion and US regulatory sell fees are left out. Both would only
  lower the net.
- **EEA retail access is not modelled.** US-domiciled ETFs generally lack a
  PRIIPs KID, so an EEA retail account may be unable to buy the ETF hedges.
  The primary held XBI and MVLL. Not checked for the owner's account.
- **Liquidation is not modelled.** The P&L assumes the leverage-2 short
  survives. BNCSTOCK's +47.7% week would have closed it, but it is booked as a
  +$29 gain. Gate 5 flags this.
- **The SNXX 99% high was not checked** against the cash high and may be a bad
  print. No gate result changes either way.
- **Idle weeks count as zero return**, as frozen. The from-first-entry view
  above shows this does not change the verdict.
- **Mark timing:** the perp mark is the close of the hourly bar ending at
  16:00 ET, while the stock trades at the official close.
- **Yahoo prices** are split-adjusted, not dividend-adjusted. No position spans
  a Yahoo split date.
- **Short sample:** one gate-0 read of the whole window, with 37 weeks from the
  first entry and no holdout.
