# Room critic, 2026-11-25: where the lead researcher fooled themselves

Scope: the thirteen documents named in the brief (reflections gap, hmrw, convergence, closed, power, decay, trend,
census, shortleg; december_decision; self_review; the R530 PREREG) and LESSONS L036-L049. Descriptive scripts run:
`check_gap_decay.py`, `check_gap_trend.py`, `check_wknd_depth.py`, `check_kraken_shortleg.py`. Sealed forward scripts,
`check_wknd_power.py` and any journal were not run or opened on purpose. Scratch analyses (outside the repo) used
R462's `experiments/xyzwknd_v1/results/events.csv` and `cells.csv`, which are results, not journal.

## 0. Disclosure

- One repo-wide recursive `grep -rln "R465"` over `*.md`, `*.json`, `*.csv` read every matching file, which may include
  files under `experiments/*/journal/`. Its output was filtered to hide those paths and I quoted none. I did not open a
  journal file on purpose. Audit this if the rule requires it.
- The only repo file written is this report. Scratch scripts are in
  `/tmp/claude-0/-home-user-T/a4c99094-0eba-54d5-9f6a-3abc85cabed2/scratchpad/` (critic_trend.py, critic_shortleg.py,
  critic_rel2.py).
- `docs/reviews/december_decision_20261125.md` changed on disk while I worked (a margin-mode paragraph, commit 434a73eb).
  I read the current version. Its 4.4% line is unchanged, and finding F8 applies to it.
- Not verified here: venue fee and maintenance claims (Kraken 5% maintenance, Hyperliquid cross margin, census rows,
  Anthropic listing facts). I did not fetch any source.

## 1. Numbers recomputed

| Claim | Where | My result | Verdict |
|---|---|---|---|
| Regime-adjusted trend = -30% of mean level per year | reflection_20261125_trend.md:63 | `check_gap_trend.py`: -0.184 %/mo per yr, t -5.24, mean 0.621 %/mo, so -30% | Reproduces |
| Trend survives dropping 2021 | not stated in the file | Drop 2021: -32% (t -5.07). Drop 2022: -32% (t -3.76). Drop 2021-22: -38% (t -3.37) | Survives all windows |
| Trend not driven by Kraken pairs | trend.md:63-64 | Without Kraken: -0.173 (t -4.38) | Reproduces |
| 0.91 correlation, return vs same-month top-20 \|gap\| | decay.md:94 | 0.916 (Spearman 0.94). Without January: 0.865 | Reproduces |
| 0.27 correlation with previous month's dispersion | decay.md:94 | 0.45 (top-20), 0.40 (mean \|gap\|), n = 11 | Does NOT reproduce |
| Worst Kraken account loss 4.4% of notional | shortleg.md:54; december_decision.md:49 | Script's daily-reset metric gives 4.4%. Measured from each leg's entry: 8.7% (simultaneous closes). Median leg held 19 days | Number reproduces; metric understates (F8) |
| December stake ~EUR 65/yr | december_decision.md:12-20 | Same chain gives EUR 66. With the live cost basis: EUR 41-51 (F1) | Arithmetic reproduces; base overstated |
| Weekend capacity table | closed.md:132-137 | All 16 cells match `check_wknd_depth.py` (e.g. xyz SunE $10k 19.4; 30 of 76 markets at 0 at $1k) | Reproduces |
| R462 per-trade gross, A and B | FINDINGS.md | From events.csv: +42.4 (n 556), +36.2 (n 260) | Reproduces |
| Balanced book A +59.9 / SD 27.7; B +30.1 / SD 35.9; 11-06 +84.89 | PREREG.md:43; power.md:172 | Reproduce exactly from events.csv, with side set by the sign of rel W and funding included. Only after dropping 05-01 (F5) | Reproduces on 17 + 6 weekends |
| Weekend power: t at 30 weekends ~1.06 | closed.md:165 | 13 / (67/sqrt 30) = 1.06 | Reproduces |

