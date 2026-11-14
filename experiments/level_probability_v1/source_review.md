# R329 source-only extraction: same-venue routed spot contract

This closes the already-collected finite source pass. The reviewer performed **zero network requests**, no market calculations, no account access and no tracked-file edits. All three raw SHA-256 identities and body lengths match the acquisition receipts. Three HTTP200 GETs received656,276bodybytes within the3GET/1.5MiB/768KiB-per-body/90s declaration; this allowance is exhausted. Acquisition began2026-10-26T10:04:46.559044UTC; the last response completed approximately10:05:19.661UTC. Exact individual response times remain in receipts. No retry, search or redirect.

## Material implications for M244

- Fixed **BTC_USDC and ETH_USDC are Coinbase-routed**, under the formal pair table updatedSeptember28,2026. Both list minimum1e-8base and price tick0.01USDC. The previously read public Standard routed taker scenario is5bp, not the native0fee schedule. Actual owner tier,fee asset/rounding and permission are unknown.
- Purchased spot can be collateral on Deribit, but only **settled** funds can buy spot. Unsettled derivative funds become spot-spendable after08UTCdailysettlement. Spot balances and derivative collateral share actual coin ownership; they cannot be counted twice. Account mode/haircuts/reservations remain open.
- Routed fills are asynchronous: acknowledgement is not fill. Nativepost-only/linked-order/conditional-stop assumptions do not carry over to routed pairs. Full CoinbaseL2 is served through Deribit, while routed public trades/candles are unavailable there. DirectCoinbasefeeds are possible source leads, not receiveddata.
- A public market display is not owner access. USDC_USDT(native) and USDT_USDC(routed) have different client-custody/access rules; replacing the fixedUSDCpair with a cheaperUSDTpair would change the problem.

## Received scope, alternatives and conflicts

All main content of three received pages was reviewed: spot-trading-venues guide,18August2026release (visibleupdateSeptember15), andSpotInstruments (visibleupdateSeptember28). The formal article's48asset-walletrows and56pairrows(44routed/12native) were scanned; the complete copyrighted tables are not copied. Only the fixedBTC/ETH_USDC facts are extracted. Navigation/templates and linked targets are unread. Nativezero-fee,makernative-orderfeatures,anddirectCoinbasetape alternatives remain enumerated with their constraints; they are not substitution recommendations or tested strategies.

A **source inconsistency remains**: the routingguide's illustrativeJSON namesUSDC_USDT withtrue routing flags, whereas the formalSpotInstrumentstable saysUSDC_USDTnative andUSDT_USDCrouted. Current typedspotmetadata, with sourceversion andeffective observation identity, must decide; the illustrativeexample cannot establish a pair's route. Likewise the general statement that spot shareshistoricalAPIs is qualified by the routedguide's explicitrejections oftrade-derivedhistory.

The guide specifies that both routeflags are omitted for native spot and everyotherkind. Omission can classify native only with explicitkind=spot on a supported instrumentquery andthissourcecontract. Notificationmetadata carriesonlyis_csr;FIXreference data has noflag. There is no basis for applying omission rules to arbitrary incomplete responses.

## Artifact and limits

`mechanisms.json` enumerates42receivedmechanical scopes, including weak alternatives,unrelatedrelease risk-fieldchanges andtwo sourcequalifications. They map to existingM244/YT26-04-DATED-CASH-CARRY; they are **not42newmethods**. CachedR327fee/API sources are referenced as previously read, not new acquisition or corpus coverage. RawHTML stays ignored; only compact paraphrases/provenance are review inputs.

No new same-venue portfolio was implemented,frozen or scored inR329. No marketquotes,currentmetadata,ownerfees,accountpermissions,settledbalances,fillcash,actualdelivery/exit/FX,margin/insurance/counterparty controls or independent positive expectedreturn were established. CompleteM244 strategy androll scope remain open; old frozenR327/R328 inputs/failures/results and historicalacquisition spend remain intact. Zero predictive trials,zero prospective strategy days,no activation or order authorization.
