# FINDINGS: rrskew_v1 (R307). The Deribit 25-delta risk reversal does not time BTC or ETH by the week

**Verdict by the frozen rules: NULL** (gate 0, on seen data). The pick, `ETH 30d chg7 follow`, fails two of three
validation checks.
- **Trials:** 24. Program total after this round: 9,478,745 (`registry.program_trials()`).
- **Read:** frozen PREREG 17d8c862, frozen and pushed in 4ff616d before the run. Run 2026-10-22 16:50 UTC with
  `scripts/run_rrskew.py`. The PREREG verified, and all 12 inputs and the COIN-M tree (50 files) matched their frozen
  hashes. The Deribit flow files were checked one by one against their provenance record.
- **Source:** the owner's reel DeKFE8OEq-i (`docs/REELS_TRANSCRIPT.md`, reel 16) and an unreviewed SMU dissertation
  reporting that the 90-day 25-delta risk reversal predicts BTC returns.
- **The series:** a daily risk reversal per coin and tenor, built from every Deribit option trade. The forward comes
  from the Binance COIN-M basis. It covers 1,083-1,091 of 1,095 discovery days and 994-1,004 of 1,004 validation days.

## Result (bp per week, net; t is Newey-West, lag 4)

Weekly long or short of the USD-M perp from Monday 00:00 UTC. Manual-web cost is 3 bp per side at 1x; API is
8.5 bp.

| Book | Discovery 1x (t) | Validation 1x / 2x / 3x / API (t at 1x) | Validation 1x without the 10 best weeks | Weeks |
|---|---|---|---|---|
| `BTC 30d sign follow` | −25.3 (−0.41) | +2.3 / +1.1 / −0.2 / +0.0 (+0.04) | −93.3 | 143 |
| `BTC 30d sign fade` | +22.5 (+0.36) | −4.8 / −6.1 / −7.3 / −7.1 (−0.09) | −100.5 | 143 |
| `BTC 30d z follow` | +2.9 (+0.05) | +42.5 / +40.8 / +39.1 / +39.4 (+0.83) | −61.6 | 143 |
| `BTC 30d z fade` | −6.7 (−0.11) | −45.8 / −47.5 / −49.2 / −48.9 (−0.90) | −131.6 | 143 |
| `BTC 30d chg7 follow` | +35.8 (+0.55) | −2.7 / −6.2 / −9.7 / −9.1 (−0.05) | −91.2 | 143 |
| `BTC 30d chg7 fade` | −43.1 (−0.66) | −4.3 / −7.7 / −11.2 / −10.6 (−0.08) | −106.9 | 143 |
| `BTC 90d sign follow` | +46.9 (+0.68) | +53.3 / +52.8 / +52.2 / +52.3 (+0.96) | −40.7 | 143 |
| `BTC 90d sign fade` | −49.2 (−0.72) | −54.5 / −55.1 / −55.7 / −55.6 (−0.98) | −151.2 | 143 |
| `BTC 90d z follow` | +13.6 (+0.21) | +26.7 / +25.1 / +23.5 / +23.8 (+0.49) | −67.6 | 143 |
| `BTC 90d z fade` | −16.9 (−0.27) | −29.9 / −31.5 / −33.1 / −32.8 (−0.55) | −126.6 | 143 |
| `BTC 90d chg7 follow` | +23.6 (+0.37) | −18.3 / −21.9 / −25.4 / −24.8 (−0.37) | −109.2 | 143 |
| `BTC 90d chg7 fade` | −30.0 (−0.48) | +11.3 / +7.8 / +4.2 / +4.8 (+0.23) | −89.1 | 143 |
| `ETH 30d sign follow` | +42.0 (+0.50) | +23.7 / +22.3 / +21.0 / +21.2 (+0.33) | −118.7 | 143 |
| `ETH 30d sign fade` | −44.2 (−0.53) | −26.5 / −27.9 / −29.3 / −29.0 (−0.37) | −174.0 | 143 |
| `ETH 30d z follow` | +74.6 (+0.84) | +149.0 / +147.5 / +146.0 / +146.2 (+1.94) | −18.4 | 143 |
| `ETH 30d z fade` | −78.2 (−0.88) | −152.0 / −153.5 / −155.1 / −154.8 (−1.98) | −271.7 | 143 |
| **`ETH 30d chg7 follow`** (pick) | **+103.5 (+1.67)** | **+111.7 / +108.1 / +104.4 / +105.0 (+1.49)** | **−44.5** | 143 |
| `ETH 30d chg7 fade` | −110.7 (−1.78) | −118.9 / −122.5 / −126.1 / −125.5 (−1.60) | −251.7 | 143 |
| `ETH 90d sign follow` | +51.7 (+0.57) | +73.9 / +72.6 / +71.3 / +71.5 (+0.89) | −90.0 | 138 |
| `ETH 90d sign fade` | −54.2 (−0.60) | −76.5 / −77.8 / −79.1 / −78.9 (−0.93) | −214.6 | 138 |
| `ETH 90d z follow` | −24.8 (−0.31) | +194.1 / +192.6 / +191.0 / +191.3 (+2.67) | +18.4 | 138 |
| `ETH 90d z fade` | +21.5 (+0.27) | −197.1 / −198.7 / −200.2 / −199.9 (−2.71) | −319.0 | 138 |
| `ETH 90d chg7 follow` | −103.6 (−1.47) | +149.3 / +145.6 / +141.8 / +142.4 (+1.74) | −16.7 | 134 |
| `ETH 90d chg7 fade` | +97.1 (+1.38) | −156.9 / −160.6 / −164.4 / −163.8 (−1.83) | −284.1 | 134 |

