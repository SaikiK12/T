# PREREG: eventdrift_v1 (R368). After an EIA release, do Binance's crude and gas perpetuals keep going the way their first minute went, far enough to pay a taker round trip?

- **Registry id:** R368
- **Owner (single writer):** Claude, this session (cloud container, 2026-10-29)
- **Date registered (UTC):** 2026-10-29

Method M444 (EIA weekly releases, from the owner's fifth pasted review of 2026-10-28). Frozen by `lab.prereg.freeze()`
before any return, first-minute reaction or test of the bars is computed. After the freeze this file is never edited; a
changed idea is a new lane.

## Question
On the 30 Weekly Petroleum Status Report releases (crude oil, Wednesdays) and the 30 Weekly Natural Gas Storage Report
releases (Thursdays) between 2026-04-01 and 2026-10-22, trading Binance's CLUSDT and NATGASUSDT perpetuals: when the
price has moved one way in the minute after the release, does it keep moving that way over the next five minutes by
more than a taker round trip costs?

## Why this lane
- The owner pasted four reviews recommending structural, event-driven mechanisms in place of generic chart rules, and
  said "Now WE need to produce edges data pnl". One of them is a second-stage drift after the EIA crude release:
  the review reports that a Journal of Financial Economics paper finds positive news incorporated within about half a
  second while negative news keeps drifting for about five minutes, and that Topstep restricts Tier-1 windows while
  FTMO Futures and FundedNext Futures allow news trading. **None of that has been read or checked here** (the paper, the
  firm rules): it is a reported claim, which is why the lane is a test and not an assumption.
- This lane does not test the paper. It has no consensus or API surprise and no CME ticks, so the news sign is the
  market's own first-minute move, and the data are one-minute bars. It asks the cheapest version of the question that
  the data held can answer: is there a drift in the direction of the first minute at all, and is it larger than a taker
  cost? A result here either closes the cheap version or justifies asking for tick data (an owner decision, rule 5).
- Binance lists crude (CLUSDT), Brent, natural gas (NATGASUSDT), gold, silver, QQQ and SPY perpetuals that trade around
  the clock; their one-minute archive from 2026-04-01 is public and SHA-verified, so the 6-month window needs no
  purchase. The same perps are recorded live from 2026-10-28 23:56 UTC (`scripts/record_commodity_perps.py`), so a
  forward replication at tick level has started.
- A NULL is the likely result and is recorded as one. The sample is small (see Power), so a NULL means "no drift larger
  than the stated minimum detectable size was seen", not "no drift".

## What the author has seen
- **Calendar.** `experiments/eventdrift_v1/events.csv`, built by `scripts/eventdrift_calendar.py` from the rules on
  EIA's two schedule pages (read 2026-10-28; see the script's docstring for the URLs and the holiday exceptions inside
  the window). No price was consulted.
- **Bars.** `scripts/fetch_tradfi_perps.py` fetched the archive. The author has looked only at row counts and the first
  and last bar of each symbol (`data/tradfi_perps/klines_1m/manifest.json`; CLUSDT 301,860 rows from 2026-04-01 09:00
  UTC, NATGASUSDT 301,840 rows from 2026-04-01 09:20 UTC, both to 2026-10-27 23:59 UTC) and a coverage count: all 60
  events have all 12 bars T-1 .. T+10. **No price, return, reaction, sign, volume or test of the bars has been
  computed or looked at.**
- **Code.** The rule and runner were exercised only on synthetic worlds (a planted drift and a world with none;
  `tests/test_eventdrift.py`). That says nothing about the real data.
- **Related evidence.** No earlier lane read these bars (`data/tradfi_perps` is new). R-lanes on MEXC TradFi perps used
  other instruments and other questions.

## Data
- `data/tradfi_perps/klines_1m/CLUSDT.parquet` and `NATGASUSDT.parquet`: Binance USD-M one-minute klines from
  data.binance.vision, each archive file checked against its published SHA-256, assembled by `lab.data.build`. Columns
  read: `t` (bar open time, epoch ms), `open`, `close`. `docs/provenance/tradfi_perps.json` holds the file hashes. The
  runner re-hashes both parquet files against `manifest.json` before it reads them.
