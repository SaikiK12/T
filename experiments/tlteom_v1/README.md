# tlteom_v1 (R473): the end-of-month Treasury rally on TLT

Gate 0 for M528. Hartley and Schwarz (2019) find that Treasury notes and bonds rise in the last days of each month
(1990-2018). They link it to insurers and index funds that buy at month end.

- **Trade:** long TLT over the last three trading days of each month. Priced for trade.xyz's TLT perp: 5.8 bp a
  round trip, plus 5.5%/yr funding.
- **R** (month-ends 2002-08 .. 2018-12) checks that TLT carries the effect inside the paper's sample.
- **U** (2019-01 .. 2026-10) decides.
- A PASS earns only a forward paper lane on xyz:TLT.

Files:
- `PREREG.md`, frozen (`PREREG.sha256`).
- `scripts/fetch_tlteom.py` (data), `scripts/run_tlteom.py` (the frozen run), `tests/test_tlteom.py`.
- `results/` after the run, and `FINDINGS.md` after the read.
