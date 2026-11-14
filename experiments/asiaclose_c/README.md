# asiaclose_c (R469): R468's Asian closure fade, read once on unseen openings

- **What:** R468's frozen rule and universe (18 Asian single-stock perps on xyz and Lighter, faded over the home
  exchange's weekday-night closure, |W| ≥ 50 bp, exit an hour into the session) on openings 2026-11-12 .. 2027-01-29.
  No lane has seen these openings; the PREREG was frozen on 2026-11-11 (`bcf3a776`).
- **Why:** R468's A paid +87.8 bp a trade but B was flat (+9.5 bp, median zero). One cheap read of a fresh sample
  comes before any forward lane. PASS (one-sided p ≤ 0.05 and mean > 2 cost units) earns a forward lane with
  tickets; NULL closes M526.
- **When:** `.github/workflows/claude-asiaclose-c.yml` runs `scripts/run_asiaclose_c.py` at 07:41 UTC on 1-4 February
  2027. The runner refuses to run before 2027-02-01 and reads once; it fetches the bars with R468's frozen fetcher.
- **Results:** `results/summary.json`, `cells.csv`, `events.csv` and `run.log`, written by the workflow only.
- Paper only: public endpoints, no key, no order.
