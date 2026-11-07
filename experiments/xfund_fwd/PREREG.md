# PREREG: xfund_fwd (R278). R275's cross-venue funding carry books, forward on paper from 2026-10-22

Freeze with `lab.prereg.freeze()` before the first tick. Never edited afterwards; a change is a new lane.

- **Registry id:** R278 (Claude block R260-R279, claimed on issue #7)
- **Gate:** 1 (forward). Only days decided live from 2026-10-22 count. Nobody had seen them when this was frozen.
- **Source:** R275 xfund_v1 (gate 0, PARTIAL: 212 of 560 books pass, best t 12.70). Its FINDINGS pre-commits two
  books to a forward lane. This lane runs them, plus one post hoc book.
- **Owner (single writer):** the session that froze it. It writes only `experiments/xfund_fwd/journal/` and
  `data/xfund_fwd/`.
- **Paper only.** Nothing here can place an order or move money.

## Books
| Book | Venue set | Lookback | Entry threshold | Slots | Why |
|---|---|---|---|---|---|
| A | gate + hyperliquid | 14 d | 5%/yr | 20 | R275's best passing book by 1x t (pre-committed) |
| B | binance + mexc | 14 d | 10%/yr | 20 | R275's best passing book with a MEXC leg (pre-committed) |
| C | gate + mexc | 7 d | 10%/yr | 20 | **post hoc:** R275's best MEXC book by annual net, chosen after reading R275 |

R275's 2025-26 days, at 1x cost:
- **A:** 1.77 bp/day (sd 9.3)
- **B:** 1.73 bp/day (sd 4.7)
- **C:** 4.46 bp/day (sd 14.3)

## Rule (R275's, unchanged unless listed under Deviations)
- **Daily axis:** 00:00 UTC.
- **Close and freshness:**
  - A venue's close on day D is its last traded close at or before 00:00 UTC.
  - It is fresh when the bar ending at that instant traded.
  - Hyperliquid uses daily bars; the other venues use hourly bars.
- **Funding:** settlements in (D − 1, D] belong to day D, with the settlement time floored to the hour.
- **Signal:** per coin and venue pair, the funding each venue settled over the last L days. The spread is their
  difference, annualized (× 365 / L). A window needs a settlement in it and the venue's funding history to cover it.
- **Identity guard:** the two venues' fresh daily log returns correlated ≥ 0.9 over the last 30 days, with at least
  20 observations.
- **Pair choice:** per coin, the widest eligible pair in the book's venue set.
- **Entries:** coins with a spread ≥ the threshold. They are taken widest first (ties by table order) into the free
  slots.
- **Position:** long the coin on the venue that paid less and short it on the venue that paid more, 1x on each leg.
- **Exits:** when the spread falls below threshold / 2, or a leg is not fresh, or the window is undefined.
- **Interval D → D + 1:** each held pair earns the long leg's close-to-close return minus the short's, plus the short
  venue's day D + 1 funding minus the long venue's.
- **Net on total capital:** (gross − cost × legs traded) / (2 × slots).
- **Code:**
  - `lab/xfund.py` (sha256 d34e99a052418995...): a line-for-line Python twin of `qx spread`, the engine R275 ran on.
  - `scripts/forward_xfund.py` (de361e3a90583ba2... at this freeze) runs the lane.
  - `experiments/xfund_v1/symbols.csv` (78201a341b9fc498...) is R275's frozen symbol table.
  - **After the freeze:**
    - `lab/xfund.py` is fixed.
    - `scripts/forward_xfund.py` may change only for data plumbing: venue clients, retries and file handling.
      Each such change needs the tests to pass and a line in `journal/CHANGES.md` with its commit.
    - A change to the rule, the books, the accounting or the decision is a new lane.
- **Parity, checked before this freeze:**
  - `scripts/xfund_parity.py` replays the three books on the archive with `lab/xfund.py`.
  - It reproduces R275's own output (`experiments/xfund_v1/results/`):
    - gate+hyperliquid: 587 of 587 trades identical;
    - binance+mexc: 271 of 271;
    - gate+mexc: 664 of 664;
    - daily 1x net within 5e-11 on every day.
  - `tests/test_forward_xfund.py`:
    - checks the twin's trades against the `qx` binary on a synthetic root;
    - checks the lane's replay against the twin;
    - checks the first-live-day take-over and that rows of a cut run are ignored.

## Deviations from R275 (forced by running forward)
1. **Forced exit.**
   - R275 forced an exit when a leg's series had ended, which only hindsight can know.
   - Here a pair exits (forced) when either leg has had no fresh close on any of the last 3 days.
   - It also exits when either leg's contract is missing from its venue's live contract list at a live decision.
     For Gate, a contract that is `in_delisting` counts as missing.
2. **Universe:** R275's frozen symbol table. Coins listed after it was built are not traded.
3. **Data:**
   - Archive rows from 2026-08-01, then the venues' public APIs on every run.
   - API rows replace archive rows on overlap, and the changed values are counted in `journal/status.json`.
   - Only closed bars are kept.
4. **Start:**
   - Each book replays from its own window start on the forward data (2026-08-01 plus L days of funding and the
     correlation history) up to 2026-10-21. The replay is not scored.
   - On 2026-10-22, the first live day:
     - replayed pairs that the rule exits that day are dropped, since they were never held on paper;
     - the remaining replayed pairs are taken over at live prices, with entry legs charged (ticket action
       `inherit`).
5. **Decided accounting (fill):**
   - R275's close accounting plus each live ticket's gap between the venue's live mid at the decision and day D's
     close, on both legs.
   - Costs are 7 / 14 / 21 bp per leg per side at 1x / 2x / 3x.
   - R275's close accounting is reported next to it.
6. **Timing:**
   - The hourly loop decides day D on its first run after 00:00 UTC on which each needed venue's share of fresh
     coins on D is at least 0.9 of its share on D − 1. It waits up to 6 h.
   - A day decided more than 7 h after 00:00, or caught up after a gap in the loop, is `late`. It has no live mid and
     books the close.
   - **Known bias:** a pair decided at hour h of day D is credited the hourly settlements in (D, D + h] that it did
     not hold. The run time is in every ticket's `run` stamp, so the bias is measurable. It is reported, not
     corrected.

## Not modeled (from R275's PREREG; still true)
- liquidation of a leg above 1x;
- moving collateral between venues;
- intraday rebalancing;
- order-book depth: K = 20 at $10k is $250 per leg;
- fees beyond the per-leg cost.

## What the author has seen
- **R275 in full:** all 560 books over 2021-01..2026-09, its audit (funding recomputed on 4 trades, missing
  settlements, forced exits, concentration) and its by-year table. Book C was picked after reading it.
- **Smoke test, after 2026-09-30:** 40 days of BTC rows from each venue client (prices and funding), printed as row
  counts, columns and time ranges only.
- **Bulk counts:** each venue's live mid and contract lists, printed as counts.
- **Not computed for any day after 2026-09-30:** no funding spread, no window and no pair choice. The replay
  (2026-08-01..2026-10-21) runs after this freeze.
- **Recorders running elsewhere:**
  - the MEXC funding recorder (current and next rate) and the Hyperliquid position and leaderboard scrapers;
  - the author has not computed a cross-venue spread from either.

## Decision (each book on its own)
- **Scored days:** every interval that starts on a live (`ontime` or `late`) decision day. The first ends on
  2026-10-23.
- **The decided series:** the daily net at 1x, fill accounting, on total capital.
- **Looks:**

  | Look | Scored days | Date | Outcome |
  |---|---|---|---|
  | 1 | 90 | 2027-01-20 | **PASS** if all hold:<br>• Newey-West t (lag 10, `lab.stats.newey_west_t`) ≥ 2.5<br>• the sum of the 2x net > 0<br>• max drawdown of the cumulative 1x net > −3%<br>**FAIL** if the 1x mean ≤ 0<br>**CONTINUE** otherwise |
  | 2 | 180 | 2027-04-20 | **PASS** on the same three conditions, else **FAIL** |

- **Kill switch:**
  - If a book's cumulative 1x net falls below −3% of capital on any day, the book is FAIL at once.
  - The lane keeps ticketing it for the record, and those tickets are reported, not decided on.
- **Multiplicity:**
  - 3 books × 2 looks. Bonferroni one-sided 0.05 / 6 needs z ≥ 2.39; 2.5 is used.
  - Book C's verdict is labelled post hoc whatever it is.
- **Timing quality:** if more than 20% of a book's scored days are `late`, its verdict is labelled degraded timing.
- **Interim:**
  - The 30- and 60-day checkpoints and the dashboard figures are descriptive only.
  - `journal/status.json` shows NW t and drawdown every hour for monitoring.
- **What a PASS earns:** gate 2.
  - A frozen small-stake plan, run through `lab.gate.go_real()` and placed by the owner.
  - Nothing here moves money.

## Expectations
Power, from R275's own 2025-26 days (in sample, before fills): the share of 90-day windows whose NW t reached 2.5.

| Book | 90-day windows | 180-day windows |
|---|---|---|
| A | 62% | 61% |
| B | 80% | 100% |
| C | 95% | 100% |

- **A** may stay CONTINUE at 90 days.
- Real fills (the mid at the decision against the 00:00 close) and the decay since 2023 make all three lower.
- **A FAIL on all three books** at full power would mean R275's carry does not survive live data and fills. That is
  a result, recorded with the same care.

## Reported, not decided on
- 2x and 3x costs;
- close accounting (R275's own);
- the fill gap per day;
- funding share of gross;
- pairs held and forced exits;
- late days and decision delay;
- data freshness per venue;
- values changed on API overlap;
- replay totals.

## Multiplicity
- Trials: 3 (books).
- Program trials before this lane: 9,478,319, after R276.
