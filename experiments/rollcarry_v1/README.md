# rollcarry_v1 (R478)

M532 gate 0. trade.xyz prices NATGAS, CL (WTI) and BRENTOIL from futures, and its oracle moves from the front to the
next contract over business days 5-9 of each month. In contango that hands longs the calendar spread, which they pay
for in funding. This lane shorts each perp and holds the US fund that owns the same front futures (UNG, USO, BNO):
the pair earns funding minus the roll-up. NATGAS-UNG decides on sample A (weeks ending by 2026-07-22); CL-USO,
BRENTOIL-BNO and sample B are reported.

- `PREREG.md`: frozen question, book, samples, power and what the author had seen.
- `results/`: written once after the fetch.
- Code: `scripts/run_rollcarry.py`, `scripts/fetch_rollcarry.py`, `tests/test_rollcarry.py`.

Paper only. No order, no money, no key. The US funds measure front-futures excess return; they are not a hedge a
French account can buy.
