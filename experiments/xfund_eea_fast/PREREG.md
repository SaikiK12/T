# PREREG: xfund_eea_fast (R510). A 30-day read of R509's journal on the funding it earns, net of measured costs

Freeze with `lab.prereg.freeze()` before R509's first scored day closes (2026-11-20 00:00 UTC). Never edited
afterwards; a change is a new lane.

- **Registry id:** R510
- **Gate:** 2 (forward paper), an early read. It trades nothing: it reads R509's journal (`experiments/xfund_eea_fwd/`)
  with a statistic that needs fewer days.
- **Owner (single writer):** the session that froze it. It writes only `experiments/xfund_eea_fast/` (FINDINGS at each
  look).
- **Paper only.** Nothing here can place an order or move money.
- **Date registered (UTC):** 2026-11-19

**Methods:** M553. Carry family, candidate C13.

## Why
- **The owner, 2026-11-19:** "why does it take so long; cut this time by several days".
- **R509's looks need 90 and 180 scored days because its whole daily net is noisy.**
  - On R508's days, the net had a daily sd of about 18 bp of capital against a mean of 6.65 bp. Almost all the noise is
    the price legs: hedged on the same coin, mean −0.3 bp/day, sd about 16 bp/day.
  - The funding the held pairs earned had an annualised Sharpe of 16.9, against 7.1 for the whole net.
- **So the funding part can say in a month what the whole net needs three to six months to say.**
  - The questions are whether the funding edge persists out of sample, and whether real book costs leave it.
  - The price legs remain a risk. Here they are a guard, and R509's own looks decide on them.

## Data
R509's journal only: `decisions.csv`, `tickets.csv`, `days.csv` and `book_fills.csv`, from completed runs. These are
the scored days R509's read defines: intervals starting on a live decision day of book A, the first ending on
2026-11-20.

## Statistic (`scripts/read_xfund_eea_fast.py`)
Per scored day:
- **fund_book** = funding − measured cost / 40.
  - `funding` is the funding the held pairs earned that day, per unit of total capital (R509's `days.csv`).
  - The measured cost is R509's: each leg-side traded at the start of the interval costs its $1,000 book walk plus the
    taker fee (Kraken 5 bp, Hyperliquid 4.5 bp), or 21 bp without a record.
- **net_book** is R509's decided series. **price** = net_book − fund_book: the price legs and the live-fill gap.

## Decision (one candidate)
| Look | Scored days | Date (about) | Outcome |
|---|---|---|---|
| 1 | 30 | 2026-12-19 | **PASS** if all hold:<br>• Newey-West t (lag 5) of fund_book ≥ 2.5<br>• the cumulative net_book over the 30 days > 0<br>**FAIL** if the mean fund_book ≤ 0<br>**NOT YET** otherwise |
| 2 | 45 | 2027-01-03 | **PASS** on the same two conditions; **FAIL** if the mean fund_book ≤ 0; otherwise **NO EARLY PASS**, and R509's own looks decide |

- **R509's kill switch applies.** If R509's cumulative net_book falls below −3%, this read is FAIL at once.
- **What a PASS earns.**
  - The owner may start a small stake early, before R509's 90-day look: at most $2,000 of two-leg capital, through
    `lab.gate.go_real()` on R509's scored daily net_book, placed by the owner.
  - It requires first that the owner confirms Kraken EEA derivatives access, the contracts offered to their account,
    leverage and margin.
  - R509 keeps running. A later R509 FAIL, or its kill switch, ends the stake.
- **What a FAIL means.** The funding edge did not survive out of sample after real costs. Its record is kept with the
  same care, and R509 runs on to its own looks.

## Power
From R508's 343 days (in sample, its flat costs scaled to the measured level):

| Cost level | 30-day windows passing (t ≥ 2.5 and cumulative net > 0) | Last 120 days only |
|---|---|---|
| 1x (7 bp) | 92% | 82% |
| 2.4x (the 2026-11-18/19 book measurements, fees included) | 84% | 66% |
| 3x | 78% | 57% |

- R508's level fell through its year. So look 1 may say NOT YET, and look 2 adds 15 days.
- Lag 5 instead of R509's 10: a 30-day series carries too few lags for 10.

## Trials and multiplicity
- **Trials:** 1. Program trials before this lane: 9,785,750; after it: 9,785,751.
- **Looks:** 2. A one-sided Bonferroni over 2 needs z ≥ 1.96; 2.5 is used.
- R509's own decision is unchanged and counted separately.

## What the author has seen
- R509's journal through its first live decision, 2026-11-19, and no scored day:
  - 19 inherited pairs, 1 entry and 1 drop;
  - book records for all 42 leg-sides: median cost per side, fees excluded, 16.7 bp on Kraken and 7.9 bp on
    Hyperliquid.
- R508's results, which set the power figures above.

## Not checked before the freeze
- **Price legs as the funding read ignores them.** The guard is the cumulative net_book. A basis that drifts
  persistently against the book can pass a 30-day guard and still fail R509 later.
- **Access, margin and delistings,** as in R509.

## Code
| File | sha256 |
|---|---|
| `scripts/read_xfund_eea_fast.py` | 4a8236d533262f1c0a0a520a666b28d37a9f873b3a76010704ed7ccaf1bfdfc1 |
| `tests/test_read_xfund_eea_fast.py` | d4ad774e315d6544eee76ef68a0bfff97eb3e36e6482b6b9d5fd46ad5b667456 |
| `scripts/read_xfund_eea_fwd.py` | 633d3a7be7489ba55399f371d8bab0ca690fae7cd26d325067f8acc1feac97eb |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 |
