# Reflection 2026-11-25 (cycle 2 of the day): where is the weekend option rent still young? (register O7)

- **Lens:** "change the scale". One coin becomes every coin and every book.
- **Rule 2:** widen a strong result the moment it appears.
- **The family is options, for the second session running.** It still binds because O3b found a four-year rent, and
  its closure date is the most informative fact about where the next one is.

## 0. What the lab already knows
- **O3b** (`docs/reviews/o3b_daily_vrp.md`, read once):
  - Deribit's one-day BTC options overpriced Saturday by about 48 bp a day over 2022-26 (t −7.3).
  - By year: −118, −57, −22 and −40 bp, then +15 in 2026.
  - Makers priced a Saturday at about 62% of a weekday's vol, while it realizes about 40%.
- **The field.** Deribit's own blog backtest sold Friday-to-Sunday strangles at a 27.4% APR (2020-24) and found
  Sunday sales losing. No paper measures the weekend share of crypto option premia (the reader, 2026-11-25).
- **Data held:**
  - Deribit BTC trades, 2022-01..2026-10;
  - ETH, downloading now with the same fetcher;
  - Binance hourly klines for every perp coin.
- **Not held:** the USDC-settled alt options on Deribit (the fetcher reads BTC and ETH only), and other venues'
  option history.

## 1. The economic question
Is there a book, today, where makers still price a Saturday too close to a weekday, so that a seller of one-day
Saturday straddles earns more than costs and tails? Can the owner reach it?

## 2. The mechanism
- **The question.** Who must pay? Saturday option buyers. Demand for weekend protection comes from:
  - perp traders hedging across the closed TradFi window;
  - structured products.
- **What sets the price.** The quote is the maker's vol surface, which is built in calendar time and adjusted by a
  "weekend weight".
- **Why the rent exists.** The rent is the error in that weight. A new book inherits whatever weight the maker's
  model starts with, and learns it from the book's own realized weekends.

## 3. The barrier
- **Little.** The same few market-making firms quote most crypto option books.
  - Deribit's BTC makers learned between 2025 and 2026.
  - A maker who has learned on BTC can copy the weight to ETH and to alts in a day.
- **So the rent is most likely open where:**
  - the makers are different;
  - the book is too small for the main firms to care;
  - realized weekend behaviour differs from BTC's.
- **The incumbents' quotes come first (L052):** the snapshot of weekend dailies on each book, now.

## 4. Fermi
- **The size, if a book is open at the 2022-25 average.** About 45 bp a Saturday at the bid on the straddle's
  notional, minus about 16 bp of costs: about 30 bp. Over 52 Saturdays, about 15% a year on notional, before tails.
- **The tails are real.** One −15% Saturday costs about 14% of notional against a 1.2% premium. The by-year means
  already include the 2022 weekends.
- **The owner's capital.** On Deribit, short options need margin of roughly 10-20% of notional (to check per book).
  €10k could carry €30-50k of notional, about €4-7k a year if open at that level.
