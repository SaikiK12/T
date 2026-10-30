# PREREG: xbook_fwd (R285). The cross-family forward book: carry, flow and events at equal risk (M281)

Freeze with `lab.prereg.freeze()` before the first book day exists. Never edited afterwards; a change is a new lane.

- **Registry id:** R285. **Method:** M281.
- **Gate:** 1 (forward). Only book days from 2026-10-23 count. When this was frozen (2026-10-21), none of them existed.
- **Owner (single writer):** the session that froze it.
  - It writes only `experiments/xbook_fwd/journal/`.
  - It reads the other lanes' journals and never writes them.
- **Code:**
  - `scripts/forward_xbook.py` calls `verify()` on this file first. It runs from `scripts/forward_all.sh` after the
    lanes it reads.
  - `scripts/xbook_archive.py` gives the archive context below.
  - `tests/test_xbook.py` covers it.
- **Why:** the owner's "having one strategy is maybe limiting ourselves", and the multi-PM arithmetic.
  - With N sleeves of Sharpe S at pairwise correlation ρ, a book's Sharpe is S·√(N/(1+(N−1)ρ)).
  - Each lane below is decided on its own. This book asks whether the families together reach the bar sooner than any
    of them alone.
  - Sources: Odd Lots 2024-10-07, `docs/VIDEO_DIG.md`.

## What the author has seen
- **The archive results of every lane below** (gate 0, in sample). `scripts/xbook_archive.py` rebuilds them as three
  daily family series over 2023-06-01..2026-09-30 (1,218 days). Output: `archive/context.json`, sha256 `64999691…`.
  - **Family correlations:**

    | | Carry | Flow | Events |
    |---|---|---|---|
    | Carry | 1 | 0.009 | 0.014 |
    | Flow | | 1 | 0.000 |
    | Events | | | 1 |

  - **Inside a family:** flow A vs X2 0.97, A vs B 0.47; the carry books 0.00 to 0.29.
  - **In-sample Sharpe:**
    - carry 12.4 (close accounting, before fills);
    - flow 1.8;
    - events 3.3;
    - the risk-balanced book 10.0.

    These numbers come from rules picked on the same years. They are an upper bound, not an expectation.
- **The forward journals,** read for their columns and their row counts by `kind` only:
  - flow (R215, R218): 1 on-time day;
  - carry (R278, R279): replay rows only;
  - events: no ticket in R268, R270 or R272, and one unscored ticket in R266.

  No forward net was read for this design.

## The sleeves (frozen)
Each sleeve is a running lane's own decided series at 1x. Its `replay` rows are dropped; `ontime` and `late` rows both
count.

| Family | Sleeve | Source (`experiments/<lane>/journal/`) | 1x / 2x columns |
|---|---|---|---|
| Carry | R278 A, R278 B | `xfund_fwd/days.csv`, book A / B (fill accounting, on total capital) | `net` / `net_2x` |
| Carry | R279 A, R279 B | `xfund_kc_fwd/days.csv`, book A / B | `net` / `net_2x` |
| Flow | R215 A, R215 B | `mexc_fwd/tickets.csv`, book A / B (MEXC, one bar late) | `net` / `net_2x` |
| Flow | R218 X2 | `mexc_fwd_sq/tickets.csv`, book X2 | `net` / `net_2x` |
| Events | R266 unlock short | `unlocks_fwd/tickets.csv` + `scores.csv` | `net` (measured cost) / `net_2x` (model) |
| Events | R268 delisting short +1 h | `delist_fwd/tickets.csv` + `scores.csv` | same |
| Events | R270 Monitoring Tag short +24 h | `montag_fwd/tickets.csv` + `scores.csv` | same |
| Events | R272 FF long 1 h and PL short 168 h | `announce_fwd/tickets.csv` + `scores.csv` | same |

