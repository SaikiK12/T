# FINDINGS: volrisk_v1 (R241). Short-volatility timing on SVXY, and VIX reversal on unseen years

**Verdict: NULL.** SVXY-CONTANGO passed discovery (t 2.39) and validation (t 1.82). It then fell short on the holdout:
+7.5 bp/day (+19%/yr), t 1.70 against the required 2. SVXY-CALM failed discovery (t 1.16). VIXREV-QQQ had 11 triggers
in 2013-2019 and no alpha (t -0.05).

- **Registry row:** R241 (trials 3). Program trials after it: 9,471,933.
- **Gate:** 0, with the holdout read once for the one validation passer. Nothing passed gate 1.
- **Reproduce:** prereg sha c4e7a1d3, frozen in commit 928e355 before the run. Run `python scripts/run_volrisk.py`
  (seconds). Data sha256 in `results/verdict.json`.
- **Origin:** queue M224, M214, M226 (M197 is the same idea).

## SVXY-CONTANGO (long SVXY when VIX < VIX3M at the prior close)

| Window | Net bp/day 1x / 2x / 3x | NW t (1x) | Per year | Vol | Max drawdown | Invested | Buy-and-hold SVXY: bp/day, max drawdown | Alpha vs buy-and-hold, bp/day (t) | Beta to SPY |
|---|---|---|---|---|---|---|---|---|---|
| Discovery 2011-10..2016 | +21.6 / +21.5 / +21.3 | **2.39** | +54% | 58% | 66% | 95% | +24.8, 91% | +1.4 (0.33) | 3.19 |
| Validation 2017-19 | +15.2 / +15.0 / +14.9 | **1.82** | +38% | 38% | 45% | 91% | +3.5, 162% | +14.1 (2.34) | 1.72 |
| Holdout 2020-26 | +7.5 / +7.4 / +7.3 | **1.70** | +19% | 33% | 50% | 93% | +6.8, 90% | +2.4 (0.84) | 0.93 |

- Drawdowns are on summed daily returns at unit size. 162% means buy-and-hold lost more than its stake on that scale.
- Per year (bp/day):
  - 2011 +14.2, 2012 +41.1, 2013 +25.0, 2014 +5.5, 2015 +9.3, 2016 +29.2;
  - 2017 +44.8, 2018 -13.6, 2019 +14.5;
  - 2020 +7.2, 2021 +18.5, 2022 -3.3, 2023 +24.4, 2024 -5.6, 2025 +6.8, 2026 +4.1.
- Worst single days: 2024-08-05 -21.5%, 2011-11-09 -20.1%, 2017-05-17 -19.1%. Worst 5 days: -38% (holdout).

**Validation was decided by one day, as the PREREG said it might be** (checked after the run):

| Close | ^VIX | ^VIX3M | Position at the next open |
|---|---|---|---|
| 2018-02-01 | 13.47 | 14.72 | long |
| 2018-02-02 | 17.31 | 17.03 | **flat** |

The rule was flat from the open of 2018-02-05. It lost -13.5% on 2-02 and -5.3% overnight into 2-05. It then missed
the -32% and -83% days that ended XIV and cut SVXY's exposure. The VIX crossed VIX3M by 0.28 points one session
before. A slower signal would have taken the whole loss, and the 1.82 validation t rests on that margin.

Similarly in 2020 the rule went flat at the open of 2020-02-25, after one -9.6% day.

## SVXY-CALM (the same, and VIX below its 1-year median)
Discovery: +7.8 / +7.5 / +7.2 bp/day, t 1.16, invested 59%, max drawdown 82%. Fails. The filter left the market in
calm stretches that still paid and stayed in through 2015's losses (2015 -17.6 bp/day).

## VIXREV-QQQ on 2013-2019
Eleven triggers in seven years (1.9% of days invested). Alpha -0.02 bp/day, t -0.05. Fails. The holdout was not
read. R239's 2001-2012 near miss came from the crisis years, and 2013-2019 had almost none.

## Cost sensitivity
SVXY-CONTANGO changes position about 12 times a year, so 3 bp one-way costs about 0.15 bp/day at 1x and 0.45 at 3x.
No verdict depends on cost. The holdout t is 1.70 / 1.68 / 1.64 at 1x / 2x / 3x.

## Reading
- **The strongest cross-market result so far, and still not a pass.**
  - Short volatility in contango earned in every window: +54%, +38% and +19% a year.
  - It missed the gate-1 bar on the unseen years (t 1.70).
- **The return is the volatility premium R239 measured, with crash risk attached.** Single-day losses of 20%, a
  5-day loss of 38%, and drawdowns of 45-66% are normal for this book.
  - Under GATES.md gate 3 this fails any prop-firm rule (5-10% maximum loss).
  - At own-capital stakes it would need a size near 0.2x to hold a 10% drawdown budget. That leaves about 4%/yr.
- **The timing adds something, but the evidence is thin.** The alpha against buy-and-hold was +14.1 bp/day (t 2.34)
  in validation and +2.4 (t 0.84) in the holdout. It comes from the tail days (checked after the run):
  - In validation, 2018-02-05/06/08 supply 38% of the alpha total, with 2018-02-06 alone at 26%.
  - In the holdout, March 2020 (9th, 12th, 16th) and April 2025 (4th, 10th) are the five largest days.

  The term-structure signal mostly saves the crash days.
- **Not forward-ready.** A 90-day daily paper lane at this volatility has a t-statistic around 0.4 at the observed
  mean. It could not confirm or reject anything on the gate dates.

## Not checked
- VIX futures directly (paid data), and short VXX instead of SVXY.
- Intraday timing of the switch (the open after the cross).
- Other term-structure measures (VIX/VIX9D, front-month futures basis).
- Volatility-targeted sizing.
- Crypto implied volatility (Deribit DVOL), which `data/deribit` holds in part.
