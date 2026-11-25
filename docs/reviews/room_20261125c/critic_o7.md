# Critic on O7 (weekend options), 2026-11-25 (adversarial, Haiku critic)

Scope: `docs/reviews/reflection_20261125_o7.md`, O3a/O3b/O7/O7b rows of `docs/reviews/open_questions.md`, `o3b_daily_vrp.md`, `o7_eth_daily_vrp.md`, `room_20261125c/audit_o3b.md`, `weekend_venues.md`. Data: BTC and ETH Deribit flow, `data/klines_1h/{BTC,ETH}USDT.parquet`. Scratch code: `/tmp/claude-0/-home-user-T/a4c99094-0eba-54d5-9f6a-3abc85cabed2/scratchpad/critic_*.py`.

Verdict: the O3b overpricing survives, but the story is cleaner than the data: 2026's "closure" rests on two Saturdays, the Fermi is far too rich at the recent level, the "chase" rule is not predictive, and the pre-registered O3b misses are unreported.
## A. Errors (with corrections)

**E1. Fermi size.** `reflection_20261125_o7.md:46`: "The size, if a book is open at the 2022-25 average. About 45 bp a Saturday at the bid". My pooled 2022-25 at ±2% is −59.5 bp (not 45). The 45 matches the equal-weight average of five years at ±2% (−118.5, −56.6, −21.5, −40.1, +14.6 → −44.4), so it includes 2026 and is not "2022-25". It also uses the ±2% band that the audit (`audit_o3b.md:57`) says overstates ATM by about 12 bp. Correct figures (my run, Saturdays only):

