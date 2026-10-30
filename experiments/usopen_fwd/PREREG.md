# PREREG: usopen_fwd (R371). R300's "us10 n3 follow", forward on paper, on days nobody has read

Freeze with `lab.prereg.freeze()` before the first ticket. Never edited afterwards; a changed idea is a new lane.

- **Registry id:** R371
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w`. The lane's daemon
  (`scripts/forward_usopen.py`) is the only writer of `experiments/usopen_fwd/journal/`; it holds `journal/.writer.lock`
  and a second writer exits.
- **Date registered (UTC):** 2026-10-29

Method M318 (intraday cross-sectional relative strength), candidate C17, parent R300 (`experiments/intrars_v1`, NULL).
Claim: issue #7, comment 6485901209, before this freeze. Gate 1: every day is decided and entered after this freeze, on
days no lane has read. Execution mode: manual web on MEXC (book M, what a person can do by hand: six orders in, six out) with
the lab's API-cost replica of R300 (book B) alongside. **Paper only:** public endpoints, no account, no key; nothing in
the code can place an order.

## Question
Starting 2026-10-29, on each NYSE trading day, does going long the 3 strongest and short the 3 weakest of the 50 most
traded Binance USDT perps (by move since 00:00 UTC, measured at 10:00 New York) and holding to 24:00 UTC earn a positive
mean net of what a person pays on MEXC's web terminal: a Newey-West t of 2 or more after 500 scored days, with a positive
2x mean and a positive mean without the 10 best days?

## Why this lane
- **R300 was NULL by its own gate and is not re-opened.** Its pick (us10 n3 follow) was the best of 24 books in
  discovery (t +1.88). In validation (2024-01..2026-09) it earned +72.7 bp/day gross, +38.7 net at API 1x (t +1.28, below
  the 2.0 bar), +4.7 at 2x, -29.3 at 3x, and -3.3 without its 10 best days. The daily standard deviation is about
  650 bp. The edge was positive gross in every calendar year and moved from the leaders (2021-23) to both legs (2024-26).
- **What this lane adds is days, nothing else.** Archive history is spent; the only evidence that can still move the
  verdict is days after the freeze. Forward days cannot be bought back, so the clock starts now. This is the cheapest
  honest test of a lead that is cost-only: most of its gross is eaten by 34 bp of API cost a day.
- **Why two books.** Book B repeats R300's exact universe and cost on new days, so a failure of the replica is visible
  (the rule, not the venue, would be the problem). Book M is what the owner can do: only coins with an open MEXC crypto
  perp, filled at MEXC one-minute opens, at MEXC's own fee and half-spread. M decides; B explains.
- **The expected answer is NULL.** Re-pricing R300's validation at MEXC web cost gives about +61 bp/day (t about 2.0), but
  that re-price is on seen days (the lane is not told by it) and the pick is the winner of a search: its true mean is
  likely lower. See Power.

## What the author has seen
- **R300 in full:** discovery and validation tables, the 10-best-days result, the yearly gross, the placebo clocks (in
  `experiments/intrars_v1/FINDINGS.md`), and the MEXC re-price above, which was a calculation on R300's seen days.
- **One past day, for plumbing.** On 2026-10-29 the author ran the daemon's ticket and scoring functions once on
  2026-10-27 with a temporary journal outside the repo, to see that the live endpoints answer and the code runs end to
  end. That day is before the lane's first day and is not in any statistic. It showed B +16.2% and M +15.0% net on that
  day (one coin down 65%); it is mentioned so the reader knows it was seen, not because it informs anything.
- **Code tests.** The rule and daemon were exercised on synthetic bars and stubbed endpoints (`tests/test_usopen.py`).
- **Not seen:** any day from 2026-10-29 on; the 2020 reserved sample; MEXC-only coins.

## Data
- **Bars and funding for the signal and for book B:** Binance USDT perpetuals through `lab/live.py` (hourly klines via
  the shared cache `klines_cached`, funding via `funding_history`; `https://www.binance.com`). The universe at D is every
  USDT perpetual that `live.perpetuals()` lists as trading when the ticket is written, TradFi perps included (as in
  R300). A symbol that fails to load is left out and logged.
