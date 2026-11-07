# M449: public WTI/Brent funding history exists; cash units remain unqualified

Nov7follow-up: the official [historical-funding issue182](https://github.com/elliottech/lighter-python/issues/182)
still has only public-user questions and no maintainer cash-unit answer in
the retained thread. Exact body/comment identities and read scopes are in
[R427's source intake](../lighter_contract_20261107/SOURCES.md). R427 supports
the recorded trade-role assignment; it does not qualify funding cash.
The latest conservative acquisition proof is now7819calls/251220970bytes,
including the whole tiny static-document cap; the730833market bytes below
are unchanged, with no new market source or allowance renewal.

This is **counts/schema/identity/time qualification only**, acquired before
any new financial PREREG. No rate magnitude, mean, sign distribution,
cross-venue spread, price, return or PnL was summarized. M449 remains
UNTESTED. Historical API availability neither supplies prospectively
recorded days nor waives the method's existing minimum observation rule.

The one-shot [acquisition](acquisition.json) records exact URLs, timestamps,
hashes, byte limits and read scope. Raw responses and individual receipts are
preserved beside this note. Four ordinary unauthenticated GETs, no redirect,
default Python urllib identity, completed2026-11-07T18:23:52..18:23:53UTC;
all HTTP200. Publication date: undated live historical APIs, not a versioned
point-in-time vintage.

| Organization / symbol | Public URL | Rows / unique timestamps | Oldest..newest returned | Client bytes |
|---|---|---:|---|---:|
|Lighter / WTI145|[fundings](https://mainnet.zklighter.elliot.ai/api/v1/fundings?market_id=145&resolution=1h&start_timestamp=1792800000&end_timestamp=1794009600&count_back=0)|335/335|2026-10-24T01..2026-11-06T23UTC|27342|
|Lighter / BRENTOIL159|[fundings](https://mainnet.zklighter.elliot.ai/api/v1/fundings?market_id=159&resolution=1h&start_timestamp=1792800000&end_timestamp=1794009600&count_back=0)|335/335|2026-10-24T01..2026-11-06T23UTC|27292|
|Kraken / PF_WTIOILUSD|[historical-funding-rates](https://futures.kraken.com/derivatives/api/v3/historical-funding-rates?symbol=PF_WTIOILUSD)|3918/3918|2026-05-28T12..2026-11-07T18UTC|454711|
|Kraken / PF_BRENTOILUSD|[historical-funding-rates](https://futures.kraken.com/derivatives/api/v3/historical-funding-rates?symbol=PF_BRENTOILUSD)|1902/1902|2026-08-20T12..2026-11-07T18UTC|221488|

The Lighter query bounds were2026-10-24T00..2026-11-07T00UTC. The oldest
returned hour is later than the requested lower bound. Missing endpoints
were not imputed0; interior grid/cash alignment has not been measured.
Lighter fields are timestamp, value, rate and direction. Kraken fields are
timestamp, fundingRate and relativeFundingRate. Their existence and types
do not establish conversion between rate/value or a cash payment.

## Primary documentation, exact read scope

- **Lighter SDK**, [CandlestickApi.md](https://github.com/elliottech/lighter-python/blob/main/docs/CandlestickApi.md),
  undated, accessed2026-11-07, **partial** endpoint/fundings/authorization
  sections: "Get fundings. Maximum 750 fundings will be returned per call."
  Its prose also says
  count_back0returns all; this must not be interpreted as overriding the cap.
- **Lighter SDK**, [Funding.md](https://github.com/elliottech/lighter-python/blob/main/docs/Funding.md),
  undated, accessed2026-11-07, **full** small model document: timestamp is int;
  value/rate/direction are str. Description cells are empty. Cash unit,
  percent/decimal scale and payer direction are **not found there**.
- **Lighter agent kit**, [schemas-read.md](https://github.com/elliottech/lighter-agent-kit/blob/main/references/schemas-read.md),
  undated, accessed2026-11-07, **partial** market-funding section: "/api/v1/funding-rates"
  is described as an "8-hour-equivalent" cross-exchange value. That endpoint
  differs from the acquired historical `/fundings`; its normalization cannot
  be transferred to the latter without a source contract. The same document
  has an unresolved trade-side conflict, recorded in R426's source supplement.
- **Kraken**, [EEA linear multi-collateral specifications](https://support.kraken.com/articles/perpetual-contract-specifications-for-clients-in-the-eea),
  updated2026-10-30, accessed2026-11-07, **partial** title, geographic notice,
  table heading and both oil rows. The rows give first trading **28-Sep-2026**
  for both PF_WTIOILUSD and PF_BRENTOILUSD, min lot0.1, tick0.001 and max
  position30000base; classC/D respectively, max pro leverage10x. These are
  specifications, not proposed leverage or proof of the owner's entitlement.
  The older global API timestamps above are NOT an EEA-eligible launch date.
  The geographic notice says: "This article is for clients located in the"
  European Economic Area. Individual French access remains unconfirmed.

## Binding gaps before a financial test

Lighter historical cash units and period/payer sign need primary qualification
against a distinct trusted field/cash witness. Same-symbol oil exposures can
have different Pyth/index, expiry/roll, closed-market or oracle policies;
matching names do not prove a hedge. EEA launch dates, actual account fees,
collateral denomination, margin/liquidation and France eligibility remain
binding. No prices, synchronized books or executable exit have been acquired
for this scope. No net return, high-yield claim or test admission follows.

The original accumulated allowance is retained: **7815calls/250926054bytes**
as a conservative upper charge, including the inherited reservations and
these four capped requests. Actual new bytes730833. No grant reset, paid
source, large download, account, credential, native tick or recorder.
