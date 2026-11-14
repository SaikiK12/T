# adlstress_v1 (R487)

M534, gate 0. A worst-case auto-deleveraging (ADL) stress bound on 2025-10-10 for the nine audited cross-venue carry
books (six forward: R278 A/B/C, R390 A, R279 A/B). For every pair open over that UTC day, the profitable leg on an
ADL venue is assumed closed and the other leg naked from the day's best to its worst print, then re-hedged at one
extra round trip (7/14/21 bp per side). The bound, in % of book capital, is compared with one month of each book's
v2 net at 2x.

- `PREREG.md`: frozen question, scenarios (S1 documented ADL venues decides; S1B, S2 reported), fills, gates, inputs.
- `raw/`: venue candles fetched once after the freeze by `scripts/fetch_adlstress.py`, with `manifest.json` (sha256).
- `results/`: written by `scripts/run_adlstress.py` (`pairs.csv`, `books.csv`, `report.json`).
- `FINDINGS.md`: the bounds at 1x/2x/3x against `registry.program_trials()`.
- Venue evidence: `research/intake/adl_venues_20261113.md`. Tests: `tests/test_run_adlstress.py`.

A bound, not an estimate: per-account ADL incidence is not public keyless. Paper only. No order, no money, no key.
