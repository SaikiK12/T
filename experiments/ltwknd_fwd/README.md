# ltwknd_fwd (R467): R465's Lighter weekend fade, forward

R465's PARTIAL, tested forward on fresh weekends from Friday 2026-11-13. When a Lighter US-stock perp (50 markets,
Standard account at zero fee, France-reachable) has moved 50 bp or more from Friday 20:00 to Sunday 19:00 New York,
fade it until Sunday 22:00. By then external prices (the Blue Ocean overnight session) are back.

- **Rules and decisions:** [PREREG](PREREG.md) (frozen `e9fb7621`): futility at 15 traded weekends, interim at 20,
  final read at 30. The same rule as R463 on trade.xyz; the two lanes trade largely the same events at two costs and
  are read together.
- **Measure A (decides):** R465's prices (traded hourly candle closes) and funding. Each fill pays Lighter's listed
  taker fee plus the $1k book cost recorded on `claude/xyz-books-data` (`lighter/books/`).
- **Measure B (must agree for a PASS):** point-in-time tickets.
  - At Sunday 19:00 the tick workflow decides from the candles then available and walks Lighter's live book.
  - At 22:00 it walks the book again to exit.
  - This is what an automated account would have filled.
- **Runner:** `scripts/run_ltwknd_fwd.py`.
  - `tick` runs in `.github/workflows/claude-ltwknd-tick.yml`. `claude-clock.yml` dispatches it at 18:10 and 21:10
    New York on Sundays, and its crons are a second path. A run up to 70 minutes early sleeps to the instant.
  - `score` runs daily in `.github/workflows/claude-ltwknd.yml` at 06:37 UTC.
- **Journal** in `journal/`:
  - `tickets.csv`: B's entries and exits;
  - `a_trades.csv`: one row per market and weekend;
  - `b_trades.csv`: one row per ticketed trade;
  - `status.json`.
- Paper only: public endpoints, no key, no order.

## Faults and notes
None yet.
