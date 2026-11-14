# FINDINGS: reserved_batch3 (R392)

**Verdict: GLT PASS, but tiny; C17 and M319 FAIL.**
- **GLT** (R275's carry on Gate's long tail) passes its frozen gate-1 rule. It earns only +0.73% a year, below cash.
- **C17** (R300's intraday relative-strength pick) is strongly positive on 2020: t 3.04. It still fails α 0.001, by a
  hair (p 0.0012), and two thirds of its gross comes from its 10 best days.
- **M319** is positive and weak.

FINDINGS was written by the orchestrator from the run's own outputs. The lane agent hit the rate limit after the run
and before writing it up.

## Read
- **Run once** on 2026-11-10 at 03:15 UTC, with `scripts/run_reserved_batch3.py --run` (exit 0).
  - Both frozen files and all 47 inputs matched before the read.
  - GLT ran through `scripts/qx_run_verified.py`, which checked `data/gate_hist` and `data/mexc_hist` against their
    provenance records before and after. Run receipt:
    `results/run_receipts/20261110T031526.746901Z-beb6a9b3.json`.
- **Order:** PREREG `aea63caf…` and RESERVED `f4c70994…` were frozen and pushed in 94030af before GO.
  - The REGISTERED row went into 9036ada a few minutes earlier.
  - The owner decided on 2026-11-09 to read batch 3 now rather than on or after 11-17. The PREREG records it.
- **Reads spent:**
  - reserved 2020: 2 of 4;
  - Gate long tail: 2 of 4.
  - No KuCoin, dYdX, Lighter or MEXC-only reserved row was read.
  - `docs/GATES.md` is a frozen input of earlier lanes, so its batch table is not edited. As in R391, this file and the
    registry row record the read.
- **Outputs:** `results/batch3.json`, `decisions.csv`, `daily.csv`, `trades.csv`, `strategies.csv`, `report.json`,
  `SUMMARY.md`, and the run receipt. Log: `run.log`.

## Decisions (weighted Bonferroni, total α 0.05)
| Candidate | Sample | Days | t (NW) | p one-sided | α | 2x > 0 | Trimmed > 0 | L2CO > 0 | Decision |
|---|---|---|---|---|---|---|---|---|---|
| C17 | reserved 2020 | 128 | 3.04 | 0.0012 | 0.001 | yes | yes | yes | **FAIL** (p) |
| M319 | reserved 2020 | 183 | 1.80 | 0.036 | 0.001 | yes | yes | yes | **FAIL** (p) |
| GLT | Gate long tail + MEXC | 507 | 2.26 | 0.012 | 0.048 | yes | yes | yes | **PASS** |

## C17: R300's pick "us10 n3 follow" on 2020 (bp a day)
At 10:00 New York, the book is long the 3 top-50 perps that rose most since 00:00 UTC and short the 3 that fell most,
held to 24:00 UTC.

| | Gross | 1x | 2x | 3x |
|---|---|---|---|---|
| Mean | +120.2 | **+86.2** | +52.2 | +18.2 |
| Without the 10 best days | +40.0 | +6.0 | −28.0 | −62.0 |

- **Sample:** 128 NYSE days, 2020-07-01 to 12-31. Before July, 2020 had fewer than 30 eligible names, so the grid
  starts in July. The PREREG expected about 200 days.
- **By month at 1x, all positive:** Jul +15, Aug +95, Sep +107, Oct +102, Nov +67, Dec +130.
  - Halves: +72 and +101.
- **Both legs earn:** long +83, short +38, basket −10 bp.
- **Robustness:** the 10% trimmed mean is +67.6. Leaving out CRV and OMG gives +44.4.
- **Concentration:**
  - The 10 best days make 69% of the gross and 94% of the 1x net. Without them, 1x is +6 bp and 2x is negative.
  - This is the same pattern R300 found on 2021-26: net 1x +38.7 bp, t 1.28, negative without its 10 best days.
- **What it says:** intraday relative-strength continuation was strong in the second half of 2020, a trending alt
  market. It was far weaker in 2021-26, where 2x was +4.7 bp a day.
  - The 2020 read raises the prior that the sign is real.
  - It does not show that the edge survives costs today. The concentration makes even 2020's net fragile.

## M319: the 08:00-clock variant on 2020 (bp a day)
16:00 UTC decision, held to 08:00 UTC.

| | Gross | 1x | 2x | 3x |
|---|---|---|---|---|
| Mean | +90.5 | +56.5 | +22.5 | −11.5 |
| Without the 10 best days | +18.8 | −15.2 | −49.2 | −83.2 |

- **Sample:** 183 days, from 2020-07-01.
- **By month at 1x:** August −21 and December +9.
- **Legs:** the long leg carries the book (+93); the short leg earns −2.
- **Verdict:** FAIL. The sign is positive, but it is weaker and less robust than C17's.

## GLT: R275's carry "gate+mexc L14d th5% K20" on the Gate long tail
The universe is 31 bases with a MEXC partner; 23 were ever eligible. The window runs from 2025-05-12 for 507 days.

| | 1x | 2x | 3x |
|---|---|---|---|
| Net, %/yr on book capital | **+0.73** | +0.11 | −0.51 |

- **Statistics:**
  - NW t 2.26; reality-check p 0.015.
  - Halves +0.05 and +0.35 bp a day; trimmed mean +0.26 bp; leave-two-coins-out +0.08 bp.
- **Book:**
  - 5.0 of 20 slots held on average, 123 trades.
  - Funding is 107% of the net.
  - The top 10 days make 57% of the sum. Max drawdown −0.34%.
- **Read with R391,** the same book on the KuCoin, dYdX and Lighter long tail (+2.48%/yr, PASS): long-tail carry is
  real and repeatable. At $10k it pays less than a T-bill, because few pairs clear the threshold and the slots stay
  mostly empty.

## Read against the program
- **Program total:** 9,784,972 trials, including this round's 3.
- **GLT:** its p of 0.012 passes the lane's own weighted Bonferroni. It is a confirmation of a carry family already
  passed twice (R275 gate 0, R391 gate 1), not a new discovery. Its size is below cash.
- **C17:** p 0.0012 on a blind sample is the strongest out-of-sample sign the intraday relative-strength family has
  shown. It is still one read on six months of a single regime, and it fails its pre-set α.
- **No candidate gives a tradable result:**
  - GLT is too small.
  - C17 at today's costs remains unproven.
  - R371 `usopen_fwd` keeps running on its own frozen rules and is the decider. It is not pooled with this read.

## Limits
- **2020 sample:** six months only, July to December, because fewer than 30 names were eligible before July. It is a
  single bull regime.
- **2020 costs:** the frozen cost units (34, 68 and 102 bp a day) are today's. 2020 spreads on these names were likely
  wider.
- **Gate long tail:** only 31 of 744 bases have a MEXC partner, and MEXC's history starts in 2025.
  - The universe is survivor-only.
  - Fills are modelled, not measured.
- **Read budget:** two of four reads remain for both the 2020 and Gate samples. The two-week spacing was shortened
  once, at the owner's request.
