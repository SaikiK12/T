# FINDINGS: fundgate_v1 (R297). Funding on up days was low in 2026, as the guest said, but it does not time the market

**Verdict: NULL.** M295 is TESTED.
- **Trials:** 4, gate 0.
- **Read:** frozen PREREG d388bcbf (committed and pushed in b25702b before the run), run 2026-10-22 06:34 UTC,
  `scripts/run_fundgate.py`. All 4 inputs matched their frozen hashes.
- **Program trials** after this round: 9,478,597 (`registry.program_trials()`).
- **No pass, in either direction.** The largest validation |t| is 0.88.

## What was tested
**The claim.** A Bankless guest (2026-04-14) read 2026 as a bear structure because "funding rates on positive days
so far this year have been lower than funding rates on positive days in 2022". If longs do not pay up when the
market rises, nobody is chasing it. The crowding reading is the opposite: a strong funding response warns of crowded
longs.

**The test.** Data are the 50 most traded Binance perps, decided each day at 00:00 UTC from the daily point-in-time
panel. Two measures, each over the last 30 days and z-scored against the year before:
- **slope:** how far the day's funding (10% trimmed mean) rises per unit of the day's return (OLS);
- **up-day funding:** the mean funding on up days, the guest's own words.

Each is read against the equal-weight top-50 basket's next 7 and 30 days, for 4 trials. BTC is a split.

Discovery is 2021-04..2023-12, and validation 2024-01..2026-09.

## Result

| Trial | Discovery t | Validation t | Non-overlapping t (disc / valid) | BTC t (disc / valid) | Given momentum (disc / valid) | Validation by year 2024 / 2025 / 2026 |
|---|---|---|---|---|---|---|
| slope h7 | +0.65 | +0.88 | +0.84 / +0.88 | +0.11 / +0.28 | +1.00 / +0.90 | +0.94 / +2.15 / −0.42 |
| slope h30 | +1.67 | −0.60 | +0.37 / −0.83 | +0.75 / −1.13 | +2.21 / −0.50 | −0.62 / +2.17 / −0.67 |
| up-day funding h7 | +0.33 | +0.05 | +0.19 / −0.02 | +0.58 / +0.29 | −0.15 / +0.14 | −0.44 / −1.54 / +0.46 |
| up-day funding h30 | +0.21 | −0.58 | −0.52 / −0.33 | +1.17 / +0.17 | −0.21 / −0.22 | −1.20 / −1.50 / +0.11 |

- **The bar** is a validation |t| ≥ 2.50 (Bonferroni over 4, two-sided) with the same sign in discovery.
- **The t** is Newey-West with lag 2h. Rows: 824-881 in discovery and 974-997 in validation.
- **The correlations** with the next 7 or 30 days are between −0.06 and +0.13 in every trial and window.
- **Neither measure leads the market:** not the basket, not BTC, not at 7 or 30 days. That holds with or without the
  last 30 days' return taken out.
  - Two single years reach about +2.2 (slope, 2025). In 2024 and 2026, the same trials are between −0.7 and +0.9.
- **Slope h30 is the only trial with a discovery t above 1.5** (+1.67, and +2.21 given momentum). It turns negative in
  validation (−0.60).

### What the guest saw is real, but it is the funding level

| Year | Funding, all days (bp/day) | On up days | On down days | Up days | Slope of funding on return |
|---|---|---|---|---|---|
| 2021 | +11.5 | +13.5 | +9.3 | 54% | 0.0062 |
| 2022 | −0.3 | +0.0 | −0.6 | 46% | 0.0014 |
| 2023 | +2.1 | +2.3 | +2.0 | 52% | 0.0010 |
| 2024 | +4.3 | +4.8 | +3.8 | 46% | 0.0009 |
| 2025 | +0.1 | +0.5 | −0.2 | 45% | 0.0008 |
| 2026 (to Sep) | −0.9 | −0.5 | −1.2 | 46% | 0.0016 |

These are 10% trimmed means over the top 50. Binance's base rate is about +3 bp/day.

- **Up-day funding in 2026 was below 2022's** (−0.47 against +0.01 bp/day). The guest's premise holds in this data.
- **It is the funding level.** The up-day z-score is 0.99 correlated with the plain 30-day funding level's, and 0.44
  with the basket's last 30 days.
- **The response itself** (the slope) was higher in 2026 than in 2022 (0.0016 against 0.0014). The slope is nearly
  uncorrelated with the level (−0.16) and with momentum (−0.08).
- So "funding on up days is low" says funding is low on every kind of day. Funding is low after a falling market,
  and that has not told us about the next week or month.

### The rules

Each rule is long when x ≥ 0 ("claim") or x < 0 ("crowding"), and flat otherwise. Returns are net of the funding longs
pay. The table shows annual net returns.

