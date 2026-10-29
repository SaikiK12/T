# Edge leads after the registry map

> **Historical review — 2026-10-26.** This document describes an earlier checkout. Its counts, data coverage, calculations and recommendations have not been refreshed or revalidated. The [original revision](https://github.com/SaikiK12/T/blob/7d73c9540d7059190040207d2d6b666614b60541/reports/Edge%20leads%20after%20the%20registry%20map.md) retains the received text. Use the [current panel](../docs/PANEL.md), [live queue](../registry/methods.csv) and linked lane evidence for present decisions. Local links below have been made portable; unavailable source paths are labelled.

Written 2026-10-26 on `ccr-23562535-bd0mr3`. Registry facts come from the owner's head `c54872e` (149 rows, read from a snapshot). MEXC facts come from two public endpoints read once on 2026-10-26. They describe market structure and are not results. Nothing was downloaded, frozen, appended to a journal, or ordered.

## 1. Answer

- No edge in the registry has passed a holdout except funding carry at 1x (R191, t 2.07). It is small: +1.45% over 15 months with 25% of capital invested, roughly 1% a year on the capital at risk. It falls to t 1.14 at 2x.
- The model route and the equation route have both run on the same candles and funding data. R311 is INCONCLUSIVE. Its preselected policy loses at 2x (−$28.47) and 3x (−$157.45) over 2026-01-01..09-30. The blocker is missing inputs (R313: 7 of 144 eligible cost observations), not a missing formula.
- Statistical power is the binding constraint. A strategy with annual Sharpe S has t ≈ S·√T after T years, so t = 2 needs (2/S)² years: 4 years at S = 1, 1 year at S = 2. A 90-day forward decision can only show a Sharpe near 2 or more.
- One fact here changes a cost decision: MEXC fees are not one number (section 3).

## 2. Coverage map

| Family | Rounds | Result |
|---|---|---|
| Funding carry | R190, R191, R275–R288, R294 | CONFIRMED at 1x (R191). Venue replication 5 of 6 (R288). Not confirmed at 2x. Forward running (R278, R279, R294, R220). |
| Flow books, 72 h | R196–R218 | In-sample pass R197 (t 3.25; 3x still +11.3%/yr). Holdout R198 NULL (t 1.22, Sharpe 1.05). Book A replay gross was 49% TradFi (R216). Forward running. |
| Listings, delistings, announcements | R188, R189, R267–R272 | NULL. Holdout t −0.78; squeezes to +710%. |
| Liquidation and cascade fades | R206, R252, R255 | NULL. |
| Funding onsets, squeezes, settlement capture | R223, R273, R274 | NULL. |
| Limit-order entries | R193, R194, R170 | NULL. Attributed to adverse selection. |
| Two-sided quoting (market making) | E08 / R168 | Never tested. Blocked on a tick-level recorder. |
| Liquidity-provision reversal | R308 | NULL. This tests a reversal signal, not quoting. |
| Cross-sectional, time-series, pairs, PCA | R222, R230, R237, R238, R245, R250, R287, R303 | NULL. |
| Premia, options, flow proxies | R209, R210, R291, R292, R295, R307 | NULL. Korean premium and funding gap are NULL in MAP. |
| Chart and pattern rules | R243, R246, R248, R249, R251, R263, R306 | NULL. R263 read the spent window as exploratory (owner decision pending). |
| ML rankers | R299, R304, R305 | PARTIAL. R304 has a look-ahead; R332 refetch pending. |
| Equations | R310, R311 | INCONCLUSIVE. Inputs missing. |
| Atlas | R185, R192, R195 | In-sample gross only. 8.3M trials in R192 alone. |
| Stablecoin supply (DefiLlama) | none | Free data, untested. A flow proxy like the Coinbase premium (R210, NULL). Low prior. |

## 3. MEXC fees and what they change

Public contract detail (`contract.mexc.com/api/v1/contract/detail`, 1,179 contracts, all enabled), with spreads from `/contract/ticker`. Spread is in ticks, and the tick is in basis points of price:

| Maker / taker | Contracts | Median 24 h amount | Median spread (ticks) | Median tick (bp) |
|---|---:|---:|---:|---:|
| 1 bp / 4 bp | 1,047 | 127k | 3.0 | 1.62 |
| 0 / 0 | 97 | 394k | 1.0 | 2.02 |
| 0 / 2 bp | 18 | 2.3M | 2.0 | 0.37 |
| 0 / 1 bp | 6 | 11.9M | 2.5 | 0.04 |
| 4 / 10 bp | 11 | 136k | 12.0 | 12.48 |

- The "0 maker / 0.02% taker" figure in the MEXC articles we read is not the default. For most contracts the default is 1 bp maker and 4 bp taker.
- `OLD_SESSION_EDGES.md` (E08) reports maker 0 on 545 of 1,089 contracts. Today the endpoint shows maker 0 on 121 of 1,179. Either the schedule changed or the two sources measure different routes. S6 also records 6 bp on API orders, with the side not stated. R317 (`fee_routes_v1`) must settle the route before any cost convention is set.
- Taker round trip before impact: default group ≈ 2 × (4 + 1.5 × 1.62) ≈ 13 bp. Zero-fee group ≈ 2 × (0 + 0.5 × 2.02) ≈ 2 bp. The lowest tier in `engine.cost_matrix` (6 bp one way) is about right for the default group. For zero-fee contracts the tiers overstate cost several times over.
- The zero-fee group is not thin. Nine of the top 50 contracts by 24 h amount are zero-fee: ZEC, SILVER, XRP, ADA, ONDO, BTW, UNI, NGAS, BR. Some are TradFi or non-crypto names, so a crypto-only test has to filter them.
- Depth: the only depth file on the owner's head (`experiments/depth_quotes_v1/observations.jsonl.gz`, 288 rows) has source timestamps spanning about 54 seconds. There is no depth time series yet.

## 4. Market making: the equation

A passive quote at the touch earns the half-spread and pays the maker fee. Per fill, the margin is

margin = half-spread − maker fee

and quoting is positive only if the average adverse move per fill, E[Δmid | fill, holding horizon], is smaller than that margin.

- Default group: 1.5 × 1.62 − 1.0 = 1.4 bp per fill.
- Zero-fee group: 0.5 × 2.02 − 0 = 1.0 bp per fill.
- On BTC and ETH the whole spread is about 0.05 bp and 0.17 bp (4 ticks each), which is far below any fee.

This is the one non-fee source in the old list that has not been tested. It needs a tick-level L1 and trade recorder, which is a continuous process and needs owner approval (E08). Prior: low. R170, R193 and R194 were NULL and attributed to adverse selection.

## 5. Ranked leads

1. **Carry at 1x, forward only.** Keep R278, R279, R294 and R220 running. It is the only frozen holdout pass, and it is small. No new family.
2. **Zero-fee variant of the flow family, crypto only.** It tests the cost lever on the family with the strongest in-sample evidence (R197). One frozen variant, coin list fixed from the endpoint before the first tick, 1 trial. The verdict is slow: at the holdout Sharpe (about 1), t ≈ 1 after one year, so this is a multi-year test. It is cheap and clean, but it is not a fast answer.
3. **Market making on zero-fee contracts.** Only if the owner approves a tick-level recorder. Gate: measured adverse move per fill below 1.0 bp, forward only.
4. **Model routes (R227 Kronos, mlrank_v3).** Do not run them on the spent window. Their inputs are the candles the atlas already mined. If run at all: forward only, weights hashed, one variant.
5. **Equations.** No new formula until the inputs exist: executable quotes, fair funding and fees (R313, R322–R328, all PARTIAL).

## 6. What was not done

- No new market statistic. Every historical window through 2026-09 has already been read by at least one round, and the holdout policy is undecided (R263). A new test there would be exploratory and would not count.
- No download, freeze, registry row, forward lane, or room claim of an R-id. The owner asked that forward journals not be written from another checkout.
- Each endpoint was read once. The reads describe structure; they test nothing.

## 7. Decisions for the owner

1. Stop adding families. Spend the forward clock on carry and the flow books.
2. Settle the MEXC route (web or API) in R317 before changing `engine.cost_matrix` or FOUNDATION's flat 0.002.
3. Approve or decline the zero-fee flow variant (1 trial, forward, owner's journal).
4. Approve or decline a tick-level recorder for the market-making gate.
5. Keep Kronos and mlrank_v3 out of the spent window.

## 8. Dates and reproduction

- Forward clock from 2026-10-20: 90 on-time days → 2027-01-18; 182 → 2027-04-20; 365 → 2027-10-20. The counting convention still needs confirming.
- Fee groups from the public endpoint:

```bash
curl -sS https://contract.mexc.com/api/v1/contract/detail -o contract_detail.json
python3 -c "import json,collections; d=json.load(open('contract_detail.json'))['data']; print(collections.Counter((c['makerFeeRate'], c['takerFeeRate']) for c in d))"
```
