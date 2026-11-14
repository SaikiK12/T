# xvwknd_v1 (R466)

The Sunday-evening gap between trade.xyz's and Lighter's perp on the same US stock (new method M524), traded as a
hedged pair: sell the dearer venue and buy the cheaper one at Sunday 19:00 New York, close at Monday 10:00. Gate 0,
exploratory: sample A (Fridays 2026-05-01 .. 2026-09-25) decides, B (2026-10-02 .. 2026-11-06) confirms.

- [PREREG](PREREG.md), frozen before any Lighter price was read and before any gap was computed.
- Universe: [universe.csv](universe.csv), the 50 markets of R465 with R462's xyz growth flag.
- Code: `scripts/xvwknd_rule.py`, `scripts/run_xvwknd.py`, `tests/test_xvwknd.py`.
- Data: R462's `data/xyz_wknd` and R465's `data/lighter_wknd`, each re-hashed against its manifest.
- Run: `python scripts/run_xvwknd.py` after R465's fetch.
- Results: `results/` and FINDINGS.md once run.
