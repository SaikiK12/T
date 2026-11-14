# PREREG: xfund5_fwd (R440). R439's five-venue carry book, forward on paper from 2026-11-11

Freeze with `lab.prereg.freeze()` before the first tick. Never edited afterwards; a change is a new lane.

- **Registry id:** R440
- **Claim:** Claude, session on `claude/yo-9a1k5w` (hunt mode, 2026-11-10); CLAIM posted on issue #7.
- **Gate:** 1 (forward). Only days decided live from 2026-11-11 count. Nobody had seen them when this was frozen.
- **Source:** R439 `carry5_v1` (gate 0, CONFIRMED). R275's all-four rule as one book over Binance, Gate, Hyperliquid,
  MEXC and KuCoin: +18.46%/yr at 1x on the M468 engine, NW t 8.71, 2x and both halves positive.
  - R439's PREREG names this lane: "if it SURVIVES and the paired difference is positive, a forward paper lane of the
    five-venue book is the next id". The paired difference was +1.48%/yr (t 0.54, not significant).
  - Why it is worth a forward lane although the paired gain is small: on R439's archive the five-venue book has about
    half the daily volatility of the four-venue book (sd 23 bp against 45 bp a day) at a similar return. A forward
    test of it reaches a decision about three times sooner.
  - No forward lane trades this book. R278 runs gate+hyperliquid, binance+mexc and gate+mexc; R279 gate+kucoin and
    binance+kucoin; R390 binance+gate.
- **Owner (single writer):** the session that froze it. It writes only `experiments/xfund5_fwd/journal/` and
  `data/xfund5_fwd/`.
- **Paper only.** Nothing here can place an order or move money.

