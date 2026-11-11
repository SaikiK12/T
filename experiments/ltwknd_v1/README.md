# ltwknd_v1 (R465)

R462's frozen trade.xyz weekend fade (M515), run unchanged on Lighter's prices and funding for the 50 of R462's US-stock
markets that Lighter lists, at Lighter's 0 maker / 0 taker fee. Gate 0, exploratory: sample A (R462's Fridays
2026-05-01 .. 2026-09-25) decides, B (2026-10-02 .. 2026-11-06) confirms, C (2026-02-27 .. 2026-04-24) confirms when
large enough.

- [PREREG](PREREG.md), frozen before any Lighter price of these markets was fetched for this question.
- Universe: [universe.csv](universe.csv), from R462's universe and Lighter `orderBookDetails` (2026-11-11).
- Code: `scripts/fetch_lighter_wknd.py`, `scripts/run_ltwknd.py`, `tests/test_ltwknd.py`; rule in `xyzwknd_rule.py`.
- Run: `python scripts/run_ltwknd.py` after `python scripts/fetch_lighter_wknd.py bars --start 2026-02-13T00:00:00Z
  --end 2026-11-10T00:00:00Z`.
- Results: `results/` and FINDINGS.md once run.
