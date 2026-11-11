# hlpinv_v1 (R454): HLP's inventory as a cross-sectional perp signal

Hyperliquid's HLP vault makes markets and takes over liquidations, so its net position in a coin is roughly the other
side of the crowd's. Its positions are public in real time but kept nowhere, so this lane is forward only. Each hour,
`scripts/record_hlp_positions.py` snapshots every child vault's positions and every main-dex perp's open interest.
Every snapshot then ranks the eligible coins by HLP's net size over open interest:
- book **F** (follow HLP) shorts the eighth where HLP is most net short;
- book **R** (reverse) shorts the eighth where HLP is most net long.

Each short is a 72 h slice hedged with the universe, as R200's flow books, at 9 bp a trade.

- Rule and decisions: [PREREG](PREREG.md) (frozen `9df27190…`). Method M510; two trials.
- Data: `hlp/` on the data branch `claude/xyz-books-data` (hourly, `claude-xyz-books.yml`); Hyperliquid's hourly
  closes and funding in `journal/hl/`.
- Runner: `scripts/run_hlpinv.py`, weekly in `.github/workflows/claude-xperp-reads.yml`. It writes
  `journal/tickets.csv`, `journal/coins.csv` and `journal/status.json`.
- Looks: a futility screen at 90 counted days (from 2026-11-15), the decision at 365 against 1,000 random-bin
  placebo books. 365 days detect an annual Sharpe of about 2.8 only.
