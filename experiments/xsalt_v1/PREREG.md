# PREREG: xsalt_v1 (R222), slow altcoin cross-sections: low beta, residual momentum, MAX, premium net of funding

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R222
- **Owner (single writer):** the session that froze it
- **Code:** `scripts/run_xsalt.py`, `lab/slices.py`, `lab/research.py`
- **Source:** the owner ("stop focusing on BTC, other coins could lead"); `docs/ALTCOIN_LEADS.md` items 2-5:
  - Frazzini & Pedersen 2014; Sila et al. 2025;
  - Blitz, Huij & Martens 2011; Fieberg et al. 2023;
  - Ozdamar, Akdeniz & Sensoy 2021 vs Bali, Cakici & Whitelaw 2011;
  - Chi, Hao, Hu & Ran 2023.
  Item 1 (seesaw) was R219.

## What the author had seen
- The atlas (R185) had funding, premium, OI, taker imbalance and volume as hourly-horizon cells. All were dead in
  2024-25 at those horizons.
- R219 (hourly lead-lag): NULL net.
- No beta, residual momentum, weekly MAX or funding-residual premium sort at weekly or monthly horizons has been
  computed in this lab. pack_v1 (R194) measured the long-alt book's beta (1.0); it did not sort coins by beta.

## Universe and timing
- **Universe:** coins eligible in the archive (top-50 by trailing liquidity), crypto contracts only (R216's TradFi
  list excluded).
- **Signals:** computed once a day, on the row whose bar closes at 00:00 UTC, from data up to that close only.
- **Trading:** a slice opens at that close and is held H hours.
- **Daily return:** the log change of the 00:00 UTC close from one day to the next.

## Variants (the trials)
Each is a quintile long-short on the day's eligible crypto coins with a score, needing at least 15 scores.

| Variant | Score | Long / short | Hold |
|---|---|---|---|
| BETA | OLS slope of the coin's daily return on BTC's over the last 90 days (at least 60 pairs) | long lowest quintile, short highest | 7 d |
| RESMOM | Explained below | long top, short bottom | 30 d |
| MOM (control for RESMOM) | Sum of the coin's daily log returns over days d-179..d-30 (at least 120) | long top, short bottom | 30 d |
| MAX_POS | Max hourly log return over the last 168 h (at least 120 finite), residualized cross-sectionally on ln(mean quote volume over 720 h) | long highest, short lowest | 7 d |
| MAX_NEG | Same score | long lowest, short highest | 7 d |
| PREM | 168 h mean premium index, residualized cross-sectionally on 168 h mean funding rate (OLS across that day's coins) | long highest, short lowest | 7 d |

**RESMOM in full.**
1. For each coin, regress its daily log return on the equal-weight mean of the other eligible crypto coins' daily log
   returns, over days d-179..d (at least 120 pairs).
2. Score = the sum of the residuals over d-179..d-30, divided by the residual standard deviation over d-179..d.
3. Deviation from the brief: 180 days instead of 365, because most alts are younger than a year in the archive.

## Book
- Slices open daily, each of size 1 / ((H / 24) x K), where K is the mean number of coins per quintile on discovery
  days. So each leg's gross is about 1.
- The universe hedge applies to the eligible crypto coins.
- Costs are tier costs, 1x/2x/3x.
- Returns include funding, as `research.load_universe`.

## Decision statistic
**Alpha t.** First fit the full-window OLS slope beta of the book's daily 1x net on BTC's daily return over the same
24-row days (sum of BTC's hourly `ret`). Then take the NW t of (net - beta x BTC) with lag 10 (lag 30 for RESMOM and
MOM).
- This is the intercept t with the beta's estimation error ignored.
- The mean must also be > 0.
- The book is long-short and universe-hedged, so beta should be small. A low-beta sort is the one that could earn by
  being short the market; the alpha t removes that.

## Stages (per variant)
1. **Discovery** 2021-01-01..2023-12-31 (each signal is NaN until its window fills): pass if mean > 0 and alpha
   t >= 2.
2. **Validation** 2024-01-01..2025-06-30, discovery passers only: pass if mean > 0 and alpha t >= 1.5.
3. **Holdout** 2025-07-01..2026-09-30, validation passers only, one shot (unread for this family): **CONFIRMED** if
   mean > 0 and alpha t >= 2.

RESMOM's value also needs RESMOM - MOM > 0 in the same window. This is reported; it is not a gate.

## Reported (not decided on)
- Gross, cost and net at 1x/2x/3x;
- book beta;
- long and short legs' gross;
- the mean daily quintile spread (top minus bottom, gross, next 24 h);
- BETA's persistence: the cross-sectional rank correlation of beta 90 days apart.

## Multiplicity
Trials = 6. Program trials before: 9,471,739 (after R221).

## Expectations
- **MAX:** NEGATIVE (low MAX wins) as in equities, or nothing. The two arms are mirror images before costs, so at
  most one can pass.
- **BETA:** gross positive (BAB), with weak beta persistence; likely NULL after the alpha correction.
- **RESMOM vs MOM:** crypto cross-sectional momentum is weak and reversal-prone among small coins. Expect NULL or a
  small edge, RESMOM above MOM.
- **PREM:** unknown sign. Expect NULL.
- Overall guess: all NULL at the discovery gate, one or two gross-positive.
