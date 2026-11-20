# PREREG: hip3gap_v1 (R518). R275's carry book between HIP-3 dexes whose funding designs differ for the same ticker

Freeze with `lab.prereg.freeze()` before any cross-dex spread is computed. Never edited afterwards.

- **Registry id:** R518
- **Owner (single writer):** the Claude session that froze it. `scripts/run_hip3gap.py` is the only writer of
  `experiments/hip3gap_v1/results/`.
- **Date registered (UTC):** 2026-11-20

**Methods:** M559 (new: the funding-design gap between HIP-3 deployers). Carry, candidate C13.
- **Paper only:** public data; nothing can place an order.

## Why
- **The design is the deployer's.** Hyperliquid's "HIP-3 deployer actions" (read 2026-11-20) let each deployer set,
  per asset:
  - a funding multiplier (0-10);
  - an 8-hour interest rate (-0.01..0.01);
  - a clamp (default 0.0003).
- **Designs on 2026-11-20** (`perpDexs`, the public API):

  | Dex | Design |
  |---|---|
  | trade.xyz | multiplier 0.5 on 138 of 147 markets |
  | Felix | 0 on 15 of 16 |
  | Dreamcash | 0.000001 on all 17 |
  | Kinetiq | default multiplier, with 8 h interest 0.0000457 (about 5%/yr) on 20 of 23 |
  | mkts | the default (0.01%/8 h, about 11%/yr) on most |
  | Paragon | 0.6 on 30 of 40 |
  | EntropyIO | 0.5 on 13, 0.125 on 4, default on the rest |

  - The same stock (GOOGL: xyz, Kinetiq, Dreamcash, mkts, EntropyIO) can cost a long nothing on one dex and the
    whole floor on another.
- **The analogue.** This is R507/R508's design gap (Kraken has no interest term; Hyperliquid has the floor), which
  passed on two pairs.
- **Reach.** Both legs sit under one Hyperliquid wallet, so no broker and no second venue are needed.
- **Why it may fail.**
  - Designs may have changed over the year (only today's were read).
  - A zero-funding perp has nothing anchoring its price to the oracle, so the long leg may carry a premium that
    decays.
  - R470's two-oracle price noise applies.

## Question
Does R275's carry book, unchanged, earn a positive net return at R275's costs between HIP-3 dexes listing the same
ticker, over R517's data (2025-10-01..2026-11-20, the book from its first eligible day)?
- This is gate 0.
- A PASS earns a forward lane on the same dexes, as a new id.

## Data
- **Source:** R517's fetch (`scripts/fetch_hip3list.py`, frozen in R517) into `data/hip3list`. It is running at
  this freeze. The run verifies its `manifest.json` first.
- **Loader:** R517's frozen loader (`run_hip3list.universe`): daily closes from 4-hour candles; hourly funding.
- **Universe:** every HIP-3 market whose base is on at least two dexes (R517's universe), delisted ones included.

## Rule (`scripts/run_hip3gap.py`)
- **R275's rule on `lab.xfund_v2`:**
  - lookback 14 days, entry 5%/yr, exit below half;
  - 20 slots, the widest pair first;
  - correlation guard 30 days >= 0.9 on 20 observations;
  - `xfund_v2`'s blowout (20% ratio move) and dead-leg exits.
- **Venues:** every dex in the universe.
- **Costs:** 7 / 14 / 21 bp a leg. HIP-3 fees are near Hyperliquid's (about 4.5 bp taker), plus spread on thin books.
- **The only trial:** this book. Nothing else is decided.

## Decision: R391's rule on book days, read by R516's `report` and R507's `decide`
- **UNREADABLE:** fewer than 60 book days.
- **PASS:** all of these hold:
  - the one-sided NW p (lag 10) of the 1x daily net is at most 0.05;
  - the 2x mean is above 0;
  - the 10% trimmed mean is above 0;
  - the mean without the two best coins is above 0.
- **FAIL:** otherwise.
- **Also reported:**
  - calendar-day %/yr against cash (about 4%/yr);
  - net by dex pair;
  - by year and exits.

## Power and supply
- **Supply.** 45 bases are on two or more dexes, most for months, so the book is not short of pairs.
- **The gap's size.** A floor gap of about 5-11%/yr on a stock is 2.5-5.5%/yr on two-leg capital unlevered, before
  costs. A PASS then needs the premium spreads above that, or few trades.
- **The window.** The book's window is about 10 months: enough book days.

## What the author has seen
- Today's funding designs (above).
- R517's counts of listings by month, from first funding timestamps.
- **Funding of these markets, read before:**
  - R475/R476 read US-stock funding on every HIP-3 dex for a single-dex trailing rule;
  - R470 read xyz against Lighter;
  - R479 runs forward.
  - No cross-dex spread was computed.
- **Order of reads:** R517 (listing phase) will be read before this lane. Its trades are a different phase of the
  same series. This PREREG is frozen before R517 runs.

## Trials
- **This round:** 1.
- **Program trials:** 9,785,760 before, 9,785,761 after.

## Inputs
| File | sha256 |
|---|---|
| `scripts/run_hip3gap.py` | 1410c9186cce65a165b2ab9c3de0f320ccc65a91e3a23f5d2e3a33e325c0e56e |
| `tests/test_hip3gap.py` | 9ece2302fdeb59ed68fd10deefd70288a699630e062dc6d4efef58252f26b609 |
| `scripts/run_hip3list.py` | 53bedabb5368e621aed5684b17524b84ff123782685b214475130e64d52f2ea9 |
| `scripts/fetch_hip3list.py` | 374bda4e82a5d4c73b8ff1e8734ec2789b0cf9ff584cd8853cb845aa537bf2ca |
| `scripts/run_xfund_listing.py` | c0d601be3a53b9a6dd1c81f84e645a7aec2416d1845f99db0df6ba0ae759c2c2 |
| `scripts/run_xfund_bfx.py` | 62c1c214856c80b5006527824778815069cf341b740bb5d48c4d646364d30b79 |
| `lab/xfund.py` | d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d |
| `lab/xfund_v2.py` | fa85ef56885a1d6736dd92e73f8bce44e97ce9ee001739526caef86ae1ba62cd |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 |
