# PREREG: xfund_kc_fwd (R279). R277's two replicating KuCoin carry books, forward on paper from 2026-10-22

Freeze with `lab.prereg.freeze()` before the first tick. Never edited afterwards; a change is a new lane.

- **Registry id:** R279 (Claude block R260-R279, claimed on issue #7 on 2026-10-21).
- **Gate:** 1 (forward). Only days decided live from 2026-10-22 count. Nobody had seen them when this was frozen.
- **Source:** R277 xfund_kd_v1 (gate 0, PARTIAL).
  - It applied R275's best carry book, unchanged, to four sets on venues R275 never read.
  - 2 of 4 replicated: gate+kucoin (NW t 11.41) and binance+kucoin (NW t 11.17).
  - Its PREREG allowed a replicating set with a venue the owner can trade its own forward lane, with a new id.
    Its FINDINGS pre-committed these two books.
- **Owner (single writer):** the session that froze it. It writes only `experiments/xfund_kc_fwd/journal/` and
  `data/xfund_kc_fwd/`.
- **Paper only.** Nothing here can place an order or move money.

## Books
| Book | Venue set | Lookback | Entry threshold | Slots | R277, 2025-26, 1x |
|---|---|---|---|---|---|
| A | gate + kucoin | 14 d | 5%/yr | 20 | 5.92 bp/day (sd 14.4) |
| B | binance + kucoin | 14 d | 5%/yr | 20 | 5.69 bp/day (sd 12.1) |

Both are R275's best book (gate+hyperliquid L14d th5% K20), whose parameters R277 fixed before reading KuCoin.
Neither book was chosen among variants here.

## Rule (R275's, as run by R278, unchanged unless listed under Deviations)
- **Daily axis:** 00:00 UTC.
- **Close and freshness:**
  - A venue's close on day D is its last traded close at or before 00:00 UTC.
  - It is fresh when the bar ending at that instant traded.
  - KuCoin uses daily bars, as in R277. Binance and Gate use hourly bars.
- **Funding:** settlements in (D − 1, D] belong to day D, with the settlement time floored to the hour.
- **Signal:** per coin and venue pair, the funding each venue settled over the last 14 days. The spread is their
  difference, annualized (× 365 / 14). A window needs a settlement in it and the venue's funding history to cover it.
- **Identity guard:** the two venues' fresh daily log returns correlated ≥ 0.9 over the last 30 days, with at least
  20 observations.
- **Entries:** coins with a spread ≥ 5%/yr, taken widest first (ties by table order) into the free slots.
- **Position:** long the coin on the venue that paid less and short it on the venue that paid more, 1x on each leg.
- **Exits:** when the spread falls below 2.5%/yr, or a leg is not fresh, or the window is undefined.
- **Interval D → D + 1:** each held pair earns the long leg's close-to-close return minus the short's, plus the short
  venue's day D + 1 funding minus the long venue's.
- **Net on total capital:** (gross − cost × legs traded) / (2 × slots). Costs are 7 / 14 / 21 bp per leg per side.
  - KuCoin's listed taker fee is 6 bp, Gate's 5 bp and Binance's 5 bp.
- **Universe:** R277's frozen symbol table (`experiments/xfund_kd_v1/symbols.csv`).
  - gate+kucoin can trade 629 coins and binance+kucoin 642.
  - Coins listed after the table was built are not traded.

## Code
| File | sha256 at this freeze | After the freeze |
|---|---|---|
| `lab/xfund.py` | d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d | fixed; the run script refuses to run if it changes |
| `experiments/xfund_kd_v1/symbols.csv` | 15c8054f7e10f921bd9a797fbf2b9ac927c99fdfbc2388a54199be0cace6fb3b | fixed; checked the same way |
| `lab/carrylane.py` | fe24ae2a6a21f7fc9d42b7b1fb144889edb325369a8b4976fa3325f5520064cb | data plumbing only |
| `scripts/forward_xfund_kc.py` | 497b6c6f0e50331456559856608f98243371e283c7a9623dfca87a610cbce916 | data plumbing only |

- **What the files are:**
  - `lab/xfund.py` is the line-for-line Python twin of `qx spread`, the engine R275 and R277 ran on. It is R278's
    fixed file.
  - `lab/carrylane.py` is R278's lane (`scripts/forward_xfund.py`) for any set of venues, plus KuCoin's public
    clients:
    - daily candles: `/api/v1/kline/query`;
    - funding: `/api/v1/contract/funding-rates`;
    - live mids: `/api/v1/allTickers`;
    - contract list: `/api/v1/contracts/active`, with status `Open`.
- **Changes after the freeze:** data plumbing only (venue clients, retries, file handling). Each change needs the
  tests to pass and a line in `journal/CHANGES.md` with its commit. A change to the rule, the books, the accounting or
  the decision is a new lane.
- **Parity, checked before this freeze:**
  - `python scripts/xfund_parity.py --lane xfund_kd_v1` replays both books on the archive with `lab/xfund.py` and
    reproduces R277's engine output:

    | Book | Trades identical | Daily 1x net |
    |---|---|---|
    | gate+kucoin | 1,153 of 1,153 | within 5e-11 on all 2,078 days |
    | binance+kucoin | 1,168 of 1,168 | within 5e-11 on all 2,078 days |

  - `tests/test_carrylane.py`:
    - runs `lab/carrylane.py`, set up as R278, next to R278's own script on one synthetic root over four ticks
      (replay, take-over, delisting, a further day): the journals are byte-identical;
    - checks a KuCoin lane's replay against the twin on a synthetic root with daily KuCoin bars;
    - checks the KuCoin clients' paging, mids, contract status and error codes.

## Deviations from R277 (forced by running forward; R278's, plus 7)
1. **Forced exit.**
   - A pair exits (forced) when either leg has had no fresh close on any of the last 3 days.
   - It also exits when either leg's contract is missing from its venue's live contract list at a live decision.
   - For Gate, a contract that is `in_delisting` counts as missing. For KuCoin, so does a contract whose status is not
     `Open`.
2. **Universe:** frozen, as above.
3. **Data:**
   - Archive rows from 2026-08-01, then the venues' public APIs on every run.
   - API rows replace archive rows on overlap, and the changed values are counted in `journal/status.json`.
   - Only closed bars are kept.
4. **Start:**
   - Each book replays from its own window start on the forward data (2026-08-01 plus the funding and correlation
     history) up to 2026-10-21. The replay is not scored.
   - On 2026-10-22, the first live day:
     - replayed pairs that the rule exits that day are dropped, since they were never held on paper;
     - the remaining replayed pairs are taken over at live prices, with entry legs charged (ticket action
       `inherit`).
5. **Decided accounting (fill):**
   - R277's close accounting plus each live ticket's gap between the venue's live mid at the decision and day D's
     close, on both legs.
   - R277's close accounting is reported next to it.
6. **Timing:**
   - The hourly loop decides day D on its first run after 00:00 UTC on which each needed venue's share of fresh
     coins on D is at least 0.9 of its share on D − 1. It waits up to 6 h.
   - A day decided more than 7 h after 00:00, or caught up after a gap in the loop, is `late`. It has no live mid and
     books the close.
   - **Known bias** (as R278): a pair decided at hour h of day D is credited the settlements in (D, D + h] that it
     did not hold. Every ticket's `run` stamp makes it measurable. It is reported, not corrected.
7. **No entry on a delisted contract (new; R278 does not have it).**
   - At a live decision, a coin whose contract is missing from a venue's live list cannot be entered on that venue.
   - In R278 a pair forced out by a delisting can be entered again the same day and forced out the next, which
     churns 4 legs a day. This was found while writing this lane's tests. R278 stays as frozen and the flaw is noted
     in its lane notes.

## Not modelled (from R275's PREREG; still true)
- **Liquidation of a leg above 1x.** R280 (levcarry_v1) measures it on the archive.
- Moving collateral between venues.
- Intraday rebalancing.
- **Order-book depth:** K = 20 at $10k is $250 per leg.
- Fees beyond the per-leg cost.
- **Whether the owner can open a KuCoin futures account where they live** is for the owner to check. A PASS
  without access is evidence, not a trade.

## What the author has seen
- **R277 in full** (KuCoin from 2021-01 to 2026-09-30): its four sets, audit, by-year table, the dYdX crash days and
  the in-sample power figures below.
- **R278's replay** (2026-08-22..2026-10-21 on Gate, Hyperliquid, Binance and MEXC) ran before this freeze, and its
  status file shows each R278 book's replay total. No R278 book has a KuCoin leg.
- **KuCoin after 2026-09-30, while writing this lane (2026-10-21):**
  - while checking file formats: the last 3 rows of the BTC daily candle file (bars opening 2026-10-17..19) and of
    the BTC funding file (3 settlements, 2026-10-20 00:00..16:00);
  - one row each of the live tickers and active-contract lists, which were XBTUSDTM's contract terms and ANIMEUSDTM's
    quote;
  - the clients' smoke test: BTC's last 40 days of daily bars and funding, printed as row counts, columns and time
    ranges only;
  - counts: 702 live mids, 702 contracts `Open`, and all 642 of the table's KuCoin symbols quoted and listed.
- **Not computed for any day after 2026-09-30 on KuCoin:** no funding spread, no window and no pair choice. The
  replay runs after this freeze.

## Decision (each book on its own, as R278)
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
  - 2 books × 2 looks: Bonferroni one-sided 0.05 / 4 needs z ≥ 2.24.
  - 2.5 is used, the same bar as R278.
- **Timing quality:** if more than 20% of a book's scored days are `late`, its verdict is labelled degraded timing.
- **Interim:**
  - The 30- and 60-day checkpoints and the dashboard figures are descriptive only.
  - `journal/status.json` shows NW t and drawdown every hour for monitoring.
- **What a PASS earns:** gate 2, if the owner can trade KuCoin.
  - A frozen small-stake plan, run through `lab.gate.go_real()` and placed by the owner.
  - Nothing here moves money.

## Expectations
Power, from R277's own 2025-26 days (in sample, close accounting, before fills):

| Book | 90-day windows with NW t ≥ 2.5 | 180-day windows | Worst 90-day drawdown |
|---|---|---|---|
| A | 85% | 100% | −0.66% |
| B | 96% | 100% | −0.52% |

- **Lower in practice:** real fills (the live mid at the decision against the 00:00 close) and any decay from the
  2025-26 level make both lower.
- **A FAIL on both books** at this power would mean the KuCoin carry does not survive live data and fills. That is a
  result, recorded with the same care.

## Reported, not decided on
- 2x and 3x costs;
- close accounting (R277's own);
- the fill gap per day;
- funding share of gross;
- pairs held and forced exits;
- late days and decision delay;
- data freshness per venue;
- values changed on API overlap;
- replay totals;
- the comparison with R278's books over the same days.

## Multiplicity
- Trials: 2 (books).
- Program trials before this lane: 9,478,326, after R277.
