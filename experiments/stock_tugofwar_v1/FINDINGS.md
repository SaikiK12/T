# R435 stock_tugofwar_v1: NULL

Across MEXC's 24/7 US-stock perps, past overnight winners do earn more overnight than past losers, but not enough to pay for trading them. The primary book, before costs, makes +18.6 bp a day with a confidence interval that includes zero. After the listed fee and recorded spread at 1x it makes −3.5 bp a day, and at 2x −25.8 bp. The overnight-versus-intraday tug of war of Lou, Polk and Skouras (2019) shows up weakly, and only with the earlier 09:00 New York open proxy. No result survives correction for this lane's 20 trials.

- Registry R435, method M492. 20 trials: 8 signal cells and 12 books.
- Program trials at run time: 9,784,969. The coordinator's GO figure was 9,784,957; this run's 20 trials are counted in both.
- Run once on 2026-11-10, 03:10:47 to 03:11:00 UTC, exit 0, by the frozen runner `scripts/run_stock_tugofwar.py` (sha 4efee793…).
- PREREG sha af1d59fa… was committed in 7fcc51d before the run. The run printed "PREREG verified af1d59fae23e; 5 inputs match; 1316 data files match the manifest; trials 20".
- Outputs: `results/cells.csv`, `results/summary.json`, `results/sessions_L{20,60}_o{+30,-30}.csv`, `run.log`.

FINDINGS was written by the orchestrator from the lane agent's text. The harness does not let subagents write it.

## Setup (as registered)

- **Universe:** US-stock perps, classed point in time from each contract's first 30 days of index prices. 320 names qualified.
  - Each day keeps the top 30 by trailing 20-day quote volume, counted strictly before that day.
  - A contract must be at least 30 days old to enter.
- **Sessions:** 328 NYSE sessions; holidays and the three early-close days are dropped.
  - Close is 16:00 New York.
  - The open is proxied at 10:00 (o+30) or 09:00 (o−30), because the data are hourly bars.
- **Returns:** overnight (ON) runs from the prior close to the open; intraday (ID) runs from the open to the close.
- **Signal:** the trailing mean of ON returns over 20 sessions (at least 15 valid) or 60 sessions (at least 45 valid).
- **Books:** quintiles, at least 3 names a leg.
  - B1, overnight momentum: long the top ON quintile, short the bottom, held close to open.
  - B2, intraday reversal: held open to close.
  - B3: both B1 and B2.
- **Costs and funding:** cost = 2 × multiplier × (listed taker fee + recorded median half-spread). Funding is charged on each leg over its holding window.
- **Inference:** 5-session block bootstrap with 10,000 draws (seed 435). Newey-West t at lag 5 for the signal ICs.
- **Primary cell:** B1, L = 20, o+30.
- **PASS rule:** n ≥ 120, 1x mean > 0 with its lower bound > 0, 2x mean > 0, and both halves positive.

## Verdict: primary B1, L = 20, o+30 (bp a day, 249 sessions, 2025-10-17 to 2026-10-20)

| Cost | Mean | 95% block-bootstrap CI |
|---|---:|---|
| gross | +18.55 | −6.34 to +43.85 |
| **1x** | **−3.48** | −27.73 to +21.12 (p ≤ 0: 0.61) |
| 2x | −25.78 | −50.10 to −1.02 |
| 3x | −48.07 | — |
| API taker 8 bp | −27.48 | — |

- **Halves at 1x:** +3.05 and −9.95 bp.
- **Rules failed:** the 1x mean, the 1x lower bound, the 2x mean and one half. Gate 0.
- **Cost wedge at 1x:** about 22 bp a day. Fee plus spread is about 22.3 bp; funding is about −0.3 bp.
- **Book size:** median 6 names a leg. The legs' median trailing quote volume is $643k a day; the universe median is 30 names.
- **Power:** the daily SD is about 253 bp, against the 120 bp the PREREG assumed. The smallest effect this sample could detect is about 45 bp a day, not the planned 21. The test is underpowered relative to its plan, but even the gross mean does not cover the cost wedge at 2x.

## Signal ICs (Spearman, mean IC, NW t at lag 5)

| Cell | ON → next ON (persistence) | ON → next ID (reversal) | n |
|---|---:|---:|---:|
| L20 o+30 | +0.0104 (t 0.70) | −0.0130 (t −0.79) | 249 |
| L20 o−30 | +0.0429 (t 2.23) | −0.0259 (t −2.00) | 249 |
| L60 o+30 | +0.0078 (t 0.41) | +0.0050 (t 0.26) | 226 |
| L60 o−30 | +0.0395 (t 1.84) | −0.0337 (t −2.09) | 226 |

