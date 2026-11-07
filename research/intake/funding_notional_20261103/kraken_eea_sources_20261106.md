# Kraken EEA carry: the deployable-universe gap and current source qualifications

Accessed **2026-11-06 UTC**, by Codex; primary sources unless stated otherwise.
Linked economic lane: [R418](../../../experiments/kraken_carry_v1/PREREG.md),
canonical M487. M439 already proposed Kraken for execution; this extends its
missing spot/perp carry economics rather than claiming a new venue discovery.
The owner's report's OKX route does not exhaust documented EEA derivatives.

## Product/access facts, not an owner eligibility determination

- Kraken, [Overview of changes for EEA clients](https://support.kraken.com/articles/overview-of-changes-for-eea-clients), updated **2025-05-26**: EEA derivatives under MiFID II; onboarding conditions apply.
- Kraken, [EEA derivatives eligibility](https://support.kraken.com/articles/derivatives-eligibility-requirements-eea), updated **2025-12-10**: verified account, appropriateness and TIN requirements; provider Payward Europe Digital Solutions (CY) Limited, CySEC **342/17**. No account, credentials or personalized eligibility query was used.
- Kraken, [EEA contract specifications](https://support.kraken.com/articles/perpetual-contract-specifications-for-clients-in-the-eea), updated **2026-10-30**. Exact product description: “Below you can find detailed information on Kraken's linear multi-collateral perpetual and fixed maturity derivatives contracts.” The table contains PF_XBTUSD/PF_ETHUSD and dated FF contracts. BTC is called XBT in the API.
- Public metadata's `platformsPermitted` includes `europa`/`europa_crypto`; empty `countriesBanned` is not an owner's entitlement. Both named EEA **retail** schedules agree at initial **0.1** and maintenance **0.05** below the next USD-notional boundary **30,000,000**, in the saved current response. The top-level `retailMarginLevels` begins at **0.01/0.005** and must not stand in for the EEA schedule. Metadata is current, not a point-in-time historical schedule.

## Fees: a material stale-source problem in M439's old audit

Kraken Developers, [historical funding endpoint's shared OpenAPI](https://docs.kraken.com/api-reference/historical-funding-rates/historical-funding-rates.md), undated, saved in `kraken_eea_20261106/kraken_funding_docs.txt`, says under Fee Schedules:

> “**DEPRECATED** — Effective 2026-06-22, the fee values returned by these endpoints no longer reflect the fees actually charged on Futures trades.”

It directs account-specific rates to authenticated Spot `GetTradeVolume`. We did
not query it. Therefore an October retrieval of `/feeschedules` is not evidence
of an October fee entitlement. The API `AssetPairs` fee arrays are also **unused**.

Kraken, [Cross-platform fee tiers](https://support.kraken.com/articles/cross-platform-fee-tier-changes), updated **2026-10-30**, changes effective **2026-07-09**. Exact selected table rows (all fees in percent):

> “Tier 1 | $0+ | < $5M | N/A | 0.40 % | 0.80 % | 0.0200% | 0.0500%”
>
> “Tier 3 | $10K+ | ≥ $10M | 20k | 0.22 % | 0.38 % | 0.0150% | 0.0400%”
>
> “Tier 4 | $25K+ | ≥ $15M | 50k | 0.20 % | 0.35 % | 0.0125% | 0.0350%”
>
> “Tier 5 | $50K+ | ≥ $25M | 100k | 0.15 % | 0.30 % | 0.0100% | 0.0300%”

Columns: tier, spot trailing volume, futures trailing volume, assets on platform,
spot maker/taker, futures maker/taker. The page says the best qualifying measure
applies and assets are assessed point in time. R418 uses the **Tier 1 taker
ceiling** for every capital, not a claimed personalized or optimal tier. It does
not retroactively assert these were 2025 fees. The full-funding USD scenario
avoids non-USD conversions; no free borrowing, cash yield or earned tier upgrade
is assumed. Lower-fee versions are untested rather than disproved by this screen.

## Funding units, timing and the missing-hour treatment

The EEA specification cited above says:

> “absolute rate: The amount of funding an account will receive by maintaining a 1 contract unit short position for 1 hour.”
>
> “absolute funding payout = # of contracts * absolute funding rate * time elapsed within funding period without position alteration”

Historical endpoint documentation defines `timestamp` as “Start of the period to
which the funding rate applies.” R418 consumes **absolute `fundingRate`**, USD per
base unit per hour for these linear contracts, and a half-open holding window.
It neither multiplies a relative rate by a later mark nor treats an hourly rate
as an eight-hour payment. Specification/metadata give the current relative cap
as **±0.5% per hour** (`maxRelativeFundingRate=0.005`). Funding settles hourly;
positive rates credit the short. The current cap is an explicit assumption when
bounding historical missing periods, not proof of old venue rules.

The new saved v3 responses contain **8,929 rows per coin**, first **2025-10-30
09:00 UTC**, last **2026-11-06 18:00 UTC**. These are observed coverage counts,
not a promise of API retention. Five hourly periods per coin are missing inside
the fixed R418 window: **2025-12-04 09:00; 2026-02-04 12:00; 2026-02-13 18:00;
2026-05-09 06:00; 2026-10-30 03:00 UTC**. No rate is imputed. Each interval is
bounded in a conditional cap scenario using the maximum high of the public
reference-index hour before, during and after that gap. The index envelope and
current cap do not certify the omitted payments. Exact terminal net is unknown.

## Public inputs actually acquired, without measuring returns

Saved raw gzip bodies and UTC/hash receipts:
[`kraken_eea_20261106/`](kraken_eea_20261106/). `acquisition.json` and
`gap_acquisition.json` enumerate each exact URL and receive time; `coverage.json`
contains only counts/timestamps. Requests use Python urllib's normal default
User-Agent, no credentials or redirects. No forward loop or recorder ran.

- [Public instruments](https://futures.kraken.com/derivatives/api/v3/instruments), current metadata, **219** instruments. Only named BTC/ETH inputs enter R418.
- [Historical funding docs](https://docs.kraken.com/api-reference/historical-funding-rates/historical-funding-rates), undated: public v3 `historical-funding-rates?symbol=...`, successfully returned. Older repository acquisition used v4; no alternate endpoint was needed here.
- [Market candles docs](https://docs.kraken.com/api-reference/candles/market-candles), undated: bounded `from/to/count`; actual first hourly mark responses stop at **7,000** rows despite a higher requested count. A bounded second page finishes both series, **8,041** mark rows each, with no gaps. Daily trade opens: **336** rows per coin. No interpolation.
- [Spot OHLC API](https://docs.kraken.com/api-reference/spot-rest/get-ohlc-data), undated: actual XBT/USD and ETH/USD traded daily bars, **341** rows per response. The unfinished current bar and rows after the frozen end do not enter R418.
- Public [spot pair metadata](https://api.kraken.com/0/public/AssetPairs?pair=XBTUSD,ETHUSD), [spot depth](https://api.kraken.com/0/public/Depth?pair=XBTUSD&count=500) and [perp book](https://futures.kraken.com/derivatives/api/v3/orderbook?symbol=PF_XBTUSD): one bounded snapshot per named market, separate receipt clocks. API spot fee arrays and derivatives `feeScheduleUid` are not used as current fees.
- [Market analytics docs](https://docs.kraken.com/api-reference/analytics/market-analytics), undated: funding, basis, spreads/slippage and liquidation analytics exist in the specification. **Docs only**; no analytic values were fetched or admitted as settled funding. Liquidation analytics are a future data lead, not demonstrated alpha.

All stated new coverage numbers are reproducible from the raw inputs and saved
counts. The accumulated historical allowance is not reset: older reported use
is **7,757 requests / 229.85 MiB**, exact older bytes unavailable. Both new
acquisition files record exact incremental bytes and request counts; charge all
new market calls conservatively when reconciling the original **8,000 / 250 MiB**
ceilings. This batch is a small bounded public acquisition, not authorization for
bulk order-event history.

## Other EEA routes: keep data qualification separate

- Coinbase, Daniel Seifert and Vinayak Doraiswamy, [European futures launch](https://www.coinbase.com/blog/futures-contracts-europe), **2026-03-09**: France is explicitly in the launch list. Long-dated perpetual-style products and funding are described. **Announcement read; European product/API identity, public funding history, EEA fees and owner eligibility not qualified.** Do not substitute Coinbase International products for the European offering.
- One Trading, [instruments docs](https://docs.onetrading.com/rest/public/instruments), [funding history](https://docs.onetrading.com/futures/funding-rate-history), [legal notice](https://www.onetrading.com/legal-notice), undated: regulated venue and public interfaces documented. The first ordinary `api.onetrading.com/fast/v1/instruments` GET returned **HTTP 403** on this date; stop that host. No alternate host, retry or account.
- OKX EEA's prior **403** remains stopped; [its separate note](okx_eea_sources_20261106.md) and M484 remain authoritative for that blocker. These failures do not prove economic absence.

Read status: product/access/fee/funding/candle sources above **partial** (relevant
sections extracted); saved developer `.md` pages **full**; raw named market
responses **full capture**, numeric outcomes not inspected before the R418
freeze. No external source here supplies an audited carry performance record.
