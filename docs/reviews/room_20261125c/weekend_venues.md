# Weekend (Sat/Sun) daily option expiries across crypto venues

Research reader, room 20261125c. Snapshot taken 2026-11-25 20:27 UTC, from a session that is geo-blocked from several venues (see section 0). Quotes are exact where the page was readable; "snippet" means a search-result summary I could not open on the primary page.

## 0. What I could and could not reach

| Venue | Public API from here | Primary doc read |
|---|---|---|
| Deribit | Yes, HTTP 200 (`deribit.com/api/v2/public/*`) | Fee KB page 403, not read |
| OKX | Yes, HTTP 200 (`okx.com/api/v5/public/opt-summary`) | Expiry help page read; fee page had no options rows |
| Aevo | Yes, HTTP 200 (`api.aevo.xyz/markets`) | API reference 404, not read |
| Bybit | **Blocked**, HTTP 403 "CloudFront distribution is configured to block access from your country" | Tickers doc read; FAQ and fee pages HTTP 503 |
| Binance | **Blocked**, HTTP 451 "Service unavailable from a restricted location" | Mark-price doc read only in search snippet |
| Derive | **Unreachable**: `api.lyra.finance` HTTP 521/522, `api.derive.xyz` HTTP 404 | Instrument-names page read; fee page 404 / 503 |
| CME | **Blocked**, HTTP 403 "This IP address is blocked due to suspected web scraping"; guessed endpoint 404 | 24/7 page timed out; CME FAQ read in snippet only |
| AMF lists | Yes (web) | Bybit EU GmbH page read; blacklist page read; Bybit blacklist PDF unreadable |

## 1. Who lists Saturday and Sunday daily expiries (checked 2026-11-25)

| Venue | Sat/Sun daily expiries seen | Underlyings with weekend dailies | Expiry time | Index / settlement | Evidence |
|---|---|---|---|---|---|
| Deribit | Yes: Sat 28 Nov, Sun 29 Nov, 08:00 UTC | BTC (coin and USDC), ETH (coin and USDC) | 08:00 UTC | `price_index` = `btc_usd`, `eth_usd` (API field) | API `get_instruments`: Sat 1 and Sun 1 expiry date in USDC lists; BTC coin list 46 Sat and 44 Sun instruments |
| Deribit USDC alts | **No** (5 expiries each, all Thu/Fri) | SOL, XRP, HYPE, AVAX, TRX (`_USDC`) | 08:00 UTC | `price_index` `sol_usdc` etc. | API `get_instruments?currency=USDC`; TRX rejected in coin query ("invalid currency") |
| OKX | Yes: Sat 28 Nov, Sun 29 Nov (BTC-USD, ETH-USD); Sat 28 Nov only (SOL-USD_UM) | BTC, ETH, SOL | 08:00 UTC | not checked | Quote: "Daily options expire every day at 08:00 UTC." (okx.com/ar-ae/help/vii-introduction-to-options-expiration-dates) |
| Aevo | Yes: Sat 28 Nov, Sun 29 Nov (BTC, ETH); none for SOL | BTC, ETH | 08:00 UTC (from expiry timestamps) | not checked | API field `expiry` in nanoseconds, all 08:00Z |
| Bybit | Stated by FAQ (snippet): daily at 8AM UTC; weekend listing **not verified** | probably BTC, ETH, SOL (not verified) | 08:00 UTC | BTC spot index (fee guide snippet) | Snippet: "Daily Expirations: Daily, Bi-Daily, Tri-Daily, listed daily at 8AM UTC" (bybit.com FAQ-Options-Trading) |
| Binance | Stated by listing rules (snippet): daily at 08:00 UTC; weekend listing **not verified** | BTC, ETH, SOL (per announcements) | 08:00 UTC | not checked | Snippet: "daily options expire at 08:00 UTC on day of expiry" (binance.com listing rules) |
| Derive | Unknown (API unreachable) | unknown | 08:00 UTC by default | not checked | Quote: "Options settle at 08:00 UTC on that date by default; some markets configure a different settlement time" (docs.derive.xyz/trading/instrument-names) |
| CME | **No weekend expiries** (Bitcoin options expire on weekdays only, Fridays for weeklies) | BTC, ETH | Deliverable weeklies 4pm London; BFF 4pm New York | BRR-type reference rate | CME FAQ (snippet): "Cryptocurrency futures and options trade continuously on Globex." |

