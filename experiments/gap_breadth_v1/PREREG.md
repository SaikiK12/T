# PREREG: gap_breadth_v1 (R525). The design gap on every floorless × floor venue pair the lab holds, and the portfolio of all of them

Freeze with `lab.prereg.freeze()` before any new pair's spread is computed. Never edited afterwards.

- **Registry id:** R525
- **Owner (single writer):** the Claude session that froze it. `scripts/run_gap_breadth.py` is the only writer of
  `experiments/gap_breadth_v1/results/`.
- **Date registered (UTC):** 2026-11-23

**Methods:** M552 (the design gap, widened). Carry, candidate C13.
- **Paper only.**

## Why
- **The owner, 2026-11-23:** "Ta eu un breakthrough énorme je crois donc creuse ou creuse à côté". Standing rule 2
  in `CLAUDE.md`.
- **The breakthrough** (`docs/reviews/framework_20261123.md`): four design-gap books are nearly uncorrelated, and
  their equal-weight portfolio had Sharpe 8.5 in sample.
- **This round widens it.** Every pair of a floorless venue (Kraken, Bitfinex, Deribit) with a floor venue (Binance,
  Gate, Hyperliquid, KuCoin) whose data the lab holds.
  - MEXC is left out: the lab's symbol map gives it no rows today.
- **Questions:**
  - How many pairs pay?
  - What does the portfolio of all of them earn, at what drawdown?

## Data and universe
- **Symbols:** `symbols.csv`, keyed by the Binance perp.
  - Gate, Hyperliquid, KuCoin and Kraken come from `lab.venues.table()`.
  - Bitfinex comes from R507's table; Deribit from R519's (bases matched by R274's name rule).
  - Built from names only.
- **Coins per pair:**
  - Kraken: 178 with Binance, 176 Gate, 113 Hyperliquid, 172 KuCoin;
  - Bitfinex: 69 / 69 / 57 / 61;
  - Deribit: 88 on each.
- **Data:** the lab's held folders (`spec.toml`), rebuilt 2026-11-17..21 (`docs/reviews/data_rebuild_20261117.md`).
  - Hourly bars for Binance, Gate, Bitfinex and Deribit (Deribit from `prices_1h`, closes at 00:00 UTC per R519's
    deviation); daily for Hyperliquid, KuCoin and Kraken.
  - Window 2021-01-01..2026-09-30. Each pair starts when both venues have data.

## Rule (`scripts/run_gap_breadth.py`)
- **Each pair:** R275's book unchanged on `lab.xfund_v2`, read by R391's rule (R507's `decide`).
- **Portfolio (decided):** each day, the mean 1x net over the pairs live that day.
  - PASS if its NW t (lag 10) ≥ 3.0, its 2x-cost mean > 0, and both halves are positive.
  - Equal weight, no selection.
- **Also reported:**
  - three floorless sleeves, each the mean of its pairs;
  - pair correlations on common days;
  - by year.

## Break-even, power and supply (`CLAUDE.md` step 4)
- **Break-even.** Each pair is the same book as R507/R508/R519, whose nets cleared 3x costs. A new pair pays only
  if its floor-minus-premium spread on the coins it trades clears 28 bp a round trip over about 3-4 weeks of hold.
- **Power.** The portfolio averages 12 pairs over up to 5.7 years. At the four known books' in-sample level (Sharpe
  8.5 together), NW t ≥ 3 is near certain if the new pairs are not negative. A FAIL would mean the new pairs dilute
  or reverse it.
- **Supply:** continuous holding on 57-178 coins a pair.

## What the author has seen
- **The three known pairs** (R507, R508, R519's reported book) and their correlations (framework note).
- **Kraken, Hyperliquid, Binance, Gate and KuCoin funding** were read by many carry lanes (R275, R277, R439, R508…),
  in other pairings.
- **Never computed:** Kraken against Binance, Gate or KuCoin; Bitfinex against Hyperliquid, Gate or KuCoin; Deribit
  against Binance, Gate or KuCoin.

## Trials
- **This round:** 9 (the new pairs). The portfolio is their combination, not a separate selection.
- **Program trials:** 9,785,772 before, 9,785,781 after.

## Inputs
| File | sha256 |
|---|---|
| `scripts/run_gap_breadth.py` | 501c0286dbb28bd0adc519c3c9e953c68d1cdd872d7a34c001a9dcc83494b27b |
| `tests/test_gap_breadth.py` | 33289a8da211648ea0207da105e72511d29b7bbce431cc3e0359e93abbd6f72f |
| `scripts/run_carry_v2_audit.py` | 1ba92fe3df40a0eac920e47c69ac4b7b9024750d4ba13f94edcfbe8f4550b7e5 |
| `scripts/run_xfund_bfx.py` | 62c1c214856c80b5006527824778815069cf341b740bb5d48c4d646364d30b79 |
| `lab/xfund.py` | d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d |
| `lab/xfund_v2.py` | fa85ef56885a1d6736dd92e73f8bce44e97ce9ee001739526caef86ae1ba62cd |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 |
| `experiments/gap_breadth_v1/spec.toml` | fec0e888ef64efa4547fade7f5b2015f5503f708687ad83d9ba818b3ad6617a6 |
| `experiments/gap_breadth_v1/symbols.csv` | 74494ecaa77f7aa5db6b63afa562e3c044a7388cc74d8c8c47c547d3dbd1f9d9 |
