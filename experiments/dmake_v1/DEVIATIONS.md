# DEVIATIONS: dmake_v1 (R522)

## 2026-11-23: R522's fetcher overwrote an existing script of the same name (repaired; the result is unchanged)
- **What happened.**
  - On 2026-11-21 the session wrote R522's fetcher to `scripts/fetch_deribit_trades.py` with a shell heredoc,
    unaware that a script of that name already existed.
  - The existing one was the Deribit options-flow fetcher that R295 (optflow_v1), R408/R409 (vrpsell), charm_expiry
    and dealerflow name in their PREREGs (by name, not by hash).
  - The provenance step also overwrote `docs/provenance/deribit_trades.json`.
  - R522's data went to `data/deribit_trades/`, the old lanes' folder. Its files sat at the top level, and the old
    data sits in `<CUR>/flow/` subfolders, so no data file was overwritten.
  - The full test suite caught it on 2026-11-23: `tests/test_fetch_deribit_trades.py` errored.
- **Repair** (no history rewritten):
  - `scripts/fetch_deribit_trades.py` and `docs/provenance/deribit_trades.json` are restored byte-for-byte from
    their versions before commit 7ccfe06c. Their tests pass again.
  - R522's fetcher is kept byte-identical as `scripts/fetch_deribit_perp_trades.py`. Its sha256 66a00945… equals the
    one R522's PREREG pins under the old path.
  - R522's data moved to `data/deribit_perp_trades/` (68 files; manifest unchanged). Provenance is in
    `docs/provenance/deribit_perp_trades.json`.
- **To reproduce R522:**
  - check out its fetcher from commit 7ccfe06c, or use the identical copy;
  - point `run_dmake.py`'s `DATA` at `data/deribit_perp_trades`, or copy the files back. The frozen runner still names
    `data/deribit_trades`.
  - The verdict (FAIL) and every number in FINDINGS are unchanged: they were computed before the move.
