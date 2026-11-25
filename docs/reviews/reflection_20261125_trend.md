# Reflection, 2026-11-25 (cycle 8 of rule 11): is the design-gap family decaying, or does it follow the market?

## How I approached the last subject, and what I would change
- **Cycle 7 found that R508 earns realized cross-venue dispersion** (corr 0.91), which fell about threefold in 2026.
  It took the structural hint from **one** matched pair of sell-off months.
- **What I would change:** one matched pair is an anecdote. The lab holds a 5.7-year panel of the same family (R525,
  12 pairs from 2021). The question "trend or regime?" belongs on the longest series available, with the regime
  measured, not matched by eye.
- **Also:** cycle 7 concluded "the sleeve pays most in sell-offs". R525's by-year table already says otherwise in one
  place: 2022, the deepest bear market, earned only +4.1%. I wrote a conclusion that the lab's own record half
  contradicts. Step 0 would have caught it.

## 0. What the lab already knows
- **R525** (seen, in sample): the equal-weight portfolio by year at 1x was 2021 +13.7, 2022 +4.1, 2023 +9.4,
  2024 +8.6, 2025 +2.2, 2026 to September +9.5 (%/yr). The Kraken pairs join in December 2025 and lift 2026.
- **Per-pair daily nets** are in `experiments/gap_breadth_v1/results/pair_daily_net_1x.csv`, 2021-01-22 ..
  2026-09-30.
- **He et al.:** |ρ| falls about 22 points a year on Binance, and rises with past 120-day returns (extrapolative
  leverage demand).
- **Cycle 7:** for R508, the top-20 dispersion fell about threefold in 2026.

## 1. The economic question
Does the family's return have a downward trend once the market's state is accounted for, or is it a cyclical payer
whose level is set by the market?

## 2. The mechanism, and what each answer predicts
- **Dispersion between venues' funding comes from leverage demand that differs across venues**, absorbed by
  arbitrageurs with limited capital (W/m).
  - **Structural decay:** W grows (more cross-venue capital, better margin tools), so for the same market state the
    dispersion shrinks year by year. The regime-adjusted trend is negative.
  - **Cyclical:** leverage demand spikes in some states (strong rallies in thin alts, crashes that crowd one side) and
    dispersion follows. The regime coefficients carry the variation, and the trend is near zero.
- **Which state matters is itself a question.**
  - He et al. find ρ rises with past returns (extrapolative longs).
  - Cycle 7 suggested sell-offs; 2022 says perhaps not.
  - Measure, do not assume: past 120-day BTC return, the month's BTC return and the month's realized volatility.

## 3. The cheapest decisive observation, with the prediction written first
- **Data:** R525's per-pair daily nets (seen) and BTC's daily closes from the lab's Binance hourly file.
- **The panel:** monthly return per pair, with pair fixed effects. Regressors:
  - a linear time trend (years);
  - BTC's past 120-day return;
  - the month's BTC return;
  - the month's realized volatility.
  - Standard errors clustered by month, and a check on the equal-weight portfolio alone.
- **Prediction:** the regime-adjusted trend is negative, at least −20% of the family's mean level a year. The
  dominant regime variable is the past 120-day return (He et al.), with a positive sign.
- **What would refute it:**
  - A trend indistinguishable from zero (|t| < 1.5) means cyclical. The money plan should then expect the family's
    average over a cycle, not the autumn 2026 level.
  - If the sign of the past-return effect is negative, the family pays in downturns.

## 4. The observation (`scripts/check_gap_trend.py`; R525's seen nets, 2021-01 .. 2026-09)
**Panel:** 486 pair-months, 12 pairs, 68 months. Mean +0.62%/month (+7.5%/yr). Pair fixed effects, standard errors
clustered by month.

| Model | Trend (%/month per year) | BTC past 120 days | BTC this month | BTC volatility |
|---|---|---|---|---|
| trend only | −0.225 (t −5.81) | | | |
| trend + regime | **−0.184 (t −5.24)** | **+0.777 (t +4.91)** | +0.754 (t +1.75) | +0.343 (t +0.87) |
| trend + regime, no Kraken pairs | −0.173 (t −4.38) | +0.748 (t +4.77) | +0.982 (t +2.64) | +0.552 (t +1.29) |

