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

### The registered read for ETH (written and committed before the ETH data is opened; a measurement, 0 trials)
- **The rule.** It is the O3b rule unchanged (`reflection_20261125_greeks.md` §3), with ETH options, ETHUSDT hourly
  closes, and a minimum of 100 ETH traded in the set. The 5-BTC floor is about $400k; 100 ETH is about $300k.
- **The command:** `scripts/measure_daily_vrp.py --coin ETH --min-amount 100 --out docs/reviews/o7_eth_daily_vrp.md`.
- **Predictions:**
  - Over 2022-26, Saturday move − premium ≤ −30 bp with t ≤ −3: P ≈ 0.75.
  - 2026 Saturday within ±20 bp of zero (closed, as on BTC): P ≈ 0.55.
  - Sunday not underpriced beyond costs (move − premium ≤ 16 bp, or t < 2): P ≈ 0.75.
  - A wide band, after L054.
