# FINDINGS: fxindex_v1 (R239). Forex and US-index battery

**Verdict: NULL.** None of the six tradeable rules reached t 2 in discovery (2001-2012). The VRP measurement passed
discovery and validation and then failed the holdout (t 1.11, because of 2020). Nothing passed gate 1.

- **Registry row:** R239 (trials 7). Program trials after it: 9,471,928.
- **Gate:** 0, with the holdout read once for validation passers. Only VRP reached it.
- **Reproduce:** prereg sha 6e42eb27, frozen in commit 7cd4e46 before the run. Run `python scripts/run_fxindex.py`
  (a few seconds). The sha256 of each data file is in `results/verdict.json`.
- **Origin:** queue M193 (spot part), M216, M218, M219, M215.

## Numbers (discovery; 1x / 2x / 3x)

The test column is the alpha against buy-and-hold for the ETF rules, and the raw net for the FX rules.

| Rule | Days from | Test bp/day 1x / 2x / 3x | NW t (1x) | Net bp/day (1x) | Ann. vol | Invested or turnover | Beta |
|---|---|---|---|---|---|---|---|
| FXMOM | 2006-09 | +2.18 / +2.11 / +2.04 | 1.20 | +2.18 | 15.6% | 18.6x/yr | -0.19 to SPY |
| DOLLAR | 2007-06 | -0.37 / -0.39 / -0.40 | -0.25 | -0.37 | 9.5% | 3.8x/yr | -0.09 to SPY |
| VIXREV-SPY | 2001 | +1.27 / +1.23 / +1.20 | 1.10 | +2.37 | 16.2% | 20.7% of days | 0.58 |
| VIXREV-QQQ | 2001 | +2.94 / +2.91 / +2.88 | **1.94** | +4.05 | 20.4% | 21.7% of days | 0.51 |
| HALLOWEEN-SPY | 2001 | +1.39 / +1.39 / +1.38 | 1.32 | +2.25 | 14.2% | 49.2% of days | 0.44 |
| PREHOL-SPY | 2001 | +0.16 / +0.09 / +0.02 | 0.44 | +0.21 | 3.2% | 3.5% of days | 0.02 |

VRP, the mean of `VIX^2 - next-21-day realised variance x 12` in annualised %² (NW t at lag 21):

| Window | Mean | NW t | Days positive | Median | Worst day |
|---|---|---|---|---|---|
| Discovery 2001-12 | +116 | 2.55 | 85% | +139 | -6,690 (2008) |
| Validation 2013-19 | +70 | 5.71 | 82% | +92 | -805 |
| Holdout 2020-26 | +82 | **1.11** | 85% | +148 | -7,503 (2020) |

Per year at 1x (bp/day; VRP in %²):

| Rule | 2001 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FXMOM | | | | | | +5.1 | -3.2 | +13.4 | +4.8 | -0.2 | -0.8 | -1.8 |
| DOLLAR | | | | | | | +4.2 | -0.5 | -1.9 | -2.5 | +0.3 | +0.2 |
| VIXREV-QQQ | +20.7 | +7.9 | -1.6 | -2.3 | -0.5 | -1.6 | -2.8 | +9.3 | +3.5 | -2.4 | +8.9 | -3.6 |
| HALLOWEEN | +4.3 | +1.9 | -0.1 | +1.2 | -0.8 | +1.0 | -0.9 | +3.4 | -1.6 | +2.7 | +3.2 | +2.5 |
| VRP | +228 | +84 | +256 | +119 | +59 | +72 | +64 | -397 | +414 | +222 | +119 | +158 |

VRP later: 2013 +82, 2014 +74, 2015 +48, 2016 +117, 2017 +76, 2018 -5, 2019 +100; 2020 -127, 2021 +227, 2022 +86,
2023 +130, 2024 +91, 2025 +19, 2026 +174.

## Cost sensitivity
Costs are tiny at these turnovers: at most 0.2 bp/day at 3x (FXMOM). Only PREHOL, which trades about nine times a
year, loses most of its alpha between 1x and 3x. No verdict depends on cost.

## Reading
- **VIXREV-QQQ is the near miss (t 1.94).** Buying QQQ the morning after a >1% drop, when VIX was above 25, earned in
  the crisis years (2001-02, 2008, 2011) and lost a little in quiet ones. That is Nagel's (2012) liquidity-provision
  story, with 237 triggers in 12 years. A near miss is not a pass, and a second look at 2001-2012 with another
  threshold or hold would be a new lane whose trials add to the count.
- **FX spot momentum and the dollar trend add nothing**, as R237's FX leg already suggested. FXMOM's best year, 2008 (+13.4),
  was the carry unwind: from September to December the book was short AUD and NZD and long JPY (positions checked
  after the run). That side pays carry, which these spot returns leave out, so the year is overstated (see the
  PREREG).
- **Halloween:** positive alpha in 8 of 12 years, t 1.32. Not enough.
- **Pre-holiday:** nothing.
- **VRP: the premium is real on average and its tails are what a seller is paid for.** Implied variance exceeded the
  next month's realised variance on 82-85% of days in every window. The losses come in a few weeks (late 2008, March
  2020), and those weeks set t. This was a measurement: the lab has no free option or VIX-futures history before
  SVXY (2011-10), so a short-volatility book cannot be tested on these windows. A short-volatility lane would need its
  own windows from 2011 and is queued as such, with the 2018 and 2020 blow-ups inside them.

## Data notes
- **The PREREG's FX start dates were wrong.** It said about 2004-04 (FXMOM) and 2004-12 (DOLLAR). Yahoo's AUDUSD
  starts 2006-05-15, so with all seven currencies required the books started 2006-09-01 and 2007-06-01. The rule text
  ("when all 7 currencies have their lookback") governed. The FX discovery window is therefore 6 years, not 8.
- **Bad ticks.** 11 G10 daily moves above 8% were found; none were filtered, as pre-registered.
  - Real: CHF 2011-09-07 (-8.8%, the SNB floor), CHF 2015-01-16 (+19.3%, the floor's removal), and probably AUD
    2008-10-13 (+9.4%).
  - Spike-and-reversal pairs, almost surely bad prints: EUR 2008-10-08/09 (+10.1/-9.1) and 2008-12-08/09
    (+17.3/-13.4), JPY 2008-12-08/09 (-15.0/+18.3), CHF 2009-02-06/09 (+8.2/-7.3). JPY 2008-10-09 (+10.6) is
    doubtful.
  - Held across both days, a pair adds its sum (at most 3.9%) to a summed return. All four together are worth at most
    0.28 bp/day to FXMOM and 0.09 to DOLLAR. Neither verdict changes.
- VRP's last 21 days of each window use realised variance from the next window. That changes nothing material.

## Not checked
- FX carry (no free foreign rate series reachable), EM currencies, and FX calendar effects in London time.
- Other VIX thresholds, drop sizes and holds for VIXREV.
- Day-of-week effects.
- A tradeable short-volatility rule (SVXY or VIX futures term structure, from 2011).
- 2013-2026 for every rule except VRP.
