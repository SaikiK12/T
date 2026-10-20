# FINDINGS: tsmom_v1 (R237). Cross-asset time-series momentum

**Verdict: NULL.** Neither TS12 nor BLEND reached t 2 in discovery (2001-2012). Validation and holdout were not
computed, so 2013-2026 stays unread by the lab.

- **Registry row:** R237 (trials 2). Program trials after it: 9,471,905.
- **Gate:** 0.
- **Reproduce:**
  - prereg sha ac33a409, frozen in commit a4d43ca before the run;
  - `python scripts/run_tsmom.py` (a few seconds);
  - data sha256 of all 23 files in `results/verdict.json`.
- **Origin:** queue M194; `docs/FOREX_AND_INDICES.md` row 1.

## Numbers (discovery 2001-01..2012-12, 3,131 union days)

| Strategy | Net bp/day 1x / 2x / 3x | Per year (1x) | Volatility | NW t (1x) | Sharpe | Beta to SPY | Turnover / yr |
|---|---|---|---|---|---|---|---|
| TS12 | +0.53 / +0.50 / +0.47 | +1.3% | 4.9% | 1.00 | 0.28 | -0.05 | 3.9x |
| BLEND | +0.49 / +0.43 / +0.37 | +1.2% | 4.8% | 0.93 | 0.26 | -0.06 | 7.2x |

Gross by class, TS12 at 1x (bp/day of the portfolio):

| Class | Equity | Metals | FX | Bonds |
|---|---|---|---|---|
| Gross | +0.42 | +0.29 | -0.10 | -0.05 |

TS12 per year (bp/day):

| 2001 | 2002 | 2003 | 2004 | 2005 | 2006 | 2007 | 2008 | 2009 | 2010 | 2011 | 2012 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| +1.0 | +1.1 | +0.7 | +0.7 | -0.4 | +0.9 | +0.9 | **+3.3** | -1.3 | +1.0 | -1.4 | -0.1 |

## Cost sensitivity
Costs are tiny: 0.03-0.06 bp/day at 1x, because positions change monthly and most series cost 1 bp. No verdict
depends on cost. The rule fails on its gross.

## Reading
- **The sign is right, but the size is small.** A Sharpe of 0.28 over 12 years, with 2008 the one big year, is the
  weak trend era the literature describes. The 2001-2012 window was expected to be the favourable half.
- **The portfolio runs at about 5% volatility.** The rule targets 10% per series and divides by N. That does not change
  t or Sharpe, but it is why the per-year return is small.
- **FX and bonds contribute nothing.**
  - FX is spot only: carry, the main FX return, is not in this test.
  - The bond futures are Yahoo's unadjusted continuous series. Their quarterly roll gaps run against a long position,
    so the bond trend is understated. This was stated in the PREREG, before any statistic.
- **No variant follows.** A back-adjusted futures series or carry-inclusive FX returns would be a new lane. It would
  also be a second look at a failed rule on the same window, so its trials add to the count.

## Not checked
- Futures back-adjustment.
- FX carry.
- Energy and grains (excluded before the run).
- A 40%/N volatility scaling as in Moskowitz-Ooi-Pedersen, which does not change t.
- Longer data (pre-2000).
- 2013-2026.
