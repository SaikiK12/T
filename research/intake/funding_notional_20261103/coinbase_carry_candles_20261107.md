# Coinbase CDE public candles: bounded source intake for R424

Primary organization: Coinbase. API/doc publication date undated. Sources
accessed2026-11-07; exact per-response UTC clocks below. **Counts/schema/time
coverage only before R424's committed freeze; no OHLC/rate-difference/return
statistics.** R423's sampled rate-field mapping is already complete and is
not rerun. This supplement does not edit any of its frozen parents.

The documented [public candles route](https://docs.cdp.coinbase.com/api-reference/advanced-trade-api/rest-api/public/get-public-product-candles)
was read in the request/query/response sections (partial; current public docs,
accessed2026-11-07). It supports ONE_HOUR and start/end Unix seconds. Exact
limit sentence: “The number of candle buckets to be returned. By default,
returns 350 (max 350).” The first tiny fixed4-hour probe returned5candles
per asset. Actual larger pages requested350but returned **300** each, dropping
their leading data; four bounded leading fragments48/22rows per asset finish
that paging coverage. No failed/denied endpoint, authentication, redirect,
spoofed browser UA, retry loop or source-budget renewal.

The fixed primary period is the **first28complete UTC days** after the old
MDA history lower bound:2026-08-10T00 to2026-09-07T00. No price/return selects
the window. With the preceding hour and exit-opening candle there are
674expected slots: **670observed** per asset. Four missing trade-bar starts
are Aug14/Aug21/Aug28/Sep4at21UTC. The corresponding funding-rate timestamps
exist. Missing candles are not fabricated or funding set to zero. This does
not establish whether a no-trade/fallback/closed-market rule explains them.
The saved [coverage](cde_carry_bars_20261107/coverage.json) verifies all672
CDE payment rates,672Kraken absolute-rate intervals and673Kraken marks for
each fixed asset, with no missing required rate or Kraken mark.

Coinbase's [CDE funding mechanism](https://help.coinbase.com/en/derivatives/perpetual-style-futures/funding-rate)
(undated, accessed2026-11-07, relevant sections read) defines3-minute trade
VWAP and midpoint/fallback marks, and hourly calculation with clearing cash
adjustments. Candles alone **do not reconstruct these marks or clearing cash**.
Its [US customer overview](https://help.coinbase.com/en/coinbase/derivatives/us-perpetual-futures-overview)
(undated, same access, partial funding section) expresses funding payment as
rate × quantity × multiplier × futures mark price ×−1 for a long. Its US retail
posting time must not replace the separate frozen European CFSE policy.
[Nodal Clear's market-data directory](https://www.nodalclear.com/resources/market-data/)
(undated, same access, full short directory) points to the ordinary Coinbase
derivatives landing page; that page's market-data navigation was read
partially. No public historical **cleared funding-cash or hourly cash-mark**
series is thereby qualified.

R424 explicitly keeps last completed CDE trade close as a **proxy**; its
bar-low/high envelope is **hypothetical**, not a verified bound on the true
funding mark. At the four absent prior bars the proxy is one hour staler;
no interpolation or claim it is fresh. Kraken cash uses the already qualified
absolute USD/base/hour rate. Current fees and R421's observed Nov7depth
friction are hypothetical historically. These limitations block gate1/real
admission even if a conditional net scenario is positive.

This bounded plumbing used **10requests /142,468client bytes**, all200.
The last conservative cumulative receipt is **7,806calls /247,546,845bytes**
including previous worst-case reservations, below the original8,000calls /
250MiB ceilings. The old229.85MiB exact-byte uncertainty remains; no reset.
The three consumed one-shot markers and every exact raw body/hash are kept.

## Complete market response receipts (full captures)

- https://api.coinbase.com/api/v3/brokerage/market/products/BIP-20DEC30-CDE/candles?start=1786240800&end=1786255200&granularity=ONE_HOUR&limit=8 — HTTP200, 536client bytes, accessed2026-11-07T14:53:56.293263+00:00.
- https://api.coinbase.com/api/v3/brokerage/market/products/ETP-20DEC30-CDE/candles?start=1786240800&end=1786255200&granularity=ONE_HOUR&limit=8 — HTTP200, 534client bytes, accessed2026-11-07T14:53:56.562078+00:00.
- https://api.coinbase.com/api/v3/brokerage/market/products/BIP-20DEC30-CDE/candles?start=1786316400&end=1787572800&granularity=ONE_HOUR&limit=350 — HTTP200, 31671client bytes, accessed2026-11-07T14:57:35.197111+00:00.
- https://api.coinbase.com/api/v3/brokerage/market/products/BIP-20DEC30-CDE/candles?start=1787576400&end=1788739200&granularity=ONE_HOUR&limit=350 — HTTP200, 31668client bytes, accessed2026-11-07T14:57:35.534281+00:00.
- https://api.coinbase.com/api/v3/brokerage/market/products/ETP-20DEC30-CDE/candles?start=1786316400&end=1787572800&granularity=ONE_HOUR&limit=350 — HTTP200, 31644client bytes, accessed2026-11-07T14:57:35.812382+00:00.
- https://api.coinbase.com/api/v3/brokerage/market/products/ETP-20DEC30-CDE/candles?start=1787576400&end=1788739200&granularity=ONE_HOUR&limit=350 — HTTP200, 31554client bytes, accessed2026-11-07T14:57:36.139527+00:00.
- https://api.coinbase.com/api/v3/brokerage/market/products/BIP-20DEC30-CDE/candles?start=1786316400&end=1786485600&granularity=ONE_HOUR&limit=350 — HTTP200, 5081client bytes, accessed2026-11-07T14:59:08.993832+00:00.
- https://api.coinbase.com/api/v3/brokerage/market/products/BIP-20DEC30-CDE/candles?start=1787576400&end=1787652000&granularity=ONE_HOUR&limit=350 — HTTP200, 2345client bytes, accessed2026-11-07T14:59:09.369079+00:00.
- https://api.coinbase.com/api/v3/brokerage/market/products/ETP-20DEC30-CDE/candles?start=1786316400&end=1786485600&granularity=ONE_HOUR&limit=350 — HTTP200, 5092client bytes, accessed2026-11-07T14:59:09.607394+00:00.
- https://api.coinbase.com/api/v3/brokerage/market/products/ETP-20DEC30-CDE/candles?start=1787576400&end=1787652000&granularity=ONE_HOUR&limit=350 — HTTP200, 2343client bytes, accessed2026-11-07T14:59:09.931268+00:00.
