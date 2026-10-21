# FINDINGS: pitfac_v1 (R282). Age and volume/cap pass the frozen rule, but their books are noise around a strong median effect

**Verdict: PARTIAL (27 trials, gate 0).** By `scripts/qx_run.py`'s frozen rule, two factors pass: **age** and
**vol_mcap**.
- **The reality check:** 18 of 27 series beat it, with p_RC 0.0005 for most of them. The family's null 95th
  percentile of max |t| is 5.49.
- **The cost leg:** a factor also needs its daily book positive at 1x and 2x of the complete paid cost.
  - Age (long old coins, short young ones) nets **+3.9 / +3.5 / +3.1 bp/day** at 1x / 2x / 3x.
  - Vol_mcap (long low volume per unit of cap, short high) nets **+1.6 / +0.6 / −0.5 bp/day**.
- **Neither book is evidence of money.**
  - Age's book has NW t 0.68 gross and 0.64 net. Vol_mcap's has 0.39.
  - Both books lose their whole gain without their 10 best days.
  - The strong part of the result is the rank IC, a median effect, and a quintile book does not earn it.
- **Pre-committed consequences (PREREG):**
  - A pass earns a forward paper lane with a new id on a live twin of the daily panel.
  - Age and vol_mcap become eligible for the reserved 2020 batch. Size is the third factor 2020 can compute, but it
    failed the cost leg (−5.6 bp/day at 1x).
  - See "What happens next" for what the power numbers say about both.

**Reproduce**
- prereg sha f3f75640, frozen in commit e6f27f7 before any forward return was read.
- `nice python scripts/qx_run.py experiments/pitfac_v1 --register` takes about 4 minutes.
  - It rebuilt the daily panel and the factor table in a temp folder from the archive. The rebuild was byte-identical,
    and all 14 inputs match their frozen hashes.
  - It then ran qx `factors` and appended the R282 row.
- `results/SUMMARY.md`, `results/report.json` and `results/ic.csv` (per date and series) hold every number below.

## The decision (frozen rule: RC p < 0.05 on some horizon, and the 24 h book in the rank IC's direction positive at 1x and 2x)
| Factor | 24 h rank IC (t) | RC survivor horizons | Direction | Net bp/day 1x / 2x / 3x | Net %/yr 1x / 2x / 3x | Passes |
|---|---|---|---|---|---|---|
| age | +0.053 (+13.8) | 24, 72, 168 | long old | +3.9 / +3.5 / +3.1 | +14.3 / +12.8 / +11.3 | yes |
| vol_mcap | −0.068 (−15.7) | 24, 72, 168 | long low | +1.6 / +0.6 / −0.5 | +5.9 / +2.1 / −1.7 | yes |
| n_venues_7d | +0.034 (+9.6) | 24, 72, 168 | long many venues | −1.2 / −1.7 / −2.3 | −4.2 / −6.3 / −8.4 | no |
| size | +0.046 (+10.4) | 24, 72, 168 | long large | −5.6 / −6.4 / −7.3 | −20.4 / −23.4 / −26.5 | no |
| wick_30d | −0.036 (−13.2) | 24, 72, 168 | long few wicks | −8.1 / −9.4 / −10.7 | −29.4 / −34.2 / −38.9 | no |
| oi_mcap | −0.078 (−14.2) | 24, 72, 168 | long low OI/cap | −37.8 / −39.7 / −41.5 | −138 / −145 / −152 | no |
| fee_yield | −0.020 (−3.5) | none (p 0.48) | | | | no |
| fund_gap_all_7d | −0.005 (−1.9) | none (p 0.73 at best) | | | | no |
| kr_rel_7d | −0.005 (−1.6) | none (p 0.99) | | | | no |

- **Multiplicity:** the reality check covers this family's 27 series. The program now holds 9,478,385 trials.
  - A rank IC t of 10-16 would clear even a program-wide Bonferroni bar (about 6).
  - A book t of 0.4-0.7 clears nothing.
- **Universe:** the top 150 Binance perps by 30-day volume, on days the perp traded, 2021-01..2026-09.
  - Mean names per day: 142 for age, 118 for the Coin Metrics factors, 56 for oi_mcap and 35 for fee_yield.

## Reported, not decided on
**One cluster, not nine signals.** Mean daily rank correlation between the factors (no returns involved):
- size vs vol_mcap −0.79, size vs oi_mcap −0.82, vol_mcap vs oi_mcap +0.92;
- n_venues_7d vs size +0.66, age vs size +0.42, age vs oi_mcap −0.52.

So six of the nine factors describe one coin type: young, small, heavily traded against its cap, levered, quoted on
few venues, and wicking often. Kr_rel_7d, fee_yield and fund_gap_all_7d are nearly uncorrelated with that cluster, and
none of the three survives the reality check.

