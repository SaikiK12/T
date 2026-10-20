# PREREG: xfund_v1 (R275). Cross-venue funding carry on Binance, Gate, Hyperliquid and MEXC

Freeze with `lab.prereg.freeze()` before any price return or funding statistic is read. Never edited afterwards; a
change is a new lane.

- **Registry id:** R275 (Claude block R260-R279, claimed on issue #7 on 2026-10-20)
- **Gate:** 0. Every month here is in the archive (2021-01..2026-09), and Binance funding there has been read by
  carry_v1 (R190) and many lanes. The Gate, Hyperliquid and MEXC funding histories are new to this question.
- **Method:** M059 (`registry/methods.csv`): the old session's E02 (Hyperliquid vs Binance) and X28 (`xvenue_carry`).
- **The question:** the same coin pays different funding on different venues. Long the perp where funding is lower
  and short it where it is higher; the price legs cancel, the funding difference is collected. Does a rule that
  enters only wide, persistent spreads keep enough of the difference after four legs of cost, price gaps between the
  venues and the days a coin trades on one venue only, to beat a T-bill?
- **Execution mode:** API. Both legs are placed at the same daily close on two venues. Each venue needs its own
  collateral; moving collateral between venues is not modelled (see limits).
- **Paper only.** Nothing here places an order.

## What the author has seen
- **The old session (docs/OLD_SESSION_EDGES.md):** E02 "spread real, about 3-4 times the CEX-CEX null; 2026 liquid-20
  book +2.05%/yr gross"; X28 `xvenue_carry` "+22%/yr gross in 2021, +0.9%/yr in 2024-26". Its rules and code are not
  in this repo. S4 proposed the hurdle and the NW t gate used here.
- **The live funding board** (`scripts/record_funding_board.py`, 2026-10-20 21:00 and 22:00 UTC snapshots, after the
  archive ends): cross-venue spreads of several hundred %/yr exist on thin coins at a given hour. Nothing about their
  persistence or their price legs.
- **Binance funding:** carry_v1 / carry_fwd (R190, R191, R220) and the funding-onset lanes (R273, R274).
- **MEXC funding:** R274 counted onsets at or below -0.3% (MEXC funding values at those settlements). No spread
  between MEXC and any other venue was computed.
- **Gate, Hyperliquid:** row counts, column names, and the first or last 2-3 rows of BTC files while checking the
  formats (e.g. Gate BTC_USDT funding 0.000226, 0.000100, 0.000439 on 2021-01-01; Hyperliquid BTC hourly rates of
  1e-5 in 2026-10). No statistic, no spread.
- **Engine checks:** unit tests and one end-to-end run on a synthetic data root (3 made-up coins with a planted
  spread), never on real data.
- **KuCoin and dYdX** (`scripts/fetch_venue_history.py`, downloading when this file is frozen): row counts and first or
  last timestamps of BTC, ETH and PEPE files while testing the fetcher. No rate statistic, no spread.

## Inputs (frozen)

```inputs
experiments/xfund_v1/symbols.csv  SYMBOLS_SHA
experiments/xfund_v1/spec.toml  SPEC_SHA
scripts/venue_symbols.py  VS_SHA
engine/src/spread.rs  SPREAD_SHA
engine/src/data.rs  DATA_SHA
engine/src/events.rs  EVENTS_SHA
engine/src/factors.rs  FACTORS_SHA
engine/src/stats.rs  STATS_SHA
engine/src/main.rs  MAIN_SHA
engine/Cargo.lock  LOCK_SHA
rebuild: python scripts/venue_symbols.py {tmp}/symbols.csv
```

Data digests at freezing (`docs/provenance/<folder>.json`, combined sha256): PROVENANCE_LINES

## Universe (`scripts/venue_symbols.py`, from file names and contract lists only)
- One row per Binance USD-M perp that has klines and funding in the archive, with the same coin's file on:
  - **Gate:** `data/gate_hist/open/` contracts that `fetch_gate_history.py` routed to that Binance perp;
  - **Hyperliquid:** coins in both `candles_1d` and `funding`; "k" coins are the 1000x contracts (kPEPE = 1000PEPE);
  - **MEXC:** USDT perps in `contracts.json` with klines and funding files.
  - The name rule is R274's `binance_perp` (plain, 1000 or 1000000 prefix).
- Rows listed on fewer than 2 venues are dropped. COUNTS_LINE
- **Reserved samples are never read:** the table only contains coins with a Binance perp, so no MEXC-only coin and no
  Gate long-tail contract is opened. Gate's 2020 rows are not in `open/`, and qx drops every row before 2021-01-01 as
  it reads (Binance 2020 included).
- **Same ticker is not proof of the same coin:** the correlation guard below decides identity on prices.

## Accounting (qx `spread`, `engine/src/spread.rs`)
- **Daily axis:** day d is the instant 2021-01-01 + d days, 00:00 UTC, through 2026-10-01.
  - A venue's close on day d is its last traded close at or before that instant: hourly bars (Binance, Gate, MEXC) or
    daily bars (Hyperliquid, whose API serves only 5,000 hourly bars). A bar is traded when its close is finite and
    positive and its volume > 0.
  - A venue is **fresh** on day d when the bar ending at that instant traded.
- **Funding:** a settlement at time s (floored to the hour) belongs to day ceil((s - start) / 1 day), so funding in
  (day d - 1, day d] is day d's. The long pays +rate; the short receives it. Rates are summed as settled, whatever the
  venue's interval (1 h, 4 h, 8 h).
- **Signal on day d, lookback L days:** each venue's settled funding over (day d - L, day d]. A venue is eligible when
  it is fresh on day d, its first settlement is on or before day d - L + 1, and it settled at least once in the
  window. Spread = higher minus lower, annualized x 365 / L.
- **Identity guard:** a pair is eligible on day d only if the two venues' log returns on days where both were fresh
  on that day and the day before, over (day d - 30, day d], number at least 20 and correlate at least 0.9.
- **Widest pair:** a set of more than two venues takes, per coin, its widest eligible pair.
- **Book, K slots, entry threshold th:**
  - each day, exits first: a held pair exits when both legs are fresh and its own spread (same orientation, same L)
    is below th / 2 or undefined. A leg whose venue never trades again (delisted) closes at its last close, flagged
    `forced`;
  - then entries: coins not held, with spread >= th, widest first (ties by table order), into free slots;
  - no switching: a held coin keeps its pair until it exits.
- **Return:** each slot is 1/K of capital, posted 1x on each leg, so a leg's notional is 1/(2K), reset daily.
  - Net day (day d close to day d + 1 close) = [sum over held pairs of (long return - short return + short venue's
    day d + 1 funding - long venue's day d + 1 funding) - cost x legs traded at day d's close] / (2K).
  - Pairs still open on the last day pay their exit on the last interval.
- **Cost:** 7 / 14 / 21 bp per leg per side at 1x / 2x / 3x (taker fee about 4.5-5 bp on all four venues, plus a
  half-spread). An entry or exit is 2 legs.
- **Window:** a (set, lookback) starts on its first day with any eligible pair; every book of that pair shares it.
  Days with no position count as 0.

## The family and the decision
- **Books:** 7 venue sets (binance+gate, binance+hyperliquid, binance+mexc, gate+hyperliquid, gate+mexc,
  hyperliquid+mexc, all four) x L {1, 3, 7, 14 d} x th {5, 10, 20, 40, 80 %/yr} x K {3, 5, 10, 20} = **560**.
- **Reality check (RC):** moving-block bootstrap of the day axis, blocks of 10 days (circular), 2,000 replications,
  ChaCha8 seed 275. Every book uses the same blocks; each book's days are centred on its own mean; the family
  statistic is the max t (mean / (sd / sqrt(n)), ddof 1) over books. p_RC = (1 + #(family max t >= the book's t)) /
  2,001. A book that never trades has no t and p_RC 1.
- **Gates (each book, 1x unless stated):**

  | Gate | Rule |
  |---|---|
  | RC | p_RC < 0.05 |
  | NW | Newey-West t (Bartlett, 10 lags) > 2 |
  | HALVES | both halves of the window have a mean > 0 |
  | RECENT | days from 2025-01-01 have a mean > 0 |
  | TRIM | the mean without the top and bottom 1% of days > 0 |
  | HURDLE | annual net (mean x 365) >= 4.13% (the old S4 T-bill value) |
  | COST2X | the mean at 2x cost > 0 |

- **Verdict:** PASS (gate 0) for each book that clears all gates. The registry row reads PARTIAL if any book passes,
  NULL if none does. Gate 0 cannot confirm.

## Pre-committed (written before the result)
- **If any book passes:**
  - the passing book with the highest 1x t gets a frozen forward paper lane (new id) on the live funding board and
    the venues' public prices, tickets frozen before entry;
  - if the best passing book needs no MEXC leg, the passing book with a MEXC leg and the highest t also goes forward
    (the owner trades MEXC first), if one exists;
  - the best passing book whose set is binance+gate joins the first reserved batch (Binance and Gate 2020 rows,
    `RESERVED-2020-READ` and `RESERVED-GATE-READ`).
- **If none passes:** the binance+gate book with the highest 1x t joins the first reserved batch only if its t >= 2
  and its 2x mean > 0. Otherwise nothing from this family enters a batch or goes forward.
- **Venue replication (whatever the result):** a new lane, frozen before it runs, applies one book's lookback,
  threshold and slots unchanged to four sets built only on venues this family never read: binance+kucoin,
  binance+dydx, gate+kucoin, kucoin+dydx (histories from `scripts/fetch_venue_history.py`, 2026-10-20).
  - The book: the best passing book by 1x t, or the best book by 1x t if none passes.
  - 4 books, no other parameter. Same accounting and costs.
  - **A set replicates** when its NW t > 2.50 (one-sided p < 0.0125, Bonferroni over 4), HALVES holds and its 2x mean
    is > 0.
  - Read as a confirmation only if R275 passed. Otherwise it is a record, and the lane reads NULL unless a set clears
    the same bar.

## Reported, not counted
- Per (set, lookback): window start, coins ever eligible, mean coins per day at or above each threshold.
- Per book: annual net at 1x / 2x / 3x, Sharpe, max drawdown, funding share of the gross, average pairs held, trades,
  forced exits, top-10-day share; daily rows and trades for the survivors and the 10 best by t.

## Known limits (written before the result)
- **Survivorship:** Hyperliquid and MEXC histories hold only contracts live on 2026-10-20; Gate and Binance include
  delisted ones.
- **Hyperliquid prices are daily candles,** so a Hyperliquid leg is fresh only if the day's bar traded, and its close is
  the daily close.
- **Not modelled:** liquidation of one leg (each leg is 1x here; at 3x a 33% adverse move on one leg liquidates it),
  moving collateral between venues and its fees, intraday rebalancing of leg notionals, and funding paid on drifted
  notionals.
- **Short windows:** MEXC data start 2025-04, Hyperliquid funding 2023-05. Sets with them have fewer days, and the
  RECENT gate covers most of a MEXC window.

## Program reading
- Read against `registry.program_trials()` after this row: 9,477,741 before it, plus 560.
