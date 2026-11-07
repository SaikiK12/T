# FINDINGS: usindex_calendar_v1 (R235). Turn-of-month and overnight drift on SPY and QQQ

**Verdict: NULL.** No strategy beat buy-and-hold of its ETF with t >= 2 in discovery (2000-2012). Validation and
holdout were not computed, so 2013-2026 stays unread by the lab.

- **Registry row:** R235 (trials 4). Program trials after it: 9,471,901.
- **Gate:** 0. Nothing here moves towards money.
- **Reproduce:**
  - prereg sha 99abfe9f, frozen in commit e807639 before the run;
  - `python scripts/run_usindex_calendar.py` (a few seconds);
  - data sha256 SPY 93da2bde, QQQ cdd726a6 (Yahoo daily, fetched 2026-10-20).
- **Origin:** queue M196 (turn-of-month) and M195 (overnight). It is the first lab test outside crypto, after the owner
  widened the objective.

## Numbers (discovery 2000-01..2012-12, 3,268 days)

Alpha is the intercept of the daily net return regressed on the ETF's own return (bp/day over all days, NW t lag 10).

| Strategy | Invested | Net bp/day 1x | Alpha 1x / 2x / 3x | Alpha t (1x) | Trimmed alpha | Sharpe (ETF) |
|---|---|---|---|---|---|---|
| TOM-SPY | 19% | +1.48 | +1.21 / +1.12 / +1.02 | 1.45 | +1.28 | 0.51 (0.22) |
| TOM-QQQ | 19% | +1.88 | +1.68 / +1.58 / +1.49 | 1.24 | +1.35 | 0.40 (0.10) |
| ON-SPY | 100% | +0.09 | -0.38 / -2.38 / -4.38 | -0.41 | -0.11 | 0.03 (0.22) |
| ON-QQQ | 100% | +2.00 | +1.76 / -0.24 / -2.24 | 1.36 | +2.01 | 0.39 (0.10) |

- Intraday (open to close) mean: SPY -0.53 and QQQ -2.93 bp/day.
- Turn-of-month alpha per year, SPY at 1x: positive in 8 of 13 years. Its largest years are 2000 (+5.9), 2010 (+4.8)
  and 2003 (+4.3). Its losses are in 2002 (-3.9) and 2008-09.

## Cost sensitivity
- **TOM** trades once a month, so costs barely matter: alpha falls from 1.21 to 1.02 bp/day between 1x and 3x on SPY.
- **ON** pays 2 bp a day at 1x. That is the whole of SPY's overnight edge. QQQ's +1.8 bp/day alpha at 1x becomes
  -0.2 at 2x.

## Reading
- **Turn-of-month is there, but small and noisy.**
  - It is about +1.2 to +1.7 bp/day of alpha over all days, or 6-9 bp per invested day: about 3-4%/yr on 19% of the
    days.
  - Its t of 1.2-1.5 over 13 years does not pass the frozen bar.
  - Its Sharpe (0.51 on SPY) is higher than buy-and-hold's (0.22) because it sits out most of the drawdowns. That is
    not the test.
- **Overnight drift on QQQ is real gross and gone net.** The intraday leg lost 2.9 bp/day in 2000-2012, as published.
  But a daily round trip at 1 bp each way eats it, and SPY's split is nearly flat.
- **No new lane.** Both effects are in the expected direction but below the bar on the window chosen in advance.
  Testing 2013-2026 now would be a second look at the same rule after a failure.

## Not checked
- TOM with the T-4 start (Etula et al.).
- Futures (ES/NQ) instead of ETFs, where overnight costs are lower per unit but roll handling is needed.
- A maker-only overnight version.
- Other indices (IWM, DIA) and other countries.