**Left out:**
- R278 C (post hoc);
- R220 carry_fwd (R191's rule, about 1.2%/yr at 1x);
- R214 (Binance twin of the flow books);
- R225 (a sizing overlay on R215/R218).

## The book
**Book day d:** a UTC calendar day, labelled as each lane labels its rows. The days run from 2026-10-23 to the day
before the run.

**Family values on d:**
- **Carry and flow:** the mean over the family's sleeves that have a live row labelled d. If none has one, the family is
  missing that day.
- **Events:**
  - Each event ticket is booked on the UTC day of its primary exit (`exit_ms`).
  - The family's capital is split into 10 slots. Its value on d is the sum of the scored nets of the tickets exiting
    on d, divided by 10.
  - A day with no exit is 0. A ticket not yet scored counts 0 and is counted in `unscored`.

**Risk weights, fixed here from `archive/context.json`** (each family's daily sd over the archive window):

| Family | Daily sd |
|---|---|
| Carry | 0.0005196660416284657 |
| Flow | 0.024151067161747936 |
| Events | 0.01271633250070641 |

**The decided series:**
- book(d) = mean over the three families of value(d) / sd. Each family carries the same archive risk.
- book_2x uses the 2x columns the same way.

**Final days:**
- A book day is final when carry and flow both have a value and it is at least 9 days old. 9 days covers the longest
  event hold (168 h) and its scoring.
- **Scored days** are the final days, in date order.

## Decision

| Look | Scored days | About | Outcome |
|---|---|---|---|
| 1 | 180 | 2027-05 | **PASS** if all hold:<br>• the Newey-West t (lag 10, `lab.stats.newey_west_t`) of book ≥ 2.5<br>• the sum of book_2x > 0<br>• at least two of the three families have a positive mean over the same days<br>**FAIL** if the book's mean ≤ 0<br>**CONTINUE** otherwise |
| 2 | 365 | 2027-11 | **PASS** on the same three conditions, else **FAIL** |

- **Each look is written once** to `journal/decisions.csv` (append-only). The lane stops deciding after a PASS or a
  FAIL.
- **Multiplicity:** one book, two looks. Bonferroni one-sided 0.05/2 needs z ≥ 1.96; 2.5 is used, as in R278.
- **No pruning:** the sleeves stay as listed whatever their own lanes decide.
- **Interim:** `journal/status.json` and `journal/book_days.csv` are rebuilt every tick and are descriptive only.
- **What a PASS earns:** a gate-2 proposal for the book, through `lab.gate.go_real()`, placed by the owner.
  - It must be capital-feasible. Equal risk needs carry notional about 46 times flow's (the sd ratio), and R280 found
    carry legs liquidated even at 1x under isolated margin. The plan will say how it gets near equal risk, or at what
    weights it does not.
  - A sleeve whose own lane has FAILED by then is left out of that plan.
- **What a FAIL means:** these families, combined this way, did not beat the bar. Each lane's own verdict stands.

## Reported (not decided on)
- **Each family alone:** days, mean, NW t, drawdown.
- **Family correlations** on the scored days. This is the ρ the arithmetic depends on.
- **The equal-capital book** (the plain mean of the three families' nets): mean, NW t, drawdown.
- **The on-time-only book:** the same book using only sleeve rows of kind `ontime`.
- **Event tickets and unscored tickets.**
- **What diversification paid:** the book's t against the best single family's t.

## Power
In-sample, the risk-balanced book reached t ≥ 2.5 in 97% of 90-day windows and in every 180- and 365-day window. That
is the upper bound from picked rules.

More realistic: with near-zero correlation, book Sharpe ≈ (S_carry + S_flow + S_events) / √3, and the expected t at n
days ≈ Sharpe·√(n/365).

| Forward Sharpe guess (carry / flow / events) | Book Sharpe | E[t] at 180 d | E[t] at 365 d |
|---|---|---|---|
| 2.5 / 0.5 / 1.5 | 2.60 | 1.82 | 2.60 |
| 2.0 / 0.0 / 1.0 | 1.73 | 1.22 | 1.73 |
| 1.5 / 0.0 / 0.5 | 1.15 | 0.81 | 1.15 |

A PASS at 180 days needs a book Sharpe near 3.5. At 365 days it needs about 2.5. A FAIL is the likely outcome unless
at least two families hold most of their archive edge.
