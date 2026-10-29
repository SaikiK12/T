# PREREG: cmelead_v1 (R370). After an EIA release moves CME's crude or gas future, does Binance's TradFi perp still trade at the old price long enough to pay a taker's catch-up?

- **Registry id:** R370
- **Owner (single writer):** Claude, this session (cloud container, 2026-10-29)
- **Date registered (UTC):** 2026-10-29

Methods M444 (EIA releases) and M443 (cross-venue disagreement on the 24/7 commodity perps), from the owner's fifth pasted
review of 2026-10-28. A gate-0 test on history, frozen by `lab.prereg.freeze()` before any statistic of it. After the freeze this
file is never edited; a changed idea is a new lane. It does not touch R369 (`experiments/eventlag_fwd`), the forward lane on
Lighter, which keeps running unchanged.

## Question
At each of the 60 EIA releases of 2026-04-01 .. 2026-10-22 (30 crude, 30 natural-gas storage), when the front-month CME
future (CL for crude, NG for gas) has traded far from its pre-release price, has Binance's perpetual (CLUSDT, NATGASUSDT)
covered less than half of that move one second later? If so, does a taker order on Binance at that moment, closed at T + 60 s,
earn more than two cost units, counting only what the public trade prints show?

## Why this lane
- R368 (`experiments/eventdrift_v1`) used Binance's one-minute bars and found nothing that continues after the first minute.
  R369 asks the first-seconds question across the 24/7 venues but can only begin on 2026-10-29 and reads about 8 releases of
  each type by 2026-12-23. The missing piece is the true leader: CME's trades. Databento sells them tick by tick for the
  past, so the same question can be asked of 60 past releases now, with the real price-discovery venue as the leader.
- Binance is the follower because its public archive holds every aggregated trade of CLUSDT and NATGASUSDT since
  2026-04-01 with a published checksum, so every release can be read.
- A NULL is the likely result: Binance's makers have the same CME screens as everybody, and R347/R348 found Lighter's makers
  close a lead over Binance on crypto within a second. A PASS would not be tradeable as it stands, because acting on a CME
  trade needs a live CME feed, which the lab does not have (see Stop rules). The lane measures how big and how long the
  lag is, which sets what R369's forward evidence can hope to find.

## What the author has seen
- **R368's diagnostics** (Binance one-minute bars, the same 60 releases): the median absolute first-minute move was 48.7 bp
  for gas and 11.1 bp for crude. They set the two thresholds below (taken over from R369 unchanged).
- **A probe of CME crude, outside the sample.** One Databento pull of CL.c.0 on 2026-10-28 14:25-14:45 UTC (the day after the
  last day of the archive; the 10-28 release is not among the 60), `mbp-1`, to check the key, the format and the price. The
  author looked at the column list, the action codes (about 3,200 trade rows in 20 minutes), the dtype of the timestamps,
  the median one-tick spread, and the minute-end mids of those 20 minutes. No sub-minute path, no Binance price and no lag
  was looked at for that day.
- **The price.** `metadata.get_cost` quotes for the 180 windows below before any pull; the pulls were then made with a cap
  of 5 cents each and $2 in all. Spent: $0.6649 over 180 pulls (quotes $0.0003 to $0.0188 each, 6.0 MB), well under both caps.
