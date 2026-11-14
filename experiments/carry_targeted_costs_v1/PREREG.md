# R402: targeted public contract and lot-matched depth qualification

Registry id: R402

Claimed in room #7 before source collection. Freeze and publish this protocol,
its plan and code before one capture; append one final registry row afterwards.
Predictive trials:0. Prospective paper days:0. No historical return or label read.

## Fixed design

All28 published R391 symbol rows remain, with no outcome-based selection or
replacement. Sorted economic key, then MEXC and KuCoin.25 MEXC and18 KuCoin
contracts, metadata then depth if metadata qualifies: at most86 new public GETs.
16 keys declare both venues; dYdX/Lighter entries remain explicit and unpriced.
The official endpoint/quantity evidence is in
research/intake/funding_notional_20261103/carry_sources_20261104.md.

Use symbol-filtered detail on the announced api.mexc.com domain and public
KuCoin per-contract detail/depth20. No auth, private endpoint, orders, redirects,
retries, fallback host or substituted symbol.32KiB per response; partial tails
retain the full reservation. R401's1request/2MiB is a conservative baseline in
ONE accumulated5MiB scope, not a renewed allowance. Max combined4915200bytes;
reserve4seconds per request including owned-worker cleanup, worker3seconds,
300second dispatch window. Global starts at least1second apart; MEXC metadata
starts at least5.1seconds apart (official limit1request/5seconds).

Freeze-bound code verifies all inputs before and after collection. A protocol-
local exclusive attempt marker is file/directory-fsynced before any request;
changing the output path cannot repeat it. An append-only BudgetJournal reserves
before dispatch and never refunds. Off-host BEGIN notice consumes the attempt
before launch. These checks do not prove protection against storage rollback or
an external writer removing guards. No marker deletion/reset is authorized.

## Failure and unit rules

Any incomplete body, worker error/unreaped process, budget overrun, non-200/404,
Retry-After or invalid JSON stops all future dispatch.404 is retained as missing
contract/endpoint and never retried. Successful JSON with unsupported metadata
or depth mechanics leaves that contract unscored; continue other fixed contracts.
Filtered metadata must contain exactly the requested symbol, as an object or
singleton. Require open crypto MEXC type1, and KuCoin linear noninverse perpetual,
USDT quote/settlement, exact base identity and positive explicit multiplier/lot.
MEXC apiAllowed is reported separately; it does not authenticate owner access.
MEXC minimum contract quantity is required before pair arithmetic. Neither
minimum notionals, maximum order limits nor actual owner eligibility is proved.

Depth is at most20 sorted unique noncrossed levels per side. MEXC triples are
price/contracts/order-count; KuCoin pairs are price/contracts. Quantities must
be lot multiples. Multiply contracts by explicit multiplier. Keep local request
and receipt clocks, reported versions/sequences and source timestamps. KuCoin
raw timestamp unit is unqualified; no synchronized/continuous/stale-free book
or simultaneous executable pair is asserted.

## Conditional cost and decision

Use a common base quantity on both venues: rational LCM of base lot increments,
rounded down so each leg's MID notional is at most1000USDT. This is not a bound
on cash consideration at the ask. Require explicit minimum contract quantities
and sufficient shown depth. Calculate both buy/sell directions; compare each
leg to its OWN snapshot mid, never count cross-venue basis as profit. Normalize
sum of spread/impact costs by SUM of both entry mid notionals, not capital.

Account fees, future exits, funding, collateral, margin/transfer costs, source
clock authentication, sequence continuity and fills remain unverified. At1x,
2x and3x full cost and pair PnL stay UNKNOWN. No cost estimate promotes a method.
DATA_PASS means no global stop and at least one conditional paired entry-book
calculation, certifying only these input mechanics. Otherwise PARTIAL. Preserve
all cohort rows and missing/source/schema reasons. Report qualified/unknown
counts, receipts and charged budget, never a ranking or strategy success.

## Frozen plan and inputs

Plan SHA256: a484193f2a3139dddfd3c634878d2b436721e737982be0712f670454dfd7425f

```inputs
f50159fad3f4319868eb38717b91d55843c41e9803014c8de05e116a6d0bcfdc  .python-version
86c25399d20c46402f22a04c5256e9c3a57b916fe7a4cb6760c692ec2af9822e  experiments/carry_cost_qualification_v1/evidence/mexc_metadata.receipt.json
5ebfaec83a5c2c47831ec5fbf9b0e683ac3bdf0e88562caf99bfbb834c9ed748  experiments/reserved_batch2/symbols.csv
0a5da0a741d8fa1280f0a8a5b2e08f1e4ced787565de8260bb0d53c101ea98bb  lab/acquisition_budget.py
85d90f1024414957c5beda81dec61e6fe9f88927532b3a8bb5e1a4eb4ff34556  lab/carry_snapshot_cost.py
3d6d7084f45b01e9e24669ec9914673cde56ca04cadea5cfe01ef22072f404bb  lab/mexc_depth.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508  lab/prereg.py
4cf65930e08965601cefe33b1785271bb024d22f39eac22582e5fd393bb2b466  requirements-test.lock
172a7e6b8d8cc60fd1c5d9c324d14124e6628a4faab97b342dd61d2415d491c2  scripts/qualify_carry_costs.py
112a585d3aa1cbe66ab01fc355ff0cd7e0a535773a17f14fcd3ba405ec49156a  scripts/qualify_carry_costs_targeted.py
```