Frozen inputs: all nine sha256 values in the PREREG `inputs` block match the files on disk (e.g.
`scripts/run_xyzbal_fwd.py` a134009d...). The freeze chain is intact on disk.

## 2. Findings, ranked by how much each would change a money decision

### F1 (high): the December stake's base is too high, on two counts

(a) **Cost basis.** R508's monthly returns are net at 7 bp per leg (`experiments/xfund_eea_v1/FINDINGS.md`, "1x (7 bp
a leg)" and the monthly table). The same FINDINGS file has a live snapshot (one time, fees excluded): Kraken at $1,000
costs 16.5 bp per side for coins under $10k/day and 12.8 bp for $10-100k/day, the buckets that earn most of the return.
R508's own cost sensitivity is 1.77%/yr per 7 bp per leg. So the extra 5.8-9.5 bp costs 1.5-2.4%/yr at 1x.

Recomputed with the same steps as `december_decision.md` section 1:

| Cost basis | Net at 1x | Halved | Leverage 1.5 | Venue -2% | After 31.4% tax | Over cash | EUR/yr on 2,000 |
|---|---|---|---|---|---|---|---|
| As written (7 bp) | 12.0% | 6.0 | 9.0 | 7.0 | 4.80 | 3.30 | 66 |
| 12.8 bp bucket | 10.5% | 5.3 | 7.9 | 5.9 | 4.05 | 2.55 | 51 |
| 16.5 bp bucket | 9.6% | 4.8 | 7.2 | 5.2 | 3.57 | 2.07 | 41 |

Assumption: linear cost slope from R508's sensitivity. Whether R508's 7 bp includes fees is not stated in the file.
If it does not, the gap is wider. If the 2% venue cost is applied to the levered base instead, the figure is EUR 52.

(b) **Level versus trend.** The 1%/month used is the autumn average of R508 (Aug-Oct: 1.56, 1.23, 0.86; mean 1.22).
The lab's own regime-adjusted fit for the non-Kraken family crosses zero around 2025.9 at zero regime values. With
September 2026 regime values (btc_past120 0.000, btc_ret +0.077, btc_vol 0.412) the fitted level is about +0.07%/mo,
against an actual -0.075. The Kraken pairs' +2.6%/mo (R525, 10 months) started in December 2025, the peak dispersion
window (top-20 208%/yr in January 2026). Neither fact is adjusted for in the stake arithmetic.

Fix: state stake 1's expectation as a range from about EUR 0 to 50, apply the cost correction before stake 1 is
proposed, and say which level (autumn, or trend-adjusted) is used.

### F2 (high): the closed-market base rate counts PARTIAL as PASS

- `registry/rounds.csv`: R462 PARTIAL (line 249), R465 PARTIAL (line 252; its sample C is NULL), R468 PARTIAL (line 255;
  B p 0.71), R464 NULL (line 251), R432 NULL (line 218). Zero PASS verdicts in the family.
- `experiments/xyzbal_fwd/PREREG.md:142` says "pass 3 of 5 decided". Those three are gate-0 readings, not registry passes.
- Prior sensitivity, same formula as the PREREG (P(PASS) = pi x 0.92 + (1-pi) x 0.06):

| prior pi | P(PASS) | PPV |
|---|---|---|
| 0.35 (PREREG) | 0.36 | 0.89 |
| 0.15 | 0.19 | 0.73 |

- The PPV of 0.89 is a PPV for "an effect exists". The money question is "the book beats $1k costs at size", which
  is a narrower claim. The PPV also uses alpha 0.06, while the decision claims 0.05 (PREREG, zero-effect power
  "6%").

### F3 (high): R530's in-sample edge is last-trade based, and the cost model does not correct the bounce

