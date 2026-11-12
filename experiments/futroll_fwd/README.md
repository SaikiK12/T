# futroll_fwd (R480)

Forward paper lane for M532, earned by R478. Short trade.xyz's NATGAS perp and hold the NYMEX contracts its oracle
references, rolled on xyz's own schedule (business days 5-9, 20% steps). The pair keeps the funding perp longs pay
minus the roll-up the oracle passes them, minus costs. NATGAS decides; CL and BRENTOIL are reported.

- `PREREG.md`: frozen book, reads, power and what the author had seen.
- `results/futility/` (after 2027-05-15) and `results/final/` (after 2027-11-13): written once each by
  `.github/workflows/claude-futroll.yml`.
- Recordings: `claude/futroll-data`, written twice a day by `.github/workflows/claude-futroll-recorder.yml`
  (`scripts/record_futroll.py`). Yahoo drops expired contracts and the venue keeps ~208 days of 1-hour candles, so
  the reads depend on it.
- Code: `scripts/run_futroll.py` (R478's frozen `simulate` with a rolled-futures index), `scripts/record_futroll.py`,
  `tests/test_futroll.py`.

Paper only. No order, no money, no key.

## Faults and notes
- (none yet)