- **The regime-adjusted trend is −30% of the family's mean level a year.** Every pair with at least 40 months has a
  negative trend, regime-adjusted t from −1.65 to −4.62:
  - Bitfinex pairs −0.16 to −0.30;
  - Deribit pairs −0.08 to −0.18.
- **The non-Kraken equal-weight portfolio, %/month by year:** 2021 +1.16, 2022 +0.34, 2023 +0.79, 2024 +0.71,
  2025 +0.14, 2026 (to September) −0.08.
  - Outside Kraken the family earns nothing in 2026.
  - R525's +9.5% for 2026 came from the Kraken pairs (about +2.6%/month each, ten months).
- **The family pays after rallies, not in sell-offs.**
  - By quartile of BTC's past-120-day return: fallen most +0.24%/month, Q2 +0.22, Q3 +0.63, risen most +1.02.
  - By quartile of the month's volatility: calmest +0.23 up to most volatile +0.89.
  - This is He et al.'s extrapolative leverage demand: after rises, longs crowd the floor venues and pay.
- **The prediction held** on both counts: a negative trend of at least 20% a year (it is 30%), and a positive
  past-return effect.
- **It also corrects cycle 7.** "The sleeve pays most in sell-offs" was read from R508's one winter. Over 5.7 years
  and 12 pairs, the family pays after rallies and in volatile months. R508's winter is better explained by the new
  Kraken pairs' first months than by the sell-off.

## 5. What it changes
- **The money case narrows to Kraken's thin coins, and even that is a decaying rent.**
  - The liquid pairs (Bitfinex, Deribit) were the "breadth" of the family. In sample they have reached about zero.
  - At −30% of the mean level a year, a rent that starts at Kraken's +2.6%/month in its first months is worth a
    year or two, not a permanent allocation. The plan's "quarterly reassessment" was right in spirit and too slow in
    tempo: reassess monthly, against the regime-adjusted trend.
- **Dated forecasts for the forward reads,** written 2026-11-25 before any of them and without reading an interim,
  so the self-review can score them. The `fund_book` reads score funding net of costs, without the price legs, so
  they pass more easily than full-net reads.

  | Read | Lane | What it scores | P(PASS) |
  |---|---|---|---|
  | R510 (about 12-20) | Kraken + HL | fund_book, fast | 0.60 |
  | R509 | Kraken + HL | full net | 0.45 |
  | R512 | Kraken + HL + Aster | full net | 0.40 |
  | R523 (about 12-13) | Kraken+HL with Deribit+HL | fund_book, combined | 0.45 |
  | R527 (about 12-15/12-25) | three floorless venues | fund_book, combined | 0.40 |
  | R521 (about 12-22) | Deribit + HL | fund_book, fast | 0.30 |
  | R520 | Deribit + HL | full net | 0.10 |
  | R524 | Bitfinex + Binance | full net | 0.10 |

- **The strategic consequence: the product is the pipeline of new rents, not one rent.**
  - Every pair decays. The paying pairs are the new ones: Kraken's, in their first year of the lab's data.
  - The family's value lies in finding the next floorless venue, or the next set of thin listings, early. That is
    what the mechanism map is for, and it puts a premium on speed over depth of proof.
  - A rent found a year late has already lost about a third of its level.
- **Hamming's important problems, revised:**
  1. find new design gaps early (new venues, new listings, new margin regimes);
  2. measure each rent's decay from the first month;
  3. prove fast (the balanced R530 design, executable-price checks), because a slow proof spends the rent's best
     year.

## 6. What could make this wrong
- **In-sample nets on R525's engine,** with its costs and last-trade valuation (cycle 3 found last-trade price legs
  can overstate losses).
- **A linear trend over 5.7 years** with one bear market (2022). The trend and the regime are partly collinear: 2025
  was weak and also late.
- **Kraken pairs have only 10 months,** and Kraken serves one year of funding. Their earlier history is unknown, so
  "new pairs pay" partly means "pairs the lab could only see recently".
