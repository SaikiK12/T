# FINDINGS: qbasis_v1 (R301). The quarterly basis does not rank the perps that follow

**Verdict: NULL.** M170 is TESTED and closed as a perp signal.
- **Trials:** 16, gate 0 on seen prices.
- **Read:** frozen PREREG 55fd8cf4, committed and pushed in 415d13d before the run. Run 2026-10-22 08:40 UTC with
  `scripts/run_qbasis.py`. All 7 inputs matched their frozen hashes.
- **The pick fails all three checks.** The best discovery book is level low h7 k2: each week, long the 2 coins with the
  lowest annualized quarterly basis and short the 2 highest, held 7 days.
  - Discovery net 1x +14.6 bp/day, t +1.83.
  - Validation net 1x +1.2 bp/day, t +0.16; 2x −0.5; without its 10 best weeks −94 bp per week.

## What was tested
Chi, Hao, Hu and Ran (2023): the dated-futures basis is the strongest cross-sectional signal on crypto futures. Here:
- **Universe:** the 14 coins with a Binance COIN-M quarterly (9-10 at a time until 2025-09, then 5), traded in their
  USD-M perps. At least 5 names a day.
- **Signals:** the annualized basis (level) or its 7-day change (chg7).
- **Books:** long the k highest and short the k lowest (side high), or the reverse (low); k = 1 or 2; held 1 day
  (daily) or 7 days (weekly).
- **Costs and funding:** API 8.5 bp per side at 1x on each rebalance's turnover. Funding is paid and received.
- **Windows:** discovery 2021-01..2023-12, validation 2024-01..2026-09.
- **Not in these books:** the carry a quarterly earns by converging to spot. This lane asks only whether the basis
  predicts the perp's price.

## Result

**The pick: level low h7 k2 (bp per week unless marked; t is Newey-West, lag 2 on weeks)**

| Window | Weeks | Gross bp/day (t) | Net 1x / 2x / 3x bp/day | t at 1x | Median week, 1x | Without best 10 weeks (1x) | Best 10 weeks' share (1x) | Sharpe (1x) | Long leg | Short leg |
|---|---|---|---|---|---|---|---|---|---|---|
| Discovery | 156 | +16.3 (+2.05) | +14.6 / +12.8 / +11.1 | +1.83 | +30.2 | −19.7 | 118% | 1.07 | +105.0 | +9.1 |
| Validation | 142 | +2.9 (+0.38) | +1.2 / −0.5 / −2.3 | **+0.16** | +2.5 | **−94.4** | 1,141% | 0.10 | +62.6 | −42.1 |

- **The checks:**
  - t ≥ 2.0 at 1x: **fails** (+0.16);
  - a positive 2x mean: **fails** (−0.5 bp/day);
  - a positive mean without the 10 best weeks: **fails** (−94 bp per week).
- **Even in discovery the pick was its tail.** Its gross without the 10 best weeks was −7.6 bp per week.
- **By year, net 1x bp/day:**

  | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (to 09) |
  |---|---|---|---|---|---|
  | +37.8 | +16.4 | −11.2 | +15.5 | −13.7 | +2.0 |

- **Break-even** is 79.5 bp per side in discovery and 14.4 in validation (gross per week over turnover of 1.43 a week).
- **The legs:** the low-basis coins were BNB (35-39% of slots), DOT, SOL and BCH. The high-basis coins were BTC, LTC,
  LINK, ETH and XRP.

**All 16 books (bp/day; t at net 1x)**

| Book | Gross disc / valid | Net 1x discovery (t) | Net 1x validation (t) | Validation 2x | Turnover per period |
|---|---|---|---|---|---|
| level high h1 k1 | −13.6 / +5.9 | −25.5 (−1.94) | −8.4 (−0.84) | −22.6 | 1.40 / 1.67 |
| level low h1 k1 | +13.6 / −5.9 | +1.7 (+0.13) | −20.1 (−2.01) | −34.3 | 1.40 / 1.67 |
| level high h1 k2 | −7.1 / +6.1 | −15.5 (−1.55) | −3.7 (−0.52) | −13.6 | 0.99 / 1.16 |
| level low h1 k2 | +7.1 / −6.1 | −1.3 (−0.13) | −16.0 (−2.21) | −25.9 | 0.99 / 1.16 |
| level high h7 k1 | −6.6 / −1.9 | −9.1 (−0.82) | −4.4 (−0.40) | −6.8 | 2.01 / 2.03 |
| level low h7 k1 | +6.6 / +1.9 | +4.2 (+0.38) | −0.6 (−0.05) | −3.0 | 2.01 / 2.03 |
| level high h7 k2 | −16.3 / −2.9 | −18.0 (−2.27) | −4.7 (−0.61) | −6.4 | 1.44 / 1.43 |
| **level low h7 k2 (pick)** | +16.3 / +2.9 | +14.6 (+1.83) | +1.2 (+0.16) | −0.5 | 1.44 / 1.43 |
| chg7 high h1 k1 | −19.3 / +5.5 | −38.1 (−2.99) | −16.9 (−1.68) | −39.3 | 2.21 / 2.64 |
| chg7 low h1 k1 | +19.3 / −5.5 | +0.5 (+0.03) | −27.9 (−2.75) | −50.3 | 2.21 / 2.64 |
| chg7 high h1 k2 | −11.7 / +13.9 | −28.3 (−2.95) | −4.7 (−0.68) | −23.4 | 1.95 / 2.20 |
| chg7 low h1 k2 | +11.7 / −13.9 | −4.9 (−0.51) | −32.6 (−4.62) | −51.3 | 1.95 / 2.20 |
| chg7 high h7 k1 | +21.9 / −10.4 | +17.4 (+1.05) | −14.8 (−1.38) | −19.2 | 3.68 / 3.65 |
| chg7 low h7 k1 | −21.9 / +10.4 | −26.4 (−1.59) | +5.9 (+0.56) | +1.5 | 3.68 / 3.65 |
| chg7 high h7 k2 | +0.6 / −5.2 | −3.6 (−0.32) | −9.2 (−1.26) | −13.3 | 3.39 / 3.30 |
| chg7 low h7 k2 | −0.6 / +5.2 | −4.7 (−0.42) | +1.2 (+0.17) | −2.8 | 3.39 / 3.30 |