- The paper's signs (persistence > 0, reversal < 0) appear only with the 09:00 proxy, at |t| about 2.
- That is far from the lane's Bonferroni threshold of 0.05/20 = 0.0025 (|t| about 3.0).
- With the 10:00 proxy the signs are not distinguishable from zero.

## All books (bp a day)

| Cell | Book | Gross | Net 1x | Net 2x | Net 3x | API |
|---|---|---:|---:|---:|---:|---:|
| L20 o+30 | B1 (primary) | +18.55 | −3.48 | −25.78 | −48.07 | −27.48 |
| L20 o+30 | B2 | −0.56 | −23.07 | −45.37 | −67.67 | −47.07 |
| L20 o+30 | B3 | +17.99 | −26.55 | −71.14 | −115.74 | −74.55 |
| L20 o−30 | B1 | +14.73 | −8.59 | −31.22 | −53.84 | −32.59 |
| L20 o−30 | B2 | +10.42 | −12.08 | −34.70 | −57.33 | −36.08 |
| L20 o−30 | B3 | +25.15 | −20.67 | −65.92 | −111.17 | −68.67 |
| L60 o+30 | B1 | −1.79 | −23.14 | −43.26 | −63.38 | −47.14 |
| L60 o+30 | B2 | −2.00 | −22.17 | −42.29 | −62.41 | −46.17 |
| L60 o+30 | B3 | −3.79 | −45.31 | −85.55 | −125.80 | −93.31 |
| L60 o−30 | B1 | +16.02 | −7.40 | −28.57 | −49.74 | −31.40 |
| L60 o−30 | B2 | +32.22 | +11.32 | −9.85 | −31.02 | −12.68 |
| L60 o−30 | B3 | +48.24 | +3.92 | −38.42 | −80.76 | −44.08 |

- **Two cells are positive at 1x**, both L60 o−30:
  - B2 nets +11.3 at 1x (CI −21.7 to +44.0) and −9.8 at 2x. Gross CI 0.2 to 64.4.
  - B3 nets +3.9 at 1x (CI −36.3 to +44.9) and −38.4 at 2x. Gross CI 8.2 to 87.7.
- Their 1x intervals straddle zero, both turn negative at 2x and at the API fee, and neither is the primary. They do not change the verdict.

## Read against the program

- The primary's p ≤ 0 of 0.61 is not evidence of an edge at any threshold.
- The best signal t (2.23) is one cell of 20 in this lane, out of 9,784,969 program trials.
- A gross-only CI excluding zero in 2 of 12 books is about what 20 correlated trials produce by chance.

## Limits

- **Survivor universe:** the instruments are current listings; 8 delistings were seen and are not reconstructed. This most likely flatters the gross figures.
- **Spreads:** measured from 2026-10-20 to 2026-11-06, after the sample, as a median half-spread per symbol. There is no depth, queue or impact model, and fills are at the hourly-bar close.
- **Open proxy:** hourly bars force the 10:00 / 09:00 New York proxy. The true open is not observed; the 09:00 cell is pre-open on these perps.
- **Sample:** data end 2026-10-22. One year, 249 sessions, with SD about twice the planned value.
- **Not tested:** maker execution, weekly rebalancing, and size-weighted or depth-weighted legs. Any of them needs a new lane id frozen before reading this sample.

## What it means

The overnight/intraday cross-section on MEXC US-stock perps is real enough to show the textbook signs at the pre-open proxy. It is too small and too noisy to pay about 22 bp a day of taker costs on a 6-name-a-leg book. Retuning this sample is closed. A successor needs a new id and a structurally cheaper route, such as maker fills or a weekly signal with much lower turnover, frozen before reading.

## Note added 2026-11-10: `docs/GATES.md` was restored
This lane's inputs block hashes `docs/GATES.md` at `ed486814…`. That version came from a paragraph added in 5d13ba1,
which broke rule 2: GATES.md is a frozen input of seven earlier lanes, at `e7dd02fa…`. GATES.md has since been
restored to `e7dd02fa…`, and the paragraph now lives in `docs/loop/STATE.md`. To re-verify this lane's inputs, check
out GATES.md from 5d13ba1. The file holds rules text only; no result here depends on it.
