# llpinv_v1 (R455): Lighter LLP's inventory as a cross-sectional perp signal

LLP is Lighter's protocol pool: it makes markets and takes over liquidations, as HLP does on Hyperliquid, so its net
position in a market is roughly the other side of the crowd's. Lighter shows the pool's positions in real time but
keeps no history, so this lane is forward only. Each hour, `scripts/record_llp_positions.py` snapshots LLP's
positions and every Lighter perp's open interest and volume. Every snapshot then ranks the eligible markets by LLP's
signed position value over open interest, with R454's rule unchanged:
- book **F** (follow LLP) shorts the eighth where LLP is most net short;
- book **R** (reverse) shorts the eighth where LLP is most net long.

Each short is a 72 h slice hedged with the universe, as R200's flow books, at 9 bp a trade. Lighter does not exclude
France, so a PASS could be traded as the paper is.

- Rule and decisions: [PREREG](PREREG.md) (frozen `ea4f9f26…`). Method M511; two trials. Sibling of
  [hlpinv_v1](../hlpinv_v1/README.md) (R454), read separately.
- Data: `llp/` on the data branch `claude/xyz-books-data` (hourly, `claude-xyz-books.yml`); Lighter's hourly closes
  and funding in `journal/px/`.
- Runner: `scripts/run_llpinv.py`, weekly in `.github/workflows/claude-xperp-reads.yml`. It writes
  `journal/tickets.csv`, `journal/coins.csv` and `journal/status.json`.
- Looks: a futility screen at 90 counted days (from 2026-11-15), the decision at 365 against 1,000 random-bin
  placebo books (seed 455). 365 days detect an annual Sharpe of about 2.8 only.
