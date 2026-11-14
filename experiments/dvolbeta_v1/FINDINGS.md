# FINDINGS: dvolbeta_v1 (R385). Sorting the top-150 perps on their return beta to BTC or ETH DVOL changes earns nothing net in validation

**Verdict by the frozen rule: NULL (gate 0, on seen data).** The pick, ETH LH (long the lowest ETH-DVOL beta fifth, short the highest), fails two of three checks: validation net 1x t +0.15 (needs 2.0) and net 1x mean without its 10 best weeks -150.2 bp/week (needs > 0). It passes only the 2x-mean check, at +0.3 bp/day, a rounding-level positive.

- **Trials:** 4 books, all counted. Program total 9,479,252 + 4 = 9,479,256 (`registry.program_trials()`). The result does not lean on that count, since the pick fails on its own.
- **Read:** PREREG sha256 `be3f0602...` (full value in `PREREG.sha256`), frozen before the run, and 12 inputs matched their frozen hashes. One run on 2026-11-02 with `scripts/run_dvolbeta.py` (`run.log`). Validation was read once. Registry row R385 appended.
- **Tested:** on every 7th day from 2022-01-01, a coin's beta is the OLS slope of its daily return on the daily log change of DVOL (BTC or ETH) over the last 90 rows (at least 60 pairs). Top and bottom fifth of about 135 scored names (26-27 per leg), equal weights, hold 7 days, API costs 8.5/17/25.5 bp per side. Everything except the beta comes unchanged from R299's `scripts/run_mlrank.py`.
- **Out of scope, not tested:** the gamma-weighted option inventory half of M456. It needs chain-priced option data over years. `data/deribit_trades` holds trades, not marked chains, and `data/option_expiry` starts 2026-10-29. The M456 row also frames this as a filter on a strategy that already passes. None does, so this is the stand-alone sort only.

## Result

**The pick, ETH LH (bp/day; t is Newey-West at 1x)**

| Window | Weeks | Gross | Net 1x / 2x / 3x | t at 1x | Mean wo best 10 (bp/week) | Long / short leg (bp/week) | Rank IC (NW t) |
|---|---|---|---|---|---|---|---|
| Discovery 2022-23 | 104 | +6.3 | +5.4 / +4.5 / +3.6 | +0.76 | -57.4 | -0.9 / +45.2 | -0.012 (-0.82) |
| Validation 2024-01..2026-09 | 142 | +2.8 | +1.6 / +0.3 / -0.9 | +0.15 | -150.2 | +38.8 / -19.4 | -0.015 (-1.32) |

- **Checks:** t >= 2.0 at 1x fails (+0.15). A positive 2x mean passes (+0.3 bp/day, +2.4 bp/week). A positive 1x mean without the 10 best weeks fails (-150.2 bp/week). The 3x net is negative.
- **Discovery never reached significance:** the best of the four was t +0.76, so the pick was weak before validation.
- **Cost:** validation gross is +2.8 bp/day against about 1.2 bp/day of 1x cost (turnover about 1.0 per week).

**All four books (bp/day; t of net 1x)**

| Book | Disc gross | Disc net 1x (t) | Valid gross | Valid net 1x / 2x / 3x (t at 1x) | Valid mean wo best 10 (bp/week) | Corr with EW top-150 return |
|---|---|---|---|---|---|---|
| BTC LH | +4.2 | +3.3 (+0.45) | -0.9 | -2.1 / -3.2 / -4.4 (-0.19) | -193.8 | +0.15 |
| BTC HL | -4.2 | -5.1 (-0.70) | +0.9 | -0.3 / -1.4 / -2.6 (-0.02) | -124.3 | -0.15 |
| **ETH LH (pick)** | +6.3 | +5.4 (+0.76) | +2.8 | +1.6 / +0.3 / -0.9 (+0.15) | -150.2 | +0.22 |
| ETH HL | -6.3 | -7.2 (-1.01) | -2.8 | -4.0 / -5.2 / -6.4 (-0.40) | -141.8 | -0.22 |

- LH and HL of the same DVOL are mirrors in gross, so each pair differs only by cost. For BTC the gross changes sign between windows (LH +4.2 then -0.9). For ETH it stays positive but shrinks from +6.3 to +2.8.
- The beta score is a weak, unstable sort. Rank IC against the next-week ranked net return is -0.012 to -0.015 for the LH sign (t -0.82 to -1.34) and the mirror for HL. It is not significant in either window. The HL books lose net in both windows.
- Beta is mostly a market-beta sort. The median beta is -0.26 (BTC) to -0.28 (ETH), and 72-75% of scored rows are negative. LH's gross correlates +0.15 to +0.22 with the equal-weight top-150 return, so LH leans long high-market-beta names.
- No book is positive at 3x in validation.

## Reading

Trailing 90-day return beta to Deribit DVOL changes, used as a weekly fifths sort on the 150 most traded Binance perps, does not earn a net return at API costs in 2024-01..2026-09. The best book's discovery edge (t +0.76) is indistinguishable from noise. Its validation edge (t +0.15) vanishes once the 10 best weeks are dropped. Against 9,479,256 program trials, the one passing check (2x mean, +0.3 bp/day) carries no weight. This is a null of this reading only: one DVOL transform (log change), one window (90 days, minimum 60), one hold (7 days), fifths, signed beta, univariate. Per-coin DVOL does not exist, so this is each coin's exposure to the BTC or ETH index, not to its own implied vol.

## What this changes

- M456's sort half is tested and NULL on this panel. The gamma-weighted option inventory half stays UNTESTED until chain-priced data exists (`data/option_expiry` accumulates from 2026-10-29).
- No forward lane and no real money: gate 0, seen data, rule failed.

## Not checked

- The gamma-weighted option inventory half of M456, and DVOL as a state filter on a parent strategy (none passes).
- Other windows (30 or 60 days), absolute beta, multivariate beta with a market control, DVOL levels instead of log changes, other quantiles or holds. Not tried, by design.
- Later-delisted share of each leg (survival flag), and the GATES.md dependent-null, on-time clock, trimming and leave-two-coins-out items.
- Rows before 2022-01-01 (outside the windows). DVOL history before 2021-03-24 is not held.
- The unit tests used synthetic data only. The DVOL day-alignment (row D takes the bar opening 23:00 of day D-1) was tested on a synthetic series, not cross-checked against Deribit's published daily DVOL.
- The tables above were transcribed from the lane agent's report of `results/`. The main session re-read the pick, the three checks and the BTC LH discovery row against `results/summary.json` and `run.log`; the other cells were not individually re-checked.

## Process note

The lane agent downloaded a pyarrow wheel to a temporary folder before noticing `.venv` already had it, against the lane's "download nothing" line. It was a package, not data; it was deleted and never installed.

## Files

`PREREG.md`, `PREREG.sha256` (frozen), `run.log`, `results/periods.csv`, `results/rank_ic.csv`, `results/summary.json`, `scripts/run_dvolbeta.py`, `tests/test_run_dvolbeta.py`.
