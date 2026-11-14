# PREREG: xfund_bg_fwd (R390). The binance+gate carry book that passed reserved batch 1 (C14), forward on paper from 2026-11-04

Freeze with `lab.prereg.freeze()` before the first tick. Never edited afterwards; a change is a new lane.

- **Registry id:** R390
- **Claim:** Claude block R390-R399, claimed on issue #7 on 2026-11-03.
- **Gate:** 1 (forward). Only days decided live from 2026-11-04 count. Nobody had seen them when this was frozen.
- **Source:** R286 `reserved_batch1`, candidate C14 (`experiments/reserved_batch1/FINDINGS.md`).
  - It read R275's binance+gate L14d th10% K20 book, frozen before the read, once on 2020 Binance and Gate rows nobody
    had read.
  - It passed every frozen check: +2.86 / +1.86 / +0.85 %/yr at 1x / 2x / 3x, NW t 4.03, p 2.8e-5 against α 0.0297.
    The trimmed, leave-two-coins-out and 2x means were all positive.
  - R286's PREREG says a passing candidate without a forward lane "gets a new frozen forward paper lane (new id)".
    None of R278, R279 or R294 trades this set: R278 runs gate+hyperliquid, binance+mexc and gate+mexc.
- **Owner (single writer):** the session that froze it. It writes only `experiments/xfund_bg_fwd/journal/` and
  `data/xfund_bg_fwd/`.
- **Paper only.** Nothing here can place an order or move money.

## Book
| Book | Venue set | Lookback | Entry threshold | Slots | R275 2021-26, 1x | R286 2020, 1x |
|---|---|---|---|---|---|---|
| A | binance + gate | 14 d | 10%/yr | 20 | +10.05%/yr, NW t 5.96, 2,078 days | +2.86%/yr, NW t 4.03, 345 days |

The book is R275's, unchanged. It was pre-committed as C14 before R286's read, and it was not chosen among variants
here.

## Rule (R275's, as run by R278 and R279 on `lab/carrylane.py`, unchanged unless listed under Deviations)
- **Daily axis:** 00:00 UTC.
- **Close and freshness:**
  - A venue's close on day D is its last traded close at or before 00:00 UTC.
  - It is fresh when the bar ending at that instant traded.
  - Both venues use hourly bars.
- **Funding:** settlements in (D − 1, D] belong to day D, with the settlement time floored to the hour.
- **Signal:** per coin, the funding each venue settled over the last 14 days. The spread is their difference,
  annualized (× 365 / 14). A window needs a settlement in it and the venue's funding history to cover it.
- **Identity guard:** the two venues' fresh daily log returns correlated ≥ 0.9 over the last 30 days, with at least
  20 observations.
- **Entries:** coins with a spread ≥ 10%/yr, taken widest first (ties by table order) into the free slots.
- **Position:** long the coin on the venue that paid less and short it on the venue that paid more, 1x on each leg.
- **Exits:** when the spread falls below 5%/yr (half the entry threshold, as in the engine), or a leg is not fresh,
  or the window is undefined.
- **Interval D → D + 1:** each held pair earns the long leg's close-to-close return minus the short's, plus the short
  venue's day D + 1 funding minus the long venue's.
- **Net on total capital:** (gross − cost × legs traded) / (2 × slots). Costs are 7 / 14 / 21 bp per leg per side.
- **Universe:** R275's frozen symbol table (`experiments/xfund_v1/symbols.csv`). Coins listed after it was built are
  not traded.

## Code
| File | sha256 at this freeze | After the freeze |
|---|---|---|
| `lab/xfund.py` | d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d | fixed; the run script refuses to run if it changes |
| `experiments/xfund_v1/symbols.csv` | 78201a341b9fc498b67f4893f1dd30d67d790d94ca8257a4b1a2ce8f569ab8e0 | fixed; checked the same way |
| `lab/carrylane.py` | 12efdca302dfdbc1312dc7499a53de23af9276406e1934c547b9e8642622e895 | data plumbing only |
| `scripts/forward_xfund_bg.py` | a156c1e00a898d988365d1f8352619f6e76c3e841123d8b693caec9ae355f002 | data plumbing only |

- `lab/xfund.py` is the line-for-line Python twin of `qx spread`, the engine R275 ran on. `lab/carrylane.py` is the
  shared forward lane of R279 and R294, run here with venues `binance` and `gate` in R275's spec order.
- **Changes after the freeze** are data plumbing only (venue clients, retries, file handling). Each needs the tests to
  pass and a line in `journal/CHANGES.md` with its commit. A change to the rule, the book, the accounting or the
  decision is a new lane.
