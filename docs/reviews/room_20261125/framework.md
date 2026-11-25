# Framework above strategies: allocation, state variables, pipeline, gaps (room, 2026-11-25)

- **Author:** room member (Haiku 5.5), read-only pass. No experiment was run; no sealed journal or forward script was
  opened. Every number is from a cited review file or from arithmetic shown here.
- **Labels:** "(measured)" = a number a lab document reports; "(inference)" = my derivation; "(assumed)" = an input I
  chose and did not check.

## Short answer
1. **Allocate by sleeve, not by strategy.** Four sleeves exist. Only two earn an excess over euro cash after tax, and
   both are small: about 3% a year now on the design gap and about 6% on margin for the weekend book, before the
   forward discount. Blended, the framework earns about 2-3.6% a year over cash on €50k. A €10k a year income needs
   roughly €280k-550k deployed at those rates. The breakthrough is not reachable by allocation alone.
2. **Use state variables to size, not to switch.** The family's quartile returns are all positive, so a binary
   switch loses money. Only a continuous tilt is worth testing. A forward test of any tilt needs about 9 years at a
   0.3%/month effect, so the tilt must be justified by mechanism and history, and pre-registered once.
3. **Find rents with a scored pipeline, weighted by time to proof.** A rent loses about 16% of its value per 6 months
   of delay (0.7^0.5). The scoring rule is in section 3.
4. **Three gaps decide more money than any new rent:** the euro-dollar exposure (larger than the blended excess),
   whether margin is shared across Hyperliquid accounts, and an out-of-sample decay forecast that a one-year forward
   read cannot give.

## 0. What the lab already knows (the inputs)
- **Design gap, decay.** Regime-adjusted trend −0.184%/month per year on a mean of +0.62%/month: −30% of the level a
  year (measured; `docs/reviews/reflection_20261125_trend.md` §4). Non-Kraken pairs about −0.08%/month in 2026
  (measured; same section).
- **Design gap, regime.** Pays after rallies: past-120-day BTC return +0.777 (t +4.91). Quartiles of the past-120-day
  return, %/month: fallen most +0.24, Q2 +0.22, Q3 +0.63, risen most +1.02 (measured; same section).
- **Design gap, current level.** R508's Kraken+Hyperliquid book about 1%/month at 1x in autumn 2026, down from about
  3%/month in winter (measured; `reflection_20261125_decay.md` §0 and §4). Halved for Thorp: 6%/yr at 1x (decision,
  `december_decision_20261125.md` §1).
- **Dispersion.** R508 return vs same-month top-20 |gap|: correlation 0.91; vs previous month 0.27 (measured;
  `reflection_20261125_decay.md` §4 point 2). Kraken hours above Hyperliquid's floor: 20% to 35-44% (measured; same).
- **Weekend balanced book (R530, frozen).** About 29-37 trades a weekend, about 45 weekends a year, margin 3x,
  $1k a trade at the €10k stage, capacity about $5k a trade (measured; `reflection_20261125_power.md` §7-§10).
  Prior that it passes 0.35, power at half the effect 0.92, P(PASS) about 0.36 (measured; same, §8).
- **Weekend, euro figures.** The state note says $7k a year at half the edge and $23k at full, at $5k a trade
  (measured; `docs/STATUS.md`, "Seconde famille" bullet). See section 5 for the inconsistency.
- **Liquid design gaps (Bitfinex, Deribit).** Net about zero in 2026 (measured; `december_decision_20261125.md` §1).
- **Idle USDC.** About 2.65% gross under portfolio margin (measured; `reflection_20261125_decay.md` §0, citing L008).
- **Costs and tax.** Flat tax 31.4%. Euro cash after tax about 1.5% (decision, `answers_20261124.md` §2-§3). Venue
  failure about 2%/yr of the stake (measured from the closure studies; `docs/STATUS.md`). Kraken EEA maintenance 5%, so
  1.5x (measured; `answers_20261124.md` §1).
- **FX.** Euro-dollar volatility 7-10%/yr; the book's own volatility about 2% (measured; `answers_20261124.md` §3).
  US 13-week bill 4.13% against about 2% in euros (measured; same).
