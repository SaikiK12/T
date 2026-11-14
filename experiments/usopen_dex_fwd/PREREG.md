# PREREG: usopen_dex_fwd (R457). R371's US-open picks traded on Lighter and Hyperliquid

Freeze with `lab.prereg.freeze()` before the first day. Never edited afterwards; a changed idea is a new lane.

- **Registry id:** R457
- **Owner (single writer):** the Claude session that froze it, on `claude/yo-9a1k5w`.
  - `scripts/run_usopen_dex.py` is the only writer of `experiments/usopen_dex_fwd/journal/`.
  - It runs daily in `.github/workflows/claude-usopen-dex.yml`.
- **Date registered (UTC):** 2026-11-11

**Methods:** M318 (intraday cross-sectional relative strength), candidate C17. **Parent:** R371 (`usopen_fwd`,
PREREG `d3cfa47e…`, rule `scripts/usopen_rule.py` `dba0257e…`).
- **Paper only:** public endpoints, no account, no key; nothing in the code can place an order.

## Question
R371 trades C17 on MEXC (book M decides) and Binance (book B); a French resident can use neither
(`docs/reviews/venue_access_fr_20261110.md`). Lighter and Hyperliquid are open to them, and Lighter's Standard account
pays no trading fee. On the same NYSE days, from 2026-11-12, does R371's rule, applied to the names each venue lists
and filled at that venue's own prices, earn a positive mean net of what the venue's book charged: a Newey-West t of 2
or more after 500 scored days, with a positive 2x mean and a positive mean without the 10 best days?

## Why this lane
- **C17 has the lab's strongest blind evidence** (`docs/reviews/pnl_ranking_20261111.md`). R392 read it on the
  reserved 2020 sample: +86.2 bp/day at 1x, NW t 3.04, p 0.0012 against an alpha of 0.001. Its 10 best days were 94%
  of that net.
- **Its cost decides it.** R300's pick earned +72.7 bp/day gross in validation and paid 34 bp/day at API cost. A
  zero-fee venue keeps the spread and the depth as the whole cost.
- **R371 cannot be executed from France as frozen.** If its M book passes, nothing tells the owner what the same picks
  earn on a venue they can use. This lane is that venue's record, on days nobody has seen.
- **The owner asked on 2026-11-11 that real trading match paper.** Both books are priced at fills a bot could get
  (one-minute opens 3 minutes after each clock) and at each venue's recorded book cost.

## What the author has seen
- R300 in full, R392's 2020 read, and R371's PREREG and status on 2026-11-11 (3 scored days, means printed in its
  `status.json`; one leg row of its first ticket).
- **One past day, for plumbing.** On 2026-11-11 the author ran this lane's scoring once on R371's ticket for
  2026-11-10, with live endpoints and no book files, printing counts only:
  - Lighter: 43 of the 50 names mapped, 40 eligible, a book formed, 12 fills at the fallback cost.
  - Hyperliquid: 41 mapped (2 of the six legs on xyz), 40 eligible, a book formed.
  - Before xyz and the two oil aliases were added, the same day mapped 20 names on Hyperliquid's main dex and 41 on
    Lighter. The unmapped names were read: mostly Binance's TradFi perps (SOXL, NVDA, XAU, CL, TSLA, QQQ...) and new
    small caps.
  - No return, cost or price of that day was printed. That day is before the lane's first day and is in no statistic.
- **Book costs:** `lighter/books/`, `main/books/` and `books/` exist on `claude/xyz-books-data` from 2026-11-11. No
  cost value from them was read.
- **Code tests:** `tests/test_run_usopen_dex.py` on synthetic tickets and stub venues.

## Data
- **Signal:** R371's journal on the default branch, `experiments/usopen_fwd/journal/`: `tickets.csv` (a day counts
  only with status `ok`) and `signals.csv` (the 50 names, their Binance rank, move `sig` and Binance close `c_e` at D,
  written by R371 within 2 minutes of D). A day R371 missed is missed here too; nothing is made up.
- **Prices and funding:** each venue's public API.
  - Lighter: `candles` at resolution 1m, `fundings` through `lab/carrylane.py`.
  - Hyperliquid: `candleSnapshot` at 1m and `fundingHistory`, on the main dex and on xyz.
- **Book costs:** `claude/xyz-books-data`, written hourly on GitHub.
  - Lighter: `lighter/books/` (`scripts/record_lighter_costs.py`), $1k and $10k columns.
  - Hyperliquid main dex: `main/books/`; xyz: `books/` (`scripts/record_xyz_books.py`), $1k and $10k columns.
  - xyz's fee inputs: `markets/` (growth mode and deployer fee scale by day).

## The rule
Constants are in `scripts/run_usopen_dex.py`; R371's are in `scripts/usopen_rule.py`. All times UTC.
- **Days.** Every R371 ticket with status `ok` and a date from 2026-11-12. D is that ticket's decision time (10:00 New
  York); the exit clock is 24:00 UTC that night.
- **Names on a venue.** A Binance symbol from R371's 50 maps to a venue perp:
  - Lighter: the base, the aliases CL -> WTI and BZ -> BRENTOIL, the base without a 1000/1000000 prefix, or with 1000.
  - Hyperliquid: the main-dex base or its k prefix for 1000x coins, else R451's xyz coin (`xyz:<base>`, or R451's
    five aliases).
- **Eligible.** A mapped name is eligible when the venue has a one-minute bar that opened in the hour before D and
  the last such close is within 10% of R371's Binance close at D (a guard against a different asset under the same
  ticker). Only bars before D decide eligibility.
- **Pick.** R371's own `pick` on the eligible names: long the 3 largest moves, short the 3 smallest. With fewer than
  30 eligible the venue has no book that day (`no_book`).
