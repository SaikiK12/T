# Gate-1 reserved-sample plan for cross-venue carry: the samples are largely spent (intake, 2026-11-14)

The binding constraint is a *genuinely new* gate-1 result. A read-only subagent (S2) mapped the reserved samples and
the carry family's prior reads to find where a fresh gate-1 read could still live. Its honest answer: **the
cross-venue carry family has already been read at gate 1 on three reserved samples, and the remaining fresh cells are
too small to power a new discovery.** This page records that map and the one remaining, correctly-labelled
confirmation/futility design, registered as method **M540**. No backtest was run; `data/` is empty in this checkout,
so every data-side statement is a build plan, not a verified fact.

## Why gate-1 evidence is scarce (not neglect)
Cross-venue funding carry (M059 family) gate-1 reads already taken:
- **R286 / reserved_batch1** — 2020 Binance+Gate.
- **R391 / reserved_batch2** — KuCoin/dYdX/Lighter reserved long tail + MEXC (dYdX took 0 trades).
- **R392 / reserved_batch3** — Gate reserved long tail + MEXC.
The open-coin reads (R275 `xfund_v1`, R277 `xfund_kd_v1`, R288 `xfund_lt_v1`) cover all venues' `open/` lists.
So a fresh carry read must use a reserved cell **no carry lane has decided on**, and that cell is small.

## M540 — `reserved_batch4`: gate+dydx long tail (R490, NOT YET REGISTERED)
- **Sample:** dYdX `reserved/` long tail paired with the Gate `reserved/` long tail. 31 bases; **25 fresh**, 6 named
  overlaps (`AURORA CORE CRO MNT PI XDC`). Largest fresh-with-partner set; alternatives are smaller
  (gate+kucoin 25/13 fresh; gate+lighter 20/13). Tokens: `RESERVED-VENUE-READ` + `RESERVED-GATE-READ`.
- **Rule:** R275's carry book, every parameter unchanged (trailing-14-day annualized funding spread; enter widest
  gaps >= 5%/yr into 20 slots; exit below 2.5%/yr; long low-funding venue, short high; identity guard 30-day
  correlation >= 0.9). One book only, no search. Window `2021-01-01..2026-09-30` (dYdX funding starts 2023-10).
- **Gates:** NW t (lag 10) one-sided p <= alpha, 2x mean > 0, 10% trimmed 1x mean > 0, leave-two-coins-out 1x mean >
  0; N_min 60 book days. Null: block bootstrap (block 10, 2,000 replicas, seed 490). Costs 7/14/21 bp per leg per
  side at 1x/2x/3x (R275's cost). Registry family count 584 -> 585.
- **Power (honest):** at R483's implied excess Sharpe (~2.75) 80% power needs ~300 days — reachable. But at the
  long-tail shrinkage actually observed (R391 +2.48%/yr, R392 +0.73%/yr, top-10-day share 95%; diluted Sharpe ~1.0)
  80% power needs ~2,250 days, which the window cannot reach. So this is a **confirmation/futility screen**, not a
  discovery. A NULL does not overturn R275/R277/R391/R392.
- **Limits:** already-read family; venue-own-universe survivorship; settled (not paid) funding; spends dYdX 2/4 and
  Gate 3/4 of the reserved read budget; dYdX 2025-10 crash wicks likely drop pairs. A PASS authorizes only a gate-1
  confirmation and a *candidate* forward lane — no money, no order, no key, not gate 2.
- **Runner when frozen:** `scripts/fetch_venue_history.py dydx` + `scripts/fetch_gate_history.py`, an extended
  `reserved_venue_table.py`, then `scripts/qx_run_verified.py experiments/reserved_batch4` and
  `scripts/decide_reserved_batch2.py`. Freeze the PREREG and append the R490 row *before* the run.

## Read / unread
READ (repo, read-only): GATES/LEADS/SOURCES/DIRECTION/DATA_SOURCES docs; `templates/lane/PREREG.md`;
`registry/{data_manifest,rounds,candidates,methods}.csv`; xfund_v1/kd_v1/lt_v1 and reserved_batch1-3 PREREG/FINDINGS/
symbols; `lab/{prereg,registry,panel}.py`; `engine/src/reserved.rs`; the venue fetch scripts; provenance JSONs.
UNREAD (deliberately): every reserved price/funding/timestamp row; all of `data/` (empty here); forward journals
beyond FINDINGS.