- **Book M:** MEXC contract table `mexc.contracts()` filtered to type 1 (crypto) and state 0 (enabled); Binance symbols
  map to contracts with `mexc.map_symbols` (base asset, the 1000x prefixes and the lab's alias list); one-minute opens
  from `kline/<contract>` (interval `Min1`); MEXC funding from `mexc.funding_history`; half-spread from the lab's MEXC
  ticker recorder (`data/recorders/mexc_ticker/<date>/<hour>.parquet`).
- No input is a file frozen by hash except the rule module (Code). The data are live public endpoints; the ticket stores
  the signal table and the legs it traded, so a day can be audited later without re-fetching.

## The rule
All times UTC unless written otherwise. `scripts/usopen_rule.py` (hash below) holds the pure parts.
- **Trading days.** A day is a NYSE trading day by `lab.sessions` (weekends and the exchange's holidays out; early
  closes count). The first possible day is 2026-10-29. **D** = 10:00 America/New_York that day (14:00 UTC until
  2026-11-01, 15:00 UTC after).
- **Universe and rank.** For every symbol that traded in the hourly bar that opened at D - 1 h (volume > 0, close > 0),
  vol = the sum of quote volume over bars with open time in [D - 720 h, D); rank 1 is the largest vol (ties by symbol).
  Only bars opened before D are read. The top 50 are eligible.
- **Signal.** sig = (close of the bar that opened at D - 1 h) / (close of the bar that opened at 00:00 - 1 h on that date,
  the bar that closed at 00:00 UTC) - 1. An eligible symbol with no trading in the 00:00 bar has no signal and is skipped.
- **Pick.** Among the top 50 with a signal: long the 3 largest sig, short the 3 smallest (ties by symbol). If fewer than
  30 are eligible there is no book that day ("no_book").
- **Book B (R300 replica).** All Binance symbols as above. Entry price = the close at D (the bar that opened at D - 1 h);
  exit price = the last traded hourly close with open time in [D, 24:00 UTC), that is the close at 24:00 UTC (a coin with no
  trade after D exits at its entry price and is counted "stopped"). Funding = the sum of Binance rates for settlements in
  [D, 24:00 UTC), shorts receive and longs pay. Each side is the equal-weight mean of its three legs, one unit a side.
  Cost 1x = 4 units x 8.5 bp = 34 bp (R300's API cost).
- **Book M (the decision).** The same rule applied only to symbols with an open MEXC crypto contract, re-ranked within them
  (top 50 of that set; fewer than 30 eligible means no M book that day). Entry = the open of the first MEXC one-minute bar
  at or after D + 3 minutes and within 5 minutes of it; exit = the open of the first one-minute bar at or after 24:00 UTC
  + 3 minutes, within 5 minutes of it. If either price is missing the day's M book is skipped ("unpriced") and not made
  up. Funding = MEXC rates for settlements from the first full hour after the entry minute up to and including the hour
  of the exit minute (so the 00:00 UTC settlement is inside M and outside B). Each side the equal-weight mean of its three
  legs.
- **M cost 1x.** Per leg: 2 x the contract's taker fee (from the contract table; many are 0) + the half-spread
  (ask - bid)/(ask + bid) of the ticker recorder's snapshot of the UTC hour of the entry fill (one a hour, taken by the forward
  loop at about 15-17 minutes past the hour) + the same for the exit fill; a missing snapshot uses 10 bp for that fill and flags the day. The book cost is the mean leg cost of the longs plus
  the mean leg cost of the shorts. 2x and 3x multiply the whole cost.
- **Net** = price return + funding - k x cost, k = 1, 2, 3.
- **Ticket.** Written within 2 minutes of D (bars of the hour that closed at D are served within seconds; the daemon
  waits up to the deadline for them). Later than that the day is a "missed" row and is not made up. A ticket holds the
  50-name signal table, the six legs of each book, the MEXC contracts and the taker fee and quote at the ticket time.
- **Scoring.** Each ticket is scored once, 20 minutes after its exit minute (24:00 UTC + 3 minutes), from history. A score that fails on a data
  error is retried by the next tick.

## Trials
Two cells (B and M, one rule), **one decision** (M at 1x with its 2x and trimmed-mean conditions). Registry trials: 2.
Program trials before: 9,479,189 (9,479,191 after). R300's own 24 books were counted in R300's row; this lane does not
recount the parent search but does not reset it either (see Power).

## Decision
On the M book, over scored days in calendar order (Newey-West t with lag 5 on the calendar-day grid, as R300):
- **PASS:** at the 500th scored day, t >= 2.0 at 1x **and** the 2x mean > 0 **and** the mean without the 10 best days > 0.
- **NULL:** at the 500th scored day otherwise.
- **NULL (futility):** at the 125th scored day, a negative 1x mean with t <= -1.
- The futility read uses the first 125 scored days and the PASS/NULL read uses the first 500, each once. Days after a
  read are descriptive and cannot change it (a mean that recovers after day 125 does not undo a futility stop).
  Everything before the read is descriptive: the daemon writes the current table every tick and the decision field says
  "pending".
- **PARTIAL** is not used. A PASS earns a request to the owner for small calibration orders on MEXC (hard rule 5), the
  gates in `docs/GATES.md`, and `lab.gate.go_real()`; it does not authorize real money.

## Costs (1x, 2x, 3x)
1x is M's measured web cost per leg above (21 bp for the book on the one plumbing day; it varies with the picks, since some
MEXC contracts have a 0 taker fee and others 2-4 bp, and with each coin's spread) and B's 34 bp. The FINDINGS table gives mean,
t, hit rate, trimmed mean and the best-10 share at 1x, 2x and 3x for both books.

## Power
The decision data are about 250 NYSE days a year. With a daily SD near 650 bp, an expected t of 2 needs a true mean of
about +61 bp/day at 500 days (R300's re-price at MEXC cost, which is on seen days and the winner of 24). At half that mean,
the expected t at 500 days is about 1.05 and a PASS is unlikely; at 125 days an expected t of 1 needs the full +61. So the
honest reading: the lane is a slow test with a low chance of a PASS, a high chance of a clear NULL if the edge is
absent, and it reports a stable estimate of the daily mean either way. The yearly gross of R300 (positive in every
calendar year) is the reason to run it, not a promise.

## Reported (not decided on)
Book B alongside M; both books' gross, funding, cost, nets at 1x/2x/3x, hit rate, the 10 best days' share, the leg split
(longs against shorts, versus the 50-name basket), missed and unpriced counts, "stopped" legs, flagged spreads, the eligible
counts, and `lab.gate.go_real` on M's 1x series as a descriptive check. A comparison to R300's validation numbers
(same signal on new days) belongs in the FINDINGS.

## Evidence lineage and admission
- **Methods:** M318 (parent), M235 (the video that prompted the re-price), candidate C17.
- **Parent rounds:** R300 (`intrars_v1`, NULL; 24 books; pick chosen on discovery). Neighbours named in M318: R245, R290,
  R293 (seen-data NULLs on daily reversal and clock effects); not a source of this rule.
- **Decision group:** the US-open leaders signal. One cell decides. R300's own history and this lane's days are different
  samples; a batch-2 read of C17 on 2020 (reserved) is a separate frozen PREREG and is **not pooled** with this lane unless
  that PREREG says so before it reads.
- **Samples:** days from 2026-10-29 on, recorded live; nothing overlaps R300's windows (to 2026-09) or any reserved sample.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`. Met: forward and
  point-in-time; ticket frozen before entry; cost sensitivity at 1x/2x/3x; one pre-named decision with futility; trimmed
  mean. Left unmet: gate 1 needs 500 scored days; gate 2 (execution evidence from calibration orders on MEXC) and gate 3
  (account risk) are not touched by a paper lane.

## Stop rules
- The lane's verdict is read at the 125th scored M day (futility only) and the 500th. Nothing is retuned: no other hour,
  coin count, universe size, ranking window, hold, venue, cost model or threshold. A different idea is a new lane.
- A ticket written wrongly (a data fault) is not edited; the journals are append-only and a note in `NOTES.md` names the
  day, the fault, and whether the day counts. A fault in the daemon is fixed in the daemon with a test, without touching the
  rule file; if the fix changes what a day means, the lane is stopped and re-registered.
- No orders, no money, no credentials.

## Known limits (written before the first day)
- **The proxy for spread.** The half-spread is the ticker recorder's one snapshot of the hour, taken about 15-17 minutes
  after the hour (so 12-14 minutes after a fill at D + 3 minutes or 24:00 + 3 minutes), not the book at the fill. An hour
  with no snapshot file uses 10 bp and is flagged. On 14:00 UTC US-open days the book is often wider than at that snapshot. The fill
  itself is the one-minute bar's open, which does not tell the size a $10k market order would have moved. Calibration orders
  are the only cure and are not yet authorized.
- **Hand execution.** Six orders in the first two minutes after 10:00 New York, and six at 24:00 UTC, by hand, is hard to do
  on the clock; the three-minute lag is a guess at what a person manages. A person may also not be able to short every MEXC
  perp on the web terminal. The lane records the picks; it does not check the terminal.
- **Calendar.** NYSE days come from `lab.sessions`, which is not frozen. A holiday table fault would be seen in the tickets.
- **Crypto-listed TradFi perps** move with the stock open; a day's picks can be an equity-index perp. This is part of
  R300's universe and is kept.
- **Funding sign and window** differ between B and M by design (M holds across the 00:00 settlement), so B is not an exact
  replica of M's cash flows.
- **The container** must stay up through each D; a missed D is a missed day, logged, not repaired. Hourly klines for the
  bar closing at D are served a few seconds late; the daemon retries until the 2-minute deadline.

## Code
```fixed
dba0257e4877d2bbd81603447d5e213cf24496752329da87ee41926e72817af6 scripts/usopen_rule.py
```

| File | sha256 at this freeze | After the freeze |
|---|---|---|
| `scripts/usopen_rule.py` | dba0257e4877d2bbd81603447d5e213cf24496752329da87ee41926e72817af6 | fixed: the daemon checks it and this file before every tick and stops if either changed |
| `scripts/forward_usopen.py` | not hashed | the daemon: ticketing, scoring, journals. Operational; changed only with a test and a note in `NOTES.md` |
