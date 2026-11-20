# PREREG: hip3list_v1 (R517). R516's listing-phase carry, unchanged, between HIP-3 dexes that list the same ticker

Freeze with `lab.prereg.freeze()` before the data are fetched. Never edited afterwards.

- **Registry id:** R517
- **Owner (single writer):** the Claude session that froze it. `scripts/fetch_hip3list.py` is the only writer of
  `data/hip3list/`, and `scripts/run_hip3list.py` the only writer of `experiments/hip3list_v1/results/`.
- **Date registered (UTC):** 2026-11-20

**Methods:** M558 (new). Carry, candidate C13; a transfer of M557 (R516) to where new books still appear.
- **Paper only:** public data; nothing can place an order.

## Why
- **Where R516 left off.** R516 passed: +1.76% net per trade. But Binance + Hyperliquid listing events fell from 43
  (2023) to 6 (2026), so supply was the binding fact.
- **HIP-3 still opens new books.**
  - Hyperliquid's builder-deployed dexes started 15-30 new markets a month through 2026: 54 in January, 30 in August,
    20 in October (first funding timestamps, 332 markets on 11 dexes).
  - Many tickers appear on several dexes: TSLA, NVDA, GOLD and others on xyz, Kinetiq, Dreamcash, EntropyIO, Felix
    and Paragon.
- **Reach.** Both legs are on Hyperliquid, under one wallet, with no broker. The owner can reach it.
- **Why it may fail.**
  - R470 (trade.xyz vs Lighter on the same stocks, established phase) was NULL: +3.6%/yr of funding, with price noise
    between two oracles.
  - The listing phase is what R470 never isolated.

## Question
Does R516's listing-phase book, unchanged except for `LAUNCH_GAP`, earn a positive net return at R275's costs
between HIP-3 dexes, 2025-11-15..2026-11-20?
- This is gate 0.
- A PASS earns a forward lane (a new id) on the same dexes.

## Data (fetched after this freeze)
- **Fetch:** `python scripts/fetch_hip3list.py --end 2026-11-20 --out data/hip3list`, once.
- **Source:** Hyperliquid's public info API (perpDexs, meta, fundingHistory, 4-hour candleSnapshot), through R475's
  frozen client.
- **Universe:** every HIP-3 market, delisted ones included, whose base (the name after "dex:") is on at least two
  dexes. Spellings are not merged: US500 and USA500 stay apart. The main dex is not included.
- **Pinned:** the fetch writes `manifest.json` with every file's sha256, and the run verifies it first.
- **Daily series:** closes from 4-hour candles (fresh when a bar with volume ended in the day), and hourly funding
  summed per day (`lab.xfund_v2.load_daily`).

## Rule
- **R516's `ListingBook` and constants** (`scripts/run_xfund_listing.py`, frozen in R516):
  - younger venue's funding age 3-21 days at entry;
  - older venue at least 30 days ahead;
  - funding window min(14, ages), at least 3 days;
  - prices within 5% (a power-of-1000 multiplier allowed);
  - exit at half the threshold, at the younger venue's age 35, on a 20% ratio blowout, or when a leg stops trading.
- **The one change: `LAUNCH_GAP` = 0.**
  - On Binance + Hyperliquid, a venue's first funding day in the data was its data start.
  - A HIP-3 dex's launch day opens real new books, so its first markets count as listings.
- **Venues:** every HIP-3 dex in the universe. Each pair of dexes listing a base is eligible; the widest
  eligible pair is taken.
- **Primary (the only trial):** threshold 20%/yr, K = 10, costs 7 / 14 / 21 bp a leg.
  - Hyperliquid's HIP-3 fee is about 1x-2x the main dex's 4.5 bp taker, plus spread on new books, so 1x is light.
    The 2x and 3x lines matter.

## Decision: R391's rule on book days, as in R516
- **UNREADABLE:** fewer than 60 book days.
- **PASS:** all of these hold:
  - the one-sided NW p (lag 10) of the 1x daily net is at most 0.05;
  - the 2x mean is above 0;
  - the 10% trimmed mean is above 0;
  - the mean without the two best coins is above 0.
- **FAIL:** otherwise.
- **Also reported:**
  - calendar-day %/yr against cash (about 4%/yr);
  - return on capital in use;
  - by year, exits, and short venues.

## Supply and power (counted before the freeze from first funding timestamps only)
- **Events.** 44 cases where a dex listed a ticker that another dex had listed at least 30 days earlier:
  - 15 in 2026-01, 5 in 02, 2 in 03, 1 in 04;
  - 2 in 07, 4 in 08, 3 in 09, 6 in 10, 6 in 11.
- **By younger dex:** EntropyIO 11, Dreamcash 10, Kinetiq 9, xyz 5, mkts 4, Felix 2, Paragon 2, HyENA 1.
- **Not all are tradable:**
  - HyENA closed in August 2026 (news reports, read 2026-11-20);
  - some names are commodities, FX or indices; the price check removes mismatches.
- **Power.**
  - At R516's +1.76% a trade and its spread of outcomes, 40 trades give t ≈ 3.
  - At R470's thin stock spreads (median 13.7%/yr), few pairs reach 20%/yr and the lane may be UNREADABLE.

## What the author has seen
- **Funding of these markets:**
  - R475 and R476 read US-stock funding of every HIP-3 dex for their trailing 28-day rule;
  - R470 read xyz and Lighter;
  - R479 runs forward.
  - None of them computed a cross-dex spread in the listing phase.
- **To count listings (2026-11-20), the session fetched each market's first fundingHistory page.** Up to 500 hourly
  rates were in memory; only the first timestamp was kept and printed.
- **News:** HyENA's shutdown, from search snippets.

## Trials
- **This round:** 1.
- **Program trials:** 9,785,759 before, 9,785,760 after.

## Inputs
| File | sha256 |
|---|---|
| `scripts/fetch_hip3list.py` | 374bda4e82a5d4c73b8ff1e8734ec2789b0cf9ff584cd8853cb845aa537bf2ca |
| `scripts/run_hip3list.py` | 53bedabb5368e621aed5684b17524b84ff123782685b214475130e64d52f2ea9 |
| `tests/test_hip3list.py` | 0df15927dce8090f4ac9bd8d87d595fbc6e426cc199ab9cfc9a0b72a8790fd80 |
| `scripts/run_xfund_listing.py` | c0d601be3a53b9a6dd1c81f84e645a7aec2416d1845f99db0df6ba0ae759c2c2 |
| `scripts/run_xfund_bfx.py` | 62c1c214856c80b5006527824778815069cf341b740bb5d48c4d646364d30b79 |
| `scripts/fetch_hip3stock.py` | 04c45090be4113b9d9cf7d3c21c534ae8200363da3e5d4d55fe5a528801fdb9b |
| `lab/xfund.py` | d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d |
| `lab/xfund_v2.py` | fa85ef56885a1d6736dd92e73f8bce44e97ce9ee001739526caef86ae1ba62cd |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 |