**CME premise check.** The lab's note says Bitcoin weekly options do not trade on weekends. That is **not confirmed**. CME's public material says crypto futures and options trade 24/7 on Globex (snippet from cmegroup.com FAQ and "24/7 Crypto Futures and Options Trading" page). What CME does not do is list weekend *expiries*: its weekly options expire on Fridays. So the right statement is "trade 24/7, expire on weekdays". I could not open the CME page itself.

## 2. Public endpoints called once: expiries and ATM mark IV

Snapshot 2026-11-25 20:27 UTC. ATM = listed strike nearest the underlying (or forward); IV = average of call and put mark IV when both listed.

### Endpoints used

| Venue | Endpoint called | Status | Fields used |
|---|---|---|---|
| Deribit instruments | `GET https://www.deribit.com/api/v2/public/get_instruments?currency=BTC&kind=option&expired=false` | 200 | `instrument_name`, `expiration_timestamp`, `price_index`, `maker_commission`, `taker_commission` |
| Deribit marks | `GET https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=option` | 200 | `mark_iv`, `underlying_price` |
| OKX | `GET https://www.okx.com/api/v5/public/opt-summary?uly=BTC-USD` | 200 | `instId`, `markVol`, `fwdPx` (SOL uses `uly=SOL-USD`, instId `SOL-USD_UM-YYMMDD-K-C`) |
| Aevo | `GET https://api.aevo.xyz/markets?asset=BTC&instrument_type=OPTION` | 200 | `expiry` (ns), `strike`, `forward_price`, `greeks.iv` |
| Bybit | `GET https://api.bybit.com/v5/market/tickers?category=option&baseCoin=BTC` | 403 (country block) | (doc: `markIv`, `underlyingPrice`; no expiry field, expiry is in symbol) |
| Binance | `GET https://eapi.binance.com/eapi/v1/mark` | 451 | (doc via snippet: `markIV`, symbol `BTC-260326-70000-C`) |
| Derive | `GET https://api.lyra.finance/public/get_all_live_instruments` (and POST variant) | 521 / 522; `api.derive.xyz` 404 | not reached |
| CME | `cmegroup.com` home and guessed endpoints | 403 / 404 | not reached |

### BTC (Deribit coin-settled, OKX, Aevo)

| Expiry (UTC 08:00) | Weekday | Hours to expiry | Deribit ATM mark IV (K=60000) | OKX ATM markVol (K=60000) | Aevo ATM IV (K=60000) |
|---|---|---|---|---|---|
| 26 Nov 2026 | Thu | 11.6 | 43.6% | 42.0% | 43.6% |
| 27 Nov 2026 | Fri | 35.5 | 48.8% | 48.7% | 48.8% |
| **28 Nov 2026** | **Sat** | 59.5 | **52.0%** | 51.6% | 52.0% |
| **29 Nov 2026** | **Sun** | 83.5 | **47.5%** | 47.2% | 47.5% |
| 4 Dec 2026 | Fri | 203.6 | 53.4% | 53.1% | 53.4% |
| 11 Dec 2026 | Fri | 371.6 | not read | 54.7% | 55.0% |

Underlying: Deribit 59,901 to 59,926; OKX forward about 59,920 to 59,960.

### ETH (Deribit coin-settled, OKX, Aevo)

| Expiry (UTC 08:00) | Weekday | Hours | Deribit ATM mark IV | OKX ATM markVol | Aevo ATM IV |
|---|---|---|---|---|---|
| 26 Nov | Thu | 11.6 | 57.4% (K=1680) | 54.6% (K=1690) | 57.4% (K=1680) |
| 27 Nov | Fri | 35.5 | 59.1% (K=1680) | 57.3% (K=1690) | 59.1% |
| **28 Nov** | **Sat** | 59.5 | **60.8%** (K=1680) | 59.5% (K=1690) | 60.8% |
| **29 Nov** | **Sun** | 83.5 | **57.8%** (K=1680) | 56.8% (K=1690) | 57.8% |
| 4 Dec | Fri | 203.6 | 65.4% (K=1700) | 65.1% (K=1700) | 65.4% |

Underlying about 1,684. OKX picked K=1690 as nearest listed strike to forward 1,684.

### SOL (Deribit USDC, OKX, Aevo)

