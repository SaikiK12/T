# PREREG: xfund_listing_v1 (R516). Cross-venue funding carry in the listing phase, the days R275's book cannot trade

Freeze with `lab.prereg.freeze()` before any listing-phase spread on Binance + Hyperliquid is computed. Never edited
afterwards.

- **Registry id:** R516
- **Owner (single writer):** the Claude session that froze it. `scripts/run_xfund_listing.py` is the only writer of
  `experiments/xfund_listing_v1/results/`.
- **Date registered (UTC):** 2026-11-20

**Methods:** M557 (new: entries in the listing phase, with a short funding window and a price identity check). Carry,
candidate C13.
- **Paper only:** held public data; nothing can place an order.

## Why
- **R275's engine cannot enter a pair in its first weeks.**
  - Both venues need a full 14-day funding window (`lab/xfund.py` `Daily.window`).
  - The identity guard needs 20 days of returns over 30 days.
  - So a pair waits about three weeks after the younger venue lists the coin.
- **Those are the widest days.** On Kraken-Hyperliquid (R508's window, 2026-11-20, descriptive), the absolute daily
  funding spread had a median of 128%/yr in the first 30 days after Kraken listed the contract (31 coin-days), and
  18%/yr after a year.
- **The mechanism (Q5).** He, Manela, Ross & von Wachter: funding passes the premium through a clamp, and thin new
  books make the premium large. Arbitrage capital is limited because each leg needs its own margin.
- **The owner, 2026-11-20:** "continue".

## Question
Does a book that trades only the listing phase of a coin on one venue, hedged on a venue that has traded it for at
least 30 days longer, earn a positive net return at R275's costs on Binance USD-M + Hyperliquid,
2023-06-01..2026-09-30?
- This is gate 0.
- A PASS earns a forward variant on the venues the owner can reach (Kraken, Hyperliquid, Aster), as a new id.

## Data
- **Venues:** Binance USD-M and Hyperliquid. Both histories hold delisted coins: Hyperliquid's 235 coins are its whole
  universe (56 delisted, checked against its meta on 2026-11-20).
- **Binance:** `data/fundingRate` and `data/klines_1h` (public data.binance.vision files, to 2026-09-30).
- **Hyperliquid:** `data/hyperliquid/funding` and `candles_1d` (rebuilt 2026-11-18).
- **Symbols:** R275's manifest as R439 carries it (`experiments/carry5_v1/symbols.csv`). 216 coins have both venues.
- **Pinned:** `data_manifest.json` holds the sha256 of all 864 price and funding files of those coins.
- **Spec:** `spec.toml`. The loaded window starts 2022-01-01, so listings from then on are dated; the book starts
  2023-06-01, and Hyperliquid's funding starts 2023-05-12.

## Rule (`scripts/run_xfund_listing.py`, `ListingBook` on `lab.xfund_v2`)
- **Ages.** A venue's age for a coin is its days of funding history through the day (1 on the first funding day).
- **Eligible pair on day d:**
  - the younger venue's age is 3 to 21 days;
  - the older venue's age exceeds the younger's by at least 30 days;
  - the younger venue's first funding day is at least 7 days after that venue's first funding day in the data (a
    venue's own launch is not a listing);
  - both prices are fresh on d and match within 5% up to a power-of-1000 multiplier (kPEPE against 1000PEPEUSDT).
- **Spread.** k = min(14, both ages) days, at least 3. The spread is the short venue's funding minus the long venue's,
  over (d - k, d], times 365 / k.
- **Entry:** spread at least the threshold; the widest first; one pair per coin; K slots.
- **Exit, the first of:**
  - the spread on the same window rule falls below half the threshold;
  - the younger venue's age passes 35 days (the phase ends);
  - the legs' price ratio moves more than 20% from entry (`xfund_v2`'s blowout rule);
  - a leg stops trading.
- **Accounting:** `xfund_v2`'s replay. Notional is set at entry prices, and funding is paid on it at marks. Net per day
  = (gross - cost x legs) / (2K).
- **Primary:** threshold 20%/yr, K = 10.
  - Four legs at 7 bp cost 28 bp a round trip. Held two weeks at 20%/yr, a pair earns about 77 bp.
  - K = 10 leaves room for the 2023 cluster of listings.
- **Secondary (reported, not decided):** threshold 10%/yr and 50%/yr, K = 10.
- **Costs:** 7 / 14 / 21 bp a leg (R275).

## Decision: R391's rule, as in R507, R508, R511 and R515, read on book days
- **Book days:** days the book holds a pair or pays a leg. The book is empty on many days, and an empty day is not
  evidence.
- **UNREADABLE:** fewer than 60 book days.
- **PASS:** all of these hold on book days:
  - the one-sided NW p (lag 10) of the 1x daily net is at most 0.05;
  - the 2x mean is above 0;
  - the 10% trimmed mean is above 0;
  - the mean without the two best coins is above 0.
- **FAIL:** otherwise.
- **Also reported:**
  - the calendar-day return at 1x/2x/3x;
  - the return per unit of capital in use;
  - by year, exits by reason, and trades by short venue.

## Power
- **Events.** 87 eligible listing events, counted from funding ages only on 2026-11-20 (no rate or price was read):
  - Hyperliquid listing, Binance established: 43 in 2023, 16 in 2024, 9 in 2025, 4 in 2026;
  - Binance listing, Hyperliquid established: 1, 9, 3 and 2.
- **Size of the effect needed.** At about 15 days a trade, a pair at 50%/yr earns about 2% gross against 28 bp of
  cost.
  - With 60-80 trades, NW t above 2 needs the per-trade net to be positive in most trades and not dominated by a few
    price blowouts.
- **Read with care.** A FAIL is informative only if trades were many. A PASS from a 2023 cluster alone is weak:
  the by-year rows say which.

## What the author has seen
- **Funding was loaded before, never in the phase.** Binance and Hyperliquid funding were read by R275, R437-R439 and
  other carry lanes. Their engines never entered a pair in its listing phase, and no listing-phase spread on this
  pair was computed.
- **On 2026-11-20 the session:**
  - computed the Kraken-Hyperliquid spread by listing age (above);
  - counted the events above from funding ages only.
- **Prices around listings:** R188/R189 read the returns of new Binance perps (a fade, NULL). That is the price leg's
  risk here, not the spread.

## Trials
- **This round:** 3 (the primary and the two reported thresholds).
- **Program trials:** 9,785,756 before, 9,785,759 after.

## Inputs
| File | sha256 |
|---|---|
| `scripts/run_xfund_listing.py` | c0d601be3a53b9a6dd1c81f84e645a7aec2416d1845f99db0df6ba0ae759c2c2 |
| `tests/test_xfund_listing.py` | 40d1cc3454931b8177916396495344ee4cb4e0299b8a87c7275952177a6a54d9 |
| `scripts/run_carry_v2_audit.py` | 1ba92fe3df40a0eac920e47c69ac4b7b9024750d4ba13f94edcfbe8f4550b7e5 |
| `scripts/run_xfund_bfx.py` | 62c1c214856c80b5006527824778815069cf341b740bb5d48c4d646364d30b79 |
| `lab/xfund.py` | d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d |
| `lab/xfund_v2.py` | fa85ef56885a1d6736dd92e73f8bce44e97ce9ee001739526caef86ae1ba62cd |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 |
| `experiments/xfund_listing_v1/spec.toml` | 05872d5d554ef4b34033f8380e2f7da584511b5b2b4855896a90e142fede596c |
| `experiments/carry5_v1/symbols.csv` | 22a91dc96cd04a4ac9dce5914d5fba5485f754088acef74f7efe03f10e8e0328 |
| `experiments/xfund_listing_v1/data_manifest.json` | a964ef4e58083aa0ceca10a023295aca5c54a633f5f43eec40d4ec7fa2a15524 |
