# litbuyback_v1 (R486)

M537, gate 0 on history. Does Lighter's daily LIT buyback in USDC, as a share of LIT's own daily traded value (perp
plus LIT/USDC spot quote volume), predict LIT's next-week return on Lighter's LIT perp? Spearman rank correlation
against a circular-shift null, and a weekly long-or-flat book against always-long, 2026-01-02 to 2026-11-10.

- `PREREG.md`: frozen question, rule, gates, inputs (exchangeMetrics bodies by sha256, the pinned
  claude/okx-xperp-data commit and lit/ tree hashes) and what was seen before the freeze.
- `results/`: written once by `scripts/run_litbuyback.py` (`verdict.json`, `blocks.csv`, `pairs.csv`).
- `FINDINGS.md`: the result at 1x/2x/3x against `registry.program_trials()`.
- Tests: `tests/test_run_litbuyback.py`.

Nothing dated after 2026-11-10 is read (R447's forward window). Paper only. No order, no money, no key.
