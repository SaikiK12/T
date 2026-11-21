# PREREG: xfund_dhl_fwd (R520). R275's carry book on Deribit + Hyperliquid, forward on paper

Freeze with `lab.prereg.freeze()` before the lane's first tick. Never edited afterwards.

- **Registry id:** R520
- **Owner (single writer):** the Claude session that froze it. The carry workflow's tick
  (`scripts/forward_xfund_dhl.py`) is the only writer of `experiments/xfund_dhl_fwd/journal/` and
  `data/xfund_dhl_fwd/`.
- **Date registered (UTC):** 2026-11-21

**Methods:** M560 (forward). Carry, candidate C13.
- **Paper only:** nothing here can place an order.

## Why
- **The owner:** "il nous faut une faille" (2026-11-21), then "continue et self improve".
- **R519's reported book** (R275's rule on Deribit + Hyperliquid, 2023-06..2026-11):
  - +4.52 / +3.43 / +2.35 %/yr at 1x/2x/3x, NW t 7.02;
  - every year positive; 49 coins, BTC among them; max drawdown −0.85%.
- **The gap.** Deribit's funding has a ±0.025%/8 h dead zone and no interest term. Hyperliquid's longs pay a
  0.01%/8 h floor.
- **Why it matters.** R508's Kraken version has little capacity. This one trades liquid coins.
- **Why forward.** That book was a reported secondary on data now seen. Only unseen days can confirm it.

## Rule
- **The book:** R275's book unchanged (`lab.xfund` through `lab.carrylane`):
  - deribit+hyperliquid, lookback 14 days, entry 5%/yr, exit below half, 20 slots;
  - correlation guard 30 days >= 0.9 on 20 observations.
- **Symbols:** R519's 89-coin table (`symbols.csv`, copied from `experiments/deribitgap_v1/results/symbols.csv`).
- **Venues:**
  - Deribit through `lab.deribit` (new). Hourly bars with `bar_h` 1, so daily closes are at 00:00 UTC (R519's
    deviation); hourly funding (`interest_1h`).
  - Hyperliquid through `lab.carrylane`.
- **Clock:** warm-up from 2026-10-01; scored from 2026-11-22; ticked by `claude-carry-paper.yml` (dispatched at
  00:31 and 02:31 UTC).
- **Costs:**
  - every on-time ticket walks both live books for $1,000 and $2,500 (R509's recorder);
  - the read charges cost_bp_1000 plus the taker fee: Deribit 3.5 bp, Hyperliquid 4.5 bp;
  - a leg with no record costs 21 bp.

## Decision (`scripts/read_xfund_dhl_fwd.py`)
- **net_book per scored day:** R512's definition, through `read_xfund_eea3_fwd.series`.
- **Why two fixed looks.** R519's book has a daily Sharpe ratio of about 0.20. R512's anytime rule (E >= 40) would
  need about 300 days and stop at 180, so it would FAIL a true edge. Two fixed looks have the power.
- **Kill switch:** FAIL at once if the cumulative net_book falls below −3% before a decision.
- **Look 1, 90 scored days:**
  - PASS if NW t (lag 10) of net_book >= 2.5 and the cumulative net_book > 0;
  - FAIL if the mean net_book <= 0;
  - otherwise continue.
- **Look 2, 180 scored days:** PASS if NW t >= 2.0, otherwise FAIL.
- **A decision is final.** The overall false-pass rate is about 0.006 + 0.023 ≈ 3%.
- **Power, at R519's in-sample level** (expected t 1.86 at 90 days, 2.63 at 180): about 30% at look 1 and about 75%
  by look 2. At half that level, the lane likely FAILs.
- **Reported, not decided:** R512's anytime e-value, fund_book, and the share of late days.

## What a PASS earns, and what it does not
- **Earns:** a case for a small stake through `lab.gate.go_real()`, placed by the owner, once the owner confirms
  Deribit access from France.
- **Does not:** this lane decides nothing about money by itself.

## What the author has seen
- **R519's full history** (2023-05..2026-11-17) on these venues and coins.
- **A dry run** of this lane's code on 3 coins (BTC, DOGE, ETH) in a scratch folder on 2026-11-21. It printed only
  file row counts.
- **Nothing from 2026-11-22 on.**

## Trials
- **This round:** 1.
- **Program trials:** 9,785,763 before, 9,785,764 after.

## Inputs
| File | sha256 |
|---|---|
| `scripts/forward_xfund_dhl.py` | cd8de8a5b814aaac18ba58ed9660b10757f3abc58778a42e0526af4c2e5e754f |
| `scripts/read_xfund_dhl_fwd.py` | 71b0dd622e1a5ddfc0c5c410358ff8f7786c1900b75dad1b11845e771c429735 |
| `tests/test_forward_xfund_dhl.py` | 5e9cf47eddc19807e520eed37d73d1966c15843687d0540c6d891e9da548651a |
| `lab/deribit.py` | 03e97a1dd00ee3d2fbbcf1c30152c92a7fc9fb1f27011e70b383eeb8f55bbea5 |
| `lab/carrylane.py` | 12efdca302dfdbc1312dc7499a53de23af9276406e1934c547b9e8642622e895 |
| `lab/xfund.py` | d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d |
| `lab/kraken.py` | 92ecfe0cfa2dae1f3ceef23f177fa84ad19f283d07036b2c1383566e022d0707 |
| `scripts/forward_xfund_eea.py` | 5ea7908b79bcfc39bfa863fab8d35fc9d61794e2f2f988e2b192ff9d46863f3a |
| `scripts/read_xfund_eea3_fwd.py` | e20f356fc55980e4ff2a0c7fb02f846b9ce6f7151b2951478dad169e4b38ae3d |
| `experiments/xfund_dhl_fwd/symbols.csv` | 8809f6ccc93191b9244623f209647637d72b802ec35cfdd680475e9409d2fe98 |
