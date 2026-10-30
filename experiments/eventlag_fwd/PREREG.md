# PREREG: eventlag_fwd (R369). When an EIA release moves Binance or Hyperliquid, does Lighter still show the old price long enough to pay a taker's catch-up?

- **Registry id:** R369
- **Owner (single writer):** Claude, this session (cloud container, 2026-10-29)
- **Date registered (UTC):** 2026-10-29

Methods M444 (EIA releases), M443 (venue disagreement on the 24/7 commodity perps), from the owner's fifth pasted review
of 2026-10-28. A forward paper lane: frozen before the first release it scores (natural-gas storage, 2026-10-29 14:30
UTC), by `lab.prereg.freeze()`. After the freeze this file is never edited; a changed idea is a new lane.

## Question
At each scheduled EIA release (natural-gas storage on Thursdays, crude on Wednesdays) from 2026-10-29 to 2026-12-31,
when the mid of Binance's or Hyperliquid's perpetual has moved a large amount from its own pre-release level, has
Lighter's displayed quote moved by less than half of it one second later? If so, does buying (or selling) Lighter's stale
touch and closing it at T + 60 s earn more than two cost units, counting only what the recorded quotes show?

## Why this lane
- R368 (`experiments/eventdrift_v1`) showed on Binance minute bars that the EIA releases are visible on these perps (the
  gas perp's median first-minute move is 48.7 bp against 3.5 bp for a normal minute) and that nothing continues after the
  first minute at a taker cost. The remaining open question is the first seconds across venues: the three 24/7 venues
  have different feeds, books and participants, so a fast jump on one can sit on another for a while. That question
  cannot be answered from history: tick-level quotes of these venues exist only from the moment they were recorded
  (Lighter from 2026-10-28 22:29 UTC, Binance and Hyperliquid from 23:56 UTC). Every release that passes unrecorded is lost.
- Lighter is the follower because it is the venue the lab can reach at the lowest cost: its market listing shows a 0
  fee, observed per-account fees were 0.28-2.66 bp, and its quote feed reaches this container about 30 ms after the
  venue's own stamp. The leaders are Binance (about 60 ms) and Hyperliquid (about 350 ms).
- A NULL is the likely result: R347 and R348 found Lighter's makers close a lead over Binance within a second on crypto.
  A scheduled jump is a different regime from ordinary flow, which is why it is worth one registered test. The lane is
  paper only: nothing here places an order, and the order path to Lighter from this container is not measured.

## What the author has seen
- **Recordings.** For quality control only, the author looked at row counts, update gaps, receive-minus-venue delays and
  top-of-book sizes of the Lighter, Hyperliquid and Binance NATGAS and crude quotes of 2026-10-28 22:29 to 2026-10-29
  00:12 UTC: Lighter NATGAS ticker 0.03 s median delay (quotes are bursty: median gap 0.04 s, 90th percentile 14 s),
  Hyperliquid 0.35 s, Binance 0.06 s; the touch shows about 500-1,000 units on Lighter NATGAS. **No move, lag or
  catch-up around any release has been looked at; no release has happened inside the recordings.**
- **R368.** Its diagnostics (Binance one-minute bars, 60 releases) set the thresholds below: the median absolute
  first-minute move was 48.7 bp for gas and 11.1 bp for crude, the median normal minute 3.5 and 4.4 bp. The lane's
  decision data (tick quotes after 2026-10-29 14:30 UTC) are disjoint from them.
- **Code.** The rule and runner were exercised only on synthetic quotes (a planted 4-second lag on Lighter, a world
  without lag, a revert, a thin book; `tests/test_eventlag.py`). That says nothing about the real venues.
- **Not used:** Kraken's ticker (about one update a second, too coarse).

## Data
- Quotes with the local receive time in microseconds: Binance `data/commodity_perps/bnbook/{NATGASUSDT,CLUSDT}`
  (bookTicker, at most one row per 100 ms), Hyperliquid `data/commodity_perps/hlbbo/{NATGAS,CL}` (bbo on change),
  Lighter `data/lighter_trades/quote/{NATGAS,WTI}` (ticker on change). Columns read: `t, bid, bq, ask, aq`. Rows with a
  non-positive bid, a crossed book or a zero size are dropped.
- Events: `experiments/eventlag_fwd/events.csv`, 19 releases from 2026-10-29 to 2026-12-31 (10 gas, 9 crude) built by
  `scripts/eventlag_calendar.py` from the two EIA schedule pages read on 2026-10-28 (instants in UTC: gas storage
  2026-10-29 14:30; 15:30 from 2026-11-04 when US clocks go back; the Veterans Day and Thanksgiving shifts are in the
  script). Nothing before 2026-10-29 14:30 UTC is scored.
- An event is **valid** when each of the three venues has a reference (below) and at least one quote in the 60 s after the
  release. Otherwise it is recorded `invalid:<venue>:<why>` and not scored: a recorder outage is not a loss. It is
  scored 15 minutes or more after the release, once, and the journal is append-only.

## The rule
All times are the recorder's local receive clock. T is the release instant.
- **Reference.** For each venue, m0 is the median of the mid at the 51 one-second marks from T - 60 s to T - 10 s, the mid
  carried forward from the last quote at each mark (a quote older than 300 s does not count; at least 25 marks needed).
- **Crossing.** The leader venues are the two venues that are not the follower. t* is the first receive time at or after T
  and within 60 s of it at which a leader's mid is at least THETA bp from its own m0: THETA = **20 bp for gas storage,
  8 bp for crude**. The sign of that move is s; the venue is the lead.
- **Decision.** t_d = t* + L, with L the seconds from the crossing to the order reaching the follower's book. Decision L
  = **1.0 s**; also computed at 0.5, 2 and 5 s. D is the largest s-signed displacement among the leaders at t_d (their
  last quotes at or before t_d); skip if D < THETA ("reverted"). The follower's displacement at t_d divided by D, signed
  with s, is c. The **lag filter** keeps the trade when c <= 0.5.
- **Entry.** The follower's touch at t_d on the side of s (buy its ask if s > 0, sell its bid if s < 0). Skipped if the
  touch shows less than $250 of size ("no_size").
- **Exit.** The opposite touch at T + 60 s.
- **Gross** = s * 1e4 * ln(exit / entry), in bp; the spread of both touches is inside it. **Net** = gross - k * 2 * fee,
  k = 1, 2, 3, with fee per side of 2.5 bp (Lighter), 9 bp (Hyperliquid), 5 bp (Binance).
- **Primary follower: Lighter.** Hyperliquid and Binance are also scored as followers at L = 1 s (leaders: the other two),
  reported only.
- **Placebo.** The same rule at the same clock time on two days with no release of that kind at that time (gas: 2 and 3
  days before; crude: 1 and 2 days before), Lighter at L = 1 s, to show how often the rule fires and what it earns
  without news. Reported only.

## Trials
Lighter as follower: 2 event types x 4 latencies x {lag-filtered, unfiltered} = 16 cells; Hyperliquid and Binance as
followers: 2 types x 2 followers x {filtered, unfiltered} at L = 1 s = 8 cells. **24 cells, 2 decisions** (each event type,
Lighter, L = 1 s, lag-filtered). Registry trials: 24. Program trials before: 9,479,149 (9,479,173 after).

## Decision
For each event type, over its valid events: the lag-filtered Lighter trades at L = 1 s, their mean gross, and the
one-sided sign-flip p-value for "the mean is above 0" (exact up to 18 trades, otherwise 200,000 random flips, seed 369),
Holm-adjusted over the two types. The **first read** is made when every type that has a decision cell has at least 8
valid events and 6 lag-filtered trades (the 8th gas release is 2026-12-17, the 8th crude one 2026-12-23), and no earlier;
interim tables are descriptive.
- **PASS:** at least 6 lag-filtered trades, a Holm p at most 0.05 and a mean gross above 10 bp (two cost units of 5 bp,
  so the 2x net is positive).
- **PARTIAL:** the same with the mean above 5 bp (one cost unit) but not above 10.
- **INCONCLUSIVE:** no type has 8 valid events and 6 lag-filtered trades.
- **NULL:** otherwise.

## Costs (1x, 2x, 3x)
One cost unit is a Lighter round trip of 5 bp (2.5 bp a side, the top of the 0.28-2.66 bp observed for individual
accounts; a zero-fee account would do better). 1x, 2x, 3x subtract 5, 10, 15 bp from every gross mean. The spread of both
touches is already in the entry and exit prices. 2.5 bp is an assumption about the owner's account tier, not a quote.

## Power
Not computed before the data: the per-trade spread is unknown. At 8-10 valid events and perhaps 6-9 filtered trades, only
an effect of the order of the trade's own standard deviation can reach a Holm p of 0.05 (the smallest exact p at 6
trades is 1/64). A NULL here means "no large lag was seen in about 8-10 releases", not "no lag". The lane exists because
tick data cannot be bought back for releases that were not recorded, and because each release adds a sample.

