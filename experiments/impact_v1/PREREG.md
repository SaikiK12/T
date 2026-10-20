# PREREG: impact_v1 (R262). Square-root market impact on the flow books: how much capital can they carry?

Freeze with `lab.prereg.freeze()` before the first statistic. Never edited afterwards; a change is a new lane.

- **Registry id:** R262 (inside the R260-R279 block proposed on issue #7)
- **Owner (single writer):** the Claude session that froze it
- **Code:** `scripts/run_impact.py`. It reuses `build()` and the window dates from `scripts/run_regime.py` (R233),
  unchanged. Books A, B and X2 must equal R217's `daily.npz` (max |diff| < 1e-12) before anything else is computed.
- **Queue:** M006 (square-root impact cost at target size, Donier and Bonart; Toth et al. 2011).
- **Gate:** 0. **This is a measurement, not an edge test: trials = 0.** No rule or parameter is selected.

## What the author has seen
- The books' nets with tier costs at 1x/2x/3x (R217, R233, R260). Book A validation: +13.6 bp/day at 1x.
- **R224 (mexc_costs):** a first MEXC order-book snapshot. Median half-spread 0.66 bp; web taker at $10k about 2.5 bp.
- No impact estimate on the archive has been computed.

## Model
- **Coin statistics for day d** (from days d-30..d-1; at least 20 days with data):
  - σ[d, s]: the standard deviation of daily coin returns, where a daily return is the sum of `u.ret` over the day's 24
    rows.
  - V[d, s]: the mean daily quote volume in USD, summed from the hourly klines `quote_volume`.
  - **Missing statistics** (a traded coin without 20 days): use that day's 90th percentile σ and 10th percentile V
    across coins that have them. This is conservative. The share of traded notional this affects is reported.
  - **The archive's first days**, when no coin has 20 days of history, use the percentiles of the first day that
    has them.
- **Impact of a trade:** Q USD of coin s on day d costs Y x σ[d, s] x sqrt(Q / V[d, s]) of the traded notional.
  - **Each hourly trade is its own metaorder.** Consecutive same-direction trades are not merged, which understates
    impact.
  - Y = 1 is the decided value; Y = 0.5 is reported.
- **Book trades at capital C:**
  - The main leg trades |dP[t, s]| x C per coin.
  - The hedge leg trades |dH[t]| x C, where H = -(net exposure), split equally over the coins eligible at row t.
- **Book cost:** net(C) = the book's daily net with tier costs at 1x (or 2x or 3x), minus the daily sum of impact.
  Impact grows with sqrt(C), so C enters in closed form.
- **Capital levels:** C in {$1k, $10k, $100k, $1M, $10M}.
- **Reported break-even capitals:**
  - C50, where impact takes half of the 1x net;
  - C0, where the 1x net reaches 0.

## Windows
- **Discovery:** 2021-01..2023-12.
- **Validation:** 2024-01..2025-06.
- **Holdout:** not read.

## Decision (one, for the panel)
- **DATA_PASS:** at C = $10k and Y = 1, impact is below 10% of the validation 1x net, for each of A, B and X2. That
  means the tier cost model is adequate at the owner's scale.
- **NULL otherwise:** the tier model understates cost at that size, and every book's net must be reread with impact.

## Reported
- Per book, window, C, Y and cost level:
  - net mean bp/day, NW t;
  - impact bp/day and tier cost bp/day;
  - impact as a share of tier cost.
- C50 and C0 per book and window, at Y = 1 and Y = 0.5.
- The mean traded notional per day as a share of capital, and the median trade's Q / V at C = $10k.

## Multiplicity
- Trials = 0 (measurement).
- Program trials stay at 9,472,061.

## Expectations
- At $10k the median trade is far below 1e-4 of daily volume, so impact is a fraction of a bp per trade: DATA_PASS.
- **C50 is probably between $1M and $10M for A and X2.** B trades less, so its C50 is higher.
- **Caveats:**
  - Binance volumes are larger than MEXC's, so MEXC capacity is lower.
  - The square-root law's Y is uncertain by a factor of 2.