- **Fills.** Entry is the open of the venue's first one-minute bar at or after D + 3 minutes, within 5 minutes of it.
  Exit is the same after 24:00 UTC + 3 minutes. A pick with either price missing makes the venue's day `unpriced`.
- **Funding.** The venue's hourly settlements whose hour is after the entry minute and not after the exit minute.
  Positive rates are paid by longs.
- **Return.** R371's `book_return`: the mean long return minus the mean short return (one unit a side), plus funding
  received.
- **Cost of a fill.** The venue's taker fee plus the cost of a $1k market order on the side traded (a long buys in and
  sells out; a short the reverse). The order cost is read from the coin's book snapshot nearest the fill, if it is
  within 90 minutes.
  - **Fees:** Lighter's Standard account pays 0. Hyperliquid's main dex charges its tier-0 taker fee of 4.5 bp. xyz
    charges R453's HIP-3 fee for that coin and day (`fee_at`), or 9 bp when `markets/` lists none.
  - **Fallback:** a missing snapshot, or a book too thin for $1k, costs R371's 10 bp for that fill. It is counted.
- **Book cost and net.** A leg's cost is its two fills; the book's 1x cost is R371's `web_cost`, the mean leg cost of
  the longs plus that of the shorts. Net at k = gross − k × cost, for k = 1, 2, 3. The $10k columns give a second net
  at 1x, reported only.
- **Scoring.** A day is scored once per venue, at the first run at least 3 hours after its exit. A fetch error
  leaves it for the next run; a missing price makes it `unpriced` for good. Rows are append-only.

## Trials
Two books (L on Lighter, H on Hyperliquid) on one rule; book L decides. **Trials:** 2. Program trials before:
9,785,003 (9,785,005 after). R300's and R371's own trials were counted in their rows; this lane does not reset them.
Read against `registry.program_trials()`.

## Decision
**Book L decides**, on its scored (`ok`) days in calendar order, with R371's `decision` (NW t with lag 5 on the
calendar-day grid):
- **PASS:** at the 500th scored day, t ≥ 2.0 at 1x **and** the 2x mean > 0 **and** the mean without the 10 best
  days > 0.
- **NULL:** at the 500th scored day otherwise.
- **NULL (futility):** at the 125th scored day, a negative 1x mean with t ≤ −1. Days after a read cannot change it.
- Book H is reported only, read the same way.
- A PASS earns a request to the owner for small calibration orders on Lighter (hard rule 5), the gates in
  `docs/GATES.md`, and `lab.gate.go_real()`. It does not authorize real money. R371's own verdict is unchanged by
  this lane.

## Costs (1x, 2x, 3x)
1x is the measured cost above. FINDINGS reports, per book, at 1x, 2x and 3x: mean, t, hit rate, trimmed mean and the
best-10 share. It also reports the $10k net, the share of fills at the fallback cost, and no_book and unpriced counts.

## Power
- R300's validation daily SD was about 650 bp.
- At R300's validation gross (+72.7 bp/day, a seen winner of 24 books), a 10 bp/day cost, and the same picks, the
  expected t at 500 days is about 2.15.
- At half that gross it is about 0.9, and a PASS is unlikely.
- Venue coverage changes the picks on days when R371's top movers are not listed.
- The honest reading: a slow test with a low chance of a PASS. It gives a stable estimate of what the owner's venue
  would have paid.

## Stop rules
- Nothing is retuned: no other clock, coin count, venue, mapping, guard, fill lag, size, fee or threshold. A changed
  idea is a new lane.
- A fault in the script is fixed with a test and a note in the lane's README. If the fix changes what a scored day
  means, the lane is stopped and re-registered.
- No orders, no money, no credentials.

## Known limits (written before the first day)
- **Signal source.** The picks use Binance's top 50, which a French resident can read but not trade. A bot following
  this rule needs Binance's public bars at D.
- **Size.** For a $10k account each leg is about $1.7k-$3.3k. The $1k book cost understates that; the $10k column and
  the 2x condition bound it.
- **Snapshots.** One book snapshot an hour, minutes from the fill. A delayed recorder leaves a fill at the 10 bp
  fallback, which can understate the cost of a thin coin.
- **Minute bars.** Hyperliquid serves about 3.5 days of one-minute bars. A day not scored within that window is
  `unpriced` on H. Lighter serves at least 20 days.
- **Same-ticker guard.** The 10% price guard catches different assets and 1000x scale mismatches, not every rename.
- **Latency.** Lighter's Standard account adds latency to taker orders. A 3-minute fill lag is far longer.
- **Fees** are as of 2026-11-11. A later fee change is not modelled except through xyz's `markets/` files.

```inputs
1147f5c10e44c4733e5d96d259148c52fe1c69d9d435242b846980b8815fd8df scripts/run_usopen_dex.py
ef67ea7e11bb39bbf0937032fbcc90735c9b8f3229e8c797b7ef8ad0117c6c6a tests/test_run_usopen_dex.py
dba0257e4877d2bbd81603447d5e213cf24496752329da87ee41926e72817af6 scripts/usopen_rule.py
cecfa25866aa5873128f1e97b71f74fbeefbf00b9c2c261550062b07d4e61335 scripts/run_flow_hlstock.py
d9cc1053883c17545e52292d20c18569c751c7418d90c73502c60f54bd147e91 scripts/run_flow_hlstock_mc.py
f9fe49b24ebf85b7144bd43cad14af386aa470adaacb4fe2631ee0be0c7fe1b5 scripts/record_xyz_books.py
f691695930719a89ae4ededcd5b952f3aa6aabefbe8ea939970acd009e16b297 scripts/record_lighter_costs.py
12efdca302dfdbc1312dc7499a53de23af9276406e1934c547b9e8642622e895 lab/carrylane.py
```