### The sign does not hold between windows
- **Level:** in discovery, low-basis coins beat high-basis coins by 7-16 bp/day gross. In validation the daily books
  turned (high beats low by 6 bp/day) and the weekly ones shrank to 2-3 bp/day.
- **chg7:** the daily books' sign flipped too. Low beat high by 12-19 bp/day in discovery; high beat low by 6-14 in
  validation. chg7 high h1 k2's validation gross t of +1.99 is on the side that lost in discovery.
- Only the pick is positive at net 1x in both windows, and in validation by 1.2 bp/day.

### Is the quarterly basis just funding?
- **Mostly.** The median daily rank correlation between the basis and the perp's last 3 days of funding was +0.50 in
  discovery and +0.41 in validation.
- **Mean annualized basis by year:** +12.6% (2021), −2.8% (2022), +2.8% (2023), +9.8% (2024), +4.6% (2025), +2.0%
  (2026). It follows the market's leverage, as funding does.

### Does it just pick one coin?
- **Side high, k = 1** (long the highest basis, short the lowest) is short BNB on 52-54% of days, and long BTC, LINK or
  LTC on 55-58%. BNB's quarterly sat at the lowest basis for half of the sample.
- **chg7** spreads across all coins: no coin is in a leg more than 22% of the time.

### SPA over the 16 books against cash (net 1x, weekly)
- **Discovery:** consistent p 0.295 (bounds 0.200-0.396), best book the pick.
- **Validation:** consistent p 0.952 (0.771-0.989), best book chg7 low h7 k1.
- Neither window rejects "no book beats cash".

## What this does and does not show
**It shows, for 5-10 large coins with Binance quarterlies in 2021-2026:**
- Sorting perps on the quarterly basis, its level or its weekly change, does not predict their next day or week
  reliably in either direction.
- The discovery winner was a few weeks in 2021-22, and it did not repeat.
- The quarterly basis is about half rank-correlated with recent funding.

**It does not test:**
- **The paper's own returns.** These include each quarterly's convergence to spot. Trading the quarterlies needs
  COIN-M access the owner does not use, and would be a new lane.
- **A wider universe.** Only 5-10 coins have quarterlies. A cross-section this narrow has little power.
- **MEXC prices.** All 14 coins list there; nothing here uses them.

## Costs
- **Levels:** API, 8.5 / 17 / 25.5 bp per side on each rebalance's turnover.
- **The cost is not what failed here.** The pick's validation gross is +2.9 bp/day (t 0.38). No book reaches a gross t
  of 2 in validation.
- **At 2x** only chg7 low h7 k1 stays positive in validation (+1.5 bp/day, t well under 1); it lost −26 bp/day in
  discovery. **At 3x** no book is positive in validation.

## Read against the program
- **Program trials:** 9,478,665 once R299 (12), R300 (24) and R301 (16) are appended to 9,478,613
  (`registry.program_trials()`).
- **16 trials, one pick, one validation read.** The pick's validation t of 0.16 is far from any bar, before any
  multiplicity.
- **Power, written before the run:** a pick with a true annual Sharpe of 1.0 had 37% power. Its discovery Sharpe was
  1.07 at 1x; in validation it was 0.10. The miss is far below even a modest real effect.

## Next
- **M170 is TESTED and NULL** as a perp signal on Binance quarterlies.
- **No new lane.** The basis is half funding. Funding as a cross-sectional book is M263, which is next (R302); it has a
  universe of 150 coins instead of 5-10.
- **The data stays useful** as a regime input: the mean basis tracks the market's leverage.