| band | 2022-26 pooled, gross | 2024-26 pooled, gross | 2024-26 net of 16 bp | per year on notional (×52), net |
|---|---|---|---|---|
| ±0.5% (ATM, audit's choice) | 32.3 | 11.5 | −4.5 | −2.3% |
| ±1% | 40.4 | 12.9 | −3.1 | −1.6% |
| ±2% (registered) | 47.8 | 18.4 | +2.4 | +1.2% |

So the recent-sample net is about zero, not 30 bp (15%/yr). Before 2026 the net is positive; after 2024 it is not, at ATM.

**E2. Margin arithmetic.** `reflection_20261125_o7.md:51`: "could carry €30-50k of notional". At the stated 10-20% margin (`:50`, "roughly 10-20% of notional (to check per book)"), €10k carries €50-100k, not €30-50k. The margin itself is unchecked.

**E3. Capacity.** `reflection_20261125_o7.md:52`: "about 25 BTC a day near the money on BTC (O3b's set)". My sum over O3b's set (trades at 08-09 UTC, expiry D+32h, ±2% of index, amount buy+sell) gives a median of 98.6 BTC per Saturday (2024-26 median 88.3, n=253):
```python
cap = base[(base.strike/base.index_price-1).abs()<=0.02].groupby('D').amt.sum()   # base: 08-09 UTC, expiry D+32h
cap[cap.index.dayofweek==5].median()   # 98.6
```
The 25 figure is not reproduced. The consequence reverses the lead's claim: at the owner's size (€50k notional is about 0.6 BTC) capacity does not bind; the net edge and the tails do.

**E4. "Decay ... halved ... then vanished"** (`reflection_20261125_o7.md:54`: "the rent halved roughly every 1-2 years and then vanished"). The ±2% by-year Saturday gaps are −118.5, −56.6, −21.5, −40.1, +14.6 (`o3b_daily_vrp.md:19-23`, Sat column in the by-year table). 2025 rebounded to −40. Not a clean halving, and the 2026 +15 is the two outliers (see B).

**E5. "In 2026 both gaps are about zero on both coins"** (`reflection_20261125_o7.md:181`). BTC Sunday 2026 is −35.3 (`o3b_daily_vrp.md:23`: "| 2026 | 0.2 | -25.1 | 17.0 | -4.1 | -12.0 | 14.6 | -35.3 |"). The same reflection calls it "Sunday rich by −35" (`:195-196`). The BTC Saturday-sell/Sunday-buy pair in 2026 is −50 bp gross (my run, below), which is not zero. Only ETH is near zero.

**E6. "A Saturday-sell / Sunday-buy pair earned about 60-90 bp a weekend gross before 2026"** (`reflection_20261125_o7.md:179`). My run, same premium construction (ATM ±2%):

Pair gross (Sat e negated + Sun e): BTC 2022-25 91.0, ETH 2022-25 112.1; BTC 2022-26 68.8, ETH 2022-26 92.7; BTC 2026 −49.9, ETH 2026 −10.2. "Before 2026" is 91-112, not 60-90; 60-90 matches 2022-26 only. The BTC 2026 pair would have lost money, which the text does not say.

**E7. Pre-registered O3b predictions not reported.** `open_questions.md:24` (O3b row) wrote before the read: "P(underpriced by more than 16 bp) ≈ 0.2", "Weekday one-day VRP positive ... on at least 4 of 5 weekdays; Saturday within ±10%". The read (`o3b_daily_vrp.md:7-13`) gives:
- Sunday: move − premium = +21.00 bp (BTC) — more than the 16 bp cost, the event the row gave P ≈ 0.2. Premium/move = 159.65/180.64 = 0.88, under the 0.90 the row required.
- Weekdays with positive VRP (e < 0): Tue −18.8, Wed −15.5, Fri −24.0. That is 3 of 5, not 4 of 5 (Mon +11.5 and Thu +7.1 fail).
- Saturday move/premium = 0.62 (`o3b_daily_vrp.md:12`), not within ±10%.
So all three registered predictions failed. The reflection never says so; it reads O3b as a confirmation. The O3b row is still marked "Read".

**E8. O3a contradiction.** `open_questions.md:23` (O3a, "answered by O3b's read"): "For a straddle to expiry (75-86 bp) against a mean move of 77-81 bp, it is priced right." O3b (`o3b_daily_vrp.md:12`) says Saturday is overpriced by 48 bp. The row is not reconciled.

**E9. Weekday claim.** `reflection_20261125_o7.md:82`: "Weekdays sit at −7 bp in every band". My five-weekday average at ±2% is −7.9 bp (`o3b_daily_vrp.md:7-11`: Mon +11.5, Tue −18.8, Wed −15.5, Thu +7.1, Fri −24.0). The audit gives Tuesday at ±0.5% as "-19.66" (`audit_o3b.md:53`), so the figure is not the same in every band. Not verified per band; the sentence is stated as fact.
## B. Question 1: is 2026 one or two outlier Saturdays?

Source: `data/klines_1h/BTCUSDT.parquet` (ends 2026-09-30, so "2026" is Jan-Sep). Window D 08:00 -> D+1 08:00 UTC, P(h) = close of the bar opening at h-1 (script `critic_sat.py`).

| set | Sat mean abs | Sat median | Sat trim5 | Sat RMS, annualised | Fri mean | Sat/Fri mean | Sat/Fri median |
|---|---|---|---|---|---|---|---|
| 2025-26 | 80.9 | 51.6 | 68.2 | 24.9 | 149.5 | 0.54 | 0.50 |
| 2026 | 119.0 | 78.7 | 108.0 | 34.1 | 164.9 | 0.72 | 0.62 |
| 2026 excl. 2026-01-31 and 2026-02-28 (n=37) | 94.3 | 71.1 | – | 23.7 | 164.9 | 0.57 | 0.56 |
| 2024 | 102.2 | 66.1 | 89.3 | 29.3 | 184.4 | 0.55 | 0.53 |
| 2025 | 52.4 | 36.0 | 46.7 | 14.7 | 138.0 | 0.38 | 0.40 |

The reflection's 81 and 119 (`reflection_20261125_o7.md:115-116`) reproduce; the arithmetic is right.

- **Two outliers, both real.** 2026-01-31: move −642 bp; hourly volume rises from 2-5k BTC to 31-47k in the 14:00-18:00 UTC bars (rows 53342-53346 of the klines). 2026-02-28: +508 bp, a rally 63.8k to 67.1k; a −370 bp wick at 06:00 is before the 08:00 window start, so it is not in the move. Excluding them, 2026 is a 94 mean and a 71 median.
- **Baseline is contaminated.** The "0.54 -> 0.72" compares a pool that contains 2026 with 2026. Per-year Sat/Fri means: 2023 0.33, 2024 0.55, 2025 0.38, 2026 0.72. 2024's 0.55 is close to the pooled figure, and 2024 Saturday (102) is above 2026 excluding the two (94).
- **Sunday moved too.** Sunday mean abs 212 in 2025 vs 128 in 2026: the lead's "Sundays calmer" is correct but is part of the same two-day noise.
- **Answer:** two Saturdays, not a regime. Excluding them, 2026 looks like 2024, not a new level. "Saturday got busier" is weak; "the makers' weight moved" is not shown by this.
## C. Question 2: the forward-vol ratio against the realized ratio

Not apples to apples:
1. **Vol vs mean absolute move.** The implied side is a vol (annualised sqrt of variance). The lead compares it with a mean-absolute-move ratio (0.72). The like-for-like realized quantity is RMS, annualised as RMS × sqrt(365). My 2026 numbers: Sat 34.1, Fri 43.6, RMS ratio 0.78 (incl. outliers), 0.54 (excl.). Mean-abs ratio 0.72 (incl.), 0.57 (excl.).
2. **Levels, not ratios.** Implied Sat→Sun 34.0 (`reflection_20261125_o7.md:126`, "34.0% against 56.7%") vs realized Sat RMS 34.1 incl. outliers: priced at realized. Implied Fri→Sat 56.7 vs realized Fri 43.6: Friday is quoted about 30% above realized. So the "cheap Saturday" is a rich Friday. Excluding the two outliers, Saturday quote 34.0 vs realized 23.7 is rich, the opposite sign. The conclusion flips with the outliers.
3. **Mark IV vs trade IV, one snapshot, no variance premium adjustment.** `reflection_20261125_o7.md:125` "Snapshot 2026-11-25 20:28 UTC (Deribit mark IV; Thanksgiving week)". Mark IV is not traded price; implied carries a variance risk premium that may differ by day type; one holiday-week snapshot still yields "BTC's Saturday looks cheap". With n=39 the realized ratio's standard error is wide (the two outliers move it by 0.2).
## D. Question 3: one shared weekend model?

- `reflection_20261125_o7.md:142-143`: Deribit 34.0/56.7 = 0.60, OKX 33.2/56.5 = 0.59 (BTC); ETH 0.79 vs 0.80. The OKX row is the lead's own check, not reproduced by me (no OKX data read).
- `weekend_venues.md:91`: "OKX is 1 to 3 vol points below Deribit on BTC at most expiries". The levels differ; the ratios agree. That is not one model; it is two quotes with similar shape.
- Arbitrage: both venues expire at 08:00 UTC, so a calendar arbitrage exists in principle, but bid-ask and fees on daily strikes are wide, and the arbitrage acts on strikes, not on a single ATM forward ratio. It bounds quotes loosely; it does not force 0.60 = 0.59 to the second decimal. Equal shape can also come from a common spot-driven smile or the same makers. Cannot tell from one snapshot.
- Aevo: `weekend_venues.md:90`: "Aevo's marks look anchored to the same surface". Not independent.
- Does it matter for "no younger independent book"? Yes. Reachable venues with weekend dailies: Deribit and OKX (Aevo not independent). Bybit, Binance, Derive were not reached (`reflection_20261125_o7.md:133-134`). So the honest answer is "none reachable and independent", N=2. The word "no" overclaims.
- Internal tension: `reflection_20261125_o7.md:33` says a new book "learns it from the book's own realized weekends", and `:147` says "will reopen everywhere at once". Both cannot be a prediction without evidence.
- Threshold: `open_questions.md:32` sets "above 0.55 ... P ≈ 0.4". The readings (0.59-0.60) sit 0.04 above it. A small move flips the verdict. Set the threshold before the next snapshot.
## E. Question 4: the Fermi, recomputed

Done in E1. Summary: at ATM (audit's ±0.5%), 2022-26 gross 32 bp, net 16 bp (about 8.5%/yr on notional). 2024-26 gross 11.5, net −4.5 (−2.3%/yr). Plus tails: the 2022-26 Saturday sample has max |move| 642 bp (2026-01-31) and zero moves above 1000 bp; 2020-21 had 1464, 1092, −1006 bp (`klines`, 352 Saturdays). Short straddle loss is roughly |move| − premium: a −6.4% day costs 5.2% of notional; a 14.6% day costs 13.4%. On €50k notional: €2.6k and €6.7k, i.e. 26% and 67% of €10k. The Fermi says "before tails" with no tail term; it is an upper bound by construction.

"At the bid" (`reflection_20261125_o7.md:46`) is not measured: the audit's "A seller at the bid" (`audit_o3b.md:79`) uses sell-dominated trade rows, which are trade prices.
## F. New: the makers' weight table and "chase the previous year"

The lead's table (`reflection_20261125_o7.md:185-190`) and the chase claim (`:197-198`: "seem to chase the previous year's realized ratio") were checked. Weights: mean daily trade IV (ATM ±2%, same set as O3b, min BTC 5 / ETH 100) on Sat or Sun over the mean of Mon-Fri days in the same year (script `critic_weight.py`). Realized: mean |move| 08→08 on that day over the mean of weekday moves.

| coin, day | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| BTC Sat weight (mine / lead) | 0.77 / 0.77 | 0.62 / 0.62 | 0.54 / 0.54 | 0.51 / 0.51 | 0.59 / 0.59 |
| BTC Sat realized (mine / lead) | 0.36 / 0.31 | 0.30 / 0.29 | 0.49 / 0.48 | 0.31 / 0.31 | 0.71 / 0.70 |
| BTC Sun weight (mine / lead) | 0.81 / 0.81 | 0.74 / 0.74 | 0.73 / 0.73 | 0.83 / 0.83 | 0.90 / 0.91 |
| BTC Sun realized (mine / lead) | 0.90 / 0.89 | 0.85 / 0.86 | 0.92 / 0.90 | 1.26 / 1.28 | 0.76 / 0.72 |
| ETH Sat weight (mine / lead) | 0.78 / 0.78 | 0.64 / 0.64 | 0.57 / 0.57 | 0.61 / 0.61 | 0.61 / 0.61 |
| ETH Sat realized (mine / lead) | 0.48 / 0.42 | 0.41 / 0.39 | 0.61 / 0.58 | 0.42 / 0.46 | 0.68 / 0.67 |
| ETH Sun weight (mine / lead) | 0.80 / 0.80 | 0.77 / 0.77 | 0.74 / 0.74 | 0.79 / 0.79 | 0.94 / 0.94 |
| ETH Sun realized (mine / lead) | 0.95 / 0.97 | 0.77 / 0.81 | 0.98 / 0.94 | 1.20 / 1.23 | 0.96 / 0.96 |

Weights reproduce; realized ratios differ by up to 0.06 (ETH 2022, 2025), and the lead's table does not define its window or statistic (`reflection_20261125_o7.md:185`).

**Does the makers' weight chase last year's realized ratio?** (script `critic_chase.py`, 4 pairs 2023-26 only)
- Sunday: corr(weight_t, realized_{t−1}) = 0.89 (BTC), 0.95 (ETH). Positive, but n = 4.
- Saturday: −0.55 (BTC), +0.42 (ETH). No consistent sign.
- Predictor test: "weight_t = realized_{t−1}" has mean absolute error 0.13-0.20; "weight_t = weight_{t−1}" has 0.06-0.08. Persistence beats chasing by 2-3 times on both coins and both days.
- Verdict: the chase is a description of four points, not a rule. It is not supported as a predictive model, and the lead's "one year ahead, the last year's realized ratio would have been the makers' own mistake" (`:199-201`) is not tested. Persistence is the better default and is what the lead's own table shows (weights move slowly: BTC Sat 0.77→0.51 over four years).
## G. Tripwire O7c: power with about 26 Saturdays

Rule (`reflection_20261125_o7.md:204-205`): pooled BTC+ETH Saturday mean (move − premium) over the last three months ≤ −30 bp with t ≤ −2.

Simulation (script `critic_trip.py`): 26 Saturdays per window, resampled i.i.d. from demeaned per-Saturday residuals of BTC (sd 103 bp, n 253) and ETH (sd 164 bp, n 251), true mean shifted to μ:

| true mean (bp) | P(trip) per look |
|---|---|
| 0 | 0.04 |
| −10 | 0.08 |
| −20 | 0.13 |
| −32 (2022-26 ATM) | 0.21 |
| −41 | 0.28 |
| −48 (2022-26 ±2%) | 0.31 |

- **Low power.** At the size the lead believes in (−32 at ATM), a 3-month look fires about one time in five. The tripwire misses the effect four times in five.
- **The t condition binds.** With sd about 130 bp and n=26, t ≤ −2 needs a mean ≤ about −51 bp. The −30 bp clause is never the binding one for these sds; the test is effectively "mean ≤ −51".
- **False alarms and correlation.** Null P(trip) is 0.04 per look; 24 monthly looks (treated as independent, overlap ignored) give P(at least one) ≈ 0.61. BTC and ETH share a weekend clock, so 26 pooled Saturdays carry fewer than 26 independent ones: power is lower than simulated.
- **Verdict:** the tripwire can detect only a large gap, and will often fire on noise. It needs a longer window (a year, about 52 Saturdays per coin) or a pre-stated power target before it is registered. As written, it is a weak alarm, not a test.
## H. Fine
O3b's headline reproduces on my code (±2% −47.8 bp, t −7.34; ±0.5% −32.3, `audit_o3b.md:53`); the 2026 BTC realized ratios and the weights reproduce.
## I. Next step
1. Write 2026 as "two Saturdays dominate" (±2% gap about −6 mean, −19 median, n=37), not "closed"; report E7 in the O3b row.
2. Replace the Fermi with E1 and do not size: the recent ATM net is about zero.
3. Replace the vol vs mean-abs ratio with a level comparison, with and without the outliers; drop "cheap Saturday" until it survives both.
4. Drop "chase" as a rule (use persistence, n=4); redesign O7c with a 12-month window or a stated power target (P(detect −32) ≈ 0.2 now).
5. Fix capacity (99 BTC, not 25) and margin arithmetic; check Deribit's short-straddle margin first.
6. For O7 say "none reachable and independent" (N=2), not "no".
## J. Not checked
OKX and Aevo data; Deribit margin rules; news attributions (e.g. "tariff posts", `reflection_20261125_o7.md` ~L101-102); minute data; costs beyond 16 bp. Klines end 2026-09-30, so the November snapshot is outside the realized sample.
