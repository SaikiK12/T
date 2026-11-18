# PREREG: xfund_bfx_v1 (R507). R275's carry book on Binance + Bitfinex, a venue pair never read for carry

Freeze with `lab.prereg.freeze()` before any Bitfinex price or funding inside the window is fetched. Never edited
afterwards; a changed idea is a new lane.

- **Registry id:** R507
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w`.
  - `scripts/run_xfund_bfx.py` is the only writer of `experiments/xfund_bfx_v1/results/`.
  - Its `fetch` step is the only writer of `data/bitfinex_hist/`.
- **Date registered (UTC):** 2026-11-18

**Methods:** M552 (new: R275's cross-venue funding carry rule on a venue never read for carry). Carry family.
- **Paper only:** public endpoints, no key, no account; nothing in the code can place an order.

## Why this lane
- **The plan's one "weeks" replication** (`docs/reviews/plan_20261117.md` section 9). It asks for a replication of the
  carry rule on a venue never read for carry, frozen before its fetch. Of the venues probed on 2026-11-17, Bybit and
  BitMEX refuse this container, OKX keeps 3 months of funding, and Bitfinex keeps derivatives history.
- **The owner's request of 2026-11-17:** search wide, refine, and get more data to analyse.
- **The charter's three new rows a week.** This week already holds R499-R506, made at the owner's room-2 and
  parameter requests. This row is the plan's own replication, under the same owner request.

## Question
Does R275's carry book, unchanged, earn a positive net return at R275's costs on the never-read pair Binance + Bitfinex,
2021-01-01..2026-09-30?
- It is gate 1 "another venue" (`docs/GATES.md`): it tests whether the premium generalises.
- It does not validate the eight forward books.
- **Bitfinex's funding has a different design.** It has a dead zone: no payment while a period's average premium stays
  within ±`CLAMP_MIN` (5 bp), and only the excess beyond it is paid. So this also asks whether the rule survives a venue
  whose funding is mostly zero.

## What the author has seen
- **The Binance side is seen data.** R275 and many lanes read Binance's 2021-2026 prices and funding.
- **Bitfinex, inside the window: one slip, disclosed.**
  - While probing the format, an off-by-one-year timestamp returned 20 status rows of BTC on **2025-11-17,
    00:00-00:06 UTC**.
  - They showed a `CURRENT_FUNDING` of 0.0124% per 8 h and BTC near 94,300.
  - Nothing else from Bitfinex inside the window was requested or read.
- **Bitfinex after the window** (2026-11-01..07, and live metadata), read for format only:
  - **Status rows.** For BTC, ETH, SOL, DOGE, XRP, SUI and PEPE, one row about every minute, 480 rows per 8 h period.
    `CURRENT_FUNDING` is constant within a period.
  - **The funding rule.** The rate shown in the period after event E equals the period's accrual at E beyond ±5 bp,
    and 0 inside the band. Examples: BTC 6.10 → 1.10 bp; DOGE −6.70 → −1.71; PEPE 7.48 → 2.48.
  - **How often funding is zero.** SOL and SUI were zero in every period shown, XRP in all but one. BTC, PEPE and
    DOGE often were not.
  - **Candles, tickers and lists.** Hourly trade candles for BTC and ALG; today's tickers; the futures list (94 pairs,
    59 crypto USDt pairs after the filter); the currency map.
  - **Fees.** Bitfinex's fee page lists zero maker and taker fees on derivatives today.
  - A fetcher dry run on 2026-11-01..08 for BTC, DOGE and PEPE, into a scratch folder.
- **Stated before the fetch, from the design alone.**
  - Binance's funding sits at +0.01% per 8 h (about 11%/yr) when premiums are small, and Bitfinex's sits at 0. So a
    structural spread of about 11%/yr should appear on most coins.
  - The book would then be long Bitfinex and short Binance, near its 20 slots.
  - The question is whether the price legs and costs keep that spread. A persistent Bitfinex premium does not cost
    anything over a holding. A premium that closes while held does.

## Universe
- **Bitfinex coins.** The crypto USDt-margined perpetuals (`F0` pairs) on Bitfinex's futures list at the fetch
  (`fetch_bitfinex_history.is_crypto`). Excluded: index, FX, metal, oil and volatility contracts, test pairs, and
  pairs quoted in BTC.
- **Delisted pairs.** The frozen discovery rule in `scripts/run_xfund_bfx.py` adds them. For every Binance USD-M coin
  in the archive, Bitfinex's code for that coin is probed once for a candle inside the window.
- **Mapping to Binance.** Each code is mapped by the frozen alias rule (currency-map name, then 1000 and 1000000
  multiples).
- **Identity.** The engine's guard decides it day by day: 30-day correlation of daily returns ≥ 0.9, with at least
  20 days.
- **Survivorship.** A delisted pair whose code matches neither a Binance coin name nor Bitfinex's map is missed. The
  count of pairs found by discovery is reported.

## Data
- **Binance:** `data/klines_1h` (volume) and `data/fundingRate`, 2021-01-01..2026-09-30.
  - Rebuilt from data.binance.vision on 2026-11-17 after the container was replaced.
  - The klines match `docs/provenance/klines_1h.json` in hourly coverage for 900 of 901 files.
  - Funding has the same file set, but its bytes differ (parquet writer). Its rows were not checked one by one.
- **Bitfinex:** fetched after this freeze by `scripts/fetch_bitfinex_history.py`, from 2021-01-01 to 2026-10-01
  (exclusive). Into `data/bitfinex_hist/`:
  - `candles_1h/<CODE>.parquet`: trade candles; hours without a trade have none;
  - `funding/<CODE>.parquet`: one row per 8 h period, from the status history;
  - one receipt per pair with both files' sha256.
- **Funding booking.** The rate shown during (E − 8 h, E] is booked at E, never earlier. The exchange publishes it at
  the period's start, so the signal never uses it before it was public, whichever end of the period it is paid at.
  A period with no status row is a gap, not a zero.
- **Volume and time.** About 30,000 status requests of up to 5,000 rows each, roughly 30 GB transferred and about
  100 MB kept, at about 60 requests a minute (the limit is 90). About 10 hours, resumable page by page.
  - It runs under the owner's standing data approval (2026-10-20, "we need all data possible") and the request of
    2026-11-17.

### Feature lineage
| Feature | Parents | Source | Window and close rule | Known at decision? | Vintage |
|---|---|---|---|---|---|
| Daily close, fresh | hourly trade candles (Bitfinex), klines (Binance) | each venue's own trades | last traded close at or before 00:00 UTC; fresh when the hour ending then traded | yes | point in time (trade archives) |
| 14-day funding sum | Bitfinex `CURRENT_FUNDING` booked at each event E; Binance settled `rate` | Bitfinex status history; Binance archive | settlements in (d − 14, d] | yes: booked at E, published at E − 8 h | point in time (archived snapshots and settlements) |
| Spread | the two venues' 14-day sums | derived | (short venue sum − long venue sum) × 365 / 14 | yes | point in time |
| Identity guard | the two daily closes | derived | 30 days, at least 20 fresh pairs | yes | point in time |
| Universe | Bitfinex list at fetch + discovery | Bitfinex conf + candles | current list plus probed delisted codes | membership is today's list plus discovery | current survivors + discovered delisted |

## Rule
R275's rule, by `lab.xfund` (the Python twin of qx spread). Its parity with qx is checked by
`scripts/xfund_parity.py` and `tests/test_forward_xfund.py`. Spec values are R275's:
- **Set:** binance + bitfinex.
- **Primary book:** lookback 14 days, entry threshold 5%/yr, 20 slots (`L14d th5% K20`). This is R391's and R392's
  blind-replication book.
- **Secondary book (reported, not decided):** `L14d th10% K20`, R390 C14's threshold.
- **Mechanics.** Correlation guard 30 days, ≥ 0.9, 20 observations. Entries widest-first. Exits when the spread falls
  under half the threshold, or when a venue stops trading.
- **Costs:** 7 bp a leg at 1x (R275), with 2x and 3x. Bitfinex's fees are zero today, so 7 bp is conservative there
  unless its spreads are wide.

## Decision (one candidate, alpha 0.05): R391's rule
- **UNREADABLE:** fewer than 60 book days.
- **PASS:** all of these hold:
  - the one-sided p of the Newey-West t (lag 10) of the 1x daily net is at most 0.05;
  - the 2x mean daily net is above 0;
  - the 10% trimmed mean of the 1x daily net is above 0;
  - the 1x mean without the two coins whose trades added most is above 0.
- **FAIL:** anything else.

**Reported, never decided on:**
- the secondary book;
- 3x;
- halves and each year;
- the drawdown (running sum);
- the top-10-day share and the funding share;
- per-coin contributions and trades per long venue;
- per coin: Bitfinex's share of zero-funding periods and both venues' mean funding.

## Power
- R391 earned +2.48%/yr, NW t 3.90, over 526 days.
- At that Sharpe, 2,000 book days give t ≈ 7.6.
  - A FAIL is then informative: it says the rule does not carry to this pair.
  - A PASS says it does, for this venue's design.
- **What a PASS earns.**
  - Evidence that the premium generalises (gate 1 "another venue").
  - No money and no forward lane by itself: Bitfinex's access from France and its fills are unchecked.
  - Any forward lane would be a new frozen lane.

## Trials
- **This round:** 1.
- **Program trials** before it: 9,785,747 (`registry.program_trials('registry/rounds.csv')`); after it: 9,785,748.

## Order
1. This file frozen, committed and pushed. A RUNNING registry row.
2. `python scripts/run_xfund_bfx.py fetch`, restarted as needed. It verifies this file and every input below.
3. `python scripts/run_xfund_bfx.py run`, once. It refuses if results exist.
4. FINDINGS, with 1x/2x/3x read against program trials.

## Not checked before the freeze
- **Bitfinex execution.** Its fills, spreads and depth before 2026-11. Its access from France. Margin on two venues.
- **Funding timing.** Whether Bitfinex pays a period's rate at its start or its end. The booking above is
  conservative.
- **Discovery.** Delisted pairs under codes unrelated to the coin's name.
- **The Binance rebuild.** Its funding rows, one by one, against the original files.

## Inputs
| File | sha256 |
|---|---|
| `scripts/run_xfund_bfx.py` | 62c1c214856c80b5006527824778815069cf341b740bb5d48c4d646364d30b79 |
| `scripts/fetch_bitfinex_history.py` | 424442fdec25bb5ed9112bc5333baa348499d7c9b029067202f2e0b4b4907baf |
| `tests/test_xfund_bfx.py` | abe651feff8275d4b2cc1ad7293ef6bec6c37999d6dff430680b0434382edfba |
| `lab/xfund.py` | d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 |
