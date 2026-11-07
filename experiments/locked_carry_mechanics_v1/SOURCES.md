# R407 source scope and existing work

This engineering round extends M244; it is not a second carry queue or a new
predictive signal. R327/R328 already supply reciprocal-price cash accounting,
conditional exit conversion and a fixed-face cross-venue model in
`lab/inverse_cash.py` and `lab/dated_carry.py`. Those implementations are reused
or left unchanged. R407 adds a fixed-cash, fee-aware face selector with explicit
spot quantity rules, and a diagnosis of the later R406 rule. The M244 queue row
already reports R329's routing extraction; routing is not claimed as a new lead.

## Primary documentation read on 2026-11-05

- [Inverse Futures](https://support.deribit.com/hc/en-us/articles/31424938981533-Inverse-Futures),
  page updated September22: cash settlement in BTC/ETH, USD face/contract units,
  and delivery index/TWAP sections. BTC and ETH contract faces are10 and1USD.
  This supports units; it does not authenticate a particular book, order or fee.
- [Fees](https://support.deribit.com/hc/en-us/articles/25944746248989-Fees),
  page updated November5: standard/VIP table, spot-routing distinction, delivery
  table and exemptions. Weekly futures differ from other maturities. A public
  standard tier is an input scenario, not the owner's account fee. R407 requires
  explicit fee rates and debit bases; it does not infer them from a tier label.
- [Spot Instruments](https://support.deribit.com/hc/en-us/articles/31424969480093-Spot-Instruments),
  page updated September28: routing, account-dependent market visibility,
  settled-funds restriction and BTC_USDC/ETH_USDC specifications. These pairs
  are Coinbase-routed. Public visibility does not establish owner access.

Only these bounded sections were interpreted. No private endpoints, login,
market capture, complete venue rulebook review or fee-account verification.
Spot fee debit asset, actual account permissions, size/tick limits and rounding
must be bound before a prospective execution lane. No default rate is inferred.

## Mathematics and limits

For inverse fills with USD faces q_i and prices F_i, define
`A = sum(q_i/F_i)` and `Q = sum(q_i)`. After spot entry fees, let inventory be B.
Entry inverse fees consume `e*A` coin. Fee-covered sizing requires
`R = B-(1+e)*A >= 0`, on the declared face grid. Delivery at index P leaves
`Q*(1-d)/P + R` coin when the delivery fee is `d*Q/P` coin.

The continuous conversion is a reference only. If the spot sell fee is charged
in extra base, let `a=1/(1+f)`; otherwise `a=1`. If charged in received quote,
let `z=1-f`; otherwise `z=1`. The exit order is the rounded-down multiple of
spot step s in `a*(Q*(1-d)/P+R)`. Unused coin remains dust, not quote cash.

With explicit assumptions `exit_ratio >= rmin > 0` and `0 < P <= Pmax`, a
conservative gross quote bound is
`rmin * max(0, a*Q*(1-d) + min(0,(a*R-s)*Pmax))`.
Before reporting it, check the smallest exit order (at Pmax) against the base
minimum and the bound against the gross quote minimum. Then multiply by z and
add unspent entry quote cash. Without those assumptions/checks, no grid cash
floor is reported. Observed ratio/ceiling breaches are explicit.

The bounded independent mathematical review checked this inequality and found
the earlier continuous-exit/minimum-size flaw; the implementation now retains
dust and tests that case. The existing cash ledger separately posts fills,
daily realization and delivery. It shares the depth walker and supplied planned
spot inputs, so its check is not an independent end-to-end sizing audit.

All inputs in fixtures.json are invented. No distribution or probability is
estimated. Fee sensitivity keeps the same spot and inverse orders, chosen at3x
fees. No favorable resizing, entry-price half-spread as a future exit promise,
USD/quote parity default or unknown fee becomes zero. Bounds additionally assume
complete future fills at the declared conversion, venue survival, access and
applicable order limits. Future depth, maximum exit size, fee-asset rounding,
quote price ticks, exchange margin/liquidation paths and custody are unmodeled.
R406's frozen rule and its native journals/verdict remain unchanged.
