# PREREG: xyzwknd_fwd (R463). R462's xyz weekend fade, forward, at measured costs and ticketed fills

Freeze with `lab.prereg.freeze()` before the first weekend. Never edited afterwards; a changed idea is a new lane.

- **Registry id:** R463
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w` (the default branch).
  - `scripts/run_xyzwknd_fwd.py tick` is the only writer of `experiments/xyzwknd_fwd/journal/tickets.csv`. It runs
    in `.github/workflows/claude-xyzwknd-tick.yml`.
  - `scripts/run_xyzwknd_fwd.py score` is the only writer of `journal/a_trades.csv`, `journal/b_trades.csv` and
    `journal/status.json`. It runs daily in `.github/workflows/claude-xyzwknd.yml`.
- **Date registered (UTC):** 2026-11-11

**Method:** M515. **Parent:** R462 (`xyzwknd_v1`, PREREG `45efb6ff…`), whose FINDINGS earn this lane: "a forward
paper lane under a new id (R463) on fresh weekends from 2026-11-13".
- **Paper only:** public endpoints, no account, no key; nothing in the code can place an order.

## Question
R462 found that fading the weekend move of trade.xyz US-stock perps pays at gate 0: a move of 50 bp or more from
Friday 20:00 to Sunday 19:00 New York, faded from Sunday 19:00 to Sunday 22:00, gave +42.4 bp per market-weekend
before costs in sample A (Holm p 0.004) and +36.2 bp in B. Its prices were last trades and its costs assumed.

On fresh weekends from 2026-11-13, at that day's fees and the recorded cost of a $1k market order, is the mean net
per traded weekend above 0 (one-sided weekend-bootstrap p < 0.01 at 20 traded weekends or p < 0.04 at 30)? And do
point-in-time tickets, decided at Sunday 19:00 and filled by walking the live book, agree?

## Why this lane
- **R462 asked for it**, with fills at recorded book costs and at least 15 weekends before any verdict.
- **The owner asked on 2026-11-11 that real trading match paper.** Measure B below is what an automated account
  would have done at each instant: decide from the data then available and take the live book. A PASS needs it.
- **France-reachable and cheap.** Hyperliquid serves France (`docs/reviews/venue_access_fr_20261110.md`); 72 of the
  76 markets ran in growth mode (0.9 bp taker) on 2026-11-11.

## What the author has seen
- R462's PREREG, FINDINGS and results (all 24 weekends of 2026-05-01 .. 2026-11-06).
- **Book data:** `books/` and `markets/` on `claude/xyz-books-data` from 2026-11-11: column names, snapshot times
  (about one an hour, at irregular minutes from GitHub's cron) and market names. No cost, spread, depth or fee value.
- **Plumbing, counts only.** On 2026-11-11 the author ran this lane's code once on live endpoints, against the
  weekend of Friday 2026-11-06 (in R462's sample B, before the first weekend, in no statistic here):
  - `tick`'s entry step on the first 5 universe markets: 5 tickets `ok`, the book walk and fee fields filled; fee
    settings found for all 76 markets in `meta`.
  - `score`, journal in a scratch folder: A statuses 51 `ok` and 25 `no_trade`, 102 fallback fills and 102 fee
    fallbacks (no book or market file exists before 2026-11-11). No price, W, cost or return was printed.
- **Code tests:** `tests/test_xyzwknd_fwd.py` on a stub venue and a fake clock.

## Data
- **Prices and funding:** Hyperliquid's public info API: `candleSnapshot` (hourly) and `fundingHistory` for
  `xyz:<COIN>`; `meta` (dex `xyz`) for fee settings; `l2Book` (20 levels a side) for tickets.
- **Recorded books and fees:** `books/` and `markets/` on `claude/xyz-books-data` (`scripts/record_xyz_books.py`,
  hourly on GitHub): the cost in bp from mid of a $1k and a $5k market order on each side, and each market's
  growthMode and deployerFeeScale by UTC day.
- **Universe:** R462's frozen `experiments/xyzwknd_v1/universe.csv` (76 markets with 24/5 external hours, as listed on
  2026-11-11). Markets listed later are not added.
- **Calendar:** `scripts/xyzwknd_rule.py` (NYSE holidays from `lab.sessions`, early closes).

## Rule
Constants are in `scripts/run_xyzwknd_fwd.py`; the weekend rule is R462's, imported unchanged from
`scripts/xyzwknd_rule.py`. Times are New York local time (DST-aware) unless marked UTC.
- **Weekends:** every Friday from 2026-11-13 that R462's rule accepts: Friday a full NYSE trading day (not an early
  close) and Monday a trading day. Other weekends are skipped.
- **Instants:** R = Friday 20:00; E = Sunday 19:00 (the decision and entry); X1 = Sunday 22:00 (the exit).
- **Eligible market:** in the universe, with an hourly candle at least 7 days before R, and not before its IPO date
  (R462's rule).
- **Signal:** W = 10,000 × ln(P(E) / P(R)) in bp, P(T) = the close of the last hourly candle that opens in
  [T − 3 h, T − 1 h] (R462's `price_at`). W = 0 or a missing price: `unpriced`.
- **A trade:** |W| ≥ 50 bp. Fade: short when W > 0, long when W < 0. Otherwise `no_trade`.

**Measure A (decides).**
- **Return:** R462's g_x1 in bp: side × 10,000 × ln(P(X1) / P(E)), plus the funding the side receives over the hourly
  settlements in (E, X1].
- **Fee:** one taker fee a fill, from the market's growthMode and deployerFeeScale in that UTC day's `markets/` file:
  4.5 bp × (scale + 1 if scale < 1, else 2 × scale) × (0.1 in growth mode). A missing file or row falls back to the
  universe's settings, counted.
- **Book cost:** the $1k market-order cost on the side traded (buy to enter a long, sell to exit it; the reverse for a
  short), from the market's `books/` snapshot nearest the instant (E for the entry, X1 for the exit) if it is within
  90 minutes. Otherwise the fill costs 10 bp, counted.
- **Net:** g − k × (fees + book costs), k = 1, 2, 3. Reported only: the same at the $5k cost.

**Measure B (tickets).**
- At E, `tick` fetches each market's hourly candles, computes W as above from what is then available and, for a
  trade, walks the live `l2Book` for a $1k market order on the fade side. It records the book time, mid, the walked
  cost from mid, and the fee listed in `meta` at that moment.
- At X1, it walks the book again on the other side for each entry ticket.
- A tick run that starts up to 70 minutes early sleeps to the instant. No entry ticket is taken later than E + 30
  minutes; a weekend without one has no B trade. An exit not ticketed by X1 + 6 hours is priced at the market's first
  recorded snapshot in [X1, X1 + 6 hours] (mid and $1k cost), flagged `recorder`; with none, the trade is `unpriced`.
- **Return:** side × 10,000 × ln(exit mid / entry mid), plus funding over the settlements in (entry, exit] (book
  times), minus k × (both fees + both walked costs).

**Scoring.** A weekend is scored once, at the first daily run at least 3 hours after X1 once the recorder holds a
snapshot at or after X1 + 90 minutes, or regardless 48 hours after X1. A fetch error leaves the whole weekend for the
next run. Rows are append-only.

**Weekend net.** The mean net over the markets traded that weekend. A weekend with no trade is not counted.

## Decision
On A's traded weekends in calendar order, with weekend nets at 1x. Bootstrap p: the share of 10,000 means of whole
weekends, drawn with replacement (seed 463), at or below 0.
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
- A PASS earns a request to the owner for small calibration orders on Hyperliquid (hard rule 5), the gates in
  `docs/GATES.md`, and `lab.gate.go_real()`. It does not authorize real money.

## Costs (1x, 2x, 3x)
1x is the measured cost above. FINDINGS reports A and B per traded weekend and per trade at 1x, 2x and 3x: mean,
bootstrap p, hit rate and the mean without the best 3. It also reports A at the $5k cost, the A-minus-B gap on common
trades, the entry tickets' delay after E, funding, fallback fills and fee fallbacks, and the status counts.

## Trials
One rule, one exit, one decision; B is a condition on it, not a second test. **Trials:** 1. Program trials before:
9,785,101 (9,785,102 after). R462's 32 trials were counted in its row. Read against `registry.program_trials()`.

## Power
- From R462's 24 weekends (A and B), at a 10 bp round trip, a traded weekend's net has a mean of about +33 bp and an
  SD of about 67 bp, with about 34 trades a weekend.
- Resampling those weekends (2,000 runs, this Decision without B): A passes about 87% of the time, 51% at the 20th
  traded weekend and 36% more at the 30th; futility stops 2%. With the weekends shifted to a mean of 0, it passes
  about 5.4% of the time (the bootstrap p is slightly liberal at 20-30 weekends). The effect is R462's in-sample
  estimate and is likely smaller forward.
- About 4 weekends a month trade, less holidays: the futility read in about March 2027, the interim in about April and
  the final read in about June.

## Stop rules
- Nothing is retuned: no other threshold, instant, universe, size, venue or exit. The `rel` book and R462's 100/200 bp
  cells stay diagnostics. A changed idea is a new lane.
- A fault in the script is fixed with a test and a note in the lane's README. If the fix changes what a scored
  weekend means, the lane is stopped and re-registered.
- If trade.xyz changes its closed-market oracle (the 30-minute EMA) or its US-stock hours, the weekends after the
  change are reported separately and the lane is re-registered.
- No orders, no money, no credentials.

## Known limits (written before the first weekend)
- **Last trades.** A's prices are hourly candle closes, as in R462. B prices the same decisions at the walked book.
- **One snapshot an hour.** A's nearest snapshot can be up to 90 minutes from the instant, and GitHub's cron moves its
  minute. B's tickets come within about two minutes of the instant when a run is on time (76 paced candle requests).
- **Tick timing depends on GitHub's scheduler.** A late or dropped run leaves a weekend without B tickets; the two
  thirds coverage condition bounds that.
- **Size.** $1k a fill. Weekend depth on thin names may cap size; the $5k cost and the 2x and 3x reads bound that.
- **Correlated markets.** One weekend's moves share a market factor, so a weekend counts once, as its mean.
- **Fees.** Growth mode can end for a market; A and B charge the fee listed at the time.

```inputs
d0caa3e1a6220301f7cd663157f105ee8bba816be61e30169c0262fd4c8b7d8e scripts/run_xyzwknd_fwd.py
2583f14014b5691670cdb61058132df692f0db5c8ae4dd38b93f2a4c09e56c66 tests/test_xyzwknd_fwd.py
45efb6ffff95bf726419542890021636dd78a1421961de831a25b25d55f259e4 experiments/xyzwknd_v1/PREREG.md
b5e0700e75432eb3b651e6ab22295f2519ad8b16601fa824fa0f03f05ab1539a scripts/xyzwknd_rule.py
746d69923e55a68a5fefad555afba4647eac8b41d355b460edaaa73c1f611373 experiments/xyzwknd_v1/universe.csv
831fe1dfa2c794bc0467137bb10f9395895ecddecfffcbc860b2c6273faae18d lab/sessions.py
f9fe49b24ebf85b7144bd43cad14af386aa470adaacb4fe2631ee0be0c7fe1b5 scripts/record_xyz_books.py
9f7e79a281716a5104fb87eac1009dff882f884b32d0d7a6faf45998e493cd60 .github/workflows/claude-xyzwknd-tick.yml
3f79a5c407091ec420c350c64ccf61fd0b02f537ca207ece3936ab32f011d4f0 .github/workflows/claude-xyzwknd.yml
```
