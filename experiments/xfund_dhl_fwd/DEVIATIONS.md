# DEVIATIONS: xfund_dhl_fwd (R520)

## 2026-11-23: low-activity days on Deribit's thin perps are decided late (plumbing; nothing changed)
- **What happened.** The lane waited at the 01:21 and 02:32 UTC ticks on 2026-11-22, a Sunday, and decided at 07:09
  (`late`). On 2026-11-23 it decided at 00:59 (`ontime`).
- **Why.**
  - `lab/carrylane.py` decides only when each venue's share of fresh coins on day D is at least 0.9 of day D−1's,
    or `ready_wait_h` (6 h) has passed. A coin is fresh when a traded bar ended in the day.
  - Some of Deribit's thin new perps have days with no trade, so the ratio moves with activity: 0.759 on 2026-11-22,
    1.175 on 2026-11-23. Hyperliquid's was 0.98-1.0.
- **Effect on the read.**
  - A late day keeps the same decision, made later.
  - Its tickets get no live book record, so R512's `series` charges 21 bp a leg-side for them (`MISSING`). This biases
    R520 and R521 against the lane, not for it.
  - Expect more late days on weekends and holidays.
- **Not changed.** The lane, the read and `carrylane.py` are frozen or pinned. Checked: only the `day`, `kind`, `run`
  and `ready` columns, and `status.json`. No result was read.

## 2026-11-23: one frozen test is time-dependent
- `tests/test_forward_xfund_dhl.py::test_read_on_an_empty_journal` asserts zero scored days. It was true at the
  freeze; it fails since R520 scored its first day on 2026-11-23.
- The file is a frozen input, so it is not edited. The failure is expected from now on, and it says nothing about the
  lane.
