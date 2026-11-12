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
- 2026-11-12, after the freeze (read only; nothing in the book changes): xyz's Roll Schedules page
  (https://docs.trade.xyz/llms-full.txt, "Roll Schedules") lists each window as "<business day 5> 5:30PM ET to
  <business day 9> 5:30PM ET". Its WTIOIL example: 80/20 on 2026-10-07 (business day 5), 60/40, 40/60, 20/80, and
  0/100 on 10-13 (business day 9). This matches the runner's weights (0.2 after the mark of business day 5 ... 1.0
  after business day 9). The designated contracts also match (NATGAS and WTIOIL the next calendar month, BRENTOIL the
  one after; e.g. NATGAS Z26 to F27 in November 2026).
  - Typos in xyz's own table: the August 2027 window reads "2027-08-06 to 2027-08-11" (business days 5-8), and June
    2027 ends "2027-06-011". If xyz really rolls in four steps in August 2027, the paper hedge is off by one day's
    calendar-spread change in that cycle. That is forward risk, not repaired.
  - The same page lists COPPER (bimonthly: Z6 to H7 in November 2026) and DIESEL (ULSD, xyz:HO) as futures-referenced.
    Neither is in this lane.
