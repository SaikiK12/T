# ltroll_v1 (R481)

M532 on a second venue. Lighter prices WTI, NATGAS, BRENTOIL and XCU (copper) from futures and, until RedStone took
over WTI, NATGAS and XCU on 2026-10-22, rolled them on the same days and contracts as trade.xyz. This gate 0 asks
whether Lighter's funding paid shorts more than the roll-up the oracle passed to longs, from listing to the October
2026 roll. It uses R478's post hoc identity (perp against Yahoo's continuous front, business day 4 to 10). NATGAS
decides; the others are reported.

- `PREREG.md`: frozen question, measure, window, power and what the author had seen.
- `results/`: written once after the fetch (`cycles.csv`, `summary.json`).
- Code: `scripts/run_ltroll.py`, `scripts/fetch_ltroll.py`, `tests/test_ltroll.py`. Data in `data/ltroll/`
  (gitignored; provenance in `docs/provenance/ltroll.json`).

Paper only. No order, no money, no key.
