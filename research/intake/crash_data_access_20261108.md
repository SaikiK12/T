# M485 crash-data sources: documented availability, not acquired evidence

Reviewed2026-11-08. Public documentation only: no archive/data API call,
account, key, signed request, paid transfer, sample-file download, new
market-price statistic or reserved read. Original acquisition allowance
is unchanged. M485 stays PARTIAL. Costs1x/2x/3x: N/A, not zero.
Rendered illustrative sample rows were visible in the provider documentation;
those displayed values must not later be described as an unread holdout.
No sample file, order-book sweep, return or wallet-performance score was read.

The useful distinction is between a source advertising history and the
lab holding synchronized, correctly interpreted crash-day books. No
source below supplies that proof from a documentation page alone.

## Sources read and exact scope

All accessed2026-11-08. Undated means publication/version date not found.

| Primary source / author | Publication | Read scope / supported fact | Consequence |
|---|---|---|---|
| [Hyperliquid order-book dataset, CryptoHFTData](https://www.cryptohftdata.com/datasets/hyperliquid-orderbook-data) | Undated | Partial: coverage, source mapping, access and sample sections. Advertises history from2025-09-29, hourly Parquet and20levels/side. Exact access claim: “The sample is one real hourly Parquet file and needs no API key”. The fixed example is BTC,2026-09-02,12UTC. | Advertised history spans the crash; the anonymous sample is a DIFFERENT date. Full access is advertised as free with an API key; no account/key was created or used. Size and actual Oct10 completeness not verified. No changed URL/date to evade access. |
| [Known Data Gaps & Corrections, CryptoHFTData](https://www.cryptohftdata.com/docs/data-gaps-and-corrections) | Undated; describes September/October2026 audits | Partial: status and timestamp/correction sections. Exact policy: “A corrected file replaces the original file under the same object key”. The global release status says “Not yet deployed”. | Published history is revisable, not immutable point-in-time evidence. Freeze actual bytes/hash/version before measuring; verify symbol/date-specific corrections rather than assume a planned release is present. |
| [Reservoir overview, Hydromancer](https://docs.hydromancer.xyz/reservoir) | Undated | Full short overview, no linked archives read. Fills include liquidations/ADLs; books are20-level snapshots at1-minute cadence; S3 is requester pays. The overview describes an August2025 cutoff. | No-API-key is not no-account/no-cost: AWS credentials and transfer billing are not authorized. One-minute snapshots cannot establish queue/fills or subminute executable capacity. |
| [Hyperliquid archive, Hydromancer](https://docs.hydromancer.xyz/reservoir/hyperliquid) | Undated | Full short venue page. Advertises complete data from2025-07-28 and separate all-fills/liquidation/ADL paths. This precise start differs from the overview's August description. | Retain both descriptions; per-dataset coverage/objects remain unverified. Actual fills can inform one-leg event accounting, not replace synchronized L2. |
| [Fill schema, Hydromancer](https://docs.hydromancer.xyz/reservoir/schema-reference/fills) | Undated; states some columns begin2026-03-21 | Partial: schema/direction/subset sections. Advertises execution time, price/size, fee/token, starting position, crossed, liquidation and ADL fields. Liquidations/ADLs are subsets of all fills. | Deduplicate rather than sum subsets with all. Future columns cannot be assumed in2025 files. Wallet fill PnL is not complete net account return or independent trader identity. |
| [Quickstart, Tardis.dev](https://docs.tardis.dev/downloadable-csv-files/overview) | Undated | Partial: access and capture-order guidance. Exact rule: “Historical datasets for the first day of each month are available to download without a Data API key.” | This free rule does not grant2025-10-10; do not substitute Oct1 for the named crash or bypass entitlement. Tied event timestamps preserve capture row order. |
| [bookDepth clarification, Binance public-data repository / collaborator btechops](https://github.com/binance/binance-public-data/issues/447) | Maintainer response2026-05-12; later questions2026-10-28 | Partial: maintainer explanation and unresolved convention questions. Depth is supplied at percentage distances from mid, in coin/notional terms. | Aggregated percentage-band depth is not an exact price-level book for a taker sweep. UTC/side/cumulative conventions asked later were not resolved by the maintainer text read. Do not treat user comments as official answers. |

The Hugging Face search result for realjojo/hyperliquid-reservoir advertised
a crash-day fills extract. Direct opening failed inside the web tool;
that card, its advertised counts/size/license, and the file were **not
verified**. No mirror, file API or credential workaround was attempted.
Secondary vendor-comparison pages were search leads only; their coverage,
prices and praise were not promoted into primary evidence.

## Admission consequences before another replay

The most relevant lead is CryptoHFTData's advertised pre-crash L2 history,
subject to its access and quality conditions. Reservoir's classified fills
are complementary event-accounting leads. Neither is a profitable strategy
result or an acquired matched panel; an account/credential/paid or larger
pull still needs the owner's explicit scope under AGENTS.md.

Before a new frozen test: obtain exact permitted file identities, byte
sizes and source versions; qualify clocks/units and snapshot replacement
semantics; preserve empty-book resets and source gaps. A missing file or
HTTP denial is not a zero-event day. Validate complete daily coverage and
provider existence rules before interpreting an absent event subset as0.

Historical corrections, duplicated snapshots or missing empty-book states
could change apparent liquidity. These are source-admission concerns,
not a finding that this lab's older R417 files are wrong. Never use planned
corrections as if they already existed, sum full snapshots as deltas or
forward-fill liquidity across an unknown outage. Raw20-level depth also
cannot certify executable size beyond its visible ladder or own order path.

A one-leg replay must still retain loss before recovery, actual remaining
cash/positions, venue margin tiers and a separately sourced second leg.
R417's cash-accounting checks are reused, not retuned; original strategy
nulls, source denials and budgets remain. No hypothetical recovery or
constant-notional reset can create a gain. This research acquired no
missing books and does not claim M485 execution capacity is now proved.