**The pick's checks**

| Check | Value | Pass? |
|---|---|---|
| Validation net 1x t ≥ 2.0 | 1.49 | no |
| Net 2x mean > 0 | +108.1 bp/week | yes |
| Net 1x mean without the 10 best weeks > 0 | −44.5 | no |

**Buy-and-hold, net of funding (bp per week):** BTC +27.3 (t 0.38) in discovery and +54.3 (t 0.95) in validation;
ETH +88.1 (t 1.03) and +41.5 (t 0.47).

## What the result says
- **The risk reversal follows the market more than it leads it.** Its correlation with the week just ended is
  +0.20 to +0.48. With the week ahead it is +0.03 to +0.15.
- **BTC: nothing.** No BTC book reaches |t| 1 in either window. `BTC 90d sign follow` (the dissertation's series)
  earns +53 bp/week in validation, t 0.96. That is buy-and-hold's +54: the 90-day risk reversal was positive in 53% of
  validation weeks, during a rising market.
- **ETH: the closest call, and still not enough.**
  - The pick, `ETH 30d chg7 follow`, is long when calls got richer over the week. Per year it earned (bp/week) +205
    in 2021, +83, +42, +297, +61, and −77 in 2026.
  - It needs its best weeks: without the 10 best, validation is −44.5. Its t is 1.49.
- **`ETH 90d z follow` is the best validation book** (+194 bp/week, t 2.67, +18 without the 10 best weeks). But it
  lost in discovery (−24.8), so the frozen rule could not pick it. This is a post-hoc read and is not a lead. Only a
  sample nobody has read could test it: ETH options exist from 2019-03, so the 2020 reserve has one year of them.
- **Costs do not matter here.** At 2-3 orders a month, 1x to 3x moves a book by under 4 bp/week. Every verdict is
  about the signal.
- **Power:** at 143 weeks the lane detects an annual Sharpe of about 1.7 (PREREG). The dissertation's single-signal
  t of 1.91 is about Sharpe 0.9, which this lane cannot confirm or rule out.

## Read against the program
- **Against 9,478,745 trials:** no book passed. The best validation t, 2.67, is on a book that lost in discovery.
  The frozen pick rule exists to keep such a book out. At that trial count, a t near 2.7 on seen data is not
  evidence.
- **Against its priors:** this matches R209 (DVOL minus realized vol, NULL), R292, R295 and R296. The lab has now read
  the Deribit options tape four ways for direction, and none of them gives a tradable weekly or intraday edge on BTC
  or ETH.
- **For the reel:** the 25-delta put is usually rich for equity indices. For BTC and ETH the 30-day risk reversal was
  negative in 60-71% of weeks. The 90-day one was positive in 37-56% of weeks. The skew mirrors the recent trend; it
  does not forecast the next one.

## Files
- `results/summary.json`: every book and window at 1x/2x/3x and API, buy-and-hold, basis coverage, input hashes.
- `results/weeks.csv`: per Monday, the four risk-reversal series, the weekly returns and funding, and every book's
  net 1x week.
- `run.log`: the run.
