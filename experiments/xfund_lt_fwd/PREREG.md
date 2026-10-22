# PREREG: xfund_lt_fwd (R294). R288's mexc+lighter carry book, forward on paper from 2026-10-23

Freeze with `lab.prereg.freeze()` before the first tick. Never edited afterwards; a change is a new lane.

- **Registry id:** R294 (Claude block R280-R299, claimed on issue #7 on 2026-10-22).
- **Gate:** 1 (forward). Only days decided live from 2026-10-23 count. Nobody had seen them when this was frozen.
- **Source:** R288 xfund_lt_v1 (gate 0, CONFIRMED, 5 of 6 Lighter sets).
  - It applied R275's best carry book, unchanged, to six venue sets that pair Lighter (0/0 fees on its Standard
    account) with each venue the lab holds.
  - mexc+lighter had the highest 1x net (+6.20 %/yr, NW t 6.77, from 2025-05). Its FINDINGS named it for a forward
    lane, as the set closest to the owner's MEXC account.
- **Owner (single writer):** the session that froze it. It writes only `experiments/xfund_lt_fwd/journal/` and
  `data/xfund_lt_fwd/`.
- **Execution mode:** API. Both legs are placed at the daily decision on two venues.
- **Paper only.** Nothing here can place an order or move money. No Lighter account or wallet exists (AGENTS.md
  rule 5).

## Book
| Book | Venue set | Lookback | Entry threshold | Slots | R288, 2025-05..2026-09, 1x |
|---|---|---|---|---|---|
| A | mexc + lighter | 14 d | 5%/yr | 20 | 1.70 bp/day (sd 5.6); 2.01 in 2025, 1.44 in 2026 |

It is R275's best book (gate+hyperliquid L14d th5% K20), whose parameters R288 fixed before reading Lighter. It was
picked as the best of R288's 6 sets by 1x net, which the decision bar below accounts for only through R288's own
Bonferroni; the forward days are what test it.

## Rule (R275's, as run by R278 and R279, unchanged unless listed under Deviations)
- **Daily axis:** 00:00 UTC.
- **Close and freshness:**
  - A venue's close on day D is its last traded close at or before 00:00 UTC.
  - It is fresh when the bar ending at that instant traded.
  - Both venues use hourly bars, as in R288.
- **Funding:** settlements in (D − 1, D] belong to day D, with the settlement time floored to the hour.
  - MEXC settles every 8 hours (some coins more often), Lighter every hour.
  - Lighter's API gives an unsigned percent rate and a direction. As in R288's archive, the rate is +rate / 100 when
    the direction is `long` (longs pay) and −rate / 100 otherwise.
- **Signal:** per coin, the funding each venue settled over the last 14 days. The spread is their difference,
  annualized (× 365 / 14). A window needs a settlement in it and the venue's funding history to cover it.
- **Identity guard:** the two venues' fresh daily log returns correlated ≥ 0.9 over the last 30 days, with at least
  20 observations.
- **Entries:** coins with a spread ≥ 5%/yr, taken widest first (ties by table order) into the free slots.
- **Position:** long the coin on the venue that paid less and short it on the venue that paid more, 1x on each leg.
- **Exits:** when the spread falls below 2.5%/yr, or a leg is not fresh, or the window is undefined.
- **Interval D → D + 1:** each held pair earns the long leg's close-to-close return minus the short's, plus the short
  venue's day D + 1 funding minus the long venue's.
- **Net on total capital:** (gross − cost × legs traded) / (2 × slots). Costs are 5.5 / 11 / 16.5 bp per leg per
  side, R288's: the mean of R275's 7 bp leg and a 4 bp Lighter leg (Lighter's $10k median cost per side in its first
  recorded book).
- **Universe:** R288's frozen symbol table (`experiments/xfund_lt_v1/symbols.csv`).
  - 117 of its 195 coins are on both MEXC and Lighter.
  - Coins listed after the table was built are not traded.

## Code
| File | sha256 at this freeze | After the freeze |
|---|---|---|
| `lab/xfund.py` | d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d | fixed; the run script refuses to run if it changes |
| `experiments/xfund_lt_v1/symbols.csv` | e5a689a3bce5f16759104ab7dac945be2ad617317099b124b2137ef308fff1b1 | fixed; checked the same way |
| `lab/carrylane.py` | 12efdca302dfdbc1312dc7499a53de23af9276406e1934c547b9e8642622e895 | data plumbing only |
| `scripts/forward_xfund_lt.py` | 3c81068d5294de1dfe06a0d6e38d463fdbd4bdcb2c07e583c71da03cec23999e | data plumbing only |

