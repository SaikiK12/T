# xyzbal_fwd (R530)

The balanced (market-neutral) weekend fade of trade.xyz US-stock perps, tested forward from the weekend of Friday
2026-12-04. Frozen spec: [PREREG.md](PREREG.md) (sha256 in `PREREG.sha256`).

- **Rule.** rel W = the perp's move from Friday 20:00 to Sunday 19:00 New York, minus that weekend's median over R462's
  76 markets. Buy rel W ≤ −50 bp, sell rel W ≥ +50 bp, equal notional on each side, exit Sunday 22:00.
- **Scored daily** by `.github/workflows/claude-xyzbal.yml` (`scripts/run_xyzbal_fwd.py score`): Hyperliquid's
  public candles and funding, with the fees and $1k book costs recorded on `claude/xyz-books-data`.
- **Journal:**
  - `journal/trades.csv` and `journal/weekends.csv`, append-only, written by the workflow only;
  - `journal/status.json`, rewritten at each run.
- **Decision:** futility at 15 traded weekends; PASS at 20 (p < 0.01) or 30 (p < 0.04), with the 2x mean and the mean
  without the best 3 above 0.
- **Why it exists:** `docs/reviews/reflection_20261125_power.md`. On R462's weekends it has a third to half of R463's
  per-weekend noise.
- Paper only.
