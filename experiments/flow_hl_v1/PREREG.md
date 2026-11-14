# PREREG: flow_hl_v1 (R448). R200's flow books on crypto perps only, traded on Hyperliquid

Freeze with `lab.prereg.freeze()` before any statistic. Never edited afterwards; a changed idea is a new lane.

- **Registry id:** R448
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w`. `scripts/run_flow_hl.py` is the
  only writer of `experiments/flow_hl_v1/journal/` and `results/`. From the forward start it runs in
  `.github/workflows/claude-flow-paper.yml`, right after R200's tick.
- **Date registered (UTC):** 2026-11-11

Methods M126 (book A, three flow cells) and M127 (book B, top_vs_crowd alone). Parents: R197 (in-sample),
R198 (holdout), R200 (forward on Binance), R215 (forward on MEXC), R216 (crypto/TradFi split).
**Paper only:** public endpoints, no account, no key; nothing in the code can place an order.

## Question
Do R200's flow books, restricted to crypto perps that Hyperliquid lists, earn a positive net return on Hyperliquid's own
hourly closes and funding, at the lab's tier costs and at 2x and 3x?

## Why this lane
- **The binding constraint is the venue.** The flow books are the lab's highest-return family with live forward days,
  but every venue they have been priced on (Binance, MEXC) is closed to the owner from France. Hyperliquid needs no
  account and no KYC (`docs/reviews/venue_access_fr_20261110.md`). The signal stays on Binance's public ratios, which
  any reader can fetch.
- **Crypto only.** R216 found that R200's forward profit came mostly from Binance's stock and commodity perps; the
  crypto coins carried a much smaller part. Hyperliquid's main perp list is crypto. This lane measures what is left.
- **Coverage.** Not every Binance top-50 crypto perp is listed on Hyperliquid. The gap is measured, not assumed.

## What the author has seen
- R197, R198 and R216 in full, including R216's crypto-only archive split (holdout 2025-07..2026-09, Binance prices,
  zero delay): book A +22.33 bp/day (t 1.25), book B +18.25 bp/day (t 2.74).
- R200's forward tickets through 2026-11-05 on Binance prices (A +33.9%, B +17.1% over 36 days). R215 and R218's
  tickets on MEXC prices for the same days (A +8.0%, B +1.4%), and R216's split of the 2026-10-01..18 replay (crypto
  only: A +8.7%, B -0.5%).
- Hyperliquid: the current perp list (179 listed); that hourly candles reach back 5,000 hours (local files from
  2026-03-26); the column names of the local candle and funding files; three BTC hourly candles of 2026-11-10 fetched
  to test the forward fetch's format (prices only, no return computed).
- One plumbing run of `gate0()` on 2026-03-30, a day before this window, that printed only counts: 47 eligible crypto
  symbols, 32 mapped to a Hyperliquid coin, signal coverage 65% (A) and 89% (B). Its returns were not printed.
- **Not seen:** any book return on Hyperliquid prices, any Hyperliquid return in the gate-0 window, and any R200 hour
  from 2026-11-12 on.

## Data
- **Signal (gate 0):** the archive's flow bins `data/research/bins_flow.npy` (R197's cells top_vs_crowd/xs8,
  taker[24]/xs8 and taker[4]/xs8, bin 0), with the archive's eligibility (`elig.npy`, top 50 by trailing 30-day volume),
  tier costs (`cmat.npy`, 6/8/12/20 bp one way by Binance liquidity rank) and Binance returns (`ret.npy`, for the
  comparisons only). These files are pinned in the `inputs-gate0` block.
- **Signal (forward):** R200's journal (`experiments/flow72_fwd2/journal/signals.csv` and `ticks.csv`), written live by
  `scripts/forward_tick.py`. Signal rows and `run_at` are read as R200 wrote them; this lane never writes there.
- **Prices (gate 0):** `data/hyperliquid/candles_1h` and `data/hyperliquid/funding` from
  `scripts/fetch_hyperliquid_history.py` (fetched 2026-10-20). The 380 files of every coin an archive symbol maps to are
  pinned by sha256 in `hl_inputs.json`, itself pinned below.
- **Prices (forward):** Hyperliquid's public `candleSnapshot` (1h) and `fundingHistory`, fetched at run time for each
  mapped coin. Every closed hour fetched is appended to `journal/hl/<YYYY-MM>.csv` (t, coin, close, rate); stored rows
  are never rewritten, so reads after the API's 5,000-candle window still have their prices.
- **TradFi list:** R216's `experiments/venue_gap_v1/results/tradfi_symbols.json` (pinned). Those symbols are excluded.

## Feature lineage and point-in-time availability
- **Flow bins** (top_vs_crowd, taker[24], taker[4], xs8 bin 0):
  - parents: Binance's top-trader and taker ratios (USD-M public futures data), reduced to hours and binned over the
    tradable set at t as in R197/R200;
  - computed: gate 0, in the archive; forward, by R200 at its `run_at`;
  - available at the decision: yes. Gate 0 enters one bar late; the forward enters at the first close after `run_at`;
  - membership: the archive's point-in-time top 50, delisted symbols included; forward, R200's live universe;
  - missing: no signal, no slice.
- **Liquidity rank and tier cost:** Binance quote volume over the trailing 720 hours, as R200; available at t.
- **Hyperliquid close and funding:**
  - parents: `candleSnapshot` 1h and `fundingHistory`, main perps, USDC, rate per hour;
  - the bar opened at t; a settlement stamp falls in the hour it starts in;
  - used only as returns after entry;
  - membership: coins with a close at the time;
  - missing: no close at t means not tradable at t.

The universe is R200's (Binance top 50 by volume) intersected with Hyperliquid's list at each hour. A Binance symbol
maps to the Hyperliquid coin of the same base, or to `k<base>` for a 1000/1000000 prefix (`hl_coin`); no other alias.
Coins Hyperliquid delisted before 2026-10-20 may be missing from the local files, so gate 0's coverage is a
current-listing view; the count of unmapped eligible symbols is reported. The forward read is point-in-time.

## Rule
- **Tradable at row t:** eligible (archive or R200), not TradFi, mapped to a Hyperliquid coin, and Hyperliquid has a
  close for row t (gate 0 also requires the close of row t + 1).
- **Slices:** a signal on a tradable coin at row t opens a short slice of 1 / (72 x 9.316) at the entry row, held
  72 hours, if the coin is tradable there. **Entry row:** gate 0, t + 1 (as R214/R215); forward, the first row whose
  close is at or after R200's `run_at` for hour t, and never before t + 1 (`entry_lag`).
- **Books:** A = the three cells summed (a coin flagged by k cells holds k slices); B = top_vs_crowd alone.
- **Return:** Hyperliquid close[t+1] / close[t] - 1, less the funding a long pays at the settlement stamped in hour
  t + 1 (shorts receive it). Hedge: long the equal-weighted basket of the tradable coins for the book's net short
  exposure (idealized, as R197-R215). Costs: the archive's or R200's tier cost by Binance rank, charged on every change
  of position and of the hedge, at 1x, 2x and 3x. Hyperliquid's base taker fee (4.5 bp) is below the smallest tier.
- **Missing prices:** a held coin with no close earns nothing that hour (the lab's legacy rule, as R215); counts are
  reported.

## Gate 0: 2026-04-01..2026-09-30 (183 days), exploratory
- Rows 72 hours before 2026-04-01 open slices that carry in; days are UTC days from 2026-04-01.
- **Decision, per book:** CONTINUE if the 1x mean daily net on Hyperliquid is above 0, else NULL. Gate 0 cannot earn
  anything: R198 read these days on Binance's prices.
- **Reported, not decided on:** the same coins and slices on Binance returns (the venue gap) and every eligible crypto
  coin on Binance (the coverage gap); 2x and 3x; gross, cost, hedge and funding; coverage; correlation with the
  same-coin Binance book; trimmed mean; leave-two-coins-out; top contributors.

## Gate 1: forward from 2026-11-12 00:00 UTC
- Starts flat at 2026-11-12 00:00 UTC. One ticket per book per complete UTC day (`journal/tickets.csv`, appended, never
  rewritten), with per-coin gross in `journal/coins.csv`.
- **Counted days (docs/GATES.md):** strict on-time days only, where every one of R200's 24 hours has
  `run_at` within 60 minutes of the hour's close. Other days are written with `kind=late` and reported, not counted.
- **Futility screen at 90 counted days, per book:** NULL if the mean 1x net of the first 90 is 0 or below; otherwise
  the book continues. No PASS is possible at 90 days.
- **Final read at 365 counted days, per book:** PASS if the mean 1x net of the first 365 is above the threshold
  **and** the 2x mean is above 0 **and** the trimmed mean (10 best and 10 worst days removed) is above 0. NULL
  otherwise. The threshold is the upper 2.5% quantile of a 365-day mean under the null: gate 0's daily 1x Hyperliquid
  net for the same book, its mean removed, resampled in blocks of 10 days (20,000 draws, seed 448). 2.5% per book is
  Bonferroni over the two books.
- **Stop rule:** a book whose cumulative net (all days) falls 0.5 below its running peak is stopped and NULL.
- **Reported:** all-days results, the leave-two-coins-out gross, funding, coverage and unmapped symbols in
  `journal/status.json`, rewritten each run.

## Decision group and what a PASS means
This lane shares its cells with R200, R214, R215, R218 and R225, so it is not a new chance on the signal. It is the flow
signal's **France-reachable execution check**: an owner stake on Hyperliquid would need R200 to pass on the signal
**and** this lane to pass on Hyperliquid's prices, both within the gates in `docs/GATES.md`, then `lab.gate.go_real()`
and the owner's decision (AGENTS.md rules 5 and 6). A PASS here authorizes nothing by itself.

## Power (stated before any Hyperliquid return)
From R216's crypto-only holdout (seen, Binance prices): book B's mean 18.25 bp/day with a daily SD near 142 bp; book
A's mean 22.3 bp/day with a daily SD near 382 bp. For 80% power at one-sided 2.5%, B needs about 470 counted days and
A about 2,300. At 365 days, B's power is about 69% and A's about 20%, if Hyperliquid kept the holdout edge, which it
may not. **The 90-day read is a futility screen**; A is unlikely to pass in a year even if its edge is real.

## Multiplicity
Trials = 2 (books A and B, one rule each). Program trials before: 9,784,991 (9,784,993 after). There is no
across-family correction: a pass stays conditional on R200's.

## Costs
1x is the lab's tier cost (6/8/12/20 bp one way by Binance rank, on the books and the hedge). 2x and 3x are reported
everywhere and enter the final read through the 2x condition.

## Limits
- Gate 0's Hyperliquid files list coins listed on 2026-10-20; a coin delisted before then is unmapped in gate 0.
- Hyperliquid's funding is settled hourly against a baseline interest of about 0.01% per 8 hours; the lane books the
  settled rate and assumes the short receives it in full.
- The hedge is idealized (free internal rebalancing), as in every flow lane.
- Fills are at hourly closes. Depth on Hyperliquid for smaller alts was not measured.
- The forward read depends on R200's journal being written; an hour R200 never writes has no signal.
- Jurisdiction: Hyperliquid's terms as read do not exclude France. That is not legal advice; the owner checks.

## Stop rules
No new cells, venues, coins or windows after a result. A changed idea is a new lane.

```inputs
0c9b45bd4675d1f7177d09741fb1e65888214a9a30f4461f254310f6b45485f3 scripts/run_flow_hl.py
c1b514a3d1cf3432fa4f68a51b2c7411ac1da4359806130ccd543d4ea7fa4915 tests/test_run_flow_hl.py
2e066fcfc4b231e801c4c327bb9ac138e85a1d14d808b5bd2d53657c33cc195c experiments/flow_hl_v1/hl_inputs.json
af7b1a0fbf99471720f765ece0b16734b88247aa84feb7f21137103500d983ea experiments/venue_gap_v1/results/tradfi_symbols.json
4b255a4da93acc25eacd06ed19659118485802577efbe2ccc97cca353d539a1f lab/slices.py
66ac88bdf3034e11401d18e1dac09e7379d59cbb0654332e4d1458200fca0a27 lab/engine.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 lab/stats.py
e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926 docs/GATES.md
```

Gate 0's archive files (they exist only where gate 0 runs; the forward runs check the block above):

```inputs-gate0
21e8ee4b665d0177eff6eee53bfbc640e80407d33b90131a102590385477a8c0 data/research/meta.json
23b2663334d34691667252020a5ff96b33997a9dc8ef6a124e8d39c6f373a47a data/research/meta_flow.json
1acee88308164de0f3a03d3833ef03cc33b54c177a3f430ac45cf1c579cb5108 data/research/t.npy
8849793b9060dcdc18d34cd7a6790b93deeb3754edbfaa67c7f23236ccae2e4a data/research/elig.npy
348e3149db50ab30be02615facd54c28448987352fb98b371bac25aeb5f6f94b data/research/cmat.npy
d856af7a5c8cf00dbd7b3ea6892af3048e6300b153e315cd167292c93ce2a634 data/research/ret.npy
4d2717221f22b2bbff3e390e95df9ef67e966d89897e20a0400208ad8a6ef6d9 data/research/bins_flow.npy
```