- **What the files are:**
  - `lab/xfund.py` is the line-for-line Python twin of `qx spread`, the engine R288 ran on.
  - `lab/carrylane.py` is the forward lane R279 runs (R278's rule and accounting on any venues). For this lane it
    gained Lighter's public clients:
    - hourly candles: `/candles`, 480 a call;
    - hourly funding: `/fundings`, 700 hours a call, signed as above;
    - contract list: `/orderBookDetails`, with status `active`;
    - live mids: `/orderBookOrders` (best bid and ask), read for a coin only when a ticket needs it (below).

    Every Lighter request takes the machine-wide Lighter lock (`data/.lighter_api.lock`), shared with the book
    recorder and the history fetcher, and holds it for 1.1 s after the request. That keeps the machine under
    Lighter's 60 requests a minute.
- **Changes after the freeze:** data plumbing only (venue clients, retries, file handling). Each change needs the
  tests to pass and a line in `journal/CHANGES.md` with its commit. A change to the rule, the book, the accounting or
  the decision is a new lane.
- **Parity, checked before this freeze:**
  - `python scripts/xfund_parity.py --lane xfund_lt_v1` replays the book on R288's archive with `lab/xfund.py`. It
    reproduces R288's engine output: 305 of 305 trades identical, and the daily 1x net within 5e-11 on all 507 days.
  - `tests/test_carrylane.py`:
    - the R278 and KuCoin tests as before (R278's journals byte-identical);
    - Lighter's clients against a fake API: paging, the funding sign, the contract list, the lazy mids, and that
      the lock is held during every request;
    - a mexc+lighter lane on a synthetic root (MEXC 8-hour funding, Lighter hourly) replays as the twin does. Its
      first live day fills each inherited pair from one book read per coin.

## Deviations from R288 (forced by running forward; R279's 1-7, plus 8)
1. **Forced exit.**
   - A pair exits (forced) when either leg has had no fresh close on any of the last 3 days.
   - It also exits when either leg's contract is missing from its venue's live contract list at a live decision.
   - For Lighter, a market whose status is not `active` counts as missing.
2. **Universe:** frozen, as above.
3. **Data:**
   - Archive rows from 2026-08-01, then the venues' public APIs on every run.
   - API rows replace archive rows on overlap, and the changed values are counted in `journal/status.json`.
   - Only closed bars are kept.
4. **Start:**
   - The book replays from its window start on the forward data (2026-08-01 plus the funding and correlation
     history) up to 2026-10-22. The replay is not scored.
   - On 2026-10-23, the first live day:
     - replayed pairs that the rule exits that day are dropped, since they were never held on paper;
     - the remaining replayed pairs are taken over at live prices, with entry legs charged (ticket action
       `inherit`).
5. **Decided accounting (fill):**
   - R288's close accounting plus each live ticket's gap between the venue's live mid and day D's close, on both
     legs.
   - R288's close accounting is reported next to it.
6. **Timing:**
   - The hourly loop decides day D on its first run after 00:00 UTC on which each venue's share of fresh coins on D
     is at least 0.9 of its share on D − 1. It waits up to 6 h.
   - A day decided more than 7 h after 00:00, or caught up after a gap in the loop, is `late`. It has no live mid and
     books the close.
   - **Known bias** (as R278 and R279): a pair decided at hour h of day D is credited the settlements in (D, D + h]
     that it did not hold. Every ticket's `run` stamp makes it measurable. It is reported, not corrected. Lighter
     settles hourly, so its share of this bias is larger than for an 8-hour venue.
7. **No entry on a delisted contract** (as R279): at a live decision, a coin whose contract is missing from a venue's
   live list cannot be entered on that venue.
8. **Lighter's fill is read lazily (new).**
   - Lighter has no bulk ticker with bid and ask. Its mark price, which `/orderBookDetails` gives for every market,
     sat a median 6 bp and a p90 29 bp from the book mid in the book recorder's first 7 snapshots (1,398 rows), while
     the median half spread was 3 bp. So the mark price is not used as a fill.
   - Lighter's live mid is the best bid and ask midpoint from `/orderBookOrders`, read when a ticket on a Lighter
     leg is written. MEXC's mids are read in one request at the decision.
   - **So the two legs' fills can be minutes apart:** each Lighter read waits 1.1 s, and longer when the hourly book
     recorder holds the Lighter lock (about 4 minutes a snapshot). The gap is not stamped per ticket. It is a known
     limit of the fill accounting.
   - A failed or empty book read gives no fill on that ticket, and the close is booked, as for any venue whose mids
     fail.

## Not modelled (from R275's and R288's PREREGs; still true)
- **Liquidation of a leg above 1x.** R280 measured it for R275's and R277's books, not for this one.
- Moving collateral between venues, and Lighter's bridge. **The book is mostly short on Lighter** (Lighter pays
  more), so a Lighter failure would hit the short legs' collateral. That risk is not priced.
- Intraday rebalancing.
- **Order-book depth:** K = 20 at $10k is $250 per leg.
- **Lighter's 300 ms taker delay** on Standard accounts, and fees beyond the per-leg cost.
- **The MEXC API taker** (about 8.7 bp with spread, R288's cost note) puts this book's per-leg cost at about 6.4 bp,
  between the 1x and 2x columns. Both are reported.
- **Whether the owner can use Lighter** (an on-chain wallet and a bridge) is the owner's call. A PASS without access
  is evidence, not a trade.

## What the author has seen
- **R288 in full** (Lighter from 2025-01-17, its sets from their window starts to 2026-09-30): its six sets, audit,
  by-year table and the dYdX crash days. Also the in-sample power figures below, computed from R288's published
  `daily.csv` for this book.
- **R278's and R279's replays and first live days.** R278 has a MEXC leg in its universe; neither has a Lighter leg.
- **Lighter after 2026-09-30, while writing this lane (2026-10-22):**
  - the archive's coverage only: the last row time (2026-10-21 15:00 UTC) of the 1000BONK candle and funding files,
    and their column names;
  - one live `/orderBookDetails` answer: 240 markets, the field names, and one market's (AAOI) mark and index price;
  - the book recorder's 7 snapshots (2026-10-21..22), read for the mark-against-mid gap and the half spread above.
- **Not computed for any day after 2026-09-30 on Lighter or MEXC for this book:** no funding spread, no window and no
  pair choice. The replay runs after this freeze.

## Decision
- **Scored days:** every interval that starts on a live (`ontime` or `late`) decision day. The first ends on
  2026-10-24.
- **The decided series:** the daily net at 1x, fill accounting, on total capital.
- **Looks:**

  | Look | Scored days | Date | Outcome |
  |---|---|---|---|
  | 1 | 90 | 2027-01-21 | **PASS** if all hold:<br>• Newey-West t (lag 10, `lab.stats.newey_west_t`) ≥ 2.5<br>• the sum of the 2x net > 0<br>• max drawdown of the cumulative 1x net > −3%<br>**FAIL** if the 1x mean ≤ 0<br>**CONTINUE** otherwise |
  | 2 | 180 | 2027-04-21 | **PASS** on the same three conditions, else **FAIL** |

- **Kill switch:**
  - If the book's cumulative 1x net falls below −3% of capital on any day, it is FAIL at once.
  - The lane keeps ticketing it for the record, and those tickets are reported, not decided on.
- **Multiplicity:**
  - 1 book × 2 looks: Bonferroni one-sided 0.05 / 2 needs z ≥ 1.96.
  - 2.5 is used, the same bar as R278 and R279.
- **Timing quality:** if more than 20% of the scored days are `late`, the verdict is labelled degraded timing.
- **Interim:**
  - The 30- and 60-day checkpoints and the dashboard figures are descriptive only.
  - `journal/status.json` shows NW t and drawdown every hour for monitoring.
- **What a PASS earns:** gate 2, if the owner can trade both venues.
  - A frozen small-stake plan, run through `lab.gate.go_real()` and placed by the owner.
  - Nothing here moves money.

## Expectations
Power, from R288's own days for this book (2025-05-13..2026-09-30, 507 days; in sample, close accounting, before
fills):

| Windows | Share with NW t ≥ 2.5 | Worst drawdown in a window |
|---|---|---|
| 90 days (418) | 96% | −0.21% |
| 180 days (328) | 100% | −0.21% |

- **Lower in practice:** real fills (the live mids against the 00:00 close, minutes apart on Lighter) and the decay
  from 2025 to 2026 (2.01 to 1.44 bp/day) make it lower.
- **At 1.44 bp/day** the book earns about 5.3 %/yr at 1x, about one point over R288's 4.13% hurdle.
- **A FAIL** at this power would mean the Lighter carry does not survive live data and fills. That is a result,
  recorded with the same care.

## Reported, not decided on
- 2x and 3x costs;
- close accounting (R288's own);
- the fill gap per day, split by venue;
- funding share of gross;
- pairs held and forced exits;
- late days and decision delay;
- data freshness per venue;
- values changed on API overlap;
- replay totals;
- the comparison with R279's books over the same days.

## Multiplicity
- Trials: 1 (book).
- Program trials before this lane: 9,478,572 (`registry.program_trials()`, 2026-10-22, after R292).
