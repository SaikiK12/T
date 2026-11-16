# reserved_batch1 (R286): Reserved batch 1

**Writer lost (2026-11-16).** Last commit 4cdbb6bd (2026-11-03). This lane never had a forward writer: its one frozen
read ran on 2026-11-03 (`FINDINGS.md`: C14 PASS, five FAIL, four UNREADABLE). Its registry row still says
RUNNING / PENDING and is left as written, because `registry/rounds.csv` is append-only; `FINDINGS.md` is the result.
"Read 1 of 4" is the reserved samples' read budget; later reads are new lanes (R391, R392). Nothing here should be
rerun (docs/HANDOVER.md).
