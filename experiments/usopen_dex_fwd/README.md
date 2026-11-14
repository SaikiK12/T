# usopen_dex_fwd (R457): R371's US-open picks on Lighter and Hyperliquid

C17 (go long the 3 strongest and short the 3 weakest of Binance's 50 most traded perps at 10:00 New York, flat at
24:00 UTC) has the lab's strongest blind read (R392). R371 trades it forward on MEXC and Binance, which a French
resident cannot use. This lane takes R371's own tickets and trades the same rule on the names each venue lists:
- book L on Lighter (Standard account, no fee) decides;
- book H on Hyperliquid's main dex and xyz (4.5 bp, or the HIP-3 fee) is reported.

Fills are the venue's one-minute opens 3 minutes after each clock. Each fill pays the fee plus the cost of a $1k
market order in the nearest hourly book snapshot on `claude/xyz-books-data`.

- Rule and decision: [PREREG](PREREG.md) (frozen `dee511b4…`). Method M318, candidate C17. Two trials.
- Parent: [usopen_fwd](../usopen_fwd/PREREG.md) (R371). A day R371 missed is missed here too.
- Runner: `scripts/run_usopen_dex.py`, daily at 03:17 UTC in `.github/workflows/claude-usopen-dex.yml`. It
  appends `journal/scored.csv` and `journal/legs.csv` and rewrites `journal/status.json`.
- Reads: futility at 125 scored L days, PASS or NULL at 500, as R371.
