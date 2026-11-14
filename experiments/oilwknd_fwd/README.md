# oilwknd_fwd (R459): R432's oil weekend fade on Lighter, fresh weekends

R432's only lead, tested forward where a French resident can trade: when Lighter's WTI or BRENTOIL perp has moved
1% or more between the Friday 17:00 New York close and five minutes before the CME Sunday 18:00 reopen, fade the move
from just before the reopen to the Monday 09:30 cash open. One-minute fills, hourly funding charged, and the $1k book
cost recorded on `claude/xyz-books-data` (Lighter's Standard account pays no fee).

- Rule and decisions: [PREREG](PREREG.md) (frozen `78454c92…`; futility at 15 traded weekends, final read at 40).
- Runner: `scripts/run_oilwknd.py`, daily in `.github/workflows/claude-oilwknd.yml`; journal in `journal/`
  (`trades.csv`, one row per asset and weekend, and `status.json`).
- First weekend: Friday 2026-11-13.
