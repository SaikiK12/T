# xyzns_wknd_v1 (R464)

R462's weekend fade (M515) moved from trade.xyz's US-stock perps to its 14 US equity-index, commodity and FX perps
(method M520, idea wave 6). Gate 0, exploratory: sample A (Fridays 2026-05-01 .. 2026-09-25) decides, B (2026-10-02 ..
2026-11-06) confirms.

- [PREREG](PREREG.md), frozen before any of these markets' prices was fetched.
- Universe: [universe.csv](universe.csv), built from trade.xyz's Specification Index and Hyperliquid `meta`.
- Code: `scripts/fetch_xyz_ns.py`, `scripts/xyzns_rule.py`, `scripts/run_xyzns.py`, `tests/test_xyzns.py`.
- Run: `python scripts/run_xyzns.py` after `python scripts/fetch_xyz_ns.py bars --start 2026-04-01T00:00:00Z
  --end 2026-11-10T00:00:00Z`.
- Results: `results/` and FINDINGS.md once run.