- **Census.** Every new floor venue copies the floor; no new floorless venue exists (measured;
  `reflection_20261125_census.md`).

## 1. Allocation across families

### 1.1 The sleeves and their excess over euro cash (per € deployed, after tax)
The test for every sleeve is the same: after-tax excess over euro cash, net of venue failure.

**Formula.** For a levered funding book at gross 1x return r and leverage L:

excess = (L·r − f)·(1 − t) − c, with f = 2% venue failure, t = 31.4% tax, c = 1.5% euro cash after tax.

For the weekend book, the gross return on the margin it locks, g, replaces L·r. Margin needed is notional/3.

| Sleeve | Input (gross) | Now | Year 1 (−30%) | Year 2 | Status |
|---|---|---|---|---|---|
| S1 Kraken + Hyperliquid design gap, 1.5x | r = 6% (autumn, Thorp-halved) | **+3.3%** | +1.45% | +0.15% | Funded only after a PASS (R510/R523/R527). Decaying. |
| S2 Weekend balanced book (R530), margin-funded | g = 14% on margin (lab's $7k on $50k margin at half the edge) | **+6.1%** | +3.2% | — | Unpassed; prior 0.35. Locks margin about 3 hours a week. |
| S3 Idle parking (USDC or euro) | 2.65% gross USDC = 1.82% after tax | ≈0 over cash, unhedged FX | — | — | The default home for idle capital. |
| S4 Liquid design gap (Bitfinex, Deribit) | 2026 net ≈ 0 | 0 | — | — | Not funded unless its trailing excess passes the floor (R-A1). |

(inference, arithmetic in section 1.3.) Year-1 and year-2 decay of S1 uses the measured −30%/yr. Decay of S2 is
**assumed** at the same −30%/yr: its time series does not exist yet.

### 1.2 Allocation rule (fixed before any read)
- **R-A1 Eligibility.** A sleeve is funded only if (i) a PREREG passed, or a live record of at least 6 months matches
  paper within the cost assumptions, and (ii) the trailing 90-day realized after-tax excess over euro cash is at least
  1%/yr.
- **R-A2 Caps.**
  - S1 ≤ 0.5 × the low end of measured thin-coin capacity: 0.5 × $40k = $20k ≈ €17k (EUR/USD 1.15 **assumed**, not
    checked).
  - S2 margin ≤ 0.5 × (30 trades × $5k ÷ 3) = $25k ≈ €22k.
- **R-A3 Venue cap.** At most 50% of capital on any one venue. Venue failure is linear in exposure (2%/yr), so this caps
  the tail, not the expected loss (inference).
- **R-A4 Order.** Fund eligible sleeves in descending trailing excess until each cap. The rest goes to parking, with
  USDC kept at margin needs and euro collateral where the venue accepts it.
- **R-A5 Exit.** A sleeve goes to zero after two consecutive months under the 1% floor, or at the existing kill rules
  (25% stake loss; R509's cumulative net below −3%).
- **R-A6 Cadence.** Re-measured monthly, not quarterly. At −30%/yr a quarter is a tenth of a rent's life.

Choices in the rule: six parameters (floor 1%, lookback 90 days, cap haircut 0.5, venue cap 50%, exit 2 months,
ordering). Freeze them now; do not grid-search them.

### 1.3 Arithmetic at the three stakes (€ per year after tax and cash, inference)

**€2k (stage 1).**
- S1 only, after a PASS: €2,000 × 3.3% = **€66 now**; €29 in year 1; €3 in year 2.
- Without a PASS, the €2k stays in cash (excess 0). This is the December decision, unchanged.

**€10k (stage 2).**
- Case (a), S2 not passed: S1 takes €10k, under its €17k cap. €330 now; €145 in year 1.
- Case (b), S2 passed, margin not shared: S1 €6k + S2 margin €4k.
  - S1: €6,000 × 3.3% = €198. S2: €4,000 × 6.1% = €244. Total **€442 now (4.4%)**.
  - Year 1: €87 + €129 = **€216 (2.2%)**.
- Case (b) assumes the Hyperliquid balance cannot be shared. If it can (gap G1), S2's margin can sit in the same balance
  as S1's, and case (b) holds more S1.

**€50k (stage 3).**
- S1 €17k (cap): €561 now; €247 in year 1.
- S2 margin €20k (under its €22k cap, about $2k a trade): €1,220 now; €644 in year 1.
- Parking €13k: 0.
- **Total €1,781 now (3.6%)**; **€891 in year 1 (1.8%)**.
- Prior-weighted (S2 at P(real) 0.35, from the power note): €561 + €427 = **€988 now (2.0%)**; €247 + €225 =
  **€472 in year 1 (0.9%)**.

**What €10k a year would need** (the owner's breakthrough, decision in `answers_20261124.md` §4):
- at the current blended 3.6%: €278k deployed;
- at the prior-weighted 2.0%: €500k;
- at year-1 decay, prior-weighted 0.9%: €1.1M.
- Thin-coin capacity (about $40-100k, S1 only) does not reach these sizes. So the breakthrough needs more rents, not
  more of these two.

### 1.4 Two reads that move the table
- **Euro-dollar exposure, larger than the excess (inference).** At €50k, one standard deviation of EUR/USD (7-10%) is
  €3.5k-5.0k a year. The blended excess is €1.0k-1.8k. Hedging the dollar collateral costs about the rate gap (4.13%
  against about 2%), about 2%/yr of collateral, which is €1k on €50k: most of the prior-weighted excess. The hedge
  decision comes before stake 2.
- **Weekend margin in a shared balance (inference).** If the xyz margin draws on the same balance as the validator
  perps, S2's margin does not need its own €20k. That helps the €50k case by about €64 a year at the excess over cash
  (€20k × 0.32%), but it decides whether the weekend book can run in the same account as the design gap without
  a margin call on S1 during the weekend.

## 2. State variables: which observables may move capital

### 2.1 Candidates, with the test each one has already had
| Observable | Measured link | Use |
|---|---|---|
| Past-120-day BTC return | t +4.9 on R525's 486 pair-months (measured) | Tilt S1/S4 size. Not a switch (section 2.3). |
| Trailing 14-day top-20 \|gap\| (live dispersion) | Same-month corr 0.91, lagged 0.27 (measured, 12 months only) | Monitor, not forecast. It is the return itself, measured the same month. |
| Kraken hours above Hyperliquid's floor | 20% to 35-44% in 2026 (measured) | Monitor the structural capacity (W) proxy. Rising = the gap closing from Kraken's side (cause 1 of `reflection_20261125_decay.md` §2). |
| BTC realized volatility (month) | +0.34 (t +0.87) (measured) | Drop: not significant. |
| Hyperliquid's own margin regime | Changes in 2026 (measured, `reflection_20261125_decay.md` §0) | Event flag, not a size variable. |
| The sleeve's own trailing 90-day excess | R-A1's measure | The allocation variable itself. |

### 2.2 How many choices, and the honest test
- **Choices in the search:** 4 observables × 3 lookbacks (60/120/180 days) × 3 thresholds × 2 sleeves = **72 specs**.
  Under a 5% family-wise bar (Bonferroni over 72), a single t needs about 3.5. The lab's t +4.9 would clear it only if
  its effective sample were the 486 pair-months. It is not (next point).
- **Effective sample (inference).** The 120-day return changes slowly. Over 68 months it carries about 17 independent
  4-month blocks. A block-bootstrap on 4-month blocks would shrink t from 4.9 toward about 2.5 (rough scaling,
  not computed).
- **The test I would run, once:**
  1. Pre-register one spec: BTC 120-day return, continuous tilt (section 2.3), lookback 120 days.
  2. Fit on 2021-2023, check on 2024-September 2026. Pass only if the sign holds in both halves and the block-bootstrap
     t exceeds 2 in each.
  3. Read the other 71 specs as description only.
- **Forward power (inference).** The sizing rule's value depends on a monthly effect of size δ with monthly SD about
  1.1% (measured from R508's monthly returns, my calculation). Months needed for t = 2:
  - δ = 0.3%/month: about 108 months (9 years);
  - δ = 0.1%/month: about 970 months.
  A forward switch or tilt cannot be decided within the owner's horizon. It must rest on mechanism and history.

### 2.3 Why a switch loses and a tilt may not
- **Binary timing loses (measured quartiles, inference on the mean).** The family is positive in every quartile of
  the past-120-day return. Hold-always mean: (0.24 + 0.22 + 0.63 + 1.02)/4 = **0.53%/month**. Hold in the top two
  quartiles and sit in cash (pre-tax cash 2.2%/yr = 0.18%/month): 0.5 × 0.83 + 0.5 × 0.18 = **0.505%/month**. The switch
  is worse by 0.025%/month.
- **Continuous tilt, the only form to test.** Size S1 at weight 1.0 above the median BTC return and 0.5 below. Its mean
  depends on the bottom-half weighting, which is untested. This is the spec in section 2.2.

## 3. The pipeline: from the mechanism map to a flow of decisive observations

### 3.1 The flow
- **Input.** `docs/reviews/mechanism_map.md`, each row with an owner-free question: where does a rule force someone to
  pay, behind a barrier we can cross?
- **Step 1, the decisive observation.** For each row, name the cheapest observation that would give a PASS or a KILL.
  Examples: a venue doc field (hours), a historical file (days), a forward lane (months). Forward lanes are the
  slowest. Prefer a historical or doc-level check first.
- **Step 2, the score.** Value of a candidate row, in € per year after tax and cash:

  **V = P(real) × E (€/yr after tax, at the owner's stage) × 0.7^T**

  where T = years until the decisive observation can say PASS or KILL. The 0.7 is the measured decay.
- **Step 3, the tiebreak.** Lower hours of lab work. Lab time is not the binding input; time to proof is.

### 3.2 Worked scores (inference; P and E are my estimates, not measured)
| Candidate | P(real) | E (€/yr after tax) | T (years) | V (€) |
|---|---|---|---|---|
| Read the HIP-3 margin rule (gap G1) | 0.8 | 64 | 0.1 | ~48 |
| R530 weekend book, decisive at the 20th weekend | 0.35 | 1,220 (at €20k margin) | 0.4 | ~370 |
| A new floorless venue (none in the census) | 0.05 | 1,000 | 1.0 | ~35 |
| Pre-IPO cross-venue spread (census, 0.85% mean) | 0.10 | 300 | 0.5 | ~25 |

The worked ranking puts the cheap margin read first, the frozen weekend lane second, and the speculative rents after.
The lab's weakest step is the search for new floorless venues, which the census says cannot grow.

### 3.3 Cadence
- **Daily (automatic).** The forward scorers and the kill checks already in place.
- **Weekly (after the Sunday weekend close).** A one-hour scan of venue rulebooks and announcements. Count, per map row:
  new floor copies; new listings with funding caps; pre-IPO conversions (about 10 a year on one venue, per the
  pre-IPO addendum); new margin or oracle rules.
- **Monthly (first trading day).** The decay meter for each sleeve (trailing 90-day excess, R-A1); allocation rule
  (section 1.2); state-variable readings (section 2.1).
- **Quarterly.** Map review: a row whose P(real) stays under 0.05 for two reviews is closed, and its observation is
  archived.
- **Rule of time.** A candidate must reach its decisive observation within 60 days, or be closed. A slower proof spends
  a rent's best year (16% per 6 months of delay).

## 4. What the current framework misses: three gaps, each with its cheapest measurement

### Gap G1. Margin sharing and the capital cost of the weekend book
- **Question.** Does the HIP-3 (xyz) margin draw on the same USDC balance as the validator perps that carry the design
  gap's Hyperliquid leg? (Open in `reflection_20261125_power.md` §10.)
- **Why it matters.** If not shared, S2 locks €20k for about 165 hours a week. If shared, its peak margin sits in the
  same balance as S1's Hyperliquid leg and the weekend margin call is not a separate risk.
- **Cheapest measurement.** Read Hyperliquid's documentation on HIP-3 margin (primary source, hours). Then one
  read-only query of an existing public account's margin state on a HIP-3 dex and on the validator perps, to see
  whether withdrawable balance is shared (minutes, no order, no deposit). Prediction written first: shared (60%).
- **Value.** About €64 a year at €50k (small), but it sets whether the weekend book is safe beside the design gap.

### Gap G2. The euro-dollar exposure of a euro investor
- **Question.** What is the euro return of the sleeves' dollar legs, and what does a hedge cost?
- **Why it matters.** At €50k the FX standard deviation (€3.5-5k a year) is two to three times the blended excess.
  The lab's books report in dollars; the owner's hurdle is euro (`answers_20261124.md` §3).
- **Cheapest measurement.** The daily euro-dollar series, aligned to the lab's daily nets for R508 and R525 (the data
  folder was not checked by me; the lab must confirm the series exists). Compute the euro-denominated daily P&L and its
  volatility and correlation with the dollar book. Add the hedge's cost from the rate gap.
- **Prediction written first.** The correlation with the dollar book is near zero (|ρ| < 0.2), so the risk is additive:
  about €3.5k-5k a year on €50k, and the hedge costs about 2%/yr of collateral.

### Gap G3. A decay forecast that cannot be read forward in time
- **Question.** Can the lab forecast the design gap's decay out of sample?
- **Why it matters.** The decay (−30%/yr) is measured on one 5.7-year panel with one bear market. A forward read of the
  level cannot test it in a useful time. Inference: with monthly SD 1.1%, the slope of −0.025%/month per month (from
  1.0 to 0.7 over a year) gives t ≈ 0.3 in 12 months. Detecting it at t = 2 needs about **46 months**.
- **Cheapest measurement.** A cross-sectional decay test on the 12 pairs of R525 (`experiments/gap_breadth_v1/results/pair_daily_net_1x.csv`,
  seen): regress each pair's monthly net on months since its first listing and on venue floor status. Newer pairs
  should start higher and fall faster if decay is structural. Add the monthly capacity proxy (Kraken hours above
  Hyperliquid's floor). Both are available now, with no forward wait.
- **Prediction written first.** Pairs with less than 12 months of history fall at a rate that is at least as steep as
  the panel's −30%/yr, and the capacity proxy rises monthly.

## 5. Reconciliation problems found in the lab's own numbers
- **Weekend euro figures are not proportional.** STATUS gives $7k a year at half the edge and $23k at full (ratio 3.3,
  where the edge doubles). The power note gives $2k a year at half the edge at $1k a trade; at $5k a trade, $7k is 3.5
  times that, not the 5 times the trade size implies. Use the lower figure until the arithmetic is redone from the
  frozen results. (Measured inconsistency; not resolved here.)
- **Sharpe 8.5 for the four books is in sample, at the winter peak.** The 274-day window (2025-12-31 to 2026-09-30) holds
  the Q1 dispersion of about 170%/yr, three times the Q4 level. The forward Sharpe will be lower (inference).
- **Correlation is not diversification against the common driver.** The four books' correlations of −0.26 to +0.15 all
  depend on cross-venue dispersion, which fell together. In a crisis they may rise (the framework note's own caveat).
- **The R525 trend t is overstated** (section 2.2): the 120-day regime variable is autocorrelated.

## 6. What could make this wrong
- All excess figures use the autumn level, a halved edge, and a 2%/yr failure cost. Each one is a choice. If failure is
  5%/yr, S1's excess at 1.5x falls to about 1.2% now.
- The 30%/yr decay is a linear trend fitted with one bear market and 12 pairs. The trend and the regime are partly
  collinear (2025 weak and late).
- The weekend book's P(real) = 0.35 is a prior from the lab's base rates, not a measured edge.
- Not checked: the euro-dollar data series, the Hyperliquid HIP-3 margin documentation, Deribit's and Bitfinex's
  maintenance schedules, and the EUR/USD rate used for capacity caps.
- No experiment was run and no forward file was opened, by rule.
