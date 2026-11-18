# PREREG: xfund_eea_fwd (R509). R508's Kraken + Hyperliquid carry book, forward on paper from 2026-11-19, charged its measured book costs

Freeze with `lab.prereg.freeze()` before the first tick. Never edited afterwards; a change is a new lane.

- **Registry id:** R509
- **Gate:** 2 (forward paper). Only days decided live from 2026-11-19 count. Nobody had seen them when this was frozen.
- **Source:** R508 xfund_eea_v1 (gate 1, PASS).
  - R275's carry book on Kraken + Hyperliquid, 2025-12..2026-11: +24.28 / +22.50 / +20.73 %/yr at 1x / 2x / 3x, NW t
    7.39.
  - 97% of it came from coins trading under $100k a day on Kraken. Its FINDINGS named a forward lane with measured
    fills as the next step.
- **Why this one:** both venues are ones the owner could trade from France (Kraken's EEA derivatives, Hyperliquid's
  DEX). The owner asked on 2026-11-18 for an opening with large or stable gains.
- **Owner (single writer):** the session that froze it, then the GitHub workflow `claude-carry-paper.yml`, which
  ticks it.
  - The lane writes only `experiments/xfund_eea_fwd/journal/` and `data/xfund_eea_fwd/`.
- **Paper only.** Nothing here can place an order or move money.

## Book
| Book | Venue set | Lookback | Entry threshold | Slots | R508, 1x |
|---|---|---|---|---|---|
| A | kraken + hyperliquid | 14 d | 5%/yr | 20 | 6.65 bp/day over 343 days; 4.32 bp/day in its second half |

R508's primary book, unchanged. No variant was chosen here.

## Rule (R275's, as run by R278 and R279 through `lab.carrylane`)
- **Daily axis:** 00:00 UTC.
- **Close and freshness.** Daily candles on both venues, as in R508. The close on day D is the candle ending at
  00:00 UTC. It is fresh when that candle traded.
- **Funding:** hourly settlements in (D − 1, D] belong to day D.
  - Kraken: `relativeFundingRate`, a fraction of notional per hour, paid by longs when positive.
  - Hyperliquid: its hourly `fundingRate`.
- **Signal:** each venue's funding over the last 14 days. The spread is their difference × 365 / 14.
- **Identity guard:** daily log returns correlated ≥ 0.9 over 30 days, at least 20 observations.
- **Entries:** coins with a spread ≥ 5%/yr, widest first, into free slots.
- **Position:** long on the venue that paid less, short on the other, 1x on each leg.
- **Exits:** below 2.5%/yr, a stale leg (3 days), an undefined window, or a contract leaving its venue's live list.
- **Universe:** R508's frozen table (`experiments/xfund_eea_v1/symbols.csv`, 111 coins).
- **Warm-up and the first live day.**
  - Data from 2026-10-01, rebuilt from the public APIs; there is no archive on GitHub.
  - The book replays from its window start.
  - On 2026-11-19 it inherits the replayed pairs at live prices; the inheritance is charged as entries.

