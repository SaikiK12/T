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

## Coverage survivorship in the daily panel (found 2026-10-22, R299 audit)
A feature can have correct timing and still leak the future through **which coins have it at all**.

**The venue histories behind the daily panel** (`lab/daily.py`) were fetched like this:

| Venue | Contracts fetched |
|---|---|
| Binance klines, funding and metrics; Gate (S3 archive); dYdX | delisted ones included |
| KuCoin, Kraken | live at download time only |
| MEXC | perps listed at download time, from 2025-04 |
| Hyperliquid | listed perps only |
| Upbit, Bithumb | KRW markets live at download time only |

**So a coin that Binance later delisted has almost none of the survivor-only venues.**

| Year (top 150, rows with a close) | KuCoin funding: survivors / later delisted | Upbit price | Mean `n_venues` |
|---|---|---|---|
| 2021 | 53% / 2% | 42% / 5% | 1.29 / 0.49 |
| 2022 | 73% / 5% | 40% / 4% | 1.93 / 0.88 |
| 2023 | 89% / 5% | 40% / 3% | 2.60 / 1.06 |
| 2024 | 95% / 3% | 39% / 3% | 3.73 / 1.51 |
| 2025 | 93% / 0% | 42% / 0% | 4.52 / 1.88 |

**Columns that leak survival:**
- `n_venues`;
- the `{kucoin,kraken,mexc,hyperliquid}_*` columns (`_gap`, `_fund`, `_fund_gap`, `_qvol`, `mexc_premium`);
- `upbit_rel`, `bithumb_rel` and their volumes;
- any mean over venues that includes them (R299's `fund_gap7`, R282's `fund_gap_all_7d`).

The panel's column table labels them `pit`. That label is about timing only.

**Milder gaps that are not download survivorship:**
- Binance metrics (OI, positioning) were fetched for every archive perp. Their files are missing at similar rates for
  survivors and later-delisted perps (45% and 50%).
- A Binance spot pair's delisting is public when it happens.
- The market-cap estimate covers 52-85% of later-delisted coins against 81-91% of survivors. It is already in the
  vintage set.

**Rules for lanes:**
1. **Cross-sectional lanes** (ranking coins against each other) must not use the leaking columns, their presence or
   their count. Venue breadth can use Gate and dYdX only.
2. **Lanes that trade a venue's own contracts** (carry on KuCoin or MEXC) hold a survivor universe. Report it as a
   limit; their forward days are unaffected.
3. **A cross-sectional result must report its legs' share of later-delisted coins** against their share of the
   universe (R304's check).

**The fix at the source (queued):** refetch the survivor-only venues with delisted markets where their APIs allow it.
Where they do not, label the columns `survivor` in `lab/daily.py`'s table.

**Lanes touched:**
- **R299** (`mlrank_v1`): its PARTIAL is invalidated; R304 reruns it without the three columns.
- **R282** (`pitfac_v1`): `n_venues_7d` and `kr_rel_7d` did not pass there, so no result changes.
- **R275-R279 and R288 carry books:** their KuCoin, MEXC and Hyperliquid universes are survivor-only. This is a limit
  on their backtests, not on their forward days.

## Sources

- Glassnode, [Point-in-Time Metrics](https://docs.glassnode.com/data/point-in-time-metrics).
- Glassnode, [Point-in-Time API endpoint](https://docs.glassnode.com/basic-api/endpoints/pit).
- FRED, [real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html) and [release dates](https://fred.stlouisfed.org/docs/api/fred/release_dates.html).

These vendor documents define available fields and limitations; they do not independently validate a project's stored data. No third-party feature history or market data were downloaded, no as-known versus revised backtest was run, and no project result is asserted here.