## Reported (not decided on)
Every cell's n, mean, sd, t, hit rate, p and 1x/2x/3x nets; status counts (ok, no_cross, reverted, no_size, no_quote,
no_ref); c and t* by event; the unfiltered cells; Hyperliquid and Binance as followers; the placebo fire rates. They explain
a result and open nothing.

## Code
```inputs
67cd99094719a57a201a10dbc0a2162ac6232ab5219c05a7bb03317380024564  experiments/eventlag_fwd/events.csv
58908ff864fabf23c7686a718f6ad5617bbba64b6fb59ab11badac4bdc3d2fd1  scripts/eventlag_calendar.py
9487b60dfed5424902c511a53dbfbb0c2446513db908e657576f313606b59534  scripts/eventlag_rule.py
78053fb00e9a8875379f9ac307585ce843f8c365ded2994672c90e66331dffc6  scripts/run_eventlag.py
```
The recorders (`scripts/record_commodity_perps.py`, `scripts/record_lighter_trades.py`) are not frozen and the runner does
not import them: only the file layout above is.

## Evidence lineage and admission
- **Methods:** M444, M443 (related: M441, M447, R368, R347, R348). **Parents:** R368 (thresholds only).
- **Decision group:** M444/M443's tick-level cross-venue form on EIA releases. Two decision cells; everything else is a
  diagnostic.
