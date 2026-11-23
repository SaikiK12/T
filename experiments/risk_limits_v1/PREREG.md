# PREREG: risk_limits_v1 (R526). What the live risk limits cost the design-gap books, and whether they remove the tail

Freeze with `lab.prereg.freeze()` before any limit is computed on real data. Never edited afterwards.

- **Registry id:** R526
- **Owner (single writer):** the Claude session that froze it. `scripts/run_risk_limits.py` is the only writer of
  `experiments/risk_limits_v1/results/`.
- **Date registered (UTC):** 2026-11-23

**Methods:** M552 (the design gap), risk overlay. Carry, candidate C13.
- **Paper only.**

## Why
- **The self-review of 2026-11-23** (`docs/reviews/self_review_20261123.md`) ranks it the first piece of unasked work.
  No real money can start without priced limits.
- **R525's audit** found the tail. Under a one-day decision delay, bitfinex+gate lost −11.4%/yr. One LUNA trade
  (May 2022) lost 34x a leg's notional, and the worst day was −85.9% of book capital.
- **The audit proposed limits:**
  - an hourly divergence stop;
  - a 5% cap per coin;
  - no entry on a dead series;
  - a minimum printing activity.
- **Questions:**
  - What does each limit cost in return?
  - Does it remove the tail?

## What the author has seen before the freeze (post hoc, from R525's audit)
- **The delay result, reproduced exactly** (base +4.33%/yr; delay −11.40%/yr; worst day −85.87%).
- **The LUNA trade.**
  - The delayed book entered at day 499 (2022-05-15), long Gate and short Bitfinex.
  - **Entry prices disagreed about 5x:** Gate 0.000528, Bitfinex 0.0001. Bitfinex printed sporadically on a dying
    contract.
  - The next day's Bitfinex close was 0.0035, and the blowout check closed the trade.
- **Gate's `LUNA_USDT` changed identity.** After 2022-05-26 it is LUNA 2.0 (about $5.5 from 2022-05-28), a ticker
  reuse.
- **R525's stale-looking Bitfinex legs:** SAND, COMP and ALGO.
- **Not seen:** any limited book on real data. A pre-freeze plumbing check ran the base (it reproduces R525 exactly
  on deribit+binance and bitfinex+gate) and the stop path with a stop that cannot fire.

## The limits (`scripts/run_risk_limits.py`)
- **Book:** R525's, unchanged.
  - Engine: R275's L14d th5% K20 on `lab.xfund_v2`.
  - Loader: R437's; spec and symbols: R525's.
  - Costs: 7/14/21 bp a leg.
- **A slot is 1/K = 5% of book capital,** so the 5% cap per coin is already the book. It is not a separate variant.
- **agree** (all 12 pairs).
  - No entry when the two legs' prices at the entry instant differ by more than 2% (|log ratio| > log 1.02).
  - Two live venues on one coin quote within a fraction of a percent; a larger gap means a stale, dying or renamed
    leg.
- **active** (pairs whose legs both have hourly bars).
  - No entry unless each leg printed (volume > 0) in at least 20 of the 24 hourly bars before the entry instant.
- **stop** (hourly pairs).
  - Close both legs at the first hourly close where the legs' price ratio has moved more than 10% from entry, **and**
    both legs printed in that hour. A halted leg cannot be closed, so the stop waits for it.
  - Funding on the stop day is prorated by the hours held.
  - The coin is barred for 7 days. The engine's daily 20% blowout and dead-leg exits stay.
- **all:** agree + active + stop.
- **Sensitivity (reported, also decided):** agree at 5%, stop at 20%, and 1% extra slippage per leg on stopped
  trades.
- **Hourly pairs:** deribit+binance, deribit+gate, bitfinex+binance, bitfinex+gate.
  - Hyperliquid's hourly history starts 2026-04; KuCoin and Kraken are held as daily bars only.
- **Timing:** each variant runs at the base timing and with R525's audit delay (entries decided on day d−1's
  windows, made at day d's prices).
- **Reproduction first:** the run stops unless the base book reproduces R525's daily nets on all 12 pairs
  (tolerance 1e-12).

