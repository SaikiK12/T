# PREREG: xfund_kaster_v1 (R511). R275's carry book on Kraken + Aster, decided on 31 coins whose funding nobody here has read

Freeze with `lab.prereg.freeze()` before any Aster price or funding inside the window is fetched. Never edited
afterwards; a changed idea is a new lane.

- **Registry id:** R511
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w`.
  - `scripts/run_xfund_kaster.py` is the only writer of `experiments/xfund_kaster_v1/results/` and `data/aster_hist/`.
- **Date registered (UTC):** 2026-11-19

**Methods:** M554 (new: R508's design gap, Kraken against a floored venue, on Aster). Carry family, candidate C13.
- **Paper only:** public endpoints, no key, no account; nothing in the code can place an order.

## Why this lane
- **The owner's requests of 2026-11-18 and 2026-11-19:** find openings for large or stable gains, and cut the waiting
  time.
- **R508's limit is capacity.** Its +24%/yr came from Kraken's thin perps, about $40k-100k of capital.
- **A research agent's venue scan (2026-11-19)** found that Aster lists many of Kraken's thin coins that Hyperliquid
  lacks.
  - Aster's funding is Binance-style, with the 0.01%/8 h interest term and a ±0.05% clamp (Aster docs).
  - Its perps terms (dated 2026-02-25) do not name France.
  - Its history is public and keyless.
- **It can be tested in days, on data nobody here has read.**

## Question
On Kraken's coins that R508 never read, does R275's carry book, unchanged, earn a positive net return at R275's
costs on Kraken + Aster, 2025-11-17..2026-11-15?
- A PASS replicates R508's mechanism on new coins and a new counter-venue.
- It earns a forward lane (a new id) that would add these coins to the paper book. It earns no money.

## Universe
- **Pairs.** Kraken `open` contracts paired with Aster USDT perpetuals that trade or are settling, by the symbol rule in
  `scripts/run_xfund_kaster.py`:
  - names match after a leading `1000000` or `1000` is dropped;
  - R508's `NOT_CRYPTO` bases are left out.
- **The frozen table:** `experiments/xfund_kaster_v1/symbols.csv`, 132 coins.
  - 101 are in R508's table (`in_r508`), so their Kraken funding was read.
  - **31 are not:** ALICE, ARC, BAT, BB, BICO, CFG, CHZ, DEXE, FLOW, GPS, IOTX, JASMY, LPT, LUNA2, MANA, MOVR,
    MUBARAK, NIGHT, ONT, OPEN, OPN, PORTAL, QNT, RIVER, ROSE, SOON, SPK, SYN, TLM, YFI, ZBT.
- **Survivorship.** Kraken's list is today's live contracts. Aster's SETTLING contracts are kept; its fully delisted
  ones are not.
- **Identity.** The engine's guard: 30-day correlation of daily returns ≥ 0.9, at least 20 days.

## Data
- **Kraken** (`data/kraken_hist/open`) and **Hyperliquid** (`data/hyperliquid`): held, rebuilt 2026-11-17..18. The 466
  files the table names are pinned by `data_manifest.json`.
- **Aster:** fetched after this freeze by `run_xfund_kaster.py fetch`, for 2025-11-01..2026-11-16 (exclusive end).
  - `fapi/v1/fundingRate` gives each settlement (intervals of 1, 4 or 8 h). `fapi/v1/klines` gives daily bars.
  - Each symbol gets a receipt with both files' sha256. `run` refuses any mismatch.
- **Volume:** about 132 symbols × 2-10 requests, at 0.25 s apart.

### Feature lineage
As in R508: daily closes from each venue's daily trade candles; settled funding summed over (d − 14, d]; spread
(short − long) × 365 / 14; the 30-day identity guard. All are point in time. The universe is today's lists.

## Rule
R275's rule by `lab.xfund`, R508's spec values: lookback 14 days, entry threshold 5%/yr, 20 slots. Exits under half
the threshold or on a stale leg. Costs are 7 bp a leg at 1x, with 2x and 3x.
- **Decided book:** kraken + aster on the 31 coins outside R508's table.
- **Reported, not decided:**
  - kraken + aster on all 132 coins;
  - kraken + hyperliquid + aster on all 132, the engine taking the widest eligible pair per coin;
  - 3x; halves; years; drawdown;
  - funding share; per-coin contributions; trades per long venue;
  - each venue's mean funding per coin.

## Decision (one candidate, alpha 0.05): R391's rule, as in R507 and R508
- **UNREADABLE:** fewer than 60 book days.
- **PASS:** all of these hold:
  - the one-sided NW p (lag 10) of the 1x daily net is at most 0.05;
  - the 2x mean is above 0;
  - the 10% trimmed mean is above 0;
  - the mean without the two best coins is above 0.
- **FAIL:** anything else.

## Power
- 31 coins in 20 slots, about 340 book days.
- In R508, coins trading under $100k a day on Kraken carried 97% of the return, at an annualised daily Sharpe of 7 for
  the book. If these coins behave alike, t would be well above 2.
- If the mechanism is specific to the coins R508 held, the book will be thin and FAIL. That is informative too.

## What the author has seen
- **Kraken.** R508 read the funding and prices of the 101 `in_r508` coins. R282 used Kraken funding as a panel factor
  for Binance returns (2025-10..2026-10). No per-coin Kraken funding of the 31 decided coins has been summarised here.
- **Aster.**
  - Contract metadata (`exchangeInfo`).
  - Three BTC funding rows after the window, 2026-11-17: 0.19-0.36 bp per 8 h.
  - One BTC daily bar pair after the window.
  - The research agent's snapshot of current funding and 24 h volumes (2026-11-19, after the window). Nothing inside
    the window was requested.
- **Hyperliquid:** as in R508.

## Trials
- **This round:** 1.
- **Program trials** before it: 9,785,751 (`registry.program_trials`); after it: 9,785,752.

## Order
1. This file, `symbols.csv` and `data_manifest.json` frozen, committed and pushed. A RUNNING registry row.
2. `python scripts/run_xfund_kaster.py fetch` (resumable).
3. `python scripts/run_xfund_kaster.py run`, once.
4. FINDINGS, with 1x/2x/3x against program trials, and the liquidity split R508 reported.

## Not checked before the freeze
- **Access.** Aster from France beyond its terms; it is authorised nowhere, like Hyperliquid.
- **Fees and fills.** Aster's fees (0 bp maker / 4 bp taker per its docs) and its books over the year.
- **Funding intervals.** Whether Aster's 1 h / 4 h / 8 h intervals changed during the window. Each settlement is summed
  as paid.

## Inputs
| File | sha256 |
|---|---|
| `scripts/run_xfund_kaster.py` | 605f8aeaaba73fb0f2beb68b1f0bd2ffdb65d6f12a5abeed0c6e61d2a87f0e45 |
| `tests/test_xfund_kaster.py` | 17becf1555a79384f9fc3eb80c513ec092d0f3142da0d07f0fe593aade6d6787 |
| `scripts/run_xfund_eea.py` | 4749ebbdca13106471c4f582e7b59a4e3f0ac893c388d46181e07615d618f9e5 |
| `scripts/run_xfund_bfx.py` | 62c1c214856c80b5006527824778815069cf341b740bb5d48c4d646364d30b79 |
| `scripts/fetch_bitfinex_history.py` | 424442fdec25bb5ed9112bc5333baa348499d7c9b029067202f2e0b4b4907baf |
| `lab/xfund.py` | d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 |
| `lab/venues.py` | ff6d80e23b337ee3c26ae44c718ba5893fb8e988fd23753631ddedd28b03e820 |
| `experiments/xfund_kaster_v1/symbols.csv` | c0d111aff76f6591f1e20af728a64347bb8e0e0adf75e3abce15ac198c6f10c7 |
| `experiments/xfund_kaster_v1/data_manifest.json` | 2be062753916d2f63a98fe4f296d0a2f7308b95f4ad476ef279845eea3aa2d25 |