| Rule | Window | In market | Switches/yr | Net 1x / 2x / 3x | Always long | Excess (t) at 1x |
|---|---|---|---|---|---|---|
| slope claim, basket (API) | discovery | 30% | 20 | +13.1 / +11.4 / +9.7% | +9.5% | +3.6% (+0.08) |
| | validation | 51% | 35 | +10.8 / +7.8 / +4.9% | −8.1% | +18.9% (+0.52) |
| slope claim, BTC (manual) | discovery | 30% | 20 | +4.1 / +3.6 / +3.0% | −2.5% | +6.6% (+0.22) |
| | validation | 51% | 35 | +24.4 / +23.4 / +22.3% | +28.9% | −4.5% (−0.21) |
| up-day claim, basket (API) | discovery | 30% | 5 | +3.0 / +2.6 / +2.2% | +9.5% | −6.5% (−0.14) |
| | validation | 34% | 6 | −2.3 / −2.8 / −3.3% | −8.1% | +5.7% (+0.15) |
| up-day claim, BTC (manual) | discovery | 30% | 5 | +12.3 / +12.2 / +12.0% | −2.5% | +14.8% (+0.45) |
| | validation | 34% | 6 | +13.8 / +13.6 / +13.5% | +28.9% | −15.1% (−0.70) |
| slope crowding, basket | discovery | 58% | 20 | −6.7 / −8.4 / −10.1% | +9.5% | −16.2% (−0.47) |
| | validation | 49% | 35 | −24.8 / −27.7 / −30.6% | −8.1% | −16.7% (−0.53) |
| slope crowding, BTC | discovery | 58% | 20 | +2.0 / +1.4 / +0.8% | −2.5% | +4.6% (+0.17) |
| | validation | 49% | 35 | +2.5 / +1.4 / +0.4% | +28.9% | −26.5% (−1.53) |
| up-day crowding, basket | discovery | 59% | 5 | +18.1 / +17.7 / +17.3% | +9.5% | +8.6% (+0.27) |
| | validation | 66% | 6 | −6.7 / −7.2 / −7.7% | −8.1% | +1.4% (+0.05) |
| up-day crowding, BTC | discovery | 59% | 5 | +6.6 / +6.5 / +6.3% | −2.5% | +9.1% (+0.40) |
| | validation | 66% | 6 | +14.8 / +14.6 / +14.4% | +28.9% | −14.2% (−0.81) |

- **Costs:**
  - The basket pays API costs (8.5 / 17 / 25.5 bp per side at 1x / 2x / 3x), and its daily rebalancing is not costed.
  - BTC pays manual web costs (3 / 6 / 9 bp). API on BTC, at 8.5 bp, lowers BTC's numbers by 0.3-1.9 points a year.
- **No excess t over always long reaches 1.7** in any rule, window or cost. The largest is −1.65: the slope-crowding
  gate on BTC at 3x in validation, which trails always long.
- **The gated books look better in some cells only because they are out of the market for half the time.** For
  example, the slope-claim basket in 2024-26 was +10.8% against −8.1% for an always-long basket.
  - That cell has t +0.52.
  - The same rule on BTC trails always long (−4.5%), in the same years.
- **Drawdowns,** in `results/summary.json`, are on a summed (not compounded) scale. Most gates cut them because they
  hold the market about half the time. The slope-crowding basket deepened it in validation (−143 against −121).

## What this does and does not show
**It shows,** for 2021-2026 and the 50 most traded Binance perps:
- neither the funding response to up days nor up-day funding leads the basket or BTC over the next 7 or 30 days;
- that holds in either direction (the guest's or crowding), and with or without the last 30 days' return taken out;
- the guest's observation is correct, but it measures the funding level, not a response.

**It does not test:**
- **The guest's year-scale reading.** 2026 against 2022 is one comparison; it cannot be tested with 5.7 years.
- **MEXC's own funding,** the owner's venue. Binance funding only.
- **Funding as a crowding signal per coin.** That is cross-sectional: R238, R276 (bn_fund_3d) and R190/R191 carry.
- **Horizons beyond 30 days.** Power at 30 days was already low: 24% for a correlation of 0.3.

## Costs
- **At 1x:**
  - The basket pays 8.5 bp per side (API), and BTC pays 3 bp (manual web).
  - With 5-35 switches a year, costs take 0.15-3 points a year.
- **At 2x and 3x:** no rule's excess over always long comes near significance. The cost level does not change the
  verdict.

## Read against the program
- 4 trials, each against 2.50. No validation |t| reaches 0.9.
- The program's 9.48M trials do not change a NULL.
- The power before the run was 90% at 7 days for a correlation of 0.3. A weekly-scale effect that large is ruled out.
  Smaller ones, and 30-day effects below a correlation of about 0.5, are not.

## Next
- **M295 is TESTED (NULL).** Like the earlier gates and market-timing lanes (M003, M158, R242, R255), it is NULL.
- **The same question on MEXC's own funding** would need its own id.
  - The lab holds MEXC funding from 2025-04 (`mexc_fund` in the panel).
  - 18 months, all inside this validation window, is too short for a 30-day horizon.
- **Next in DIRECTION's table:** M290 (scheduled US releases), which waits for CPI and payroll calendars.
