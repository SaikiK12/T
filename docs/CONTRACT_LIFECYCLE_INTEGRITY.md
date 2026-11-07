# Contract lifecycle integrity: an asset is not a perpetual contract

Reviewed 2026-10-19. A token can retain economic lineage through a rebrand or swap while its exchange perpetual is closed, settled and replaced by a new instrument. Joining those contracts as one uninterrupted ticker can invent returns; dropping the old instrument can hide a forced settlement or survivorship loss.

## Code review and venue examples

The lab's archives and research panels identify instruments by symbol. `scripts/build_views.py` writes symbols and date bounds, but its metadata does not capture contract versions, open/cutoff/delist times or settlement terms. In `lab/pack.py`, a missing bar is commented as “a missing bar (halt, delisting) counts as no move”; the return is skipped when non-finite. This may be a deliberate portfolio convention, but it does not reproduce a venue's fair-price close settlement. Its historical frequency and PnL effect are unknown because no raw archive was available for this review.

Two official notices illustrate why token lineage and contract continuity must be separate. Binance announced RNDRUSDT perpetual auto-settlement/delisting on July 16, 2024, then opened RENDERUSDT perpetual on July 26; these are two venue contracts separated by a close and relaunch ([settlement notice](https://www.binance.com/en/support/announcement/detail/d1f2ae8d99b24439a7a900caa9bb6b3b), [new perpetual listing](https://www.binance.com/en/support/announcement/detail/3e0b3e47a09c4e7ea6963d467c1eec28)). MEXC's FTM-to-S token swap/rebrand also had its own FTMUSDT-M close-only and delisting schedule, with open positions settled at fair price ([swap and rebrand notice](https://www.mexc.com/announcements/article/mexc-will-support-the-fantom-ftm-token-swap-and-rebranding-to-sonic-s-17827791520794), [perpetual delisting notice](https://www.mexc.com/announcements/article/mexc-will-delist-ftm-usdt-m-perpetual-futures-january-10-17827791520897)). These examples establish venue mechanics, not an error in the lab's return results.

MEXC's current contract endpoint exposes fields such as quote/settlement coin, contract size, open time and state; its WebSocket contract-data stream publishes metadata updates ([contract info](https://www.mexc.io/api-docs/futures/market-endpoints/get-contract-info), [contract-data stream](https://www.mexc.co/api-docs/futures/websocket-api/contract-data)). Current metadata cannot reconstruct every historical version, so preserve snapshots prospectively and source archival announcements for backfill.

## Instrument registry and return rules

Keep two identifiers: an economic-asset lineage ID for research grouping and a venue-contract ID for prices, eligibility and account PnL. Version the venue record with exchange, product, symbol, base/quote/settlement coins, contract size and type, tick/quantity increments, listing/open time, close-only/cutoff time, last trading time, settlement price/source, delisting time and replacement mapping. Preserve source, observation time and confidence for every lifecycle field.

For an outcome window that crosses a contract closure, apply the documented close/settlement cash flow to open exposure, then treat a replacement contract as a new instrument with its own entry, costs and availability. Do not concatenate a new contract's candle series across the closure without an explicit, frozen roll rule. Keep delisted instruments in the point-in-time eligible universe and in coverage summaries; a missing archive row, a halted market, ineligibility and forced settlement are distinct states.

Useful integrity checks include conflicting metadata-version detection, no label spanning a contract boundary unless a registered roll rule exists, an explicit forced-settlement path for open exposure, no symbol reuse across unrelated assets, and point-in-time close-only/tradability checks. The instrument archive should be complete enough to explain both eligibility and every position exit.

## Synthetic settlement illustration

A hypothetical one-unit long entered at 100 and forcibly settled at fair price 80 loses 20 before fees. If a simulation instead turns the missing closing bar into an omitted return, the loss can disappear from measured PnL. This is arithmetic illustrating a failure mode, not evidence that a particular project row was missing or that its portfolio lost 20.

## Sources and limits

- Binance, [RNDRUSDT perpetual settlement/delisting](https://www.binance.com/en/support/announcement/detail/d1f2ae8d99b24439a7a900caa9bb6b3b) and [RENDERUSDT perpetual launch](https://www.binance.com/en/support/announcement/detail/3e0b3e47a09c4e7ea6963d467c1eec28).
- MEXC, [FTM-to-S token swap/rebrand](https://www.mexc.com/announcements/article/mexc-will-support-the-fantom-ftm-token-swap-and-rebranding-to-sonic-s-17827791520794) and [FTMUSDT-M delisting](https://www.mexc.com/announcements/article/mexc-will-delist-ftm-usdt-m-perpetual-futures-january-10-17827791520897).
- MEXC, [contract information](https://www.mexc.io/api-docs/futures/market-endpoints/get-contract-info) and [contract-data WebSocket](https://www.mexc.co/api-docs/futures/websocket-api/contract-data).
- Related code paths: [`lab/data.py`](../lab/data.py), [`scripts/build_views.py`](../scripts/build_views.py), and [`lab/pack.py`](../lab/pack.py).

This is a code review and a venue-source review, not a historical lifecycle audit: the checkout has no raw data archive, and no missing-return prevalence or portfolio impact was calculated. It does not modify the frozen portfolio lane.
