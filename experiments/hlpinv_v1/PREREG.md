# PREREG: hlpinv_v1 (R454). HLP's inventory as a cross-sectional perp signal

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a changed idea is a new lane.

- **Registry id:** R454
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w`.
  - `scripts/run_hlpinv.py` is the only writer of `experiments/hlpinv_v1/journal/`.
  - It runs weekly in `.github/workflows/claude-xperp-reads.yml`.
- **Date registered (UTC):** 2026-11-11

**Method:** M510. A new signal: it feeds no other lane's decision.
- **Paper only:** it reads files and public market data; nothing in the code can place an order.

## Question
Does HLP's net position in a coin, as a share of that coin's open interest, rank Hyperliquid's perps well enough to
pay for a hedged 72-hour book at executable costs? Two directions are tested:
- **Book F (follow HLP):** short the coins where HLP is most net short.
- **Book R (reverse):** short the coins where HLP is most net long.

## Why this lane
- The owner asked on 2026-11-11 to dig into the methods of HLP and LLP, the top deposits in the lab's ranking, and to
  do better than depositing.
- HLP's own edge is not open to a depositor's capital: spread capture as the venue's market maker, plus liquidation
  flow. Its inventory is public in real time.
  - HLP's child vaults make markets and take over liquidated positions, so their net position in a coin is roughly
    the other side of the crowd's net taker flow and of forced exits.
  - Hyperliquid keeps no history of a vault's positions, so the test can only be forward.
- **Prior from the lab:** R197 (CONFIRMED at gate 0) and R200 (forward, pending) found that crowd positioning ranks
  coins: their books short the coins where the crowd is long against the top accounts. Book F is the HLP analogue (the
  crowd long against HLP). R211 and R234 (other cuts of Binance's ratios) were NULL. No prior picks a direction for
  HLP, so both are tested.

## What the author has seen
- The API's field names (`vaultDetails`, `clearinghouseState`, `metaAndAssetCtxs`) and the recorder's first run in
  the session (2026-11-11 about 01:40 UTC):
  - HLP lists 7 child vaults; 354 position rows, 177 in each of two vaults.
  - These are counts only: no size, value, share, open interest or return was printed or read.
- A smoke run of `scripts/run_hlpinv.py` on synthetic snapshots and prices (random data, nothing from Hyperliquid).
- **Not seen:** any HLP size or share, any open interest or volume value, any return of either book.

## Data
- **Signal:** the data branch `claude/xyz-books-data`, folder `hlp/`, written hourly at :07 by
  `scripts/record_hlp_positions.py` (in `.github/workflows/claude-xyz-books.yml`) from 2026-11-11.
  - `positions/`: each child vault's signed size per coin and the response time.
  - `ctx/`: every listed main-dex perp's mark, open interest (coins) and 24 h notional volume at the run time.
- **Prices:** Hyperliquid's closed hourly candles and hourly funding settlements (public `candleSnapshot` and
  `fundingHistory`), fetched at read time into `journal/hl/` (one CSV a month, rows never rewritten).
- Returns are R448's (`scripts/run_flow_hl.py`, `hl_returns`): close-to-close less the funding a long pays at the next
  settlement.

## Rule
Constants are in `scripts/run_hlpinv.py`.
- **Runs:** positions belong to the run whose context is at most 10 minutes older. A run's snapshot time is its
  latest position time. A run with no positions is not a run.
- **Share** of a coin at a run: HLP's net size (summed over its child vaults) divided by the coin's open interest.
- **Eligible coins:** 24 h notional volume of $10M or more, open interest times mark of $2M or more, and a share.
- **Bins:** with n eligible coins, k = ceil(n / 8), one eighth of the coins.
  - F takes the k coins with the lowest share among those with share below 0.
  - R takes the k coins with the highest share among those with share above 0.
  - Ties go by coin name. A run needs at least 16 eligible coins, else it opens no slice.
- **Slices:** each bin coin gets a short slice of weight 1/k, held 72 hours. The weight stays 1/k when fewer than k
  coins qualify, so the book is then smaller.
  - A slice enters at the first hourly close at least 5 minutes after the snapshot.
  - Only the earliest run that enters at a given close opens slices. Slices start with snapshots from 2026-11-12.
  - A coin without a candle at the entry close is skipped.
- **Book:** slices are summed as R200's flow books (`lab/slices.py`): 1/72 of a unit per slice, so a full book is
  short about 1 unit.
  - The net short is hedged with an equal-weight long of the eligible coins of the latest run that have a close.
- **Costs:** 9 bp a one-way trade, main and hedge legs: Hyperliquid's tier-0 taker fee of 4.5 bp plus a margin for
  slippage. The lab's floor, as R451.
  - Reported at 1x, 2x and 3x.
- **Days:** a day's ticket is written once every hour of it has passed the recorder and its closes are stored.
  - Days from 2026-11-12 to 2026-11-14 are ramp (the book fills over 72 hours).
  - Days are counted from 2026-11-15, if at least 20 of its 24 hours opened a slice. Other days are thin: reported,
    not counted.
  - A snapshot cannot be recomputed later; a missed hour only skips one of 72 overlapping slices.

## Decision (per book, on counted days in calendar order)
1. **At 90 counted days:** futility screen. The book SURVIVES if its mean 1x daily net over the first 90 is above
   0; otherwise NULL (futility).
2. **At 365 counted days:** PASS when all of these hold over the first 365:
   - the 1x mean beats the placebo threshold;
   - the 1x mean is above 0;
   - the 2x mean is above 0;
   - the trimmed mean (top and bottom 10 days removed) is above 0.

   Otherwise NULL.
   - **Placebo threshold:** the 97.5% quantile (one-sided 2.5% per book, Bonferroni over the two books) of the same
     365-day 1x mean in 1,000 placebo books (seed 454).
   - Each placebo draws, on every row where the book opened slices, the same number of coins uniformly from that
     row's hedge basket, at the same weight, costs and hedge.
   - This null keeps the prices, their dependence across coins and hours, the turnover and the costs, and removes
     only the ranking.
3. **Stop rule:** a drawdown of 50% of capital in the summed counted daily nets stops the book.
   - A book that is NULL at the screen or hits the stop rule is closed: its decision is final, and later tickets
     are reported only.
4. A PASS earns a frozen paper lane with measured costs (a book-cost recorder on the main dex, as R453 for xyz). Then
   `lab.gate.go_real()` and the owner's own decision apply. Nothing here authorizes an order.

## Reported, not deciding
- Gross, cost, funding received and hedge return per day; gross exposure; hours that opened slices.
- Leave-two-coins-out mean gross; Newey-West t (10 lags); hit rate; worst day; maximum drawdown.
- All days, ramp and thin included, next to the counted ones.

## Power
- There is no archive, so the effect size is unknown.
- At one-sided 2.5% and 80% power, 365 days detect an annual Sharpe of about 2.8. A Sharpe of 2 needs about 716
  days, 1.5 about 1,273.
- The final read is therefore a futility screen for smaller effects. The 90-day screen only stops clearly losing
  books.

## Trials and reading
- **Two trials** (books F and R). The program total goes from 9,784,999 to 9,785,001.
- Read against `registry.program_trials()`.

## Limits
- **Execution:** one snapshot an hour, read minutes after the hour; entry at a later close than the snapshot.
- **Costs:** a flat 9 bp. Main-dex depth is not recorded; a large account pays more on small coins.
- **Shares:** HLP is one market maker among several. Its share measures the crowd's flow against HLP only.
- **Children:** HLP's child-vault list can change; the share sums every child listed at the run.
- **Delistings:** a delisted coin's later returns are missing and count as 0 while its slices remain (the lab's legacy
  missing-data rule in `lab/slices.py`).
- **Recorder:** GitHub's schedule can skip or delay hourly runs. Missed hours are counted per day and thin days are
  excluded.

## Stop rules
No new bins, horizons, costs or books after a result. A changed idea is a new lane.

```inputs
b842eec2ae944306f78184a3db329ff1e3fafbc24afcdccce44f0c0cf0419d2a scripts/run_hlpinv.py
3ce9270028f05bc56882f46ddd470a2f5a67f9cd807fb2517224bd5a9c55b17a tests/test_run_hlpinv.py
64f70363b8c41e5a1b7afca68405eb36828041667b1aa40e6c786c9c722b56ed scripts/record_hlp_positions.py
f9fe49b24ebf85b7144bd43cad14af386aa470adaacb4fe2631ee0be0c7fe1b5 scripts/record_xyz_books.py
a9b59625ba64010368e436a0259d8239674f5e361d671337dc499e7239e59fad scripts/record_okx_xperp.py
0c9b45bd4675d1f7177d09741fb1e65888214a9a30f4461f254310f6b45485f3 scripts/run_flow_hl.py
4b255a4da93acc25eacd06ed19659118485802577efbe2ccc97cca353d539a1f lab/slices.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 lab/stats.py
```
