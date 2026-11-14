# ADL on 2025-10-10/11 by venue, for R487 adlstress_v1 (M534)

Date: 2026-11-13. Agent: Kiro sub-agent, task-adl-stress-usde-flow FEAT-002. Ledger rows WS0027-WS0032.
Purpose: fix, before R487's freeze, which of the carry books' five venues (Hyperliquid, Binance, Gate, MEXC,
KuCoin) are documented to have run auto-deleveraging (ADL) on 2025-10-10/11, and each venue's ADL close-price rule.
No candle, price or funding value was read for this note.

Rule used (frozen in R487's PREREG): a venue is **documented** if a primary source (the venue itself, or a study
of the venue's own fill data) or two independent secondary sources state that it ran ADL on 2025-10-10/11.
Otherwise it is **not documented**. Not documented does not mean the venue ran no ADL.

## Prior record (not re-searched)
- SRC1112-010 (arXiv 2603.15963v2, partial read): Hyperliquid realized ADL notional $2.047bn on 2025-10-10 within
  21:16-21:21 UTC, from Hyperliquid fill data.
- SRC1112-011 (Hyperliquid docs, full): ADL ranks opposite-side users and closes them at the previous mark price.
- SRC1103-022 (Galaxy, 2025-10-15): "ADL kicked in on multiple venues"; re-read 2026-11-13 (WS0027): no venue is named
  as having run ADL.

## Per-venue evidence

| Venue | Ran ADL on 2025-10-10/11? | Evidence (read depth) | Class |
|---|---|---|---|
| Hyperliquid | Yes | arXiv 2603.15963v2 (SRC1112-010, partial) and Chitra, [Autodeleveraging: Impossibilities and Optimization, arXiv 2512.01112](https://arxiv.org/html/2512.01112) (HTML, keyword passes on "Binance", "October", "venue", the reference list; not a full read), both from Hyperliquid's public fill data: "at least 40 recorded ADL events on Hyperliquid in a 10-minute period" (Chitra). Galaxy names Hyperliquid's liquidations but not its ADL | **documented** (primary fill data, two studies) |
| Binance | Stated by one study | Chitra (arXiv 2512.01112): "on October 10, 2025 there were multiple ADL events that occurred over a short time window on both Hyperliquid and Binance. While the account-level data for Binance's usage of ADL is not public ..."; abstract: "Binance overutilized ADL far more than Hyperliquid". [Cointelegraph, 2025-11-03](https://cointelegraph.com/news/wintermute-boss-denies-plans-to-sue-binance-over-the-oct-10-crash) (full) only repeats an unconfirmed X claim about "a failure in Binance's auto-deleveraging risk mechanism"; that is a rumour, not a second source. Binance's own four statements of 2025-10-11..10-14 (CMS article API, full text, codes f3d5d97e, 0989d6c7, d9cb0d52, 3d45a1ab) do not mention ADL or deleveraging. | **not documented** (one secondary source; reported in scenario S1B) |
| Gate | Unknown | Gate announcement pages and `www.gate.com/apiw` return 403 here (not bypassed). No source found naming Gate | **not documented** |
| MEXC | Unknown | MEXC announcement pages return 403 here (not bypassed). The [MEXC ADL FAQ](https://www.mexc.com/support/article/faq-on-auto-deleveraging-adl-8127010829081) (full, updated 2026-02-17) gives the rule only. No source found naming MEXC | **not documented** |
| KuCoin | No announcement | KuCoin public announcements API, all 55 English items dated 2025-10-10 00:00 to 2025-10-15 00:00 UTC (`api.kucoin.com/api/v3/announcements`, titles read): no ADL, compensation or volatility notice | **not documented** (a primary null for announcements; ADL can run without a notice) |

## ADL close-price rule per venue
- Hyperliquid: closed at the previous mark price against the underwater user (SRC1112-011).
- MEXC: "executes direct trades with them at the bankruptcy price"; ranking = profit % x effective leverage (FAQ, full).
- Binance: the FAQ cited by both papers (`binance.com/en/support/faq/detail/360033525471`) returned an empty 202 body
  here (WAF); not read. Chitra describes Binance's queue as the PNL-leverage ranking.
- Gate, KuCoin: not read (403; KuCoin's help page is a script shell with no text).

For the bound the close price does not matter: R487 assumes the ADL'd leg's gain is lost to the bound (no offset)
and the naked leg runs from the day's best to its worst print.

## Search route and limits
- DuckDuckGo lite gave one result page (MEXC FAQ, crypto.news explainer), then a bot check on the next query (not
  bypassed). DuckDuckGo html returned no text; Bing web results were off-topic; Brave 429; Mojeek 403; Marginalia
  redirected (not followed). Wikipedia search: no page on the 2025 crash.
- [crypto.news explainer](https://crypto.news/adl-was-at-the-core-of-fridays-crypto-bloodbath/) (full): Hyperliquid
  founder defended ADL; Binance compensation for losses "not caused by market volatility"; no venue-level ADL list.
- CoinDesk 2025-10-11 Hyperliquid article (Chitra's reference [99]): HTTP 429, not read. The Block (reference
  [114]): 403, not read.

## Fixed for R487 (before the freeze)
- S1 ADL set (decides): {hyperliquid}.
- S1B (reported): {hyperliquid, binance}, adding the venue named by one study.
- S2 (reported, absolute worst case): all five venues.
- Per-account ADL incidence is not public keyless (Chitra: Binance account-level ADL data is not public).