- `experiments/eventdrift_v1/events.csv`: 60 releases. WPSR is Wednesday 10:30 ET (14:30 UTC in the window; Thursday
  16:00 UTC on 2026-05-28, 2026-09-10 and 2026-10-15 because of holidays). NGS is Thursday 10:30 ET (14:30 UTC).
- Window: releases from 2026-04-01 to 2026-10-22. WPSR events are tested on CLUSDT, NGS events on NATGASUSDT.
- An event is usable when all of bars T-1 .. T+10 exist and are positive. An unusable event is dropped and counted;
  nothing is filled or interpolated.

## The rule
All times UTC; a bar is labelled by its open time; T is the release instant (a bar open time).
- **Reaction.** r0 = 1e4 ln(close_T / close_{T-1}), in bp: the first minute from the last price before the release.
  Known at T + 60 s. Events with r0 = 0 have no sign and are dropped from every subset.
- **Entry.** The open of bar T+1, in the direction sign(r0) (long if the first minute rose, short if it fell). A
  **late entry** variant enters at close_{T+1}.
- **Exit.** The close of bar T+h, h minutes held; h in {1, 2, 5, 10}.
- **Move.** move_h = 1e4 ln(close_{T+h} / open_{T+1}). **Continuation** x_h = sign(r0) * move_h, in bp, before costs.
  The late variant is x = sign(r0) * 1e4 ln(close_{T+5} / close_{T+1}).
- **Subsets.** `all` (r0 not 0), `neg` (r0 < 0), `pos` (r0 > 0), per event type.
- **Test.** For each cell, the one-sided sign-flip randomization p-value of "the mean of x is above 0": the share of the
  2^n sign assignments whose mean is at least the observed one (all of them for n up to 18, otherwise 200,000 random
  ones plus the observed, seed 368). It is exact under the null that each continuation is as likely to go either way.
- **Decision cells** (the only two the verdict reads), both at h = 5 minutes with entry at the open of bar T+1:
  - **D1:** WPSR events on CLUSDT, subset `neg` (the review's claim concerns negative news, which here means a falling
    first minute).
  - **D2:** NGS events on NATGASUSDT, subset `all`.
  Holm adjustment over these two p-values.

## Trials
Per event type: 3 subsets x 4 horizons = 12 cells, plus 1 late-entry cell for each decision cell = 13. Two event types:
**26 cells**, of which 2 are decision cells. Registry trials: 26. Program trials before: 9,479,123 (9,479,149 after).

## Decision
- **PASS:** a decision cell has at least 10 usable events, a Holm-adjusted p at most 0.05 and a mean continuation above
  2 cost units (24 bp), so that the 2x net is positive.
- **PARTIAL:** the same with the mean above 1 cost unit (12 bp) but not above 2.
- **INCONCLUSIVE:** neither decision cell has 10 usable events.
- **NULL:** otherwise.
Nothing else is decided on. A PASS or PARTIAL would earn a forward replication, not trading (see Stop rules).

