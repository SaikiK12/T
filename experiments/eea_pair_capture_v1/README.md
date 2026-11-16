# eea_pair_capture_v1 (R419): Coinbase CDE / Kraken raw capture

**Writer lost (2026-11-16).** Last commit in this folder 90dcfa4a (2026-11-07). Codex registered this lane for a
Claude container that ended before activation (its `FINDINGS.md` still says NOT_STARTED, as written before then).
Codex's R420 takeover (`experiments/ops_takeover_v1`) then ran the unchanged capture from its GitHub `quant-*` runtime
until the lane's own end date, 2026-11-14 (`docs/OPERATIONS.md`, e.g. 12 GETs at 2026-11-08 16:00 UTC). The captures
sit in that runtime's state, not in this folder. No read was written after the end, and that runtime stops on
2026-11-19. The registry row stays REGISTERED / PENDING with 0 trials. Closing it needs one read of the takeover state
by its frozen rules, by Codex before 2026-11-19 or by a later session from the state branch; nothing restarts, because
the capture window is over.