**The median falls, the mean does not.** Daily long-short in the decision direction, gross, 24 h (bp/day):

| Book | Mean | Median | NW t | Best 10 days' share of the sum | Mean without the best 10 days | Mean trimmed 1% per side |
|---|---|---|---|---|---|---|
| age, long old | +4.35 | +13.54 | +0.68 | 100% | −0.01 | +8.19 |
| vol_mcap, long low | +2.66 | +10.18 | +0.39 | 178% | −2.08 | +6.98 |
| size, long large | −4.74 | +8.94 | −0.74 | | −9.16 | −0.24 |
| wick_30d, long few | −6.75 | +3.21 | −1.24 | | −11.67 | −2.31 |
| oi_mcap, long low | −35.96 | −0.31 | −3.10 | | −43.57 | −24.65 |

- **On a typical day,** the cluster's "lottery" side (young, small, high turnover) does worse than the rest: the
  median day is +9 to +14 bp for age, vol_mcap and size.
- **A few days of squeezes** in that same side cancel the gain. In a quintile book, the squeezes sit in the short
  leg.
- **The rank IC has the same sign every year** for age (+0.027 to +0.090), vol_mcap (−0.046 to −0.107), oi_mcap
  (−0.061 to −0.097) and size (+0.010 to +0.097).
- **The book does not.** By year, gross bp/day:
  - age: 2021 −11.8, 2022 +10.8, 2023 +14.9, 2024 +15.4, 2025 −8.2, 2026 +4.9;
  - vol_mcap: 2021 −13.7, 2022 +0.8, 2023 −9.1, 2024 +18.9, 2025 +3.2, 2026 +20.0.

**Oi_mcap's book in the other direction is a post-hoc observation, not a result.**
- Long the high OI/cap quintile and short the low one: +36.0 bp/day gross, NW t 3.10, +124.5 %/yr net at 1x.
  - Its median day is +0.3 bp. The best 10 days are 47% of the sum.
  - 2025-26 carry it: +72.7 and +75.9 bp/day, against −44.8 in 2021 and −5.9 in 2024.
- **The best days are real squeezes, not data errors.** Top-quintile coins on the four best days:
  - 2025-04-30: ALPACA +520%;
  - 2022-06-07: UNFI +450%;
  - 2025-09-12: HIFI +440%;
  - 2026-09-13: LSK +139%.

  Several of these squeezes came around delisting notices, when Binance limits new positions. A paper book would
  have held them, but a real one might not have been able to open them.
- The frozen rule took the rank IC's direction, and this direction was chosen after seeing the table. It is
  recorded so that no later lane can claim it as new.

**The R276 relation.**
- Fund_gap_all_7d's rank IC is negative at every horizon (−0.005 to −0.013), the same sign as R276's Gate and
  Hyperliquid gaps.
- It fails the reality check here too (p 0.73-0.97). Averaging six venues did not strengthen the gap.

**What the panel's new sources added.**
- Nothing tradeable from the Korean premium (rank IC t −1.6 to −0.3) or from DefiLlama fee yield (p 0.48).
- The strongest rank ICs come from Coin Metrics' free-float cap (size, vol_mcap, oi_mcap) and from the panel's own
  history (age, wick days, venue breadth).

## What happens next
1. **Forward paper lane: earned, not built yet.**
   - Age's net book has an annual Sharpe of about 0.27 (NW t 0.64 over 5.7 years). At that size, an expected t of 2
     takes about 55 years of forward days.
   - A forward lane on these books cannot decide anything, so its id is not claimed. The live twin of the daily panel
     stays on the roadmap for factors with more power.
2. **Reserved 2020 batch: eligible, with low power.** At the archive's Sharpe, one year of 2020 gives an expected
   book t of about 0.3. The batch PREREG (due 2026-11-03) decides whether to spend batch Bonferroni on them.
   - Its rank IC would have power: about t 5.8 per year at the archive's rate.
   - But a rank IC is not a return, so it cannot be the batch's money test.
3. **The lead this leaves (new method M276, queued):** harvest the cluster's median while capping its squeezes.
   - For example, short the lottery quintile with a protective cover (qx stops), or weight by rank and cap any one
     coin's loss.
   - Any such rule was suggested by this lane's tables, so its archive test is gate 0 on seen data. Only a reserved
     sample or forward days can confirm it.
   - R280 already found carry short legs pumping 95% or more within a day on 155 days. A protective cover must be
     costed against gaps through the stop.

## Not modelled
- Market impact beyond 7 bp per side. R262's square-root model applies to books above about $100k.
- The latest-vintage Coin Metrics and DefiLlama values that size, vol_mcap, fee_yield and oi_mcap use. A later
  revision could leak; vol_mcap needs vintage-checked caps before any money.
- Whether the short legs could be opened on MEXC: these books use Binance prices.
- Position limits around delisting notices, which matter most for the squeeze days above.