## Costs (1x, 2x, 3x)
One cost unit is a round trip of 12 bp of price: 5 bp taker fee each way (Binance's standard USD-M taker rate, an
assumption; the TradFi perps' own fee schedule was not read) plus 2 bp for the spread and slippage of both fills. 1x, 2x,
3x subtract 12, 24, 36 bp from every mean; the verdict reads the 1x and 2x levels as above. Spreads around releases are
wider than usual and were not measured for this window, so the 1x unit may be too low; higher costs only make the
results worse. The mean is also the break-even cost a round trip can carry.

## Power (stated before the run, computed from the sample size and the realised spread of the cells)
The minimum mean the test can detect with 80% power at the smaller Holm threshold (0.025, one-sided) is
MDE80 = 2.8 * sd / sqrt(n), with sd and n the cell's own. The run reports it for every cell. With about 15 negative
crude events and a five-minute continuation spread of a few tens of bp, MDE80 will be of the same order as one cost
unit (roughly 15-20 bp at an sd of 25 bp; 25 bp is an assumption, not a measurement), so a result under the cost cannot be
told from zero. The lane is a screen for a large drift, not a measurement of a small one. A NULL whose MDE80 exceeds
1 cost unit is recorded as "NULL, underpowered" in the FINDINGS.

## Reported (not decided on)
Every cell's n, mean, sd, t, hit rate, MDE80, p and the 1x/2x/3x nets; the per-event table; the late-entry cells;
coverage by event. They explain a result and open nothing.

## Code
```inputs
4b49a67a0d620a9ce71e1f3796cc241bd6d0f06ac014363660c7db22d481d781  experiments/eventdrift_v1/events.csv
1186d1b9324a712ca254e68962474d79f3c5b4a9a2e185613aa216dc184d6051  scripts/eventdrift_calendar.py
93bfebc40d721e37897253bdd98d4af779a2b47c40e8cbe3780a476612ce6d56  scripts/eventdrift_rule.py
15177717d7540e53540168a71d27d13fa658b30df7ad3bdbfed5801ce7973fbe  scripts/run_eventdrift.py
058b04e43a719634895083b3bb87ca9716fda3f2af2c5f41490de27343a4c5e9  scripts/fetch_tradfi_perps.py
1b1ecc7eeef5f8767803bd6e4beadd946c6b635cb287d4c61f490212055fcebb  docs/provenance/tradfi_perps.json
d941bffed424c79f2afddce68f9df4086b1fb345830bb35ba46b8a8583137bd0  data/tradfi_perps/klines_1m/manifest.json
```
The recorder (`scripts/record_commodity_perps.py`) is not frozen and is not read by this lane.

## Evidence lineage and admission
- **Method:** M444 (related: M443, M441, M321). **Parents:** none measured on these bars.
- **Decision group:** M444's cheap one-minute-bar form on Binance TradFi perps. One verdict (above); every other output is
  a diagnostic.
- **Samples:** the 60 releases of 2026-04-01 .. 2026-10-22; no holdout exists inside it. The releases after 2026-10-22
  (natural gas 2026-10-29 14:30 UTC, crude 2026-11-04 15:30 UTC after the US clock change, then weekly) are the forward
  sample and are recorded at tick level.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`. Met: one
  verdict from two pre-named cells; multiplicity (Holm over 2, 26 cells counted); cost sensitivity; power stated. Left
  unmet: gate 1 (a forward, strict on-time sample) and gate 3 (account risk); this lane is a gate-0 screen.

## Stop rules
- The lane ends with the first complete run. Nothing is retuned after it: no other horizon, threshold, entry rule,
  symbol, subset or window; a changed idea is a new lane.
- What a PASS or PARTIAL earns: a forward replication under a new id, on tick data from `data/commodity_perps`, with
  its own PREREG and its own count of at least 20 new releases per event type before any verdict, and a note to the
  owner. It does not earn trading. What a NULL earns: M444's cheap form closes NULL for these two instruments in this
  window; the review's consensus-surprise version stays open, blocked on data the lab does not hold.
- No orders, no money, no credentials. The run reads files and writes `experiments/eventdrift_v1/results/`.

## Known limits (written before the run)
- One-minute bars hide the first seconds, where most of a reaction happens, and the entry at the next bar's open assumes
  a fill at the first trade of that minute with no latency. The late-entry cell shows how much a one-minute delay
  costs.
- The news sign is the market's first-minute move, not a surprise against consensus or the API report. Pre-release
  positioning and the release's own multi-part content (crude stocks, gasoline, distillates, Cushing; storage change
  and its five-year comparison) are not used.
- The instruments are Binance's perpetuals, not CME futures; their price is a derived index with funding, and their
  behaviour at the release instant, availability to the owner (a French resident) and fee schedule were not verified.
- 30 events per type, fewer in a subset, one summer-autumn regime, DST ending on 2026-11-01 (all events are in daylight
  time). A few large moves can dominate a sample this small.
- Overlapping information: crude and natural-gas releases are on different days, so cells of the two types are
  independent; cells of one type reuse the same events at four horizons and are not independent of each other.
