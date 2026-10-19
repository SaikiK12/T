# Feature vintage integrity: use what was knowable at the decision time

Reviewed 2026-10-19. A feature can be aligned to the correct event window and still leak future information if its provider revises the historical value after the strategy decision. This is distinct from signal-computation latency: the stored value itself can change later.

## Why event time is not enough

Glassnode's point-in-time guidance explains that historical on-chain metric values can be revised as addresses are relabeled, late reports arrive, or source data are corrected. Its PIT endpoint provides a value as it was known at a historical point, whereas ordinary historical queries can return the latest revised value ([PIT guidance](https://docs.glassnode.com/data/point-in-time-metrics), [PIT endpoint](https://docs.glassnode.com/basic-api/endpoints/pit)). These are vendor statements about Glassnode's own data, not an independent audit or a guarantee for every metric.

The vendor documents `computed_at` as the time the point entered its system; it is not the time the API published it or the strategy first received it. Glassnode reports a 99th-percentile computed-to-publication lag of 9 minutes 42 seconds and median of 15 seconds in its documentation. The field is available only for relevant metric history since September 2024, and PIT coverage is constrained by each metric's tracking start; broader all-metric PIT coverage begins in July 2025. Verify metric-specific coverage before treating an API response as a complete historical vintage. A consumer's first local receipt can be later still.

## Required as-of record

For a feature row, preserve at least:

- event/window start and end, plus the window-close rule;
- provider, metric identifier, asset mapping and units;
- provider `computed_at` and published/available time when supplied;
- first local receive time, request/retrieval time and payload hash;
- value, revision/vintage identifier, quality flags and missing reason.

At a decision time, select only the latest value that had actually arrived by then and whose measurement window had closed. Keep later corrections in a separate revision stream; never overwrite the value used by an already-saved decision. If a provider cannot supply a historical vintage or availability timestamp, use forward capture for evaluation or explicitly classify the feature as unavailable for point-in-time backtesting.

Run a vintage sensitivity report before relying on a feature: compare the first-known-as-of series with the latest revised series; report the share of rows revised, absolute and signed revision distributions, the feature-value rank changes, and coverage lost under strict as-of rules. Then recompute the frozen score only in an authorized fresh evaluation lane. A large gap between revised and as-known results is a data-integrity issue, not a reason to choose whichever series performs better.

## Synthetic timing fixture

Suppose a metric describes the 10:00 window, first arrives locally at 10:12, and is revised at 16:00. A 10:10 decision must have no value; a 10:13 decision may use the first received value; a decision after 16:00 may use the revised value only if the revision has arrived. This fixture illustrates the as-of rule and is not a measured vendor latency or project result.

## Relation to the current review

The [implementation integrity review](IMPLEMENTATION_INTEGRITY_REVIEW.md) finds that the frozen R200 reconstructed segment is tagged `late` and that historical API parity does not establish first local receipt of each feature. This note supplies a general data contract for future macro, on-chain and sentiment inputs; it does not claim that the existing Binance features were revised or quantify any resulting bias. For scheduled macro data and release timing, see [market direction and regime](MARKET_DIRECTION_AND_REGIME.md). For the related issue of when a signal becomes actionable, see the project's existing 12-minute timing review in the implementation note.

## Sources

- Glassnode, [Point-in-Time Metrics](https://docs.glassnode.com/data/point-in-time-metrics).
- Glassnode, [Point-in-Time API endpoint](https://docs.glassnode.com/basic-api/endpoints/pit).
- FRED, [real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html) and [release dates](https://fred.stlouisfed.org/docs/api/fred/release_dates.html).

These vendor documents define available fields and limitations; they do not independently validate a project's stored data. No third-party feature history or market data were downloaded, no as-known versus revised backtest was run, and no project result is asserted here.
