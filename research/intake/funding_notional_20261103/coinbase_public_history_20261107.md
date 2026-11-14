# Coinbase CDE: a separate official public funding-history route responds

Codex, **2026-11-07 UTC**, source qualification after R419's freeze/commit.
**Counts, schemas, identity and date bounds only. No rate statistic or PnL.**
The frozen [earlier source note](coinbase_eea_sources_20261106.md) remains exact:
the documented FairX history endpoint returned401. That does not describe all
public Coinbase data routes. No denied endpoint, header, login or host override
was retried to obtain the files below.

Coinbase's [Derivatives landing page](https://www.coinbase.com/derivatives)
(undated, accessed **2026-11-07**, partial navigation read) links Funding Rate
Data to the [public dashboard](https://www.coinbase.com/market-data/derivatives)
(undated, same access, partial read of its funding component and native public
requests). Selecting **Coinbase Derivatives** in the ordinary page exposes:

- [BTC / BIPZ30](https://www.coinbase.com/api/mda/v1/instruments/CDE/BIPZ30/funding?result_limit=2160): native anonymous Chromium request, **HTTP200**, **178,408 bytes**.
- [ETH / ETPZ30](https://www.coinbase.com/api/mda/v1/instruments/CDE/ETPZ30/funding?result_limit=2160): the same route with the named ETH code, ordinary urllib default UA, **HTTP200**, **178,375 bytes**; returned symbol checked.

[Raw files, receipts and counts](coinbase_public_history_20261107/) retain the
exact source bodies, hashes and clock dates. These are **two** small history
responses, **356,783 uncompressed client-read bytes**. No other history page or
asset was requested; the older accumulated historical allowance is not reset.
Browser qualification also fetched bounded website configuration/icon/consent
resources; these are not additional funding datasets. A range-button attempt
timed out; no claim that the full interactive dashboard was validated.

Each response has **2,160 rows**, with only `symbol`, `funding_rate` (a string)
and `event_time`; newest **2026-11-07T02:00:00Z**, oldest
**2026-08-09T02:00:00Z**. Timestamps are unique and descending. The inclusive
hour grid has **2,161 slots**, so one slot is absent in each returned slice.
This is source coverage, not a missing-rate estimate. Do not fill it with zero
or infer all closed-hour behavior from it. Pagination echoes limit2160/offset0;
older coverage, revision policy, retention and source guarantees are untested.

The webpage labels this CDE funding and binds BTC to BIPZ30. The ETH response
echoes ETPZ30; the names agree with the current public BIP/ETP product family.
Legacy-code continuity, fixing-time semantics and raw percentage/fraction scale
still require independent qualification. The body has **no historical mark
price** and proves neither a broker cash posting nor owner eligibility. The
official Help arithmetic contradictions in the earlier note remain unresolved.

**M488 stays PARTIAL.** History availability is now established for these two
bounded public slices; executable net carry and actual cash normalization are
not. R419's collector/code/36 inputs remain frozen and inactive. No new endpoint
is inserted into its allowlist. A successor economic test needs a new R-id,
explicit mark/cash/unit/missing-hour treatment, costs1x/2x/3x, a committed freeze
and its own single run. Collection alone supplies no prospective alpha days.
