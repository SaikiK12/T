# PREREG: xfund_eea_v1 (R508). R275's carry book on Kraken + Hyperliquid, a pair the owner could trade from France

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a changed idea is a new lane.

- **Registry id:** R508
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w`.
  - `scripts/run_xfund_eea.py` is the only writer of `experiments/xfund_eea_v1/results/`.
- **Date registered (UTC):** 2026-11-18

**Methods:** M553 (new: R275's cross-venue funding carry rule on Kraken + Hyperliquid). Carry family, candidate C13.
- **Paper only:** held public data; nothing in the code can place an order.

## Why this lane
- **The owner's request of 2026-11-18:** find an opening for large or stable gains.
- **R507 (2026-11-18)** found that a venue whose funding has an interest floor, set against one without it, carried
  +5.21%/yr at 1x over 2021-2026 (Binance + Bitfinex), every year positive. Bitfinex's access from France is not
  established, so that pair has no lane.
- **The same design gap between two venues the lab treats as reachable from France:**
  - **Hyperliquid** (official funding docs, read 2026-11-18): F = average premium + clamp(0.01%/8 h − premium, ±0.05%),
    paid hourly. The interest term floors funding at 0.00125%/h, about 11%/yr, while premiums are small.
  - **Kraken Futures** linear perps (`PF_*`, offered to EEA clients): an hourly time-weighted premium with no interest
    term in the public specifications. Paid hourly; a negative rate is paid by shorts (Kraken EEA product sheet).
  - So, from the design alone: the book should be mostly long Kraken and short Hyperliquid.
- **Kraken was never in a cross-venue carry book.** R275's venues were Binance, Gate, Hyperliquid and MEXC. R277 added
  KuCoin and dYdX, R288 Lighter, R507 Bitfinex.

## Question
Does R275's carry book, unchanged, earn a positive net return at R275's costs on Kraken + Hyperliquid, over the year
Kraken serves (2025-11-17..2026-11-15)?
- It is gate 1 on a pair the owner could trade.
- A PASS earns a frozen forward paper lane (a new id), with costs measured from live books. It earns no money.

## What the author has seen
- **Kraken.**
  - R418 (2026-11-06) read PF_XBTUSD and PF_ETHUSD funding and prices, 2025-12-01..2026-11-01, for a spot-perp
    carry. It reported net returns on funded capital between −0.6% and +1.8%/yr at 1x.
  - R282 (2026-10-21) used Kraken funding, 2025-10..2026-10, as a factor for Binance returns.
  - On 2026-11-18, while checking the rebuild, I printed PF_XBTUSD's last three funding rows and daily candles. All are
    after this window: funding 2026-11-18 00:00-02:00, values about ±1e-6 an hour; candles opening 2026-11-15..17.
  - No other Kraken price or rate was read. No funding of any other Kraken contract was ever summarised.
- **Hyperliquid.**
  - R275's family read Hyperliquid funding and prices through 2026-09-30 against Binance, Gate and MEXC, never against
    Kraken.
  - On 2026-11-18 I printed BTC funding's first and last timestamps and its row count, not its values.
- **Code.** The symbol rule and the manifest read contract lists and file names only. The tests use synthetic data.

## Universe
- **Pairs.** Kraken `open` contracts paired with Hyperliquid coins by the symbol rule in `scripts/run_xfund_eea.py`:
  - names match after Hyperliquid's k-prefix becomes `1000` and a leading `1000000` or `1000` is dropped;
  - bases in `NOT_CRYPTO` are left out (metals, energy, equities and ETFs, stablecoins, gold tokens);
  - both venues need a daily candle file and a funding file.
- **The frozen table:** `experiments/xfund_eea_v1/symbols.csv`, 111 coins. Kraken's `reserved/` long tail is not read.
- **Survivorship.** Kraken's list is today's live contracts: a perp Kraken delisted during the year is missing. The
  bias is reported, not corrected.
- **Identity.** The engine's guard decides it day by day: 30-day correlation of daily returns ≥ 0.9, at least 20 days.

## Data
- **Kraken:** `data/kraken_hist/open/funding` (the venue's hourly relative rate, a fraction of notional per hour) and
  `data/kraken_hist/open/candles_1d`.
  - Rebuilt 2026-11-17..18 by `scripts/fetch_venue_history.py kraken`.
  - The funding API serves the last year only. The rebuilt files start 2025-11-17 09:00 UTC.
- **Hyperliquid:** `data/hyperliquid/funding` (hourly rate) and `data/hyperliquid/candles_1d`.
  - Rebuilt 2026-11-17..18 by `scripts/fetch_hyperliquid_history.py`.
- **Pinned.** `experiments/xfund_eea_v1/data_manifest.json` holds the sha256 of all 444 files the table names. `run`
  refuses if any differs.
- **Window:** 2025-11-17..2026-11-15, inclusive days. The book starts when a coin first has 14 days of funding and 20
  days of the guard on both venues.

### Feature lineage
| Feature | Parents | Source | Window and close rule | Known at decision? | Vintage |
|---|---|---|---|---|---|
| Daily close, fresh | daily trade candles, both venues | each venue's own trades | the candle ending at 00:00 UTC; fresh when it traded | yes | point in time (venue archives) |
| 14-day funding sum | each venue's hourly settled rate | Kraken historical funding; Hyperliquid funding history | settlements in (d − 14, d] | yes: settled before d's close | point in time (settlement records) |
| Spread | the two 14-day sums | derived | (short venue − long venue) × 365 / 14 | yes | point in time |
| Identity guard | the two daily closes | derived | 30 days, at least 20 fresh pairs | yes | point in time |
| Universe | Kraken's live list, Hyperliquid's coins | venue contract lists | today's lists | membership is today's | current survivors |

## Rule
R275's rule, by `lab.xfund` (the Python twin of qx spread, parity-tested by `scripts/xfund_parity.py`). Spec values are
R275's, as in R507:
- **Set:** kraken + hyperliquid. Both price files are daily candles (bar 24 h).
- **Primary book:** lookback 14 days, entry threshold 5%/yr, 20 slots (`L14d th5% K20`).
- **Secondary book (reported, not decided):** `L14d th10% K20`.
- **Mechanics.** Correlation guard 30 days, ≥ 0.9, 20 observations. Entries widest-first. Exits when the spread falls
  under half the threshold, or when a venue stops trading.
- **Costs:** 7 bp a leg at 1x (R275), with 2x and 3x.
  - Today's taker fees: Kraken EEA tier 1 perps 0.05% (R418), Hyperliquid base tier 0.045%.
  - So 1x leaves about 2 bp a leg for spread. 2x and 3x cover wider books.

## Decision (one candidate, alpha 0.05): R391's rule, as in R507
- **UNREADABLE:** fewer than 60 book days.
- **PASS:** all of these hold:
  - the one-sided p of the Newey-West t (lag 10) of the 1x daily net is at most 0.05;
  - the 2x mean daily net is above 0;
  - the 10% trimmed mean of the 1x daily net is above 0;
  - the 1x mean without the two coins whose trades added most is above 0.
- **FAIL:** anything else.

**Reported, never decided on:**
- the secondary book and 3x;
- halves and each month;
- the drawdown (running sum);
- the top-10-day share and the funding share;
- per-coin contributions and trades per long venue;
- each venue's mean funding per coin.

## Power
- R507's book had an annualised daily Sharpe of 3.7. Over about 330 book days that gives t ≈ 3.4, which would pass.
- At Sharpe 1.5, t ≈ 1.4: a FAIL then says the pair carries too little to read in one year, not that it carries
  nothing.
- The window is one year because Kraken serves no older funding. A FAIL does not test longer horizons.

## Trials
- **This round:** 1.
- **Program trials** before it: 9,785,748 (`registry.program_trials('registry/rounds.csv')`); after it: 9,785,749.

## Order
1. This file, `symbols.csv` and `data_manifest.json` frozen, committed and pushed. A RUNNING registry row.
2. `python scripts/run_xfund_eea.py run`, once. It refuses if results exist.
3. FINDINGS, with 1x/2x/3x read against program trials.

## Not checked before the freeze
- **Kraken's funding formula.** The public pages show no interest term, but its worked examples disagree on scaling.
  The data's rate is read as Kraken settles it: a fraction of notional per hour.
- **Access.** Kraken EEA derivatives for this account (eligibility, leverage caps for EU retail). Hyperliquid from
  France (a DEX; the lab already treats it as reachable).
- **Execution.** Kraken's and Hyperliquid's spreads and depth for the long tail over the year. Margin on two venues.
- **Missing Kraken hours.** R418 found 5 of 8,040 hourly BTC/ETH rates missing. A missing hour adds nothing to a sum.

## Inputs
| File | sha256 |
|---|---|
| `scripts/run_xfund_eea.py` | 4749ebbdca13106471c4f582e7b59a4e3f0ac893c388d46181e07615d618f9e5 |
| `tests/test_xfund_eea.py` | 69f46619ea3383d10ff368a00608a1ac54d90c0058296e62d9a63c4a88954930 |
| `scripts/run_xfund_bfx.py` | 62c1c214856c80b5006527824778815069cf341b740bb5d48c4d646364d30b79 |
| `scripts/fetch_bitfinex_history.py` | 424442fdec25bb5ed9112bc5333baa348499d7c9b029067202f2e0b4b4907baf |
| `lab/xfund.py` | d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 |
| `lab/venues.py` | ff6d80e23b337ee3c26ae44c718ba5893fb8e988fd23753631ddedd28b03e820 |
| `experiments/xfund_eea_v1/symbols.csv` | cf942d8f7e9235e5af3956b627d3edf06633f29f57c184a02670510b751975c0 |
| `experiments/xfund_eea_v1/data_manifest.json` | 977f1f4df7ad4dcd4a03dc9b1ca7a0264ddc01274aa2f7e648703ccc214afe5d |
