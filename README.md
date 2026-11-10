# OKX Europe X-Perp recordings (data branch)

Written only by `.github/workflows/claude-okx-recorder.yml`, which runs `scripts/record_okx_xperp.py` from the default
branch twice a day. Public market data only (eea.okx.com), no key, no order.

Why: OKX's public API keeps about three months of funding prints, and X-Perps are the one perp route found open to a
French resident (`docs/reviews/venue_access_fr_20261110.md` on the default branch). M490 needs longer history and
measured costs.

Layout (day-partitioned CSV, merged by key, so closed days only gain rows):
- `instruments/YYYY-MM-DD.json`: the day's X-Perp listing (crypto, stocks, commodities).
- `funding/YYYY-MM-DD.csv`: funding prints by UTC day of `fundingTime`.
- `mark_1d/`, `index_1d/`, `spot_1d/`: closed daily candles of each X-Perp's mark, its underlying index, and the
  OKX EEA spot pair that would hold the hedge leg ({base}-USDC, else {base}-EUR).
- `books/YYYY-MM-DDTHHMM.csv`: best bid/ask and $1k/$10k market-order cost in bp from mid, X-Perp and spot.
- `last_run.json`: the last run's counts and failures.