- PREREG Rule: returns are hourly candle closes (last trades). Costs are walked-book fills at $1k from snapshots within
  90 minutes. A fade's close-to-close return carries bid-ask bounce: the book sells after up-prints (the close is near
  the ask) and buys after down-prints. The bounce is a gain the fade book collects that a live fill does not.
- The PREREG names this as pre-mortem 1, and the reflection (power.md section 6c) cites Nagel: about 40% of a
  closing-price reversal is bounce, which takes R462 A from about 42 to about 25 bp.
- The decision does not use mid-based or bounce-adjusted returns. The 2x check doubles the walked cost, which is a
  different correction.
- Precedent in the lab's own data: L039 and cycle 3 found last-trade valuation of Kraken/Hyperliquid legs off by
  0.2-0.34% a trade against executable marks.
- Consequence: the "half the effect" scenario that sets the 92% power is close to the bounce-corrected edge, which is the
  outcome the lane is most likely to see. The decision should be written on that basis, with mid or bounce-adjusted
  returns.

### F4 (high): selection and trial count for the balanced book

- R462's grid has 32 cells (`results/cells.csv`): two decision cells, plus diagnostics including a `rel` group of
  eight cells. `rel` at theta 50, exit x1: A +55.8 (p < 0.001), B +36.9 (p 0.062).