| Expiry | Weekday | Hours | Deribit `_USDC` ATM mark IV (K=70) | OKX `SOL-USD_UM` ATM markVol | Aevo ATM IV |
|---|---|---|---|---|---|
| 26 Nov | Thu | 11.6 | not in my output | 82.9% | 87.0% |
| 27 Nov | Fri | 35.5 | 79.1% | 79.0% | 79.1% |
| **28 Nov** | **Sat** | 59.5 | none listed | **80.8%** (only OKX has Sat) | none listed |
| 4 Dec | Fri | 203.6 | 81.1% | not listed | 81.0% |
| 25 Dec | Fri | 707.5 | not read | not listed | 77.0% |

Deribit USDC alt ATM IVs for XRP, HYPE, AVAX and TRX (Thu/Fri expiries only): XRP 72.3% Thu, 76.5% Fri; HYPE 78.4% Thu, 86.1% Fri; AVAX 75.8% Thu, 79.1% Fri; TRX 21.4% Thu, 26.8% Fri.

### Caveats on section 2

- Snapshot only. One mark per expiry cannot show whether Saturday is rich versus Friday; that needs a time series of the same ATM and the same time of day.
- Aevo ATM IVs equal Deribit's to 0.1 vol point on every BTC and ETH expiry. Those are not two independent quotes; Aevo's marks look anchored to the same surface.
- OKX is 1 to 3 vol points below Deribit on BTC at most expiries; the timestamps are not synced.
- Deribit's Saturday BTC IV (52.0%) is above Friday (48.8%) and Sunday (47.5%). That is a single-snapshot observation, not evidence of a weekend premium.

## 3. Can a French retail client trade these options? (MiCA / AMF / MiFID)

Key point first: MiCA covers crypto-assets and their services. Options on crypto are generally financial instruments under MiFID II, so a MiCA CASP licence is not the test. The test is whether the venue (or its EU entity) holds an investment-firm authorisation for derivatives that it passports into France. Source: ESMA material via search snippets (ESMA primary pages not opened). ESMA's stablecoin-settled derivatives question is still open.

| Venue | French retail options access | Evidence |
|---|---|---|
| Deribit | **Unclear, no authorisation found.** Operator is Deribit FZE (Dubai). VARA licence described as covering derivatives only for "qualified and institutional investors" (snippet). | No MiCA or AMF entry found. AMF blacklist page does not list Deribit. Terms for French residents not read (page unavailable). |
| Bybit | **Unclear, probably no for options.** Bybit EU GmbH is passported into France, but its authorised services listed on the AMF page are custody, crypto-fiat exchange, crypto-crypto exchange, placement, and transfer. Options are not among them. | AMF page: "Statut : « Agréé MICA » (PSCA)... « N/A - Passeport »"; "Autorité d'origine et date : Autriche / 28/05/2025". "Accès à la France : Oui... en vertu de la libre prestation de services." The Bybit platform: "placée depuis le 20 mai 2022 sur liste noire AMF" (snippet of AMF PDF; the PDF itself was unreadable). |
| OKX | **Unclear.** OKX France Technology Company SAS appears on the AMF list of **deregistered** PSAN (E2023-106, registered 12/12/2023). Reason not confirmed. | Snippet from AMF "Liste des PSAN radiés". No options authorisation found. |
| Binance | **Unclear.** Secondary blog lists Binance among PSAN still awaiting authorisation mid-2026. | Snippet from a blog, not the AMF site. Not verified. |
| Derive | **Unclear, no evidence either way.** | Not on the AMF blacklist page; no licence found; API unreachable. |
| Aevo | **Unclear, no evidence either way.** | Not on the AMF blacklist page; no licence found. |
| CME | **Not a French retail route.** CME is US-regulated; access is via a broker (not checked). | Not checked. |

AMF blacklist page (protectepargne.amf-france.org, crypto-actifs): none of Bybit, OKX, Deribit, Binance, Derive, Aevo is listed. The page says: "Les acteurs mentionnés dans cette liste n'ont pas le droit de proposer leurs services en France." A missing name is not proof of authorisation.

For the owner: nothing in this check shows a MiFID-authorised route for retail crypto options from these venues. The venue's own FR terms were not readable, so this stays "unclear".

## 4. Option fees (taker / maker / cap)

All rows below are unverified against the primary fee page unless marked "official". Several primary fee pages were blocked.

