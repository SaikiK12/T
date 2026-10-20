# MEXC next-funding observations: collection protocol v1

This is a raw-data collection artifact for canonical **M090**, not a statistical
preregistration or a trading strategy. It contains no forecast test, PnL calculation,
settled-rate labels or performance selection. A later forecast-versus-settlement
study needs its own frozen specification, deadlines and missing-observation rules.

## One-shot operation

After maintainer review, one invocation collects exactly these six contracts:
`BTC_USDT`, `ETH_USDT`, `SOL_USDT`, `XRP_USDT`, `DOGE_USDT`, `ADA_USDT`.
This fixed major-coin scope does not represent MEXC's full altcoin universe.

```sh
python scripts/capture_mexc_funding_forecasts.py \
  --out /path/to/dedicated-capture-root --capture-id YYYYMMDDThhmmssZ
```

The caller supplies a unique batch ID. The collector makes at most 12 logical
requests: current funding and symbol ticker for each contract. Each response has a
64 KiB limit plus one retained sentinel byte to detect truncation; timeout is ten
seconds. There are no retries, redirects, pagination, schedules or history requests.
Default proxy and certificate verification remain in force. No authentication,
orders, account endpoints or credential files are used.

## Schema and clock contract

All request start/end times are saved in UTC, with millisecond values and raw-body
SHA256 hashes. The API success flag and code, object shape and exact symbol must
match. Nonstandard JSON constants, duplicate fields, nonfinite values, invalid
prices, crossed bid/ask pairs and reversed funding caps fail validation.

| Source field | Interpretation and handling |
| --- | --- |
| funding `fundingRate` | Current displayed rate as a fraction, not percent; may change before settlement. |
| funding `minFundingRate`, `maxFundingRate` | Required finite caps containing the displayed rate; plausibility range -1..1. |
| funding `collectCycle` | Required integer hours in 1..24; never assume every contract settles every eight hours. |
| funding `nextSettleTime` | Required Unix milliseconds, preserved exactly without hourly flooring. |
| funding `timestamp` | Required API **system** timestamp; must be within two minutes of the local request interval. |
| ticker `timestamp` | Required **trade** timestamp; preserved separately. An old trade is not treated as current server time. |
| funding `fairPrice`, `idxPrice`; ticker `fairPrice`, `indexPrice`, `lastPrice`, `bid1`, `ask1` | Positive finite values when present; absent fields become explicit nulls. These are observations, not fills. |

The next settlement must be later than batch completion plus the two-minute clock
tolerance and a 15-second settlement buffer. Its distance from the funding system
timestamp must fit the reported cycle. These are collection quality checks; they
do not define the future study's forecast horizon. The venue warns that settlement
inclusion can be ambiguous within 15 seconds of the nominal time.

## Immutable evidence and failures

`captures/<id>/intent.json` binds the collector and protocol SHA256 hashes, schema version, source versions
and fixed universe before requests. Each request gets its own raw file and metadata
file. `manifest.json` is written once at completion. Failure bodies, including HTTP
errors and truncated prefixes, remain available; a prefix hash identifies only the
retained prefix, not an unread full response.

Normalized records are written under
`observations/<symbol>/<funding-system-ms>_<next-settlement-ms>.json` only when every
contract validates and no observation key already exists. Duplicate IDs make no
request. Duplicate observation keys retain the new raw batch but prevent another
normalized batch. A root lock prevents concurrent writers and is removed only by
its owner. The collector never repairs or overwrites an existing capture. A crash
may leave an intent/raw files without a final manifest; retain that evidence. A
stale lock needs operator inspection of the writer before any manual recovery.
An interrupted write can leave observation files without a final manifest; a future
reader must require their referencing `COMPLETE` manifest rather than score those
files in isolation. The collector does not automatically delete orphan evidence.

Future research must retain the complete attempt manifest, including failed and
duplicate batches. It must not select only convenient complete cycles. Local files
and clock fields alone do not establish independent publication or on-time evidence.
No collector was run against the live market while developing these offline tests.

R190/R191/R220 use settled/trailing rates, while R223 tested holding across a
settlement using the previous settled rate. Those do not test M090's displayed-rate
revisions. R223's omitted reverse direction remains a distinct unregistered idea;
its exported events inherit future-exit availability selection and its earlier
off-cycle rows are observational controls, not an executable placebo policy. This
collector provides new observations rather than treating that archive as fresh.

## Primary sources inspected 2026-10-20

- [Current funding API](https://www.mexc.io/api-docs/futures/market-endpoints/get-funding-rate)
  and [ticker API](https://www.mexc.io/api-docs/futures/market-endpoints/get-ticker-contract-market-data):
  field definitions, public endpoints and distinct timestamp meanings.
- [Funding guide](https://www.mexc.com/support/article/mexc-futures-funding-rate-305432020820705280),
  page version 2026-06-01 13:48:50: pair-specific timing, fair-price funding notional
  and batch-processing ambiguity.
- [Funding mechanism](https://www.mexc.com/announcements/article/funding-rate-mechanism-13322295212313),
  page version 2024-09-06: displayed rates can change, cycles can change and timing
  close to settlement is uncertain. Sources and inspected versions are repeated
  in every capture intent/manifest.

## Frozen implementation

Collector SHA-256: `a7d68b0e3016c43040e14a9b55f41322e3dc189f3909453d33bd1e986dee60cd`.
This operational protocol is frozen before its first bounded live validation.
