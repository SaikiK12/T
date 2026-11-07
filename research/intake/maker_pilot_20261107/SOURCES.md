# M474 maker pilot: restored source, not a new forward sample

The owner clarified2026-11-07 that1%per year is insufficient: seek substantial
net return with recurring independent opportunities and defensible risk. No
precise monthly target or permitted drawdown was supplied; none is invented.
Existing carry papers remain intact as benchmarks/measurements.

Original public Lighter capture was recorded on2026-10-29 by
`scripts/record_lighter_trades.py`. It timestamps quote receipts in local
microseconds; trade fields retain local receipt `t`, source millisecond `T`,
transaction microsecond `tx_us`, public trade id, maker side, quantity and
liquidation flag. These are actual prints, not candles or inferred trade signs.
The source has BBO only, no full price-level queue, private order or ack.
Recorders were not started here. No foreign process, original journal or
frozen file was changed.

Public owner archive: SaikiK12/T, commit2011de73202cd8733ad8ac029d461e5166c1d086
(2026-11-04). One GET at2026-11-07T16:17:53.828965UTC retrieved
https://raw.githubusercontent.com/SaikiK12/T/2011de73202cd8733ad8ac029d461e5166c1d086/chunk-00006.tar.gz
with HTTP200 and **1407398client bytes**. Archive Git blob
20840ac91cb16065e467094df96df8b48a202ce2 and all20member SHA256/size records
match the existing manifest. Exact receipt and member manifest are retained.
Only the5Lighter quote/trade files listed by R426 may be decoded for it.
The other15HFT/tape/rawtape originals are preserved opaque; this is no R367
read, full-day recovery, new on-time observation or reserved-sample access.

Counts/schema/time bounds only before R426's committed freeze:
- WTI:2803BBO updates,102trade rows.
- BRENTOIL:2806BBO updates,32trade rows.
- NATGAS:120BBO updates; trade file absent, not0trades.
- All quotes valid, on the currently declared price grid, no duplicate local
  quote timestamps. Market files cover approximately01:31..01:36UTC. The
  fixed coverage-only common scoring window is01:31:45..01:35:30UTC, after a
 30-second warm-up and with a5-second late-report buffer available. No prices,
 fill outcomes, maker markouts or PnL were summarized before registration.

Current Lighter contract metadata (not old fee/account entitlement), undated
API, accessed2026-11-07 at the exact clocks in `metadata/*.receipt.json`:
- https://mainnet.zklighter.elliot.ai/api/v1/orderBookDetails?market_id=145
- https://mainnet.zklighter.elliot.ai/api/v1/orderBookDetails?market_id=158
- https://mainnet.zklighter.elliot.ai/api/v1/orderBookDetails?market_id=159
All200,1739/1740/1742bytes. Symbol/id/status, lot/tick precision and minima
are checked against raw bodies. Market maker_fee/taker_fee strings are0,
which does not establish the owner's charged rate or account type. Current
lot/tick/minima remain hypothetical for these nine-day-older records.

Fee hypotheses come from the lab's retained primary extraction in R317
(2026-10-25, conditional source assumptions): regular Standard maker/taker0,
Premium0.4/2.8bp, not assumed owner fees. Original source URLs:
https://docs.lighter.xyz/trading/trading-fees.md and
https://apidocs.lighter.xyz/docs/account-types . Fresh web-reader attempts
on2026-11-07 failed/redirected to an unreadable docs API page; current full
wording was NOT newly verified. The saved extraction/read scope and today's
metadata are separate, never an account entitlement. Actual source-trader
fees differ by account and are not applied to our hypothetical account.

The current accumulated conservative proof is **7811calls/249746402bytes**
under the original8000calls/250MiB ceiling, including the PublicNode denial
and every worst-case response reservation. Actual incremental reads are
1412636bytes. No allowance reset, paid/large download or credentials.

The replay will remain conditional: clock alignment, placement/cancel/fill
acknowledgements, counterfactual queue/inclusion, historical profile/minima,
funding and France-owner access are not certified. No complete economic net,
monthly income, win probability or capacity follows from this short fragment.
