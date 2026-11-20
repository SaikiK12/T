# PREREG: passive_kraken_fwd (R514). R513's passive-entry saving, measured forward on the Kraken legs R509 and R512 trade

Freeze with `lab.prereg.freeze()` before the first snapshot. Never edited afterwards; a change is a new lane.

- **Registry id:** R514
- **Gate:** 1 forward, a cost measurement. It trades nothing. It reads R509's and R512's journals and Kraken's
  public book and charts.
- **Owner (single writer):** the session that froze it, then `claude-carry-paper.yml`, which runs it after the carry
  lanes. It writes only `experiments/passive_kraken_fwd/journal/`.
- **Date registered (UTC):** 2026-11-20

**Methods:** M555. Execution, for candidate C13.

## Why
- **R513 (2026-11-20), on 91 days of history.** On Kraken's thin perps, a resting order with a taker fallback saved
  +4.91 bp a leg-side at 6 h and +8.23 bp at 1 h, against an immediate taker order.
- **Its limits.** It used a constant spread per coin, the mark price as the mid, and decision times at 00:00.
- **What this lane does.** It measures the same thing on the live tickets, with the real best quote at the moment of
  the decision. The owner asked on 2026-11-20 to do everything.

## Rule (`scripts/forward_passive_kraken.py`)
- **Snapshot.** For each new completed ticket of R509 or R512 with a Kraken leg (enter, inherit or exit; not drop),
  it records Kraken's live book:
  - the best bid and ask, the mid;
  - the side the Kraken leg trades;
  - the $1,000 walk on that side.
  - A snapshot more than 30 minutes after the ticket's run is marked `late`.
- **Evaluation**, at least 6 h later, for H = 1 h and 6 h:
  - **The passive order** rests at the best bid (buy) or best ask (sell).
  - **Filled** when a 5-minute trade candle with volume > 0, closing in (t, t + H], trades strictly through it.
    Cost: the signed gap of the limit to the mid, plus the 2 bp maker fee.
  - **Otherwise a taker order at t + H.** Cost: side × (mark_{t+H} / mid_t − 1) + the walk + 5 bp, with the mark
    from 1-minute candles.
  - **saving** = walk + 5 bp − passive cost.
- **Fees:** Kraken Pro futures tier 1, maker 0.02% and taker 0.05%.

## Decision (`--read`)
- **The series.** Each snapshot day's mean saving at H = 1 h, over snapshots that are not `late`.
- **PASS** at 30 or more days, if the mean is above 0 and its Newey-West t (lag 5) is at least 2.0.
- **FAIL:** at 30 or more days, if the mean is at or below 0; or at 60 days without a PASS.
- **RUNNING** otherwise. H = 6 h is reported.
- **What a PASS earns.** Evidence that the carry books' Kraken legs can be entered passively at lower cost. The next
  carry lane (a new id) would charge passive-then-taker costs. No money.

## Expectations
- R513 at H = 1 h: +8.2 bp a leg-side on thin coins (t 9.5), and +6.5 bp or more in every liquidity bucket.
- The tickets here mix thin and liquid coins.
- From 2026-11-21 the clock chain dispatches the lanes at 00:31 UTC, so most snapshots should be on time.
- The 2026-11-19 and 2026-11-20 tickets, snapshotted at the first run, will be `late` and are not decided on.

## Not checked before the freeze
- **Our own order is not in the market.** Its effect on the queue is not modelled. The conservative fill (a print
  through the level) avoids queue assumptions.
- **Hyperliquid and Aster legs are not measured.** Their books are deeper.

## Trials
- **This round:** 1.
- **Program trials** before it: 9,785,754; after it: 9,785,755.

## Code
| File | sha256 |
|---|---|
| `scripts/forward_passive_kraken.py` | d19ad1058cee04ae5982575c3c4bfb13a247cd22cd803bfceaba8dbab5eb3c5a |
| `tests/test_forward_passive_kraken.py` | 8dec8bed2457fb04ccc2cf9e4932a4a1e49a2bd665b671d02b85cce47a826e4b |
| `lab/kraken.py` | 92ecfe0cfa2dae1f3ceef23f177fa84ad19f283d07036b2c1383566e022d0707 |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 |