## Decision rule (frozen in `decide()`)
- **A limit is ADOPTED for live books** if, on its portfolio (P12, all 12 pairs, for agree; P4, the 4 hourly
  pairs, for the others):
  1. at the base timing, its 1x return is at least 80% of the base's; and
  2. with the delay, its worst day and its 1x return are no worse than the base's.
- **PASS** if "all" is adopted and its delay-1 worst day is above −5% of book capital.

## Supply, break-even and power (`CLAUDE.md` step 4)
- **Supply.** This round prices rare events, not an edge.
  - The tail events are coin deaths, halts and renames: a few a year across about 150 Bitfinex and Deribit coins.
  - The cost side is continuous: every blocked entry and every false stop.
- **Break-even.** A false stop costs a round trip (2 legs × 7 bp on one slot) plus forgone carry until re-entry
  (about 7 days at 5-30%/yr on 5% of capital).
  - At 1-3 false stops per pair-month, that is about 0.1-0.5%/yr of book capital, against base returns of 3.5-7%/yr
    on the hourly pairs.
  - So the stop keeps 80% only if false stops are rare.
- **Power.** The comparison is deterministic on the same days (the same trades, minus what the limits remove), so it
  needs no t. The tail check rests on one known event (LUNA) and the stale Bitfinex legs. Rule 2 can be decided by
  one trade.

## Pre-mortem: "it failed because…"
1. **The stop fires on noise.** Thin Bitfinex legs print far from fair value for an hour, so whipsaw costs eat the
   carry. Mitigations: both legs must print, and the 7-day bar. Reported: the stop count, and the share of stops
   whose ratio is back within 10% 24 hours later.
2. **The stop cannot act when it matters.** A dying coin halts on one venue, so the stop waits. Reported as found;
   agree and active then carry the protection.
3. **agree removes the edge.** If Kraken's (daily, last-trade) returns depend on entries where the legs disagree,
   agree cuts them. That would mean part of Kraken's +31%/yr is valuation of stale prints: a finding for the Kraken
   decomposition, not a reason to drop the limit. Reported per pair: blocked entries and the funding share.
4. **Hourly data gaps** in older Gate or Bitfinex history silently disable the stop. Reported: the stop count per
   pair and year.
5. **Overfitting to LUNA.** The limits were proposed after seeing one event. Rule 1 (cost at base timing) is judged
   on all trades, and the sensitivity at 5% and 20% shows whether the conclusion depends on the exact threshold.

## Trials
- **This round:** 6 (agree, agree at 5%, active, stop, stop at 20%, all).
- **Program trials:** 9,785,781 before, 9,785,787 after.

## Inputs
| File | sha256 |
|---|---|
| `scripts/run_risk_limits.py` | 0ff73f516347a10bfc7d1b72b306047a27867e385673386f5270510ed8f8101b |
| `tests/test_risk_limits.py` | fa968b2ece99e2fc93d370d65a5e7d9efec1d2129fe23944b9f5b2da34e3f50d |
| `scripts/run_gap_breadth.py` | 501c0286dbb28bd0adc519c3c9e953c68d1cdd872d7a34c001a9dcc83494b27b |
| `scripts/run_carry_v2_audit.py` | 1ba92fe3df40a0eac920e47c69ac4b7b9024750d4ba13f94edcfbe8f4550b7e5 |
| `scripts/run_xfund_bfx.py` | 62c1c214856c80b5006527824778815069cf341b740bb5d48c4d646364d30b79 |
| `lab/xfund.py` | d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d |
| `lab/xfund_v2.py` | fa85ef56885a1d6736dd92e73f8bce44e97ce9ee001739526caef86ae1ba62cd |
| `lab/stats.py` | bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 |
| `experiments/gap_breadth_v1/spec.toml` | fec0e888ef64efa4547fade7f5b2015f5503f708687ad83d9ba818b3ad6617a6 |
| `experiments/gap_breadth_v1/symbols.csv` | 74494ecaa77f7aa5db6b63afa562e3c044a7388cc74d8c8c47c547d3dbd1f9d9 |
| `experiments/gap_breadth_v1/results/pair_daily_net_1x.csv` | f1720372f66acc53023a2b4653278085cfa462b46f97b240eaed9dd1ad0ab0dd |
