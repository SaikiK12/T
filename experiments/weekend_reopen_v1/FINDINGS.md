# R432 weekend_reopen_v1: NULL (gate-0 screen). Fading Binance's TradFi perps through the CME Sunday reopen does not pay a taker at 15 minutes

**Disclosure (read first).** The primary cell's result was seen once before the freeze, so this lane is a gate-0
screen, not a blind test.
- **What happened:** at 22:55:56 UTC a dry-run path bug ran the synthetic check on the real archive. `build(data=DATA)`
  binds its default when the function is defined, so the override did not apply. It printed the primary line that
  this run reproduces exactly: n 90 on 28 weekends, gross +6.78 bp, NULL.
- **What was not affected:** the design, including the primary cell, was fixed about two minutes earlier and was not
  changed. No other cell was read. The scratch outputs were deleted unread.
- **Where it is recorded:** the PREREG (sha `c6472f1c…`) and the registry row disclose it. The freeze commit 5743f88
  says "before any outcome"; this disclosure supersedes that wording.

**Registry:** R432, 174 trials (program total 9,784,685).

**Run:** once, 2026-11-09 22:58 UTC, by the frozen runner `scripts/run_weekend_reopen.py` (12 inputs matched).
Outputs are in `results/`: `summary.json`, `cells.csv`, `slopes.csv` and `trades_primary.csv`. Log: `run.log`.

FINDINGS was written by the orchestrator from the lane agent's text. The harness does not let subagents write it.

## Verdict
**NULL.**
- **The primary cell:** fade the weekend move of all 7 perps (QQQ, SPY, XAU, XAG, CL, BZ, NATGAS) when it is at least
  50 bp, entered at Sunday 17:55 New York and exited 15 minutes after the 18:00 CME reopen.
- **Result:** 90 trades on 28 weekends earned +6.78 bp gross, against a 12 bp cost unit (a round trip).

| Cost | Mean net per trade | Weekend-bootstrap 95% interval |
|---|---|---|
| 1x (12 bp) | −5.22 bp | −38.09 to +25.70 bp |
| 2x | −17.22 bp | −50.00 to +13.10 bp |
| 3x | −29.22 bp | −63.12 to +1.20 bp |

- **By group (gross):**
  - equity +10.3 bp (10 trades, 9 of them QQQ);
  - metals −10.3 bp (28: XAU −5.9, XAG −14.1);
  - energy +15.3 bp (52: CL +25.1, BZ +36.4, NATGAS −32.3).
- **Noise:** the per-trade standard deviation is 117 bp, so the 80% minimum detectable mean is about 55 bp. This null
  rules out only a large edge at this horizon.
- **Placebo:** the same clock 24 h earlier, when nothing reopens, nets −12.3 bp (fade) and −11.8 bp (follow). The
  gross is about 0, as it should be.
- **Commodity regime split** (the 2026-05-08 order-book EWMA mark change; the date is unverified):
  - before: fade +12.7 bp net (25 trades, interval −73 to +75);
  - after: fade −14.0 bp (55 trades, −50 to +24).
  - Too wide to read.

## Exploratory, not a result: the giveback shows up in the slopes and at longer horizons, mostly in oil
- **The slopes.** Across all 199 asset-weekends, the post-reopen return regressed on the weekend move gives a slope
  of:
  - −0.12 at +15 min (interval −0.28 to +0.04);
  - −0.18 at +60 min (−0.31 to −0.03);
  - −0.26 to the Monday cash open (−0.53 to −0.05).

  A slope of −0.1 to −0.3 is what a 0.7-0.9 mapping of the weekend perp move into the reference market implies: the
  story the primary was chosen on (M442's unread source). Energy carries it, at −0.20 (x60) and −0.24 (cash), with
  intervals below 0. Metals' slopes sit around 0.
- **The best cells are energy fades with |W| ≥ 100 bp and longer holds.**
  - Enter before the reopen and exit at the Monday cash open: +102 bp net at 1x (32 trades, 16 weekends, interval
    +5 to +197).
  - The same with an exit at +60 min: +56 bp net (32 trades, interval +2 to +108).
- **Why it is not a result.** Those cells were picked from 144 after the run.
  - 8 of the 144 have a 1x lower bound above 0, and all of them are correlated variants of one oil fade.
  - The best one-sided p is about 0.02. Selection over this grid produces that much by chance, and against the
    program's 9.78M trials it is nothing.
  - Oil's 2026 weekends were unusually large: |W| had a median of about 170-190 bp on CL and BZ.
  - It rests on 16 weekends.

## Read against the program
- **Program total:** 9,784,685 trials (`registry.program_trials()`).
- **The primary:** a gate-0 NULL whose interval at 1x spans −38 to +26 bp. No correction could make it positive.
- **Prior lanes:**
  - R244 (BTC's weekend move into QQQ/SPY): NULL.
  - R368 and R370 (Binance's oil perps around EIA releases): NULL and INCONCLUSIVE.
  - The unread study in M442 reports negative out-of-sample Sharpe for weekend-perp strategies after costs. The primary
    agrees with it at the 15-minute horizon.

## What this means
- **The reopen re-anchoring is not a taker trade at 15 minutes.** Any giveback is small next to the reopen noise and
  next to a 12 bp round trip, and gold, silver and natural gas went the other way.
- **The only lead is oil.** A fade of CL/BZ weekend moves of 1% or more, held for an hour or to the Monday cash open,
  is a new hypothesis, not a finding. It needs:
  - a new lane id, frozen before new weekends (the archive from 2026-10-28 on, plus the commodity recorder of M447);
  - the funding of that hold charged;
  - a measured weekend spread.

  At about one weekend a week, 20 fresh energy weekends take about five months. MEXC's USOIL and UKOIL hourly history
  starts on 2026-01-30, so about 9 weekends before Binance's CL/BZ history (2026-04-01) are unread for this question.
  That is a futility-sized check, not a confirmation.
- **M321/M188's question (1)**, whether the weekend perp move predicts the reopen, is answered only in the slopes, as
  above. **Question (2)**, which venue catches up first, still needs the recorder's multi-venue data (M447).

## Limits
- **Costs:**
  - The cost unit is R368's assumption: a 5 bp taker fee a side plus 2 bp. The Binance TradFi fee page was not read;
    launch coverage says the fee structure is the crypto perps'.
  - Weekend and reopen spreads were not measured. The book recorder has no weekend before 2026-11-02.
  - The cash-exit cells hold across two 8-hour funding settlements that were not charged.
- **Sample:**
  - 46 Fridays, 7 dropped for NYSE holidays.
  - Energy and equity have only 25 weekends each; metals 35-39.
  - One year with an oil-volatility regime.
- **Reference:** the perp is its own reference. No CME open price is used, so the re-anchoring target is inferred, not
  observed.
- **Fills:** at 1-minute bar closes, with no queue or impact.
