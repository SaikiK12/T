# FINDINGS: xfund_eea_v1 (R508). R275's carry book passes on Kraken + Hyperliquid, mostly on Kraken's thin perps

**Verdict: PASS (R391's rule, gate 1 on a pair the owner could trade).** All four checks hold: the one-sided NW p is
7.2e-14, the 2x mean is above 0, the 10% trimmed mean is above 0, and so is the mean without the two best coins.

- **Registry:** R508, 1 trial. Program trials become 9,785,749.
- **Reproduce.**
  - The PREREG (sha 77c008af), `symbols.csv` and `data_manifest.json` (444 data files by sha256) were frozen in commit
    408471c before any statistic.
  - `python scripts/run_xfund_eea.py run`, once, on 2026-11-18. All 9 inputs and all 444 data files matched.
- **The book:** R275's L14d th5% K20, unchanged (`lab.xfund`), at 7 / 14 / 21 bp per leg.
- **Read this first.** The pass is real on its data. But **97% of the return comes from coins that trade under
  $100k a day on Kraken**. It is an illiquidity premium on small Kraken perps, so capacity is the binding limit. The
  liquid coins add about +0.7%/yr. See "Where it comes from".

## Primary book: kraken+hyperliquid L14d th5% K20, 2025-12-08..2026-11-15
| Cost | %/yr on book capital | bp/day |
|---|---|---|
| 1x (7 bp a leg) | **+24.28** | +6.65 |
| 2x | +22.50 | +6.17 |
| 3x | +20.73 | +5.68 |

- **Book days and t.** 343 book days. NW t (lag 10) 7.39; iid t 6.85; annualised daily Sharpe 7.1.
- **Robustness.** Trimmed mean +5.99 bp/day. Without NEIRO and USUAL, the two best coins: +4.90 bp/day (+17.9%/yr).
- **Halves:** +9.00 and +4.32 bp/day.
- **Risk.** Max drawdown (running sum) -0.57%. The top 10 days hold 25% of the total.
- **Where the return comes from.** Funding share 1.04: price legs cost about 4% of gross.
- **Costs.** About 1.77%/yr per 1x of costs, so the book breaks even near 15x costs (about 103 bp a leg).
- **Read against the program.** The one-sided Bonferroni threshold over 9,785,749 trials is z 5.73. The NW t of 7.39
  clears it.

### Book
- All 20 slots were held every day. 238 trades on 56 coins; 2 were forced exits.
- **Direction:** both ways, about equally often.
  - Long Hyperliquid / short Kraken: 120 trades, +490 bp net each on average, 57% winners.
  - Long Kraken / short Hyperliquid: 118 trades, +275 bp net, 59% winners.
- **Per coin:** 45 of 56 traded coins were net positive.
  - Best (bp/day of book): NEIRO +0.91, USUAL +0.84, BRETT +0.47, MELANIA +0.46, KAITO +0.44, BOME +0.40, GOAT +0.39.
  - Worst: CHILLGUY -0.05, PEOPLE -0.05.

### By month (% of book capital, 1x)
| 2025-12 | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 (to 15th) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| +1.93 | +4.51 | +2.80 | +2.41 | +1.75 | +1.73 | +2.60 | +1.32 | +1.56 | +1.23 | +0.86 | +0.11 |

Every month is positive. The level falls through the year: about +3%/month in winter, about +1% in the autumn.

### Funding profile (descriptive, 111 coins)
- **Median annualised funding per coin:** Kraken -2.4%, Hyperliquid +3.3%. The median gap is +5.3%/yr, close to
  Hyperliquid's floor, as designed.
- **Kraken's spread across coins is wide:** from -116% to +187%/yr (interquartile range -12% to +4%).
- **The book lives in that tail.** NEIRO on Kraken averaged +187%/yr against Hyperliquid's -8%; USUAL +131% against
  -6%.
- **Same coins on both venues:**
  - median Kraken/Hyperliquid price ratio 0.998-0.999 (kNEIRO 0.001, its 1000x unit);
  - daily return correlations of 0.90-0.99 for the top contributors.

### Secondary book (reported, not decided): L14d th10% K20
- +24.84 / +22.91 / +20.98 %/yr at 1x / 2x / 3x; NW t 6.92; 259 trades; max drawdown -0.74%.

## Where it comes from (diagnostics after the read, not decided on)
### By Kraken liquidity
Liquidity is measured as each coin's median daily USD volume on Kraken over the window, from its daily candles
(`diagnostics/kraken_volume.csv`).

| Kraken volume per day | Coins in universe | Coins traded | %/yr of book at 1x |
|---|---|---|---|
| under $10k | 16 | 14 | +11.21 |
| $10k-100k | 31 | 28 | +12.42 |
| $100k-1M | 40 | 13 | +0.66 |
| over $1M | 24 | 1 | -0.02 |

### Live cost snapshot (2026-11-18 21:40 UTC)
Source: `diagnostics/books_20261118.json`, written by `scripts/snapshot_eea_books.py`. One snapshot only.
Costs are per side for a $1,000 market order: half-spread plus walking the book, fees excluded (median per bucket).

| Kraken volume per day | Kraken quoted spread | Kraken cost at $500 | at $1,000 | at $2,500 | Hyperliquid at $1,000 |
|---|---|---|---|---|---|
| under $10k | 23.2 bp | 13.5 | 16.5 | 25.3 | 9.8 |
| $10k-100k | 17.9 | 11.7 | 12.8 | 18.0 | 6.0 |
| $100k-1M | 11.8 | 6.8 | 7.1 | 7.7 | 3.6 |
| over $1M | 3.2 | 2.5 | 3.0 | 3.3 | 0.8 |

- **Adding fees.** Taker fees are 5 bp on Kraken and 4.5 bp on Hyperliquid. In the thin buckets a leg-side then
  costs about 15-20 bp on average, about 2-3x the test's 7 bp. The book made +22.5%/yr at 2x and +20.7%/yr at 3x.
- **The costliest contributors:**
  - USUAL: 43 bp a side on Kraken at $1,000;
  - NEIRO: 30 bp;
  - GOAT: 28 bp.
- **Funding still large today.** Kraken's current hourly funding, annualised: MELANIA -118%/yr, GOAT +144%,
  IMX -110%, W -70%, ZK -70%. The tail the book lived in was still there on the day of the read.

## What this does not show
- **Capacity.** On a coin trading $5k-35k a day on Kraken, $1,000-2,500 a leg is about what the books held at the
  snapshot.
  - Twenty such slots are roughly $40k-100k of two-leg capital. More would move the books and the funding.
  - This is a small-account opening, not a large one.
- **One year only.** Kraken serves one year of funding. The level fell through the year, and nothing here says it
  persists.
- **Survivorship.** Kraken's list is today's survivors, so delisted perps are missing. The thin coins are the ones
  most likely to be delisted.
- **Fills.** The test fills at daily closes plus a flat cost. The snapshot is one moment. Real fills on books this
  thin need measuring over time, which is what a forward lane does.
- **Access and margin.**
  - Kraken EEA derivatives for this account (eligibility, EU retail leverage caps) and Hyperliquid from France were
    not checked here.
  - Two-venue margin is a known failure mode (R280). It was not measured.
- **Kraken's formula.** The data's rate is read as Kraken settles it, a fraction of notional per hour. Coins whose
  premium persists on both venues show matching magnitudes: ACE -116% on Kraken and -107% on Hyperliquid; SUPER -77%
  and -72%. That supports the per-hour reading.

## Next
- **Gate 2, forward paper:** a new frozen lane (new id) running this book live on Kraken + Hyperliquid.
  - Daily decisions; fills measured from live books at a fixed slot size ($1,000 a leg); fees at today's schedules.
  - It reports per-coin capacity.
  - Its read decides whether the owner's small stake is warranted (`lab.gate.go_real()`).
- **Before any real order:** confirm Kraken EEA derivatives access, leverage and margin rules for the owner's account.