## Accounting
- **Journal (`lab.carrylane`, R279's).**
  - Close and fill accounting at 7 / 14 / 21 bp a leg-side. A fill is the live mid at the decision.
- **Book records (`scripts/forward_xfund_eea.py`).**
  - After each tick, every new on-time ticket gets a record for both legs in `journal/book_fills.csv`.
  - Each venue's live book is walked for a market order of $1,000 and $2,500 on the side the leg trades.
  - The cost is in bp of the mid, fees excluded.
- **The decided series** (`scripts/read_xfund_eea_fwd.py`): the daily net with measured costs, on total capital.
  - net_book = net (1x, fill accounting) + (0.0007 × legs − the sum of measured costs) / (2 × 20).
  - The sum runs over the leg-sides of the decision day's `enter`, `exit` and `inherit` tickets.
  - A leg-side costs its `cost_bp_1000` plus the venue's taker fee: Kraken 5 bp (EEA tier 1, R418); Hyperliquid
    4.5 bp (tier 0).
  - A leg-side with no book record, a late ticket for instance, costs 21 bp.
  - `drop` tickets, replayed pairs that were never held, cost nothing.

## Decision
- **Scored days:** every interval that starts on a live (`ontime` or `late`) decision day. The first ends on
  2026-11-20.
- **Looks:**

  | Look | Scored days | Date (about) | Outcome |
  |---|---|---|---|
  | 1 | 90 | 2027-02-17 | **PASS** if all hold:<br>• Newey-West t (lag 10) of net_book ≥ 2.5<br>• the sum of net_book with measured costs doubled > 0<br>• max drawdown of cumulative net_book > −3%<br>**FAIL** if the mean net_book ≤ 0<br>**CONTINUE** otherwise |
  | 2 | 180 | 2027-05-18 | **PASS** on the same three conditions, else **FAIL** |

- **Kill switch.** If cumulative net_book falls below −3% of capital on any day, the lane is FAIL at once. It keeps
  ticketing for the record.
- **Timing quality:** if more than 20% of scored days are `late`, a PASS is labelled degraded timing.
- **Interim:** 30- and 60-day figures are descriptive only. So are the measured cost per leg-side against R508's
  7 bp, and per-coin capacity.
- **What a PASS earns.**
  - A frozen small-stake plan, run through `lab.gate.go_real()` and placed by the owner.
  - It requires first that the owner confirms Kraken EEA derivatives access, leverage and margin for their account.
  - Nothing here moves money.

## Expectations
Power, from R508's own days (in sample, close accounting, flat costs):

| Series | 90-day windows with NW t ≥ 2.5 | Latest 90-day window t | 180-day windows |
|---|---|---|---|
| 1x | 100% | 3.64 | 100% |
| 2x | 100% | 2.75 | 100% |
| 3x | 98% | 1.91 | 100% |

- The live snapshot of 2026-11-18 put thin-coin costs at about 2-3x R508's 7 bp, with fees.
- R508's level fell through its year.
- So look 1 may well CONTINUE. Look 2 is the stronger test.
- A FAIL means that Kraken's thin-book funding does not survive live fills. That is a result, recorded with the same
  care.

## Reported, not decided on
- the journal's 1x / 2x / 3x flat-cost lines and close accounting;
- measured cost per leg-side by venue and coin, at $1,000 and $2,500;
- the fill gap; the funding share;
- pairs held, forced exits and delistings;
- late days; data freshness per venue; values changed on API overlap.

## Multiplicity
- **Trials:** 1 (one book). Program trials before this lane: 9,785,749; after it: 9,785,750.
- **Looks.** 2. A one-sided Bonferroni over 2 needs z ≥ 1.96; 2.5 is used, the bar of R278 and R279.

## Not checked before the freeze
- **Access.** Kraken EEA derivatives eligibility and EU retail leverage limits for the owner; Hyperliquid's legal
  status for a French resident.
- **Margin.** Two-venue margin and transfers. R280 found isolated legs liquidated by pumps even at 1x.
- **Exchange risk.** Kraken delisting thin perps, which forces exits.
- **Depth over time.** One book snapshot is not depth over time; the lane measures it from here.

## Code
| File | sha256 at this freeze | After the freeze |
|---|---|---|
| `lab/xfund.py` | d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d | fixed; the tick refuses if it changes |
| `experiments/xfund_eea_v1/symbols.csv` | cf942d8f7e9235e5af3956b627d3edf06633f29f57c184a02670510b751975c0 | fixed; checked the same way |
| `scripts/read_xfund_eea_fwd.py` | 633d3a7be7489ba55399f371d8bab0ca690fae7cd26d325067f8acc1feac97eb | fixed; it computes the decided series |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 | fixed (Newey-West t) |
| `lab/carrylane.py` | 12efdca302dfdbc1312dc7499a53de23af9276406e1934c547b9e8642622e895 | pinned by other lanes; not edited |
| `lab/kraken.py` | 92ecfe0cfa2dae1f3ceef23f177fa84ad19f283d07036b2c1383566e022d0707 | data plumbing only; `walk` and `side_fill` keep their meaning |
| `scripts/forward_xfund_eea.py` | 5ea7908b79bcfc39bfa863fab8d35fc9d61794e2f2f988e2b192ff9d46863f3a | data plumbing only |
| `tests/test_forward_xfund_eea.py` | 6f449b5cccdc272049c279f084313102e1661e4b5927b6ae0890cea88e730c9d | tests |

- **Dry run before the freeze (2026-11-18, 21:47 UTC, scratch folder, not this journal).**
  - One tick from the public APIs, with no archive: 111 coins on each venue, 0 failures. It decided 2026-10-22..11-18
    in replay and late, with 87 tickets.
  - The live books of the last day's tickets walked at 6-29 bp a side for $1,000.
