# PREREG: xfund_lt_v1 (R288). R275's best carry book on venue sets with Lighter, the zero-fee venue

Freeze with `lab.prereg.freeze()` before any Lighter price return or funding statistic is read. Never edited
afterwards; a change is a new lane.

- **Registry id:** R288 (Claude block R280-R299, claimed on issue #7 before the freeze)
- **Gate:** 0 in time (the archive window, here Lighter's 2025-01-17..2026-09-30). It is new evidence in venues: no
  lane has read Lighter's funding or prices.
- **Method:** M059 (cross-venue funding carry), venue replication. It is plan item 4 of `docs/VENUE_STRUCTURE.md`,
  which follows the prop trader's comment in `docs/COMMENT_DIG.md`: fee tiers were one of the three things that made
  their team money. Lighter's Standard account charges 0/0 fees, API included.
- **Source:**
  - R275 xfund_v1 (PARTIAL) and its best book by 1x t: **gate+hyperliquid L14d th5% K20**.
  - R277 xfund_kd_v1 replicated it on KuCoin (2 of 4 sets, PARTIAL). R278 and R279 trade R275's and R277's books
    forward on paper.
- **Execution mode:** API. Both legs are placed at the daily close on two venues.
- **Paper only.** Nothing here places an order, and no Lighter account exists (AGENTS.md rule 5).

## What the author has seen
- **R275 and R277 in full,** including R277's audit of the 2025-10-10 crash on dYdX.
- **Lighter**, from `scripts/fetch_venue_history.py lighter` and `scripts/record_lighter_book.py`:
  - the fetch log: contract counts and the route split (240 contracts, 195 with a Binance perp);
  - while testing the fetcher (2026-10-21): BTC's first and last rows and its count of long-paying and short-paying
    funding hours (13,023 and 2,372); hourly candle and funding counts for BTC;
  - one hour of Lighter books (costs per side, `docs/VENUE_STRUCTURE.md`).
- **Not computed on Lighter:** no funding rate level or spread, no return.
- **The symbol table** is built from file names and contract lists only (`scripts/lighter_table.py`).

## Inputs (frozen)

Filled at the freeze, after the Lighter fetch has finished:

```inputs
```

- **Engine:** the `qx spread` sources must be byte-identical to R275's frozen ones (the same hashes as in R275's and
  R277's inputs).
- **Symbol table:** Binance perps that Lighter lists, with each other venue's symbol from `lab.venues` (unchanged;
  it is pinned by R277 and R282). Lighter's long tail (no Binance perp) is reserved (`docs/GATES.md`) and never
  listed.

## The family (6 books, no other parameter)
- **Books:** sets binance+lighter, gate+lighter, hyperliquid+lighter, mexc+lighter, kucoin+lighter and
  dydx+lighter, each at lookback 14 days, entry threshold 5%/yr and 20 slots.
- **Engine:** `qx spread` (`experiments/xfund_lt_v1/spec.toml`).
- **Rule and accounting:** identical to R275:
  - daily axis at 00:00 UTC;
  - identity guard (correlation ≥ 0.9 over 30 days, at least 20 observations);
  - widest pair, entries widest first, exit below th/2;
  - net on total capital.
- **Costs: 5.5 / 11 / 16.5 bp per leg per side** (1x / 2x / 3x).
  - A two-venue book trades one leg on each venue at every entry and exit, so the engine's uniform cost per leg is
    the mean of the two venues' costs.
  - The non-Lighter leg is charged R275's 7 bp. The Lighter leg is charged 4 bp: no fee, plus the median cost of a
    $10k market order on R287's 37 coins in Lighter's books (one snapshot, `docs/VENUE_STRUCTURE.md`).
  - At 2x (11 bp) the book pays more per leg than R275 did at 1x. MEXC's API taker is 8 bp plus its spread (about
    8.7 bp), so the mexc+lighter set at 1x is about 0.85 bp per leg cheaper than it should be. Its 2x column covers
    that.
- **Lighter's venue entry:** hourly candles (`lighter_hist/open/candles_1h`, column `volume`) and hourly funding
  (`lighter_hist/open/funding`, column `rate`: Lighter's unsigned `rate` in percent per hour, divided by 100, positive
  when longs pay; Lighter's docs: "When the funding rate is positive, users with long positions pay a funding fee to
  users with short positions"). Bar hours 1. The other venues are as in R275 and R277.
- **Window:** 2021-01-01..2026-09-30 as R275; each set starts when Lighter's history does (2025-01-17), about 620
  days.

## Decision
- **A set replicates when all hold** (columns of `results/strategies.csv`):
  - `t_nw_1x` > 2.64 (Newey-West, 10 lags; two-sided p < 0.05/6);
  - `half1_bp` > 0 and `half2_bp` > 0;
  - `ann_2x_pct` > 0.
- **Lane verdict (registry):**
  - **CONFIRMED** (venue replication) if at least 4 of the 6 sets replicate;
  - **PARTIAL** if 1 to 3 replicate;
  - **NULL** if none does.
- **Reported, not decided on:**
  - the engine's own family gates (RC over the 6 books, RECENT, TRIM, HURDLE) and its `pass` column;
  - 1x / 2x / 3x annual net, by year, max drawdown, funding share, pairs held, trades, forced exits and the
    top-10-day share;
  - each set at R275's uniform 7 / 14 / 21 bp, from the same daily file (gross and legs), so the fee's share of the
    result is visible.
- **What a replication earns:** a replicating set whose venues the owner can use may get a forward paper lane (a new
  id). mexc+lighter is the one closest to the owner's account. Nothing else changes: R278 and R279 keep their frozen
  books.

## Audit, committed before the result
- **Sign and units:** Lighter's median BTC funding in 2025, annualized, is compared with Binance's. If it has the
  opposite sign, or differs by more than a factor of 10, the venue entry is wrong: this lane is void (registry row
  VOID with its trials) and a fixed one gets a new id.
- **Funding recomputed** from the raw files for 2 random trades per set; each must equal the engine's to 1e-8.
- **Concentration:** coins traded, and the top-5 and top-10 coins' share of the gross per set.
- **The 2025-10-10 crash:** the result is shown with and without 2025-10-10..12, post hoc, as R277 did. It decides
  nothing.

## Known limits (written before the result)
- **Short history:** about 620 days, against R275's 2,000. Each half is about 10 months.
- **Survivorship:** Lighter's contract list holds the markets on 2026-10-21, active or not. Markets it removed may be
  missing.
- **The engine is R275's**, with its known flaw: when one venue stops trading a coin, that leg's close is carried
  forward for a day while the other leg moves. A crash with a bad hourly print on one venue (2025-10-10, R277) books
  a round trip as profit or loss.
- **Lighter's cost** comes from one hour of books; the recorder builds a real model over two weeks. The Lighter leg's
  300 ms taker delay is not modelled (a daily book does not feel it).
- **Venue risk is not priced:** Lighter is an on-chain venue with a bridge.
- **Same ticker, different coin:** the correlation guard rejects such pairs. It is not proof of identity.
- **Not modelled (as R275):** liquidation above 1x, moving collateral, and fills at the close on two venues at once.

## Multiplicity
- Trials: 6.
- Program trials before this lane: those of `registry.program_trials()` at the freeze, stated in FINDINGS.
- The bar (NW t > 2.64) is Bonferroni over the 6 sets. The lane is a replication of R275, not a new search.
