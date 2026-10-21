# lab: the research library

<!-- written by scripts/catalog.py; edit the sources (registry, docstrings), not this file -->

Imported as `from lab import <module>`. Tests are in `tests/test_<module>.py`; run them all with
`python -m unittest discover -s tests -t .` before committing a change here.

- [`atlas`](atlas.py): Edge atlas: what each feature bin says about future returns BEFORE fees, at several horizons, split by a grouping (market session, liquidity tier, BTC regime), with a placebo to say how much of it ...
- [`carry`](carry.py): Funding carry: short the perpetual and hold the same coin spot, so price moves cancel and the position collects the funding that longs pay shorts, minus changes in the perp-spot basis and the cost ...
- [`carrylane`](carrylane.py): Forward paper lanes for cross-venue funding carry books (R275's rule, run with lab.xfund), on any set of venues.
- [`config`](config.py): Constants every lane shares.
- [`daily`](daily.py): Daily point-in-time panel: one row per (day, Binance USD-M perp) with what every source the lab holds had said about that coin by 00:00 UTC of that day, plus one row per day of market-wide series.
- [`data`](data.py): Binance public-archive fetcher (data.binance.vision).
- [`engine`](engine.py): Vectorized backtester.
- [`events`](events.py): Event studies on the hourly panel: per-event returns over a holding window, clustered statistics, and the daily PnL of a book that takes every event with a fixed stake.
- [`features`](features.py): Feature library.
- [`flow`](flow.py): Order-flow datasets streamed from the public archive and reduced to hourly bars on the fly (raw files are not kept).
- [`flowfeat`](flowfeat.py): Order-flow features from the hourly metrics and bookDepth tables written by lab/flow.py, binned the same way as lab/features.py (cross-sectional rank buckets, trailing 30-day z-score buckets, or ...
- [`gate`](gate.py): The go-real gate: the only door from paper to a small real stake.
- [`ict`](ict.py): ICT / smart-money concepts as mechanical, causal detectors on [T, S] bar arrays (one timeframe at a time).
- [`inference`](inference.py): Honest statistics for a program that tries thousands of strategies.
- [`levcarry`](levcarry.py): Leverage and liquidation on cross-venue carry books (method M265): R275's rule, run with lab.xfund, where each leg sits on its venue at leverage L and can be liquidated by an intraday move.
- [`live`](live.py): Public live data from Binance USD-M futures, for paper trading only: no keys, no orders, nothing private.
- [`maker`](maker.py): Maker entries: trade a signal with a resting limit order instead of a market order, so the entry pays the maker fee and earns the distance to the reference price instead of paying spread and ...
- [`markets`](markets.py): Daily bars for markets beyond crypto perps (indices, index futures, forex, commodities, rates, volatility), from Yahoo Finance's public chart endpoint, cached under data/markets/yahoo/. Small: one ...
- [`merge`](merge.py): Merge lab: combine many signals into one forecast per (hour, symbol), re-learned walk-forward, and trade it only where the forecast clears the cost of trading.
- [`mexc`](mexc.py): Public MEXC USDT-M futures data (no keys, no orders): contract metadata, hourly klines, funding settlements, and the map from Binance USD-M symbols to MEXC crypto contracts.
- [`microstructure`](microstructure.py): Offline features from caller-validated, consecutive best-quote observations.
- [`nulls`](nulls.py): Full-pipeline null: the whole search reruns on a forward panel shifted in time against the features.
- [`pack`](pack.py): A pack: many signal cells traded in one book, each entry a limit order (lab/maker.py rules) or a market order, marked to market every hour, with an optional hedge that holds the opposite of the ...
- [`panel`](panel.py): One hourly clock for every symbol, and higher timeframes that only become visible once their bar has closed.
- [`policy`](policy.py): Judging the PROCESS of picking strategies, because strategies work for a time and not forever.
- [`prereg`](prereg.py): Pre-registration: the spec is hashed before any statistic runs, and every run re-checks the hash.
- [`propfirm`](propfirm.py): Prop-firm economics: what a strategy's return stream is worth inside an evaluation and a funded account.
- [`registry`](registry.py): Append-only register of research rounds (the machine-readable ROADMAP).
- [`research`](research.py): Glue between data and search: the point-in-time research universe, costs, and guarded rule evaluation.
- [`screen`](screen.py): The standard screen for a cross-sectional feature, so a queued method needs a frozen PREREG and a feature, not a new runner.
- [`search`](search.py): Staged beam search over conditions on feature bins, with a placebo to calibrate what counts as a find.
- [`sessions`](sessions.py): Market clocks: where each decision time sits against the hours of other markets and scheduled events.
- [`sizecarry`](sizecarry.py): Confidence-sized cross-venue carry (method M266): R275's books with the same pairs, entered and exited by the same rule (lab.xfund), but each open pair sized by a score instead of one equal slot.
- [`slices`](slices.py): Overlapping-slice books (the Jegadeesh-Titman construction): every hour a symbol is in the signal state, open a slice of fixed size and close it `hold` hours later.
- [`stats`](stats.py): Reference statistics.
- [`tearsheet`](tearsheet.py): Performance tear sheet for a daily return stream: quantstats' core metrics, plus the lab's honesty terms.
- [`venues`](venues.py): One symbol map from each Binance USD-M perp to the same coin on every other venue and data source the lab holds.
- [`xfund`](xfund.py): Cross-venue funding carry books (R275's rule) one day at a time, for forward paper.
