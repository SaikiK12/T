# PREREG: mexc_seq (R221), a sequential decision for the MEXC flow books over a year of paper days

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R221
- **Owner (single writer):** the session that froze it; it writes only `experiments/mexc_seq/`
- **Code:** `scripts/forward_seq.py`. It reads the tickets of R215 (`experiments/mexc_fwd/journal`) and R218
  (`experiments/mexc_fwd_sq/journal`) and never writes them.
- **Source:** `docs/PAPER_REFINEMENT.md` (literature report, 2026-10-19). R215 and R218 decide at 90 on-time days with
  `lab.gate.go_real()` (mean > 0, hit rate >= 55%, no day below -40%). That gate is a screen, not a test. At 90
  daily observations, a one-sided 5% test has 80% power only against an annual Sharpe of about 5, and the flow books'
  archive Sharpe is 1.0-1.8 (R217). This lane adds a pre-registered statistical decision with later looks and
  family-wise error control, without touching R215 or R218.

## What the author had seen
- R215 and R218's replay tickets (2026-10-01..18): A +4.7%, X2 +6.2%, B -0.1% on MEXC.
- R217's archive Sharpe values.
- The power numbers below.
- No on-time ticket exists yet; the first on-time day is 2026-10-20.

## Books (the trials, a family of 3)
- **A**: R215's book A, the primary, net 1x.
- **X2**: R218's agreement-squared book.
- **B**: R215's book B, top_vs_crowd alone. On MEXC this is crypto only (TradFi is not mapped). R216 found the
  crypto-only B the best holdout t in the lab (+18.25 bp/day, t 2.74, Binance archive). R215 reports B but never
  promotes it; this lane decides on it.

Only `kind == ontime` tickets count, in day order. Look k uses exactly the first n_k on-time days, whenever the script
runs, so the result does not depend on when it is read.

## Statistic
z = Newey-West t (lag 10) of the daily 1x net over the look's days (`lab.stats.newey_west_t`). One-sided: only a
positive book can pass.

## Looks and boundaries
Family one-sided alpha is 2.5%, split by Bonferroni into 0.833% per book. Spending follows Lan-DeMets, O'Brien-Fleming
type, at information fractions 182/365 and 1. Boundaries were computed by `scipy` before freezing:

| Look | On-time days | Rule for each book |
|---|---|---|
| 1 | 90 | **Futility only:** STOP if z <= -2. A stopped book is recorded as FAILED and drops out of later looks. |
| 2 | 182 | **PASS** if z >= 3.558 **and** the total net at 2x cost > 0. |
| 3 | 365 | **PASS** if z >= 2.397 **and** the total net at 2x cost > 0. **FAIL** otherwise. |

Futility is non-binding, so it does not inflate alpha.

A PASS is a statistical pass only. Real money still goes only through `lab.gate.go_real()`, the owner and small
stakes (AGENTS rules 5 and 6).

## Power (simulated before freezing; i.i.d. daily returns, these boundaries)
Chance of a PASS by day 365, by the book's true annual Sharpe:

| True annual Sharpe | 1.0 | 1.5 | 2.0 | 3.0 |
|---|---|---|---|---|
| Chance of PASS by day 365 | 8% | 19% | 35% | 73% |

A FAIL at day 365 for a book with Sharpe under 2 is therefore weak evidence against it. It is recorded with this
power next to it.

## Reported, not decided on
- At every run: days so far, total net at 1x/2x/3x, current z, and the always-on monitoring t. None of these
  promotes a book.
- Pairwise differences X2 - A and B - A (mean and NW t).
- Each look's result is appended to `results/looks.csv` once its days are complete. The file is append-only.

## Multiplicity
Trials = 3. Program trials before: 9,471,736 (after R220).

## Expectations
- At these Sharpe levels the likeliest outcome at day 365 is no PASS.
- X2 or A could pass if their archive Sharpe (1.5-2.0) holds on MEXC and costs stay as modeled.
- A futility stop at day 90 is likely only if the books lose steadily.