- **Parity, checked before this freeze.**
  - Command: `python scripts/xfund_parity.py --lane xfund_v1 --forward xfund_bg` replays the book on R275's archive
    with `lab/xfund.py`.
  - Result: `binance+gate L14d th10% K20: trades 1402 vs 1402, identical True; days 2078 vs 2078, max |net diff|
    5.0e-11; OK`.

## Deviations from R275 (forced by running forward; the same as R279's)
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
     up to 2026-11-03. The replay is not scored.
   - On 2026-11-04, the first live day:
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
   - **Known bias** (as R278 and R279): a pair decided at hour h of day D is credited the settlements in (D, D + h]
     that it did not hold. Every ticket's `run` stamp makes it measurable. It is reported, not corrected.
7. **No entry on a delisted contract (R279's rule).** At a live decision, a coin whose contract is missing from a
   venue's live list cannot be entered on that venue.

## Not modelled (from R275's PREREG; still true)
- **Liquidation of a leg above 1x.** R280 measures it on the archive and found no safe leverage.
- Moving collateral between the two venues.
- Intraday rebalancing.
- **Order-book depth:** K = 20 at $10k is $250 per leg.
- Fees beyond the per-leg cost.
- **Access:** whether the owner can hold Binance and Gate futures accounts where they live is for the owner to check.
  A PASS without access is evidence, not a trade.

## What the author has seen
- **R275 in full** on 2021-01..2026-09, including this book's archive daily series. The power table below is computed
  from it.
- **R286's 2020 read of this book** (`experiments/reserved_batch1/results/carry/`).
- **R278's lane:**
  - its tick log line "decided 83..86 (2026-10-23..2026-10-26)";
  - its status file's last day (2026-11-02).
  - None of R278's books is binance+gate. No R278 journal number for Binance or Gate after 2026-09-30 was read while
    writing this lane.
- **Not computed for any day after 2026-09-30 on this book:** no funding spread, no window and no pair choice. The
  replay runs after this freeze.

## Decision (as R278 and R279)
- **Scored days:** every interval that starts on a live (`ontime` or `late`) decision day. The first ends on 2026-11-05.
- **The decided series:** the daily net at 1x, fill accounting, on total capital.
- **Looks:**

  | Look | Scored days | Date | Outcome |
  |---|---|---|---|
  | 1 | 90 | 2027-02-02 | **PASS** if all hold:<br>• Newey-West t (lag 10, `lab.stats.newey_west_t`) ≥ 2.5<br>• the sum of the 2x net > 0<br>• max drawdown of the cumulative 1x net > −3%<br>**FAIL** if the 1x mean ≤ 0<br>**CONTINUE** otherwise |
  | 2 | 180 | 2027-05-03 | **PASS** on the same three conditions, else **FAIL** |

- **Kill switch:** if the book's cumulative 1x net falls below −3% of capital on any day, the book is FAIL at once. The
  lane keeps ticketing it for the record, and those tickets are reported, not decided on.
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
**Power, from R275's own days** (in sample, close accounting, before fills). The share of windows meeting all three
PASS conditions (NW t ≥ 2.5, 2x sum > 0, drawdown > −3%):

| Window set | Mean 1x | 90-day windows passing | 180-day windows passing | Worst drawdown in any window |
|---|---|---|---|---|
| 2025-01..2026-09 (639 days) | +4.79 bp/day (+17.5%/yr) | 51% | 33% | −5.19% |
| 2021-01..2026-09 (2,078 days) | +2.75 bp/day (+10.0%/yr) | 56% | 69% | −5.19% |

- **The drawdown condition binds.** The −5.19% trough (2026-02-10 to 2026-03-25) comes from two forced one-leg exits
  in the engine's conservative delisting accounting: A2ZUSDT on 2026-03-25 (price −140% on the leg) and YALAUSDT on
  2026-02-11 (−111%).
  - Forced trades are 2.2% of the book's 1,402.
  - The kill switch would have fired in-sample.
  - The forward lane's live contract lists (deviations 1 and 7) should exit or avoid some of these earlier. That is
    untested.
- **At R286's 2020 strength** (+0.78 bp/day, NW t 4.03 over 345 days), the expected NW t over 90 days is about 2.1.
  A PASS at look 1 then has roughly a one-in-three chance.
- **Real fills and decay** since the archive make both rows lower.
- **A FAIL** would mean the binance+gate carry does not survive live data and fills at this size. That is a result,
  recorded with the same care.

## Reported, not decided on
- 2x and 3x costs;
- close accounting (R275's own);
- the fill gap per day;
- funding share of gross;
- pairs held and forced exits;
- late days and decision delay;
- data freshness per venue;
- values changed on API overlap;
- the replay total;
- the comparison with R278's books over the same days.

## Multiplicity
- Trials: 1 (the book).
- Program trials before this lane: 9,782,840 (`registry.program_trials()` on 2026-11-03).
