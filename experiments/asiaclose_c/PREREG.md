# PREREG: asiaclose_c (R469). Does R468's Asian closure fade hold on openings no lane has seen?

- **Registry id:** R469
- **Owner (single writer):** Claude, this session (cloud container, 2026-11-11); the read itself is run by
  `.github/workflows/claude-asiaclose-c.yml`
- **Date registered (UTC):** 2026-11-11

Method M526. Parent: R468 (`experiments/asiaclose_v1`, frozen PASS recorded PARTIAL). This file is frozen by
`lab.prereg.freeze()` before any of sample C's openings has happened. After the freeze it is never edited; a changed
idea is a new lane.

## Question
R468 faded the perp's move over the home exchange's weekday-night closure on 18 Asian single-stock perps (xyz and
Lighter). A (openings 2026-04-27..08-31) gave +87.8 bp (p 0.034). B (09-01..11-10) gave +9.5 bp (p 0.71, median about
zero). The frozen rule called it PASS because B's bar was loose. Is the A effect still there on openings that
nobody has seen?

## Why this lane and not a full forward lane
- R468's stop rule earns a forward lane. B already showed no effect, so the cheaper honest step comes first: one
  frozen read of a fresh sample with R468's own rule.
- A PASS here earns a forward lane with tickets at E and recorded book costs (both venues' books are recorded hourly
  on `claude/xyz-books-data`). A NULL closes M526.

## What the author has seen
- R468's events and results through 2026-11-10 (`experiments/asiaclose_v1/results/`).
- **Nothing in sample C:** its first opening is 2026-11-12. This file is frozen and pushed on 2026-11-11 UTC.
- The runner was run only on synthetic worlds (`tests/test_asiaclose_c.py`).

## Sample, rule and data
- **Sample C:** openings D in 2026-11-12 .. 2027-01-29.
- **Rule and universe:** R468's, unchanged.
  - `scripts/asiaclose_rule.py`, `experiments/asiaclose_v1/universe.csv` and `run_asiaclose.build`.
  - Instants R, E, X1 and X2; traded candles only; P(T) at most 3 h old.
  - Kioxia's split days and the 7-day listing rule.
- **2027 holidays.** R468's holiday table ends in 2026. The runner adds the 2027 full-day closures inside C:
  - New Year's Day on all four exchanges;
  - Coming of Age Day (2027-01-11) on the TSE.
  - Checked: HKEX's 2026 list (circular SEHK CT/075/25) closes only 25 December, with the 24th a half day;
    Monday 28 December trades, so R468's 2026 table already covers C's late-December closures.
- **Bars:** R468's frozen fetcher (`scripts/fetch_asiaclose.py bars`) over 2026-10-15 .. 2027-02-01 00:00 UTC into
  `data/asiaclose_c`, with a per-file sha256 manifest. It runs inside the read.
- **When:** the read runs once, on or after 2027-02-01 00:00 UTC (crons on 1-4 February).
  - The runner refuses to run earlier.
  - It does nothing once `results/summary.json` exists.

## Cells and decision
- **Decision cell:** R468's (both venues, weekday nights, |W| ≥ 50 bp, exit X1).
  - The side is fixed by R468: fade.
  - The p is one-sided: R468's day-clustered sign-flip p (200,000 draws, seed 469) halved when the mean is positive.
- **Reported cells** (counted as trials, not used for the verdict): xyz alone, Lighter alone, and each exchange
  (KRX, TSE, HKEX, SSE).
- **INCONCLUSIVE:** fewer than 150 events or fewer than 30 days.
- **PASS:** p ≤ 0.05 and mean > 2 cost units.
- **NULL:** otherwise.
- **Costs (1x, 2x, 3x):** R468's units (xyz 5.8 bp, Lighter 4 bp, assumed slippage). Nets subtract 1, 2 and 3
  units. Funding is inside g.

## Trials
- 1 decision + 2 venue + 4 exchange cells = **7**; registry trials 7.
- Program trials: 9,785,237 before this lane, 9,785,244 after.

## Power (stated before the read)
- **R468's A as the yardstick:** p 0.034 over 65 days implies a day-level sd of the event-mean near 340 bp.
- **Size of C:** about 55 opening days and roughly 500-600 events at θ 50.
- **MDE80** (one-sided 5%) is about 2.49 × 340 / sqrt(55) ≈ **115 bp**.
  - If A's +88 bp persisted, C would PASS about 60% of the time.
  - If B's +9.5 bp is the truth, about 8%.
- **A NULL here does not exclude a smaller effect.** It closes the lane because a smaller effect would not clear
  real costs with any confidence at this size.

## Code
```inputs
1683617f6583d8660cbde73bb3e452b581bd7b26fe6748a0d1626de8a9bbd81f  scripts/run_asiaclose_c.py
5297dd38db7a527d752fe6d030c80299222d78e3c9db2bcf0a585bc3888935c4  tests/test_asiaclose_c.py
d3b45b3c2d0f4e99332fdd81034a636c4a5b6f23d3ba921c017d57f007547ab8  .github/workflows/claude-asiaclose-c.yml
f45911db2ea7cedbdf9b751de5177cdaa8f4f6395e2eca43fc253c6049727672  scripts/asiaclose_rule.py
b09e903c2cfb19603dd1fc80cf29dd8a58e27b8f53881497c6f831417bbfb96c  scripts/fetch_asiaclose.py
9579b3225edb8fdfceb7c765dc6cdaf64cd892d0c192c2e0bf9514dc0cfe35fd  scripts/run_asiaclose.py
82bf82a7639f5dbcc2b1a4242dacf5f30d9e0e26e9c278488d8160d6b4a3afc3  experiments/asiaclose_v1/universe.csv
6a9c4286ac1a12a391c0ebaca022510fb40d59affff9eb56ce71d44246a64ca1  scripts/earnperp_rule.py
14c57f1aed3a392a3cdae5a906512cb68cf60e9d3ca0458f6192cf608519e3ee  scripts/run_xyzwknd.py
b5e0700e75432eb3b651e6ab22295f2519ad8b16601fa824fa0f03f05ab1539a  scripts/xyzwknd_rule.py
12efdca302dfdbc1312dc7499a53de23af9276406e1934c547b9e8642622e895  lab/carrylane.py
831fe1dfa2c794bc0467137bb10f9395895ecddecfffcbc860b2c6273faae18d  lab/sessions.py
```

## Evidence lineage and admission
- **Method:** M526. **Parent:** R468.
- **Gates:** `docs/GATES.md` sha256 `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`.
  - Met: pre-named cell; side fixed by the parent; trials counted; costs at 1x/2x/3x; power stated; a sample that
    did not exist at the freeze.
  - Not met: gate 1 (point-in-time tickets at measured costs) and gate 3 (account risk). A PASS earns that lane.

## Stop rules
- One read, by the workflow. Nothing is retuned afterwards. A changed idea is a new lane.
- No orders, no money, no credentials. The read writes only `experiments/asiaclose_c/results/`.