- The R530 design is a new estimator: side-balanced, equal notional per side, both sides required. R462's `rel`
  cell was per-market, not side-balanced. The reflections cite "rel +55.8" as if it were the balanced book. It is a
  different number (the lane's A is +59.9).
- theta 50 itself is fair. It was R462's raw decision threshold (FINDINGS.md, "Decision cells"), not chosen from the
  `rel` grid. The side-balanced variant is what was chosen after `rel` looked strong.
- R462's Holm correction covers two decision cells, not 32. A Bonferroni over 32 cells takes the raw D2 p of 0.002 to
  about 0.06. The cells are correlated, so the true correction is smaller, but it is not zero.
- PREREG line 166 says "Trials: 1" and line 170 discloses the selection. The disclosure is good, but the count is not.
  Trials should include the grid, or the lane should be labelled a second read of R462's `rel` group.
- The half-effect value is unexplained. PREREG line 137 uses 18.2. That is the equal-weight average of the A and B
  net means (about 37), halved. Pooled by weekend the mean is 44, and half is 22. The choice changes the t at 20
  weekends from 2.5 to about 3.1. No shrinkage is applied, although the in-sample effect is the selected one and the
  true effect should be expected smaller. Report power at 1/3 and 1/2 of the in-sample effect, and say which is the
  reference.

### F5 (medium-high): the first weekend is cut, and it is the only losing A weekend

- R462's own A has 18 weekends. The lane uses 17 because 05-01 falls past Hyperliquid's 5,000-candle limit (power.md
  section 7). That is a data limit, not an outcome choice, so it is not p-hacking.
- But recomputed from events.csv, the 05-01 balanced gross is -21.1 bp, the only negative A weekend. With it, A is +55.4
  (SD 32.9, 18 weekends). Without it, +59.9 (SD 27.7, 17 weekends). "17 of 17 positive" depends on the exclusion.
- The PREREG should report the 18-weekend figure next to the 17-weekend one.

### F6 (medium-high): the lower-SD evidence is thin

- SD balanced versus raw: A 27.7 vs 49.7 (n 17); B 35.9 vs 106.1 (n 6).
- Approximate 95% intervals for the SD ratio (independent F test; it ignores the 0.68 correlation between the books):
  A 0.34-0.93; B 0.13-0.90. The B point ratio of 0.34 rests on six weekends.
- The mean edge is higher for the balanced book only in A (net +52.0 vs +43.7). In B the two are equal (+22.2 vs +21.9).
- The power note's "prediction held" is true at the point estimate only. It should say so.

### F7 (medium): beta and the common move: right sign, small in sample, no pre-registered check

- Rebuilt from events.csv (side-balanced, 23 weekends): the book's price PnL on the weekend's median E-to-X1 move has
  slope -0.13 (SE 0.10), correlation -0.27. The common move's SD is 67 bp, so it contributes about 9 bp of the book's
  SD of 32 bp.
- The sign matches pre-mortem 2: after an up-move the book is short high-beta names. The book is also tilted by the
  sign of the R-to-E move (correlation -0.23 with the price PnL, n 24), though that is weak.
- The PREREG reports the common move but has no rule on it. Pre-register the regression as a diagnostic with a
  threshold, or write a beta-neutral variant as a separate lane with its own id.

### F8 (medium, but it changes a stated number): cumulative Kraken account risk is 8.7%, not 4.4%

- `check_kraken_shortleg.py` resets each leg at its day's first open (`base = day.o.iloc[0]`) and sums only legs open at
  day start. A leg's risk is its loss since entry.
- Legs are held a median of 19 days, 90% at least 7 days, maximum 236 days (206 legs, my run of the same replay).
- Measured from each leg's entry, 1/20 slots, simultaneous hourly closes: worst account unrealized loss 8.7% of notional.
  The worst single-leg excursion from entry is BOME short, +139% over 52 days, which is about 6.9% of notional at 1/20.
  Intrabar extremes would add to 8.7%. Realized losses on closed legs are excluded.
- That is still far inside the 59% room at 1.5x and 5% maintenance, so the leverage rule survives. But
  `december_decision.md:49` and `reflection_20261125_shortleg.md:54` present 4.4% as the worst intraday loss. The stake
  check should use the cumulative figure (8.7%, with the intrabar and realized effects still to add).
- The liquidation formula (1/L - mm)/(1 + mm) is the short-side distance. The long-side distance at 1.5x and 5% is
  (1/L - mm)/(1 - mm) = 65%. The formula is conservative for this short-heavy book, but the file should say which side.

### F9 (medium): the decay story rests on a near-identity and a number I do not reproduce

- The sign-agnostic book harvests |gap| by construction. A same-month correlation between its return and same-month
  |gap| is close to an identity (0.916 reproduces). It shows the return is dispersion, not that dispersion drives or
  predicts it.
- The lag figure (0.27, decay.md:94) is not reproduced: 0.45 (top-20) and 0.40 (mean |gap|), with n = 11. With n = 11
  the 95% range for r = 0.45 is about -0.2 to 0.8. "Barely predicts" is not supported at this n. The file should show
  the lag calculation.

### F10 (medium): the trend is robust, but its regressors and pairs are weaker than stated

- The trend survives every window tested (section 1). The result stands.
- btc_ret and btc_vol are same-month. They explain a month's return and do not forecast it. Only btc_past120 is lagged,
  and its t of 4.9 comes from overlapping 120-day windows, so the effective N is below 68.
- "Every pair is negative": the eight non-Kraken pairs share two venue legs (Bitfinex in three pairs, Deribit in three).
  They are not eight independent confirmations.
- Clustering by month (68 clusters) is the conservative choice. Clustering by pair gives t -10.2, which would overstate.
- "The paying pairs are the new ones" rests on R525's ten Kraken months, which start in the peak-dispersion window
  (F1b).

### F11 (medium-low): the December mapping takes the first of several correlated reads

- R510 (two looks of 30 and 45 scored days on R509's journal), R523, R527, and R509's own full looks can each trigger
  "stake proposed". The reads share one book. Each threshold is modest (NW t 2.5-3.0), but a stake on the first to pass
  has a family error larger than any one read's alpha. The mapping should name the alpha across reads.
- I did not read any journal; this is about the mapping file.

### F12 (low): census arithmetic checks; sources are not in the repo

- Extended: 0.0035% per 8 h x 3 x 365 = 3.83%/yr, as stated. The other rows (Drift 10.95%, Variational 0%, Paradex's
  weighted median) cannot be checked from the repo. The census says "fetched 2026-11-25" and I found no cached copy.
  I did not fetch.
- "Every new venue copies the floor" covers eight venues. The LP-subsidy reason is labelled a hypothesis, which is right.

### F13 (low): pre-listing Fermi rests on one event

- The Anthropic gap of 1.4% is one event. "About 10 conversions a year" and "a third trade" are assumptions. The "watch,
  not lane" call is correct.

## 3. R530 PREREG: design flaws that would make the forward test misleading

1. **Selection (F4).** Balanced design chosen after `rel` looked strong; trials counted as 1; the half-effect value is
   unexplained; in-sample effect used without shrinkage.
2. **Beta (F7).** Dollar-neutral, not beta-neutral. Common-move exposure is reported but not decided on. Right sign, small
   in sample.
3. **Cost and valuation (F3).** Last-trade close returns against walked-book costs. Bid-ask bounce is kept as edge. The
   decision should use mid-based or bounce-adjusted returns, or pre-register an explicit bounce deduction.
4. **Decision rule.** The PPV of 0.89 overstates confidence (F2). Alpha is 0.06 at zero effect, against the 0.05 the
   rule claims. The power simulation does not include the 2x sign condition or the best-three trim, so the 92% and 63%
   figures are upper bounds on PASS probability. Quantify both.
5. **Sample.** The 05-01 exclusion removes the only losing A weekend (F5). Report both.
6. **Universe and unpriced markets.** Frozen 2026-11-11. Delisted markets are "unpriced", not zero. A delisting after a
   large move is then dropped, which can remove the most volatile names. Count the unpriced fills and report them.
7. **Entry at 19:00 New York.** The thinnest book of the week (19 bp at $10k). Fills use a snapshot up to 90 minutes away.
   Costs rest on two Sunday evenings (closed.md:193 says so). Stated as a limit; it should carry more weight.
8. **What is right.** The lane's code reproduces the seen numbers. The forward window is fresh and the exclusions are
   written down. The forecast is dated and includes a failure prediction. The failed crypto-proxy prediction is kept.

## 4. What survived the attack

- The trend's sign and size hold across every window (2021, 2022, both) and without Kraken.
- R462 per-trade figures, the balanced-book numbers (on 17 + 6 weekends), the 11-06 weekend, and the weekend capacity
  table all reproduce from the lab's own files.
- The 4.4% figure reproduces under its own method. The leverage rule survives on the cumulative figure (8.7%).
- The frozen inputs on disk match the PREREG hashes.
- The lab recorded its own failed prediction (crypto proxies). The registry keeps PARTIAL. Keep that discipline with
  the "pass" language in the reflections (F2).

## 5. Ranking (money impact)

1. F1: the December stake's base (cost basis and level versus trend). The EUR 65 headline is likely EUR 40-50 at best,
   and may be near zero on the trend.
2. F2: the closed-market base rate has zero registry PASS. The prior of 0.35 is not supported by the registry.
3. F3 and F4: R530's edge may be bounce, and its selection and trial count are understated. These decide whether a PASS
   means anything.
4. F8: the risk figure should read 8.7% cumulative. The rule holds.
5. F5 and F6: the 05-01 exclusion and the thin SD evidence.
6. F7: beta exposure, small in sample.
7. F9, F10, F11: story-level and mapping-level issues.
8. F12, F13: low.

## 6. Method notes and assumptions

- Cost slope: linear, from R508's own 1.77%/yr per 7 bp per leg.
- SD ratio intervals: independent F approximation (ignores the 0.68 correlation). Conservative only in one direction.
- Prior sensitivity: the PREREG's formula, with pi changed. P(PASS) and PPV are approximations, not simulations.
- Cumulative Kraken measure: 1/20 fixed slots; simultaneous hourly closes; realized losses of closed legs excluded;
  intrabar extremes not included (so the true figure is at least 8.7%).
