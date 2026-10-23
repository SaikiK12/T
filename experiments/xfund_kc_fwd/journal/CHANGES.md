# CHANGES: xfund_kc_fwd (R279)

Data plumbing changes after the freeze, as the PREREG allows (venue clients, retries, file handling). Each needs the
tests to pass. A change to the rule, the books, the accounting or the decision would be a new lane.

| Date | Commit | File | Change | Effect on this lane |
|---|---|---|---|---|
| 2026-10-22 | f6bade5 | `lab/carrylane.py` | Lighter's public clients and a `lighter` venue entry, for R294 `xfund_lt_fwd`. Code is added only; no existing client or Lane method changed. sha256 fe24ae2a… → 12efdca3… | None: this lane uses Binance, Gate and KuCoin only. `tests/test_carrylane.py` passes (R278 journals still byte-identical), and so does the full suite (680 tests). |
