# PREREG: llpinv_v1 (R455). Lighter LLP's inventory as a cross-sectional perp signal

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a changed idea is a new lane.

- **Registry id:** R455
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w`.
  - `scripts/run_llpinv.py` is the only writer of `experiments/llpinv_v1/journal/`.
  - It runs weekly in `.github/workflows/claude-xperp-reads.yml`.
- **Date registered (UTC):** 2026-11-11

**Method:** M511. A new signal: it feeds no other lane's decision.
- **Paper only:** it reads files and public market data; nothing in the code can place an order.

## Question
Does LLP's net position in a Lighter perp, as a share of that market's open interest, rank Lighter's perps well
enough to pay for a hedged 72-hour book at executable costs? This is R454's rule (HLP on Hyperliquid, frozen
`9df27190…`) applied unchanged to Lighter's pool and Lighter's prices. Two directions are tested:
- **Book F (follow LLP):** short the markets where LLP is most net short.
- **Book R (reverse):** short the markets where LLP is most net long.

## Why this lane
- The owner asked on 2026-11-11 to dig into the methods of HLP and LLP, the top deposits in the lab's ranking, and to
  do better than depositing, with real trading that matches the paper.
- LLP is Lighter's protocol pool: it makes markets and takes over liquidations, as HLP does on Hyperliquid. Its own
  edge (spread capture, liquidation flow) is not open to a depositor's capital; its inventory is public in real time.
  - Lighter's `account` endpoint lists LLP's positions now but keeps no history, so the test can only be forward.
- R454 tests the same idea on HLP. Lighter is a second venue with its own crowd and its own pool, read on the same
  calendar, so the two lanes are separate evidence, not a replication of one sample.
- Lighter does not exclude France (`docs/reviews/venue_access_fr_20261110.md`), so a PASS could be traded as the
  paper is.
- **Prior from the lab:** as R454 (R197 and R200: crowd positioning ranks coins; R211 and R234 NULL). No prior picks a
  direction for LLP, so both are tested.

## What the author has seen
- The API's field names (`account`, `orderBookDetails`) and two recorder runs on 2026-11-11, both before this freeze:
  - a smoke run in the session, into a scratch folder: 199 position rows, 243 perp markets, market status values `active`
    (209) and `inactive` (34), position sign values 1 and -1;
  - the first GitHub run (claude-xyz-books.yml, 02:16 UTC): files of 199 position rows, 243 market rows and one
    account row, by line count.
  - These are counts and categories only: no size, value, share, open interest, volume or return was printed or read.
- A smoke run of `scripts/run_llpinv.py` on synthetic snapshots and prices (random data, nothing from Lighter).
- **Not seen:** any LLP position or share, any open interest or volume value, any return of either book.

## Data
- **Signal:** the data branch `claude/xyz-books-data`, folder `llp/`, written hourly at :07 by
  `scripts/record_llp_positions.py` (in `.github/workflows/claude-xyz-books.yml`) from 2026-11-11.
  - `positions/`: LLP's non-zero positions per market (sign, size, value in USD) at the run time.
  - `markets/`: every listed Lighter perp's status, mark price, open interest in USD and 24 h quote volume at the run
    time.
  - `accounts/`: one row per run (the pool's equity and share count).
- **Prices:** Lighter's closed hourly candles and hourly funding settlements (public `candles` and `fundings`, read by
  `lab/carrylane.py` under its machine-wide pace of one request per 1.1 s), fetched at read time into `journal/px/`
  (one CSV a month, rows never rewritten).
- Returns are R448's and R454's (`scripts/run_flow_hl.py`, `hl_returns`): close-to-close less the funding a long pays
  at the next settlement, with Lighter's funding signed as the archive (+ when longs pay).

## Rule
R454's rule, imported unchanged from `scripts/run_hlpinv.py` (bins, slice rows, book, costs, days, placebo and
looks). Only the snapshot table and the prices are Lighter's; their constants are in `scripts/run_llpinv.py`.
- **Runs:** a run is a recorder time with an accounts row. Its positions and markets carry the same time, so a run's
  snapshot time is the run time.
- **Share** of a market at a run: LLP's signed position value (sign times value, USD) divided by the market's open
  interest in USD. A market where LLP holds nothing has share 0.
- **Eligible markets:** status active, 24 h quote volume of $10M or more, open interest of $2M or more in USD, a mark
  price above 0 and a share. Every Lighter perp market is a candidate, as listed at the run.
- **Bins:** with n eligible markets, k = ceil(n / 8), one eighth of the markets.
  - F takes the k markets with the lowest share among those with share below 0.
  - R takes the k markets with the highest share among those with share above 0.
  - Ties go by symbol. A run needs at least 16 eligible markets, else it opens no slice.
- **Slices:** each bin market gets a short slice of weight 1/k, held 72 hours. The weight stays 1/k when fewer than k
  markets qualify, so the book is then smaller.
  - A slice enters at the first hourly close at least 5 minutes after the snapshot.
  - Only the earliest run that enters at a given close opens slices. Slices start with snapshots from 2026-11-12.
  - A market without a candle at the entry close is skipped. A symbol Lighter no longer lists gets no closes.
- **Book:** slices are summed as R200's flow books (`lab/slices.py`): 1/72 of a unit per slice, so a full book is
  short about 1 unit.
  - The net short is hedged with an equal-weight long of the eligible markets of the latest run that have a close.
- **Costs:** 9 bp a one-way trade, main and hedge legs, as R454. Lighter's Standard accounts pay no fee; the 9 bp is
  the lab's floor for spread and slippage, kept so the two venues are read at the same cost.
  - Reported at 1x, 2x and 3x.
- **Days:** a day's ticket is written once every hour of it has passed the recorder and its closes are stored.
  - Days from 2026-11-12 to 2026-11-14 are ramp (the book fills over 72 hours).
  - Days are counted from 2026-11-15, if at least 20 of its 24 hours opened a slice. Other days are thin: reported,
    not counted.

## Decision (per book, on counted days in calendar order)
R454's looks, with this lane's own placebo seed.
1. **At 90 counted days:** futility screen. The book SURVIVES if its mean 1x daily net over the first 90 is above
   0; otherwise NULL (futility).
2. **At 365 counted days:** PASS when all of these hold over the first 365:
   - the 1x mean beats the placebo threshold;
   - the 1x mean is above 0;
   - the 2x mean is above 0;
   - the trimmed mean (top and bottom 10 days removed) is above 0.

   Otherwise NULL.
   - **Placebo threshold:** the 97.5% quantile (one-sided 2.5% per book, Bonferroni over the two books) of the same
     365-day 1x mean in 1,000 placebo books (seed 455).
   - Each placebo draws, on every row where the book opened slices, the same number of markets uniformly from that
     row's hedge basket, at the same weight, costs and hedge.
3. **Stop rule:** a drawdown of 50% of capital in the summed counted daily nets stops the book.
   - A book that is NULL at the screen or hits the stop rule is closed: its decision is final, and later tickets
     are reported only.
4. A PASS earns a frozen paper lane with measured costs (Lighter's books, as `scripts/record_lighter_book.py`). Then
   `lab.gate.go_real()` and the owner's own decision apply. Nothing here authorizes an order.
5. R454 and R455 are read separately. Neither lane's result changes the other's rule or decision.

## Reported, not deciding
- Gross, cost, funding received and hedge return per day; gross exposure; hours that opened slices.
- Leave-two-markets-out mean gross; Newey-West t (10 lags); hit rate; worst day; maximum drawdown.
- All days, ramp and thin included, next to the counted ones.

## Power
- There is no archive, so the effect size is unknown.
- At one-sided 2.5% and 80% power, 365 days detect an annual Sharpe of about 2.8. A Sharpe of 2 needs about 716
  days, 1.5 about 1,273. The final read is therefore a futility screen for smaller effects.

## Trials and reading
- **Two trials** (books F and R). The program total goes from 9,785,001 to 9,785,003.
- Read against `registry.program_trials()`.

## Limits
- **Execution:** one snapshot an hour, read minutes after the hour; entry at a later close than the snapshot.
  Lighter's Standard accounts trade with added latency; the hourly rule does not depend on it.
- **Costs:** a flat 9 bp. Book depth is not recorded for every market; a large account pays more on small markets.
- **Shares:** LLP is one liquidity provider on Lighter among others (Lighter's public pools and other makers). Its
  share measures the crowd's flow against LLP only.
- **Universe:** Lighter lists non-crypto perps (FX, metals, indices) next to crypto ones; any that meets the
  eligibility test at a run is in that run's cross-section.
- **Delistings:** a delisted market's later returns are missing and count as 0 while its slices remain (the lab's
  legacy missing-data rule in `lab/slices.py`).
- **Reads:** a failed price request fails the whole weekly read and writes nothing; the next read fetches again.
- **Recorder:** GitHub's schedule can skip or delay hourly runs. Missed hours are counted per day and thin days are
  excluded.

## Stop rules
No new bins, horizons, costs or books after a result. A changed idea is a new lane.

```inputs
8d6ae65f33609173cb09d91d2e11fbe354b243212d9ef3557461d167a9fef653 scripts/run_llpinv.py
3a1e23d755ce8439e87276b332de26ae51abba34fdf75bf0dbde7dae7138da71 tests/test_run_llpinv.py
73a9a5d4dded491e8d47565b5e6efa92bbbab843ee9545d317ba22de127e9b36 scripts/record_llp_positions.py
b842eec2ae944306f78184a3db329ff1e3fafbc24afcdccce44f0c0cf0419d2a scripts/run_hlpinv.py
f9fe49b24ebf85b7144bd43cad14af386aa470adaacb4fe2631ee0be0c7fe1b5 scripts/record_xyz_books.py
a9b59625ba64010368e436a0259d8239674f5e361d671337dc499e7239e59fad scripts/record_okx_xperp.py
0c9b45bd4675d1f7177d09741fb1e65888214a9a30f4461f254310f6b45485f3 scripts/run_flow_hl.py
4b255a4da93acc25eacd06ed19659118485802577efbe2ccc97cca353d539a1f lab/slices.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 lab/stats.py
12efdca302dfdbc1312dc7499a53de23af9276406e1934c547b9e8642622e895 lab/carrylane.py
```