- **The Binance archive.** File sizes and the list of days (CLUSDT and NATGASUSDT aggTrades, 2026-04-01 .. 2026-10-27).
- **Data on disk, counts only.** Per window, the number of CME trades and Binance prints, and whether each has a reference and a trade in the 60 s after T. All 60 release windows are valid (median CME trades in the window: 1,084 crude, 496 gas; Binance prints: 915 crude, 150 gas; in the 60 s after T: 214 and 204 for crude, 96 and 28 for gas, so Binance's gas perp is thin). 116 of the 120 placebo windows are valid; the four others fall on 2026-03-30/31, before the Binance archive begins. No price change, state or test was computed.
- **Code.** The rule and runner were exercised only on synthetic trades (a planted 3-second lag on the follower, a follower
  that moves at once, a revert, missing prints, a missing reference; `tests/test_cmelead.py`, `tests/test_cmelead_run.py`).
- **Not used:** CME quotes (the lane reads trades only), Binance quotes (the archive has none for these symbols), funding.

## Data
- **Releases:** `experiments/eventdrift_v1/events.csv` (R368's calendar, 30 `wpsr` and 30 `ngs`, 14:30 UTC, or 16:00 UTC on
  the three holiday-shifted crude dates 2026-05-28, 2026-09-10 and 2026-10-15). T is the release instant.
- **Windows:** `experiments/cmelead_v1/windows.csv`, written by `scripts/fetch_cmelead.py windows`: for each release the
  window [T - 310 s, T + 75 s], and the same clock time on two placebo days (gas: 2 and 3 days before; crude: 1 and 2 days
  before; the same days as R369), 180 windows.
- **CME:** Databento, dataset GLBX.MDP3, schema `trades`, `CL.v.0` (crude) and `NG.v.0` (gas), the front month by volume,
  raw CSV+zstd under `data/databento/cmelead/` with `manifest.csv`. `ts_event`, the exchange's own event time, is the
  clock; rows with action `T` and a positive price are the trades.
- **Binance:** data.binance.vision USD-M daily aggTrades of CLUSDT and NATGASUSDT (each zip checked against its published
  sha256), the windows only, `data/cmelead/binance/<SYMBOL>/<anchor ms>.parquet`: time (ms), price, quantity, whether the
  buyer was the maker (so the taker sold), aggregate id.
- **Provenance:** `docs/provenance/cmelead.json` lists every file's sha256 and the Databento spend; the runner refuses to run
  if any file differs.
- A window is **valid** when both series have a reference (below) and each has at least one trade in the 60 s after T.
  Otherwise it is `no_ref` or `no_trades_after`, counted and not scored: a hole in the data is not a loss.

## The rule
All times are the exchanges' own clocks (Databento's `ts_event`, Binance's transaction time); their offset to each other is
not measured. T is the release instant (the anchor of the window).
- **Reference.** For each venue, p0 is the median of the last trade price at the 51 one-second marks from T - 60 s to
  T - 10 s (a trade older than 300 s does not count; at least 25 marks needed).
- **Crossing.** t* is the first CME trade at or after T and within 60 s of it whose price is at least THETA bp from the CME
  p0: THETA = **20 bp for gas storage, 8 bp for crude** (R369's). The sign of that move is s.
- **Decision.** t_d = t* + L, L the seconds from the CME trade to a Binance order reaching its book. Decision L = **1.0 s**;
  also computed at 0.5, 2 and 5 s. D = s x 1e4 x ln(last CME price at t_d / CME p0); skip if D < THETA ("reverted").
  c = s x 1e4 x ln(last Binance price at t_d / Binance p0) / D. The **lag filter** keeps the trade when c <= 0.5.
- **Entry.** The first Binance taker print on the side of s (a taker buy if s > 0, a taker sell if s < 0) at or after t_d and
  within 1.0 s of it, at its price (a taker print sits on the touch, so the spread is in it). None: `no_fill`.
- **Exit.** The last Binance taker print on the opposite side at or before T + 60 s and not older than 10 s, after the entry.
  None: `no_exit`.
- **Gross** = s x 1e4 x ln(exit / entry), in bp. **Net** = gross - k x 2 x 5 bp, k = 1, 2, 3 (Binance USD-M taker, an
  assumption about the owner's account tier, not a quote). One cost unit = 10 bp.
- **Placebo.** The same rule at the same clock time on the placebo days, L = 1 s, to show how often it fires and what it earns
  without news. Reported only.

## Trials
2 event types x 4 latencies x {lag-filtered, unfiltered} = 16 cells; the placebo table and the diagnostics are not cells.
**16 trials, 2 decisions** (each event type, L = 1 s, lag-filtered). Registry trials: 16. Program trials before: 9,479,173
(9,479,189 after).

## Decision
For each event type, over its valid release windows: the lag-filtered trades at L = 1 s, their mean gross, and the one-sided
sign-flip p-value for "the mean is above 0" (exact up to 18 trades, otherwise 200,000 random flips, seed 370),
Holm-adjusted over the two types.
- **PASS:** a type with at least 10 valid release windows and at least 6 lag-filtered trades, a Holm p at most 0.05 and a mean
  gross above 20 bp (two cost units, so the 2x net is positive).
- **PARTIAL:** the same with the mean above 10 bp but not above 20.
- **INCONCLUSIVE:** no type has 10 valid release windows and 6 lag-filtered trades.
- **NULL:** otherwise.

## Costs (1x, 2x, 3x)
1x, 2x, 3x subtract 10, 20, 30 bp from every gross mean. The spread is already in the print prices. Binance's real fee for the
owner's account (VIP tier, any TradFi-perp specific schedule, a BNB discount) is not known here; at a zero-fee venue the
same gross would be worth more.

## Power
Reported with every cell: n, mean, sd, t, hit rate, and MDE80 = 2.8 x sd / sqrt(n) (the true mean that would be seen 80% of the
time). With 30 releases a type and perhaps a third of them lag-filtered, only a large effect can reach a Holm p of 0.05; a NULL
here means "no lag larger than the MDE in 30 releases", not "no lag".

## Reported (not decided on)
Every cell; status counts (ok, no_cross, reverted, no_fill, no_exit, no_ref); t* , c, the entry wait and D of every trade;
the unfiltered cells; the other latencies; the placebo fire rates and means; coverage of the windows.

## Code
```inputs
4b49a67a0d620a9ce71e1f3796cc241bd6d0f06ac014363660c7db22d481d781  experiments/eventdrift_v1/events.csv
7c6da248662a469407d58c39afca182ff9677b2822b1fd7d513c237ab1c893b7  experiments/cmelead_v1/windows.csv
df290cde750779150464b1d51ec6bf212c77d5fa34575bc14746cc7882506eee  scripts/cmelead_rule.py
5127b90ad5471a6bf08f5f22750221db2f0b30602f53f5a1a4d5f9a80be00cf0  scripts/run_cmelead.py
730053074272e586b73f0425e13c234b6aa0304f64b2ac6f79af66470be6558d  scripts/fetch_cmelead.py
b2a03bdcbcd64412c83eec66751ccbbecc3ab3b3bd34a273f1847a0aebea95b2  scripts/fetch_databento.py
20a9c9d5e87efdf90f8c2dcc0cd4c2496f7a199222b99e686983d107b221be30  scripts/fetch_settle_ticks.py
f502cfabbe654c31bdd106c93b660fdcc3e2e4bfe4cd80aa3cde04b2faa4c776  docs/provenance/cmelead.json
```
`scripts/fetch_databento.py` reads the key from a file outside the repository and never writes it anywhere.

## Evidence lineage and admission
- **Methods:** M444, M443 (related: M441, R368, R369). **Parents:** R368 (the calendar and the thresholds), R369 (the rule's
  shape; it is not changed and its forward lane is not an input).
- **Decision group:** M444/M443's tick-level cross-venue form on EIA releases. Two decision cells.
- **Samples:** 60 releases 2026-04-01 .. 2026-10-22 and their placebo days. R368 read the same releases on one-minute bars,
  so this is not independent of R368's calendar, but its prices (CME trades, Binance prints) have not been read by any lane.
  R369's releases start on 2026-10-29 and are disjoint.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`. Met: one verdict from
  two pre-named cells; multiplicity (Holm over 2, 16 cells counted); cost sensitivity; a placebo. Left unmet: gate 1 needs
  forward days; gate 3 (account risk); a fill model (see limits).

## Stop rules
- The lane ends at its one run. Nothing is retuned: no other threshold, latency, hold, venue, window or event type.
  Extending it to other releases (CPI, FOMC, the weekend reopen), to Hyperliquid or Lighter as followers, or to quotes, is a
  new lane.
- **What a PASS or PARTIAL earns:** a note to the owner that Binance lags CME at these releases by an amount that pays a
  taker, with the measured size and the number of trades; the open item is a live CME feed (a Databento live
  subscription and exchange licence fees, a cost the owner decides) and a measured order path to Binance (hard rule 5:
  orders need the owner). R369 stays the forward test of the 24/7 venues. **What a NULL earns:** M444/M443's
  CME-leader-to-Binance form closes NULL at latencies of 0.5 s and above for 2026-04..10.
- No orders, no money movement beyond the Databento pulls already capped in the fetch script, no credentials in the repo.

## Known limits (written before the run)
- Trade prints, not quotes: the follower's touch is seen only when someone trades, so "the follower has not moved yet" is
  read from its last print. The entry is the first matching taker print within 1 s after t_d, which is the price a taker
  would have got if one existed then; a longer wait would let the follower's catch-up into the entry, which is why the wait is
  short and a trade without such a print is skipped. Aggregated trades merge fills of one order at one price and stamp them at
  the first.
- Two clocks (CME's matching engine and Binance's), not aligned to each other: a lead of tens of milliseconds is not
  resolved, and L = 0.5 s is the shortest latency read.
- L = 1 s is an assumption about the whole path. A websocket round trip from this container to Binance's gateway took
  about 0.25 s (measured 2026-10-28), and a CME trade seen live adds the feed's own delay.
- `v.0` rolls to the contract with the most volume the day before; at a roll the leader can be a different month from the
  one a human would call front. The follower is a perpetual that tracks one.
- 30 releases of each type in one regime (2026), the thresholds come from minute bars of another venue, and the first
  threshold crossing is taken whichever way the market goes next (two-sided first seconds are not modelled).
- A CME trade that crosses the threshold is not necessarily a stable price; the `reverted` filter checks only the price at t_d.
