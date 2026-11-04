# PREREG: book_costs_v1, taker cost from public order books on dYdX, KuCoin and MEXC

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R404
- **Owner (single writer):** Claude (session claude/yo-9a1k5w); claimed on #7, comment 6640178334
- **Date registered (UTC):** 2026-11-04

## Question
What does a taker order of $1k, $5k and $10k cost per side on every listed perp of dYdX v4, KuCoin futures and MEXC
futures, as a function of the contract's 24 h volume? This is a measurement with 0 predictive trials. It decides
nothing alone; it is the cost input that M469 (the long-tail carry re-test on the M468 engine) needs. In the hidden-edge
audit, 54-56% of R277/R288 carry trades were in coins under $50k a day, where no book was ever measured.

## Universe
- **dYdX v4:** every perpetual with status ACTIVE in the indexer's `/v4/perpetualMarkets` at each snapshot. On
  2026-11-04, 57 of 296 markets were ACTIVE; the other 239 were FINAL_SETTLEMENT and have no book.
- **KuCoin futures:** every contract in `/api/v1/contracts/active` with status Open, linear (not inverse), quoted in
  USDT, and with no expiry date.
- **MEXC futures:** every contract in `/api/v1/contract/detail` settled in USDT, of type 1 (crypto) and in state 0
  (enabled).
- **Survivorship:** the universe is the current listing of each venue. Delisted coins cannot be measured; M469 must
  price them through the volume-band curve below and say so.

## Data
Public REST endpoints only. No key, no account, no order.

| Venue | Book | Depth read | Quantity unit | Fees |
|---|---|---|---|---|
| dYdX | `indexer.dydx.trade/v4/orderbooks/perpetualMarket/<ticker>` | full book as served | base | not served by the indexer: recorded as NaN |
| KuCoin | `api-futures.kucoin.com/api/v1/level2/depth100?symbol=<s>` | 100 levels | contracts x `multiplier` | `takerFeeRate`, `makerFeeRate` |
| MEXC | `contract.mexc.com/api/v1/contract/depth/<s>?limit=100` | 100 levels | contracts x `contractSize` | `takerFeeRate`, `makerFeeRate` |

24 h volume (USD) comes from dYdX `volume24H`, KuCoin `turnoverOf24h` and MEXC ticker `amount24`. Open interest is
converted to USD at the venue's oracle, mark or fair price.

Lighter is already measured hourly by `scripts/record_lighter_book.py` (data/recorders/lighter_book), and that
recorder is not changed. Binance futures answer HTTP 451 from this host; it is not worked around.

## Measurement
- **Recorder:** `scripts/record_book_costs.py`. It runs from the forward task graph (`lab/operations.py`, task R404)
  at every tick, and takes at most one snapshot per 3-hour UTC slot (00, 03, ... 21).
- **Output files:** `data/recorders/book_costs/<YYYY-MM-DD>/<HH>.parquet`. They are gitignored; their digests are
  committed by `record_digest.py`.
- **Pacing:** dYdX 0.25 s, KuCoin 0.2 s and MEXC 0.15 s between requests, the three venues in parallel. On HTTP 429
  the recorder waits, then retries at most twice.
- **Per book:**
  - best bid and ask, and the half-spread in bp of the mid;
  - per side and size `n` in {$1k, $5k, $10k}: `|average fill / mid - 1| x 1e4`, walking the shown levels from the
    best. It is NaN when the shown book holds less than `n`;
  - USD shown and USD within 1% of the mid, per side; level counts; 24 h volume; open interest; listed fees.
- **Rejected books:** an empty or crossed book gives no row. A market that fails is logged and the others continue.

## Summary (status.json, every run)
1. For each (venue, symbol), the side cost at size `n` is `(buy + sell) / 2` per snapshot. An unfilled side counts as
   infinite cost. Take the symbol's median over snapshots, and its median 24 h volume.
2. Put each symbol in a 24 h volume band: [0, 50k), [50k, 500k), [500k, 5M), [5M, inf) USD.
3. For each venue and band, report the median over symbols of the symbol medians at each size (none if that median
   is infinite), the share of symbols whose median is unfilled, and the median half-spread.

## Window and what is frozen for M469
- **Window:** from the first snapshot to 2026-11-18 00:00 UTC, about 110 snapshots if the host stays up. The
  recorder may keep running after that, but M469 uses only files whose slot starts before 2026-11-18 00:00 UTC.
- **Frozen input to M469:** the set of those files, by their digests in `experiments/recorders/journal/digests.csv`.
  M469's own PREREG must be frozen before any carry statistic. It takes its costs from these rows by this rule:
  - **Listed coin:** taker fee plus the symbol's median side cost at the leg's size.
  - **Coin no longer listed:** taker fee plus the venue-band median at the coin's trailing 30-day median daily quote
    volume at entry.
  - **Unfilled:** a coin or band whose median is unfilled is not tradeable at that size. M469 reports such trades
    apart and does not count them as zero cost.
  - **dYdX fee:** dYdX's published tier-1 taker fee, checked against its docs on the day M469 is frozen. The indexer
    does not serve fees.
  - **Primary size:** $1k a leg, in line with the small-stakes rule. $5k and $10k are capacity reads, all at 1x, 2x
    and 3x.
- **Not changed later:** neither the sizes, the bands nor the unfilled rule.

## Known limits (stated now)
- **Shown books only.** These are snapshots of shown books, not fills. Hidden size, queue and latency are not seen,
  and quotes can fade under a real order.
- **Today's books.** Applying today's cost-volume relation to 2024-2025 trades assumes it held then. M469 must say
  this, and should report the result by year.
- **dYdX volume collapse.** dYdX's current volume is a fraction of its history, so its bands are thin in symbols.
  Bands with fewer than 5 symbols are reported as such.
- **Host downtime.** The host can stop when the session is idle (2026-11-04 outages). Missing slots are missing; they
  are not filled in.

## Verdict
None. This round records a measurement (status DONE, verdict DATA_PASS if at least 40 snapshots with all three venues
were written in the window, else PARTIAL with the count).