- **Capacity.** Saturday one-day volume is small: about 25 BTC a day near the money on BTC (O3b's set). Alt books
  are smaller still, so the market's capacity, not the owner's capital, binds.
- **Decay.** On BTC, the rent halved roughly every 1-2 years and then vanished.

## 5. What we see that others do not
Little, except that we measured the closure year and can screen every book's weekend weight in minutes.

## 6. The cheapest decisive observation
1. **Every book's weekend weight, today,** from public quotes. The reader is doing this now
   (`room_20261125c/weekend_venues.md`). Saturday forward vol over weekday forward vol, set against the coin's
   realized Saturday-to-weekday ratio from Binance klines (held).
2. **ETH's history on Deribit:** the same read as O3b, for ETH. Did the ETH rent close at the same time? If it closed
   later, or not at all, the makers learn by book, not all at once, and younger books are likely still open.

### O3b audited (Haiku auditor `room_20261125c/audit_o3b.md`, independent code; band figures re-run by me)
- **The result is reproduced exactly:** Saturday −47.8 bp (t −7.3), n 248.
  - Expiry alignment is clean: all expiries fall at 08:00 UTC, and the same-day expiry is excluded.
  - The Deribit index against Binance changes nothing.
  - Seller-side IV changes nothing (−47.3).
- **The moneyness band is the one sensitivity.** The smile lifts IV away from the money, so the ±2% band overstates
  the at-the-money premium:

| Band | Saturday mean (move − premium) | t | By year 2022 / 23 / 24 / 25 / 26 |
|---|---|---|---|
| ±0.5% | **−32.3 bp** | −4.6 | −102 / −50 / −15 / −33 / +21 |
| ±1% | −41.6 | −6.3 | −115 / −51 / −16 / −35 / +21 |
| ±2% (registered) | −47.8 | −7.3 | −118 / −57 / −22 / −40 / +15 |

- **The honest at-the-money size is about −32 bp a Saturday** over 2022-26, before about 16 bp of cost. The pattern
  by year is unchanged.
  - Weekdays sit at −7 bp in every band, so the Saturday gap is not a band artefact.
  - Median −61 bp; 21% of Saturdays had a move above the premium.
- **Not checked:** minute data (none held), and costs beyond the 16 bp reference.

### The realized side, measured (Binance hourly, 09:00 → 08:00 UTC; mean absolute move, Saturday and Sunday over the weekday mean)

| Coin | 2023-24 Sat / Sun | 2025-26 Sat / Sun | Weekday mean move 2025-26 |
|---|---|---|---|
| BTC | 0.40 / 0.88 | 0.47 / 1.04 | 165 bp |
| ETH | 0.50 / 0.87 | 0.53 / 1.14 | 252 bp |
| SOL | 0.64 / 0.90 | 0.63 / 1.08 | 296 bp |
| XRP | 0.57 / 0.85 | 0.63 / 1.24 | 264 bp |
| HYPE | n/a | 0.72 / 0.94 | 376 bp |
| AVAX | 0.70 / 0.82 | 0.81 / 1.12 | 316 bp |
| TRX | 0.74 / 0.83 | 0.78 / 1.06 | 122 bp |
| DOGE | 0.77 / 0.87 | 0.63 / 1.14 | 310 bp |
| BNB | 0.58 / 0.98 | 0.80 / 1.18 | 178 bp |

- **The weekend discount is a BTC property, weaker in alts.** Alt moves are crypto-native, not TradFi-driven.
- **BTC's Saturday got relatively busier:** 0.40 → 0.47. Part of the 2026 closure may be the world changing, with
  weekend news such as tariff posts and 2025-10-10, not only the makers learning.
- **Consequence for O7.** A maker who copies BTC's learned weight (about 0.5-0.6) to an alt book would *underprice*
  alt Saturdays, whose ratio is 0.63-0.81. On a young alt book the rent may have the **opposite sign**: buy
  Saturday, not sell.
  - The snapshot test must therefore compare each book's implied weekend weight with **that coin's** realized ratio,
    never with BTC's.
- **Sunday is a full day everywhere** (0.94-1.24 in 2025-26). The Sunday-evening reopen and Asia's Monday make it
  so. A book that discounts Sunday like Saturday underprices it.

### The world changed in 2026, not only the makers (measured, 08:00 → 08:00 UTC mean move)

| | Fri→Sat | Sat→Sun | Sun→Mon | Sat/Fri | Sun/Fri |
|---|---|---|---|---|---|
| BTC 2025-26 | 150 bp | 81 | 176 | 0.54 | 1.18 |
| **BTC 2026** | 165 | **119** | 128 | **0.72** | 0.78 |
| ETH 2025-26 | 238 | 132 | 290 | 0.56 | 1.22 |
| **ETH 2026** | 222 | **150** | 213 | **0.67** | 0.96 |

- **Saturdays became busier in 2026,** and Sundays calmer. O3b's 2026 "closure" (+15 bp) is in large part this shift
  in realized moves. The makers' weight may have moved less than I wrote in L054.
- **A hypothesis to keep, not a finding.** 24/7 equity perps (trade.xyz from 2025; the lab's closed-market class)
  now carry equity price discovery into crypto's weekend. That would couple crypto Saturdays to equity news, the
  clock shift that makes a fixed weekend weight wrong in a new direction.
- **Snapshot 2026-11-25 20:28 UTC (Deribit mark IV; Thanksgiving week):**
  - BTC prices Sat→Sun forward vol at 0.60 of Fri→Sat (34.0% against 56.7%). Its 2026 realized ratio is 0.72, so
    BTC's Saturday looks cheap.
  - ETH prices it at 0.79 (49.2% against 62.1%). Its 2026 realized ratio is 0.67, so ETH's Saturday looks rich.
  - One snapshot, so a direction to check, not a result (L054).

### Which books could be younger? (reader `room_20261125c/weekend_venues.md`, the OKX line checked by me at 20:32 UTC)
- **Weekend daily expiries exist only for BTC and ETH,** on Deribit, OKX and Aevo:
  - Bybit and Binance list dailies but refused this container (403/451);
  - Derive was unreachable;
  - CME has no weekend expiries.
- **SOL has a Saturday expiry on OKX but no Sunday one,** so its Saturday cannot be isolated. Deribit's alts list
  only Thursday and Friday.
- **The weekend weight is one model, not several:**

| Book, 2026-11-25 ~20:30 UTC | BTC Sat→Sun / Fri→Sat forward vol | ETH |
|---|---|---|
| Deribit | 34.0 / 56.7 = **0.60** | 49.2 / 62.1 = **0.79** |
| OKX (checked by me) | 33.2 / 56.5 = **0.59** | 50.2 / 62.4 = **0.80** |
| Aevo | equals Deribit to 0.1 vol point (reader) | same |

- **So O7's first answer is no.** There is no independent younger book with weekend dailies to screen today. The
  convention rent, if it reopens, will reopen everywhere at once, and the place to watch is the shared weight
  against each coin's realized weekend.
- **French retail access to options is unclear on every venue** (the reader's AMF findings are search summaries,
  unverified). Access is the owner's question (rule 8), and nothing here asks for it yet.

### The registered read for ETH (written and committed before the ETH data is opened; a measurement, 0 trials)
- **The rule.** It is the O3b rule unchanged (`reflection_20261125_greeks.md` §3), with ETH options, ETHUSDT hourly
  closes, and a minimum of 100 ETH traded in the set. The 5-BTC floor is about $400k; 100 ETH is about $300k.
- **The command:** `scripts/measure_daily_vrp.py --coin ETH --min-amount 100 --out docs/reviews/o7_eth_daily_vrp.md`.
- **Predictions:**
  - Over 2022-26, Saturday move − premium ≤ −30 bp with t ≤ −3: P ≈ 0.75.
  - 2026 Saturday within ±20 bp of zero (closed, as on BTC): P ≈ 0.55.
  - Sunday not underpriced beyond costs (move − premium ≤ 16 bp, or t < 2): P ≈ 0.75.
  - A wide band, after L054.

## The ETH read (run once at 22:24 UTC; `docs/reviews/o7_eth_daily_vrp.md`, 1,725 days)

| | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|---|---|---|---|---|---|---|---|
| IV % | 61.9 | 61.9 | 63.9 | 62.4 | 61.2 | **40.6** | 49.6 |
| Move − premium, bp (t) | −1.9 (−0.1) | −6.6 (−0.5) | +18.3 (1.1) | +20.9 (1.3) | −23.5 (−1.6) | **−40.6 (−3.9)** | **+52.1 (3.0)** |
| Saturday by year | | | | | | 2022 −109, 2023 −44, 2024 −3, 2025 −42, **2026 +8** | |
| Sunday by year | | | | | | | 2022 +77, 2023 +9, 2024 +38, 2025 +128, **2026 −2** |

- **Predictions:** 2 of 3 right.
  - Saturday ≤ −30 bp with t ≤ −3: yes.
  - 2026 within ±20 bp: yes.
  - Sunday not beyond costs: **no**. ETH's Sunday was underpriced by 52 bp (t 3.0), well beyond about 16 bp of cost.
- **The pattern is the same on both coins.** The one weight the makers share priced Saturday too rich and Sunday too
  cheap for four years:
  - BTC Saturday −48 and Sunday +21;
  - ETH Saturday −41 and Sunday +52.
  - A Saturday-sell / Sunday-buy pair earned about 60-90 bp a weekend gross before 2026, against about 32 bp of cost
    for two straddles.
  - **In 2026 both gaps are about zero on both coins.**
- **Why it closed: both sides moved.** I first wrote "mostly the world, not the quotes". I then measured the makers'
  weight (mean trade IV on that day over the weekday mean) and that sentence was wrong:

| Year | BTC implied / realized, Saturday | BTC Sunday | ETH Saturday | ETH Sunday |
|---|---|---|---|---|
| 2022 | 0.77 / 0.31 | 0.81 / 0.89 | 0.78 / 0.42 | 0.80 / 0.97 |
| 2023 | 0.62 / 0.29 | 0.74 / 0.86 | 0.64 / 0.39 | 0.77 / 0.81 |
| 2024 | 0.54 / 0.48 | 0.73 / 0.90 | 0.57 / 0.58 | 0.74 / 0.94 |
| 2025 | 0.51 / 0.31 | 0.83 / 1.28 | 0.61 / 0.46 | 0.79 / 1.23 |
| **2026** | **0.59 / 0.70** | **0.91 / 0.72** | 0.61 / 0.67 | **0.94 / 0.96** |

  - **The makers learned Saturday slowly,** from 0.77 to 0.51 over 2022-25 on BTC, but realized Saturdays stayed
    lower (0.29-0.48), so the gap persisted.
  - **In 2026 realized Saturday jumped** (BTC 0.70) past the weight (0.59). On BTC the 2026 gap has flipped sign:
    Saturday cheap by +15-21 bp, Sunday rich by −35.
  - **On Sunday the makers raised the weight in 2026** (0.91-0.94) just as BTC's realized Sunday fell (0.72). They
    seem to chase the previous year's realized ratio (2025: 1.28).
  - **A lagging estimator against a ratio that jumps year to year** (BTC Saturday 0.31, 0.29, 0.48, 0.31, 0.70) will
    keep making errors of both signs. Whether they can be predicted is the open question. One year ahead, the last
    year's realized ratio would have been the makers' own mistake.
- **What follows (O7c, a tripwire, no lane).** Extend both reads each month with the new month of public trades. If
  the pooled BTC+ETH Saturday mean (move − premium) over the last three months is ≤ −30 bp with t ≤ −2, or the
  Sunday one is ≥ +30 bp with t ≥ 2, register a forward paper lane: the Saturday-sell / Sunday-buy pair on Deribit
  one-day straddles, at measured bid and ask.