- **Samples:** releases from 2026-10-29 14:30 UTC, recorded live; nothing overlaps an archive any lane read.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`. Met: one verdict
  from two pre-named cells; multiplicity (Holm over 2, 24 cells counted); cost sensitivity; forward and point-in-time.
  Left unmet: gate 1 needs far more releases than 2026 holds; gate 3 (account risk); a fill model (see limits).

## Stop rules
- The lane ends at its first read, or when the calendar runs out on 2026-12-31 with fewer valid events (then
  INCONCLUSIVE). Nothing is retuned: no other threshold, latency, hold, follower, event type or window; extending to 2027
  releases or to other events (US macro, the weekend reopen) is a new lane that may reuse the runner.
- What a PASS earns: a note to the owner asking for a small calibration order on Lighter to measure the real fill and
  latency (hard rule 5: orders need the owner), and a continued forward lane. What a PARTIAL earns: the same note
  with the measured caveat. What a NULL earns: M443/M444's tick-level cross-venue form closes NULL for Lighter as
  follower on EIA releases in 2026.
- No orders, no money, no credentials. The run reads recordings and writes `experiments/eventlag_fwd/journal/` and
  `results/`.

## Known limits (written before the run)
- Entries and exits are the displayed touch of a public feed with its own delay; a real order meets a different book. The
  queue, cancels by market makers inside the feed delay, partial fills and rejects are unobserved, and a stale quote on a
  public ticker may be gone from the matching book. No fill is confirmed by a trade print.
- L = 1 s is an assumption about the whole path (a leader's quote reaches this container 0.06-0.35 s after the venue's own
  stamp, the order must travel back). The container's clock against UTC is not measured, so T can be off by a fraction of a
  second; an early T makes the rule skip (the follower has already moved), a late one makes the reference include the
  jump (no crossing).
- Eight to ten releases of two types is one regime, and the thresholds come from minute bars of another venue (R368).
- Gas and crude jumps may be two-sided in the first seconds; the rule takes the first threshold crossing only.
- The recorders may be down (container restarts); a venue without a reference or without quotes after T makes the
  event invalid and uncounted, never a loss.