| Venue | Taker / maker (options) | Cap on fee | Source and status |
|---|---|---|---|
| Deribit | Fee = 0.03% of underlying index per contract, both sides (third-party reviews) | 12.5% of option price (third-party) | Deribit KB: "fees vary per product and are calculated as a percentage of the underlying asset of the contract" (snippet). Primary fee page 403. |
| Bybit | Not obtained (fee page 503) | Not obtained | Snippet: "Daily options carry no delivery fee" (Bybit fee guide). |
| OKX | Not obtained from primary (worked example in notice uses 0.03% taker) | **7% of premium** per OKX notice (snippet), which conflicts with the 12.5% figure seen elsewhere | OKX notice "Options VIP Trading Volume Calculation Adjustment": cap "applies to the lower of the percentage-of-notional fee and 7% of the premium" (snippet). |
| Binance | 2022 FAQ: min(0.03% of index, 10% of premium). 2024 Regular maker 0.030%, taker 0.0300%. July 2025 announcement: Regular maker 0.0240% (promo 20% off makes both 0.024%). | 2022 FAQ: 10% of premium. Exercise fee 0.015% of settlement, capped at 10% of intrinsic. | Binance FAQ and 2025 announcement (snippets). Current schedule not checked. |
| Derive | Not obtained (fee page 404/503) | Not obtained | Not reached. |
| Aevo | Maker 0.03%, taker 0.05% (review sites, 2026 and 2022-era) | 12.5% of option price (review sites). Daily options exempt from settlement fee. | Third-party reviews only; Aevo docs 404. |
| CME | Not checked | Not checked | Blocked. |

Note: the cap figures conflict (12.5% on Deribit and Aevo, 10% on Binance's 2022 FAQ, 7% on OKX). Only the OKX figure comes from a venue notice; the others are secondary.

## 5. What I could not do, in one list

- Bybit and Binance live option tickers (geo-blocked). Weekend expiries for both are unverified.
- Derive API and fee page (unreachable). Its expiry rule is from its docs; weekend listings unknown.
- CME pages and API (blocked; the CME 24/7 claim is from a search snippet).
- Official Deribit, OKX, Binance, Aevo fee pages (blocked or 404; figures are snippets or secondary).
- The AMF Bybit blacklist PDF (binary-only in this session).
- French residents' terms for each venue (not readable).

## 6. Where this points

- Weekend dailies are visible now on Deribit (BTC and ETH coin/USDC), OKX (BTC, ETH; SOL Saturday only) and Aevo (BTC and ETH). Bybit and Binance are very likely to have them but I could not confirm.
- The alts on Deribit's USDC list (SOL, XRP, HYPE, AVAX, TRX) have no weekend dailies on the listing today. That is a candidate gap to check for a later date, but it is a listing fact, not a pricing fact.
- Weekend IV in a single snapshot is about equal to weekdays on BTC and ETH. The lab's question needs a time series, not this table.
- For the owner, the French route looks closed or unclear for all six names. A MiFID-authorised broker is the thing to look for, not a MiCA CASP.

## Sources (quoted or read)

- Deribit public API: `https://www.deribit.com/api/v2/public/get_instruments`, `get_book_summary_by_currency` (200)
- OKX opt-summary: `https://www.okx.com/api/v5/public/opt-summary?uly=BTC-USD` (200); expiry rule: `https://www.okx.com/ar-ae/help/vii-introduction-to-options-expiration-dates`
- Aevo markets: `https://api.aevo.xyz/markets?asset=BTC&instrument_type=OPTION` (200)
- Bybit tickers doc: `https://bybit-exchange.github.io/docs/v5/market/tickers`
- Bybit FAQ (snippet): `https://www.bybit.com/en-US/help-center/article/FAQ-Options-Trading`
- Binance mark price doc (snippet): `https://developers.binance.com/docs/derivatives/option/market-data/Option-Mark-Price`
- Derive instrument names: `https://docs.derive.xyz/trading/instrument-names`
- CME FAQ (snippet): `https://www.cmegroup.com/cryptooptionsfaq`
- AMF PSCA Bybit EU GmbH: `https://www.amf-france.org/fr/espace-epargnants/proteger-son-epargne/listes-blanches/psca/bybit-eu-gmbh`
- AMF blacklist crypto: `https://protectepargne.amf-france.org/acteurs-listes-noires/crypto-actifs`
- Deribit fee KB (blocked): `https://support.deribit.com/hc/en-us/articles/25944746248989`

Scratch probe files (raw API responses) were written to the session scratchpad and deleted afterwards. Nothing else was written in the repo.