## Book
| Book | Venue set | Lookback | Entry threshold | Slots | R439 archive, v1 accounting (this lane's) | R439, M468 engine |
|---|---|---|---|---|---|---|
| A | binance + gate + hyperliquid + mexc + kucoin | 14 d | 10%/yr | 20 | +16.36%/yr, NW t 8.85, 2,078 days | +18.46%/yr, NW t 8.71 |

The book is R439's, unchanged. It was not chosen among variants here.

## Rule (R275's, as run by R278, R279 and R390 on `lab/carrylane.py`, unchanged unless listed under Deviations)
- **Daily axis:** 00:00 UTC.
- **Close and freshness:**
  - A venue's close on day D is its last traded close at or before 00:00 UTC.
  - It is fresh when the bar ending at that instant traded.
  - Binance, Gate and MEXC use hourly bars; Hyperliquid and KuCoin daily bars.
- **Funding:** settlements in (D − 1, D] belong to day D, with the settlement time floored to the hour.
- **Signal:** per coin and venue pair, the funding each venue settled over the last 14 days. The spread is their
  difference, annualized (× 365 / 14). A window needs a settlement in it and the venue's funding history to cover it.
- **Identity guard:** the two venues' fresh daily log returns correlated ≥ 0.9 over the last 30 days, with at least
  20 observations.
- **Pair choice:** per coin, the widest eligible pair among the five venues (ties by venue order: binance, gate,
  hyperliquid, mexc, kucoin, R439's spec order).
- **Entries:** coins with a spread ≥ 10%/yr, taken widest first (ties by table order) into the free slots.
- **Position:** long the coin on the venue that paid less and short it on the venue that paid more, 1x on each leg.
- **Exits:** when the spread falls below 5%/yr (half the entry threshold, as in the engine), or a leg is not fresh,
  or the window is undefined.
- **Interval D → D + 1:** each held pair earns the long leg's close-to-close return minus the short's, plus the short
  venue's day D + 1 funding minus the long venue's.
- **Net on total capital:** (gross − cost × legs traded) / (2 × slots). Costs are 7 / 14 / 21 bp per leg per side.
- **Universe:** R439's frozen symbol table (`experiments/carry5_v1/symbols.csv`, R275's manifest with R277's KuCoin
  column). Coins listed after it was built are not traded.

## Code
| File | sha256 at this freeze | After the freeze |
|---|---|---|
| `lab/xfund.py` | d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d | fixed; the run script refuses to run if it changes |
| `experiments/carry5_v1/symbols.csv` | 22a91dc96cd04a4ac9dce5914d5fba5485f754088acef74f7efe03f10e8e0328 | fixed; checked the same way |
| `lab/carrylane.py` | 12efdca302dfdbc1312dc7499a53de23af9276406e1934c547b9e8642622e895 | data plumbing only |
| `scripts/forward_xfund5.py` | see the inputs block | data plumbing only |

- `lab/xfund.py` is the line-for-line Python twin of `qx spread` (R278's accounting, the "v1" of R437-R439).
  `lab/carrylane.py` is the shared forward lane of R279, R294 and R390.
- **Why v1 and not M468.** Every forward carry lane uses v1; R437 and R438 found v1 the conservative accounting and
  the constant-notional figures the ones to compare with forward lanes. R439's book under v1 is in the Book table.
- **Changes after the freeze** are data plumbing only (venue clients, retries, file handling). Each needs the tests to
  pass and a line in `journal/CHANGES.md` with its commit. A change to the rule, the book, the accounting or the
  decision is a new lane.
- **Checks before this freeze:**
  - `tests/test_forward_xfund5.py` (4 tests): the book, venue order, costs and identity guard equal R439's; the fixed
    inputs match.
  - Dry tick on archive data only, into the scratchpad, as of 2026-09-30 23:00 UTC: replayed 2026-08-22..09-30, 54
    tickets, 39 day rows, 20 pairs held at the end. Nothing was written to this lane's folders.
  - There is no `qx` engine run of this book, so no engine parity line as in R390. The archive expectation below is
    `lab/xfund.py` itself.

## Deviations from R275 (forced by running forward; the same as R279 and R390)
1. **Forced exit.**
   - A pair exits (forced) when either leg has had no fresh close on any of the last 3 days.
   - It also exits when either leg's contract is missing from its venue's live contract list at a live decision. For
     Gate, a contract that is `in_delisting` counts as missing.
2. **Universe:** frozen, as above.
3. **Data:**
   - Archive rows from 2026-08-01, then the venues' public APIs on every run.
   - API rows replace archive rows on overlap, and the changed values are counted in `journal/status.json`.
   - Only closed bars are kept.
4. **Start:**
   - The book replays from its window start on the forward data (2026-08-01 plus the funding and correlation history)
     up to 2026-11-10. The replay is not scored.
   - On 2026-11-11, the first live day:
     - replayed pairs that the rule exits that day are dropped, since they were never held on paper;
     - the remaining replayed pairs are taken over at live prices, with entry legs charged (ticket action `inherit`).
5. **Decided accounting (fill):**
   - R275's close accounting plus each live ticket's gap between the venue's live mid at the decision and day D's
     close, on both legs.
   - R275's close accounting is reported next to it.
6. **Timing:**
   - The hourly loop decides day D on its first run after 00:00 UTC on which each needed venue's share of fresh coins
     on D is at least 0.9 of its share on D − 1. It waits up to 6 h.
   - A day decided more than 7 h after 00:00, or caught up after a gap in the loop, is `late`. It has no live mid and
     books the close.
   - **Known bias** (as R278, R279 and R390): a pair decided at hour h of day D is credited the settlements in
     (D, D + h] that it did not hold. Every ticket's `run` stamp makes it measurable. It is reported, not corrected.
7. **No entry on a delisted contract (R279's rule).** At a live decision, a coin whose contract is missing from a
   venue's live list cannot be entered on that venue.

## Not modelled (from R275's PREREG; still true)
- **Liquidation of a leg above 1x.** R280 measures it on the archive and found no safe leverage.
- **Moving collateral between five venues.** It is harder than with two.
- Intraday rebalancing.
- **Order-book depth:** K = 20 at $10k is $250 per leg.
- Fees beyond the per-leg cost.
- **Access:** whether the owner can hold futures accounts on all five venues where they live is for the owner to
  check. A PASS without access is evidence, not a trade.

## What the author has seen
- **R439 in full** on 2021-01..2026-09 (M468 engine), including both books' daily series and trades.
- **This book under v1 on the same archive** (`plumbing/expect.py`, output in `plumbing/expect.out`), computed for
  the table below.
- **The other forward carry lanes, read on 2026-11-10 at about 13:20 UTC:** each book's mean daily 1x net over its
  scored and late days to 2026-11-10 (R278 A/B/C +0.57/+3.78/+1.87 bp/day over 19 days; R279 A/B +1.00/+1.24; R390 A
  −0.36 over 6; R294 A −0.01 over 18). None of them is this book, but they share its venues and dates.
- **Not computed for any day after 2026-09-30 on this book:** no funding spread, no window and no pair choice. The
  replay runs after this freeze.

## Decision (as R278, R279 and R390)
- **Scored days:** every interval that starts on a live (`ontime` or `late`) decision day. The first ends on 2026-11-12.
- **The decided series:** the daily net at 1x, fill accounting, on total capital.
- **Looks:**

  | Look | Scored days | Date | Outcome |
  |---|---|---|---|
  | 1 | 90 | 2027-02-09 | **PASS** if all hold:<br>• Newey-West t (lag 10, `lab.stats.newey_west_t`) ≥ 2.5<br>• the sum of the 2x net > 0<br>• max drawdown of the cumulative 1x net > −3%<br>**FAIL** if the 1x mean ≤ 0<br>**CONTINUE** otherwise |
  | 2 | 180 | 2027-05-10 | **PASS** on the same three conditions, else **FAIL** |

- **Kill switch:** if the book's cumulative 1x net falls below −3% of capital on any day, the book is FAIL at once. The
  lane keeps ticketing it for the record, and those tickets are reported, not decided on.
- **Multiplicity:**
  - 1 book × 2 looks: Bonferroni one-sided 0.05 / 2 needs z ≥ 1.96.
  - 2.5 is used, the same bar as R278, R279 and R390.
- **Timing quality:** if more than 20% of the scored days are `late`, the verdict is labelled degraded timing.
- **Interim:**
  - The 30- and 60-day checkpoints and the dashboard figures are descriptive only.
  - `journal/status.json` shows NW t and drawdown every hour for monitoring.
- **What a PASS earns:** gate 2, if the owner can trade the venues the book uses.
  - A frozen small-stake plan, run through `lab.gate.go_real()` and placed by the owner.
  - Nothing here moves money.

## Expectations
**Power, from R439's archive under this lane's accounting** (`plumbing/expect.out`; in sample, close accounting,
before fills). The share of windows meeting all three PASS conditions:

| Window set | Mean 1x | 90-day windows passing | 180-day windows passing | Worst drawdown in any window |
|---|---|---|---|---|
| 2025-01..2026-09 (638 days) | +7.40 bp/day (+27.0%/yr) | 49% | 55% | −3.79% |
| 2021-01..2026-09 (2,078 days) | +4.48 bp/day (+16.4%/yr) | 75% | 87% | −3.79% |

- **The drawdown condition binds.** The −3.79% trough runs from 2026-02-09 to 2026-03-27, the same weeks as R390's
  −5.19% trough, which came from forced one-leg exits in the engine's delisting accounting. Whether the same exits
  cause this one was not broken down. 23 of the book's 1,165 trades are forced.
  - The kill switch would have fired in sample.
  - The live contract lists (deviations 1 and 7) should exit or avoid some of these earlier. That is untested.
- **The 2025+ windows pass less often** despite the higher mean: their days are more volatile.
- **Real fills, decay since the archive and selection** (R275's best of 560, inherited) make both rows lower.
- **A FAIL** would mean the five-venue carry does not survive live data and fills at this size. That is a result,
  recorded with the same care.

## Reported, not decided on
- 2x and 3x costs;
- close accounting (R275's own);
- the fill gap per day;
- funding share of gross;
- pairs held, pairs by venue and forced exits;
- late days and decision delay;
- data freshness per venue;
- values changed on API overlap;
- the replay total;
- the comparison with R278, R279 and R390's books over the same days.

## Multiplicity
- Trials: 1 (the book).
- Program trials before this lane: 9,784,982 (`registry.program_trials()` on 2026-11-10).

```inputs
d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d lab/xfund.py
22a91dc96cd04a4ac9dce5914d5fba5485f754088acef74f7efe03f10e8e0328 experiments/carry5_v1/symbols.csv
12efdca302dfdbc1312dc7499a53de23af9276406e1934c547b9e8642622e895 lab/carrylane.py
29a1729f05f54ffa8bdd1b4376200f994bd0ebb2abf8c654126caaaadeeefeee scripts/forward_xfund5.py
ab3f50faecb9753955a9a6f5f4fc117a974559addc5ed3b94eb879b94d0438d4 tests/test_forward_xfund5.py
d8a6fdc1f08d2bee570bfe061fb03e3dc6906fe3d7a4b3cccd146f15066ca503 experiments/xfund5_fwd/plumbing/expect.py
e5b6b3c49b7a42d3eba00866dd7826d55eb1b2b8d34840fb39ba09fbe9f00300 experiments/xfund5_fwd/plumbing/expect.out
```
