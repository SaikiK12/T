# xyzwknd_fwd (R463): R462's trade.xyz weekend fade, forward

R462's gate-0 PASS, tested forward on fresh weekends from Friday 2026-11-13: when a trade.xyz US-stock perp
(Hyperliquid HIP-3, 76 markets, France-reachable) has moved 50 bp or more from Friday 20:00 to Sunday 19:00 New York,
fade it until Sunday 22:00, after external prices (Blue Ocean's overnight session) return at 20:05.

- Rule and decisions: [PREREG](PREREG.md) (futility at 15 traded weekends, interim at 20, final read at 30).
- **Measure A (decides):** R462's own prices (hourly candle closes) and funding, each fill charged that day's taker fee
  and the $1k book cost recorded on `claude/xyz-books-data`.
- **Measure B (must agree for a PASS):** point-in-time tickets. At Sunday 19:00 the tick workflow decides from the
  candles then available and walks the live order book; at 22:00 it walks it again to exit. This is what an
  automated account would have filled.
- Runner: `scripts/run_xyzwknd_fwd.py`.
  - `tick` runs in `.github/workflows/claude-xyzwknd-tick.yml`: crons from Sunday 22:10 to Monday 02:40 UTC, and a
    run up to 70 minutes early sleeps to the instant.
  - `score` runs daily in `.github/workflows/claude-xyzwknd.yml` at 06:19 UTC.
- Journal in `journal/`: `tickets.csv` (B's entries and exits), `a_trades.csv` (one row per market and weekend),
  `b_trades.csv` (one row per ticketed trade), and `status.json`.
- Paper only: public endpoints, no key, no order.

## Faults and notes
- 2026-11-11, before the first weekend: GitHub starts this repository's scheduled runs 40-90 minutes late and drops
  some, so `claude-clock.yml` now also dispatches `claude-xyzwknd-tick.yml` at 18:10 and 21:10 New York on Sundays.
  Each run sleeps to 19:00 or 22:00, as the PREREG allows. The tick's crons stay as a second path. No pinned file
  changed, and no ticket rule changed.
