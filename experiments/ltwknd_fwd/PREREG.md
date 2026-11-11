# PREREG: ltwknd_fwd (R467). R465's Lighter weekend fade, forward, at measured costs and ticketed fills

Freeze with `lab.prereg.freeze()` before the first weekend. Never edited afterwards; a changed idea is a new lane.

- **Registry id:** R467
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w` (the default branch).
  - `scripts/run_ltwknd_fwd.py tick` is the only writer of `experiments/ltwknd_fwd/journal/tickets.csv`. It runs in
    `.github/workflows/claude-ltwknd-tick.yml`.
  - `scripts/run_ltwknd_fwd.py score` is the only writer of `journal/a_trades.csv`, `journal/b_trades.csv` and
    `journal/status.json`. It runs daily in `.github/workflows/claude-ltwknd.yml`.
- **Date registered (UTC):** 2026-11-11

**Method:** M515. **Parent:** R465 (`ltwknd_v1`, PREREG `874ffe52…`), whose frozen stop rule earns this lane: "a
PARTIAL earns a forward paper lane on Lighter under a new id, with tickets at E and recorded Lighter book costs, never
a trade." **Sibling:** R463 (`xyzwknd_fwd`), the same rule forward on trade.xyz.
- **Paper only:** public endpoints, no account, no key; nothing in the code can place an order.

## Question
R465 found that R462's weekend fade replicates on Lighter's US-stock perps at a zero fee: a move of 50 bp or more from
Friday 20:00 to Sunday 19:00 New York, faded from Sunday 19:00 to Sunday 22:00, gave +45.3 bp per market-weekend before
costs in sample A (p 0.005) and +35.6 bp in B, but -1.3 bp in the unseen sample C (February to April 2026). Its prices
were last trades and its 4 bp cost unit assumed.

On fresh weekends from 2026-11-13, at Lighter's listed fee and the recorded cost of a $1k market order, is the mean net
per traded weekend above 0 (one-sided weekend-bootstrap p < 0.01 at 20 traded weekends or p < 0.04 at 30)? And do
point-in-time tickets, decided at Sunday 19:00 and filled by walking Lighter's live book, agree?

## Why this lane
- **R465's frozen rule asked for it** after its PARTIAL.
- **The owner asked on 2026-11-11 that real trading match paper.** Measure B below is what an automated account would
  have done at each instant: decide from the data then available and take the live book. A PASS needs it.
- **Lighter is the cheapest venue reachable from France for this trade.** Its Standard account pays 0 maker and 0
  taker (wave 7, lens 4; `orderBookDetails` lists 0.0000 for all 50 markets on 2026-11-11), and its terms do not
  exclude France (`docs/reviews/venue_access_fr_20261110.md`). The book is the whole cost.
- **Not an independent confirmation of R463.** On the 706 market-weekends R462 and R465 share, the two venues' weekend
  moves correlate at 0.96. The two forward lanes will trade largely the same events at two costs; they are read
  together, never as two samples.

## What the author has seen
- R462's, R463's, R465's and R466's PREREGs, FINDINGS and results: every weekend from 2026-02-27 to 2026-11-06 on
  Lighter and from 2026-05-01 on trade.xyz.
- **R465's post-hoc reading:** sample C's overshoot came back on Monday 04:00-06:00, not Sunday evening, probably
  because Lighter's equity oracle (Pyth Pro) did not carry the Blue Ocean overnight session before mid-2026. Pyth
  moved its overnight feeds to Pyth Pro on 2026-06-15. This lane keeps R465's X1 exit unchanged.
- **Book data:** `lighter/books/` on `claude/xyz-books-data`: the column names, from `scripts/record_lighter_costs.py`.
  No cost, spread or depth value of these markets has been read.
- **Plumbing, counts only.** On 2026-11-11 the author ran this lane's code once on live endpoints, against the weekend
  of Friday 2026-11-06 (in R465's sample B, before the first weekend, in no statistic here):
  - `Venue.fees`: 243 perps listed, all 50 universe ids found.
  - `entry_ticket` on the first 5 universe markets: 5 tickets `ok`, the book walk and mid filled.
  - `score_a` on the same 5 markets with no book file: 5 `ok`, 10 fallback fills; 243 hourly candles (all traded) and
    9 funding rows a market.
  - No price, W, cost or return was printed.
- **Code tests:** `tests/test_ltwknd_fwd.py` on a stub venue and a fake clock.

## Data
- **Prices and funding:** Lighter's public API by market id: `candles` (resolution 1h; t, close, volume) and `fundings`
  (hourly; signed + when longs pay, as `lab/carrylane.py`), through `lab/carrylane.py`'s paced client (60 requests a
  minute). `orderBookDetails` for the listed taker fee; `orderBookOrders` (100 orders a side) for tickets.
- **Recorded books:** `lighter/books/` on `claude/xyz-books-data` (`scripts/record_lighter_costs.py`, hourly on GitHub):
  the cost in bp from mid of a $1k and a $10k market order on each side, walked through the first 100 orders a side.
- **Universe:** R465's frozen `experiments/ltwknd_v1/universe.csv` (50 markets, with Lighter market ids, as listed on
  2026-11-11; 48 active, 2 inactive). Markets listed later are not added.
- **Calendar:** `scripts/xyzwknd_rule.py` (NYSE holidays from `lab.sessions`, early closes).

## Rule
Constants are in `scripts/run_ltwknd_fwd.py`; the weekend rule is R462's, imported unchanged from
`scripts/xyzwknd_rule.py`, with R465's price preparation. Times are New York local time (DST-aware) unless marked UTC.
- **Weekends:** every Friday from 2026-11-13 that R462's rule accepts: Friday a full NYSE trading day (not an early
  close) and Monday a trading day. Other weekends are skipped.
- **Instants:** R = Friday 20:00; E = Sunday 19:00 (the decision and entry); X1 = Sunday 22:00 (the exit).
- **Prices (R465's):** the hourly candles that traded (volume > 0 and close > 0). P(T) = the close of the last such
  candle that opens in [T − 3 h, T − 1 h] (R462's `price_at`). W = 0 or a missing price: `unpriced`.
- **Eligible market:** in the universe, with a first hourly candle (traded or not) at least 7 days before R, and not
  before its IPO date (R462's rule).
- **Signal:** W = 10,000 × ln(P(E) / P(R)) in bp.
- **A trade:** |W| ≥ 50 bp. Fade: short when W > 0, long when W < 0. Otherwise `no_trade`.

**Measure A (decides).**
- **Return:** R462's g_x1 in bp: side × 10,000 × ln(P(X1) / P(E)), plus the funding the side receives over the hourly
  settlements in (E, X1].
- **Fee:** one taker fee a fill, as Lighter lists it for the market in `orderBookDetails` at the scoring run (a
  percent; × 100 for bp). It was 0 for all 50 markets on 2026-11-11.
- **Book cost:** the $1k market-order cost on the side traded (buy to enter a long, sell to exit it; the reverse for a
  short), from the market's `lighter/books/` snapshot nearest the instant (E for the entry, X1 for the exit) if it is
  within 90 minutes. Otherwise the fill costs 10 bp, counted.
- **Net:** g − k × (fees + book costs), k = 1, 2, 3. Reported only: the same at the $10k cost.

**Measure B (tickets).**
- At E, `tick` fetches each market's hourly candles, computes W as above from what is then available and, for a trade,
  walks Lighter's live book (`orderBookOrders`, 100 orders a side) for a $1k market order on the fade side with the
  recorder's arithmetic (`record_lighter_costs.impact`). It records the wall time, mid, the walked cost from mid, and
  the fee listed in `orderBookDetails` at that moment (0 if that request fails).
- At X1, it walks the book again on the other side for each entry ticket.
- A tick run that starts up to 70 minutes early sleeps to the instant. No entry ticket is taken later than E + 30
  minutes; a weekend without one has no B trade. An exit not ticketed by X1 + 6 hours is priced at the market's first
  recorded snapshot in [X1, X1 + 6 hours] (mid and $1k cost), flagged `recorder`; with none, the trade is `unpriced`.
- **Return:** side × 10,000 × ln(exit mid / entry mid), plus funding over the settlements in (entry, exit] (wall
  times), minus k × (both fees + both walked costs).
- **Timing:** `claude-clock.yml` dispatches the tick workflow on Sundays at 18:10 and 21:10 New York; the workflow's own
  crons are a second path. The clock is infrastructure, not an input: the tick's guards above bound the timing.

**Scoring.** A weekend is scored once, at the first daily run at least 3 hours after X1 once the recorder holds a
snapshot at or after X1 + 90 minutes, or regardless 48 hours after X1. A fetch error leaves the whole weekend for the
next run; after X1 + 7 days, a market whose fetch still fails is written `venue_error` and the weekend is scored. Rows
are append-only.

**Weekend net.** The mean net over the markets traded that weekend. A weekend with no trade is not counted.

## Decision
On A's traded weekends in calendar order, with weekend nets at 1x. Bootstrap p: the share of 10,000 means of whole
weekends, drawn with replacement (seed 467), at or below 0.
- **NULL (futility):** at 15 traded weekends, if the mean of the first 15 is at or below 0. Later weekends cannot
  change it.
- **A passes at a look** (20 traded weekends with p < 0.01; 30 traded weekends with p < 0.04), over the first 20 or 30
  weekends, when all hold:
  - the mean at 1x is above 0 with that p;
  - the mean at 2x is above 0;
  - the mean without the best 3 weekends is above 0.
- **Tickets agree** at a look when B has a trade on at least two thirds of those weekends and B's mean weekend net at
  1x over them is above 0.
- **PASS:** at the first look where A passes and the tickets agree.
- **At 30 traded weekends otherwise:** NULL if A does not pass; PARTIAL if A passes but tickets cover fewer than two
  thirds of the weekends; NULL if A passes and the tickets' mean is at or below 0 (paper that cannot be executed).
- Between looks the lane is pending. The looks' alphas sum to 0.05.
- A PASS earns a request to the owner for small calibration orders on Lighter (hard rule 5), the gates in
  `docs/GATES.md`, and `lab.gate.go_real()`. It does not authorize real money.

## Costs (1x, 2x, 3x)
1x is the measured cost above. FINDINGS reports A and B per traded weekend and per trade at 1x, 2x and 3x: mean,
bootstrap p, hit rate and the mean without the best 3. It also reports:
- A at the $10k cost;
- the A-minus-B gap on common trades, the entry tickets' delay after E, funding, fallback fills and status counts;
- **reported only, not decided on:** R463's and R467's results on the weekends both trade, and, where both lanes
  ticketed the same stock at E, the gap between the two venues' mids (M524's question at walked books, as R466's
  FINDINGS asked).

## Trials
One rule, one exit, one decision; B is a condition on it, not a second test. **Trials:** 1. Program trials before:
9,785,184 (9,785,185 after). R465's 32 trials were counted in its row. Read against `registry.program_trials()`.

## Power
Resampling R465's weekends (2,000 runs of this Decision without B; weekend means of g_x1 over |W| ≥ 50 bp, minus an
assumed round-trip book cost), and the same weekends shifted to a mean of 0 for the size:

| weekends resampled | gross mean / SD per weekend | trades a weekend | PASS at 4 / 10 / 20 bp | futility at 10 bp |
|---|---|---|---|---|
| A + B (24) | +43.6 / 76.4 bp | 18.2 | 91% / 79% / 49% | 4% |
| A + B + C (32) | +31.5 / 83.6 bp | 16.1 | 54% / 39% / 18% | 15% |

- At a zero mean the rule passes about 5.4% of the time (1.8% at the 20th traded weekend, 3.6% at the 30th).
- These are in-sample effects, likely smaller forward. C shows that the effect can vanish for whole months.
- About 4 weekends a month trade, less holidays: the futility read in about March 2027, the interim in about April and
  the final read in about June.

## Stop rules
- Nothing is retuned: no other threshold, instant, universe, size, venue or exit. The `rel` book, R465's 100/200 bp
  cells and the Monday exits stay diagnostics. A changed idea is a new lane.
- A fault in the script is fixed with a test and a note in the lane's README. If the fix changes what a scored
  weekend means, the lane is stopped and re-registered.
- If Lighter documents a change to its equity oracle's hours or source, or starts charging Standard accounts, the
  weekends after the change are reported separately and the lane is re-registered.
- No orders, no money, no credentials.

## Known limits (written before the first weekend)
- **Last trades.** A's prices are hourly candle closes of traded candles, as in R465. B prices the same decisions at
  the walked book.
- **One snapshot an hour.** A's nearest snapshot can be up to 90 minutes from the instant.
- **Tick timing depends on GitHub.** A dispatch starts within seconds, but a lost clock run or a GitHub outage leaves a
  weekend without B tickets; the two thirds coverage condition bounds that. The tick takes about two minutes (50
  paced candle requests, then the books).
- **Size.** $1k a fill, read from the first 100 orders a side. Weekend depth on thin names may cap size; the $10k cost
  and the 2x and 3x reads bound that.
- **Corporate actions.** Lighter delists and settles a market on a split or other corporate action (wave 7, lens 3).
  Such a market's later weekends become `not_listed` or `unpriced`; it is not replaced.
- **The fee field.** `taker_fee` is read as a percent, like Lighter's funding rate. It was 0 everywhere at the freeze,
  so the unit matters only if Lighter starts charging.
- **Correlated markets.** One weekend's moves share a market factor, so a weekend counts once, as its mean.
- **Latency.** The Standard account's taker delay (about 300 ms) is far shorter than the tick's own delay.

```inputs
54052ba2cd401685b8ced8b24bd5633e48300b0ed29142a21cc5e73378adb758  scripts/run_ltwknd_fwd.py
0c34b89f19a8a8221337aa59ede724b29217aa746beeb5799d2b2e739660d614  tests/test_ltwknd_fwd.py
874ffe525ca5c2927b6ce78f738997fe087176a48f63f402835f09cb7cc504a6  experiments/ltwknd_v1/PREREG.md
a4d7d0f4dcca6a857c69ca620ce374f118fa70423f236de5b6fedff9bb42bc28  experiments/ltwknd_v1/universe.csv
b5e0700e75432eb3b651e6ab22295f2519ad8b16601fa824fa0f03f05ab1539a  scripts/xyzwknd_rule.py
831fe1dfa2c794bc0467137bb10f9395895ecddecfffcbc860b2c6273faae18d  lab/sessions.py
12efdca302dfdbc1312dc7499a53de23af9276406e1934c547b9e8642622e895  lab/carrylane.py
f691695930719a89ae4ededcd5b952f3aa6aabefbe8ea939970acd009e16b297  scripts/record_lighter_costs.py
8f6d2857edd32dd33a2afa49c1f183a4432f7214f8159957f21ba2df721e1e8b  .github/workflows/claude-ltwknd-tick.yml
d0a28d4fccac63fcf7b2a9cc61f7782fcae54d24d76817125b3d84ac1afcb3eb  .github/workflows/claude-ltwknd.yml
```
