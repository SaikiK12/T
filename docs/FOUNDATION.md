# Foundation

Goal (owner, 2026-10-12): **positive PnL on crypto token perpetual futures**, mainly MEXC alts. An edge counts only after it survives pre-registration, a null distribution, held-out data and a forward paper test. Real money, in small stakes, comes only after paper proves a net gain, and the owner places those orders.

## Provenance

Built from reading the Claude Code session "Bot de prédiction trading": the compaction summary written 2026-10-12T20:34Z, the owner's later messages, and the final ~12 hours. **(S)** marks a fact stated there. **(I)** marks my inference or proposal.

Not read: everything before that summary (the session had already dropped ~2.8M tokens of earlier context, so the first day is gone), and all real code and data, which live on the owner's Windows machine. Check each **(S)** against the real files before relying on it.

## Lifecycle of a lane

A lane is one question tested end to end: an unlock short, a listing shock, a feature search.

1. **Register.** Write `PREREG.md` from `templates/lane/`, then `lab.prereg.freeze()`. No statistic runs before this. **(S)**
2. **Run.** The run script calls `lab.prereg.verify()` first. Discovery, validation and holdout splits; gates; a full-pipeline null. **(S)**
3. **Verdict.** `FINDINGS.md` leads with the verdict. One row is appended to `registry/rounds.csv`, including the trial count. **(S, registry I)**
4. **Forward.** A lane that survives writes a frozen forward spec and dated paper tickets, scored later. **(S)**
5. **Gate.** `lab.gate.go_real()` after 20 scored tickets. Passing it permits the owner to consider a small real stake. Nothing in this repo places orders. **(S)**

## Conventions carried from the session (S)

| Item | Value | Where |
|---|---|---|
| Universe | 900 Binance USD-M perps incl. delisted, daily bars 2021-01-01 to 2026-09-30 (`ts open high low close volume qv`) | per-lane manifest |
| Trading venue | MEXC (entries at hour open, MEXC funding, MAE tracked) | forward lanes |
| Splits | discovery < 2024-01-01; validation 2024-01-01..2025-06-30; holdout >= 2025-07-01 | `lab/config.py` |
| Horizons | 1, 3, 7, 14, 30 days | `lab/config.py` |
| Cost | 0.002 per trade | `lab/config.py` |
| Inference | per-day cell mean, Newey-West t with lag = horizon, calendar lags, gaps as zeros | `lab/stats.py` (reference; check parity with hypermine `nw()`) |
| Gates | discovery n>=120, net>0, t>=3.5; validation n>=60, t>=2; holdout n>=40, t>=2 | `lab/config.py` |
| Null | 60 replicas, common circular time shift of the forward panel (180 .. D-180); SIGNAL if real validation survivors exceed the null 95th percentile | `lab/nulls.py` |
| Candidate | holdout passed and family-wise p < 0.05; BETA-ONLY flag kept | `lab/config.py` |
| Go-real | >=20 scored, mean>0, hit>=55%, no event below -40% unlevered | `lab/gate.py` |
| Hardware | RTX 5060 Laptop 8 GB, 16 CPUs; GPU venv separate from the base Python | lane docs |

## Layout

```
README.md  AGENTS.md
docs/        FOUNDATION.md (this)  AUDIT.md
lab/         shared kit: config, stats, nulls, prereg, gate, registry
registry/    rounds.csv  one row per round, append-only, ids allocated under a lock
templates/   lane/PREREG.md  lane/FINDINGS.md
tests/       unittest, stdlib only
experiments/ one folder per lane (not in this repo yet)
  <lane>/PREREG.md PREREG.sha256 run_<lane>.py FINDINGS.md results/ ledger.csv   committed
  <lane>/cache/ data/                                                             ignored, rebuilt
```

## Open items seen at the end of the session (S)

- First forward unlock score: ZRO, 2026-10-20. Tickets dated 10-13 (ZRO), 10-16 (APR/H), 10-18 (XPL), 364 in total.
- R146 Tardis data pull: owned by another session; do not run it from here.
- mmprobe verdict after 2026-10-19.
- hypermine: batched all-replica GPU engine, with CPU parity before use.
- Claims queue from creator videos, each to become a pre-registered test.
- Rounds R143 and R144 have no date in the registry; fill them from the real ROADMAP.
