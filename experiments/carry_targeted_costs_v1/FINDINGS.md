# R402 — PARTIAL: current source units and two conditional entry-book costs

The sole frozen attempt ran on2026-11-04 after publication at31d3ce9 and
[off-host BEGIN](https://github.com/SaikiK12/T/issues/7#issuecomment-6626403579).
Protocol SHA256:379c0230dd0bac8c62397c00031b4a09040396a9ed5c78a14882f94ff5be62e9.
All frozen inputs verified before and after capture. Predictive trials:0;
prospective paper days:0. No historical returns, labels, strategy ranking,
fills, owner fees or net PnL were measured.

## Actual source result

- 19 new GETs:18 complete HTTP200 responses, then one timeout without a reported
  HTTP status. No denial inferred from that missing status.
- Metadata qualified for5MEXC and3KuCoin contracts; depth for4MEXC and3KuCoin.
- 28 original cohort rows remain. Two have both required books and contract
  conventions: BLEND and CASHCAT.26remain unscored under the fixed rules. Other
  declared venues remain explicit and unpriced.
- The 19th request, MEXC CP_USDT depth, retained no body, reported an incomplete
  response and reaped its owned worker. Total elapsed including cleanup was
  4011482545ns, exceeding the fixed4000000000ns reservation by11482545ns.
  The journal charged the overrun and blocked further dispatch. No retry,
  widened deadline, restarted budget, alternate host or substitute was used.

R401's1request/2097152bytes remains in this same accumulated scope. R402 reserves
19×32768bytes, including uncertain tails: cumulative20requests and2719744bytes
charged. No pending reservation. The nominal remaining2523136bytes is **blocked
by the recorded overrun**, not a reusable or renewed grant. This protocol's
attempt is consumed. Do not remove guards or resume it with a different path.

## Conditional arithmetic, not execution or return

Both pairs use common base lot10. Quantities were rounded down before walking
the shown books:20260BLEND and9070CASHCAT, with at most1000USDT MID notional on
each leg. Actual ask consideration can exceed1000USDT. Each side is compared
to its own snapshot mid; cross-venue price basis is not counted as profit.

| Fixed cohort key | Buy MEXC / sell KuCoin | Buy KuCoin / sell MEXC |
|---|---:|---:|
| BLEND |15.3360bp|18.0409bp|
| CASHCAT |10.4434bp|8.6749bp|

These costs cover only entry spread and shown depth, normalized by the sum of
both entry mid notionals. They are **not account-capital returns**, executable
quotes, matched fills, round-trip costs or an arbitrage recommendation. No
ranking follows. Snapshots were collected sequentially; clock authentication,
time synchronization, source freshness and sequence continuity are unverified.
Minimum notionals, maximum order limits and owner account eligibility remain
unqualified. Reported MEXC API flags are retained separately from access.

Account fees, future exits, funding/transfer/margin/collateral costs and net pair
PnL remain UNKNOWN at **1x,2x and3x**. No amount of multiplying the known entry
component establishes the missing total. Neither R391 nor any method is promoted.

## Evidence and scope

[Independent rational arithmetic check](arithmetic_check.json),
[qualification](evidence/qualification.json), [frozen plan](plan.json),
[attempt marker](qualification.started.json) and
[accumulated journal](acquisition_budget.jsonl). Every request has its raw gzip
body, SHA256 and local clock/status/cleanup receipt in `evidence/`; no response
was silently replaced. Primary-source read scopes are in the existing
[intake supplement](../../research/intake/funding_notional_20261103/carry_sources_20261104.md).

Registry verdict is PARTIAL because a global stop occurred, even though two
conditional calculations were possible. This validates narrow current-input
mechanics; it does not establish a persistent market opportunity or a full
capture-host/production deployment. No frozen R401 input was modified.
