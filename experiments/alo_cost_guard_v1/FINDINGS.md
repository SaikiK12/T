# R365: ALO cost-accounting guard, constructed inputs only

**Decision: PARTIAL engineering; the proposed ALO strategy remains untested and
blocked.** The committed example is deliberately invented and its exit is
assumed at a midpoint with a passive fee. It is an accounting diagnostic, not an
estimate of fill probability, expected PnL, capacity or live readiness.

The user's proposed markout already includes the entry spread: for signed
quantity `q`, `q*(mid_h-fill)` equals `q*(mid_at_fill-fill)` plus
`q*(mid_h-mid_at_fill)`. Adding the first term again double counts it. The
existing `PaperAccount` prices the hypothetical entry and midpoint exit; the
new guard checks that the ledger's realized component agrees with the same
signed markout less the entry and exit fees, then deducts any **explicitly
assumed** paid-action cost separately. This first implementation has material
guard defects found by independent review: it does not compare a quote's
monotonic receipt to the fill receipt; terminal/fill-history completeness is
an untimed caller assertion; and its collateral check excludes the separate
action and extra charges. It checks entry collateral only, not solvency along
the position path or at the hypothetical exit. A caller-supplied midpoint role
does not independently validate the underlying BBO. It must not be used to
score real receipts. Explicit
`unresolved` flags remain unknown, but cannot cure those other defects.

## Fixed invented example

With $2,000 segregated capital, a $1,000 entry, 100 assumed paid actions, a
3.10 bp fill-to-horizon-mid markout and the source's **base** 1.5 bp maker fee
per leg, the invented passive midpoint-exit component is:

| Stress | Total assumed cost, bp of entry notional | Component, USD | Component, bp of capital |
|---|---:|---:|---:|
| 1x | 3.500465 | -0.0400465 | -0.2002325 |
| 2x | 7.000930 | -0.390093 | -1.950465 |
| 3x | 10.501395 | -0.7401395 | -3.7006975 |

The assumed action cost is $0.05 at 1x. The $0.0005 per paid action was
provided as a **hypothetical input** and was not verified by the fetched
rate-limit page. The 100 are entry submissions; the imagined exit contributes
no additional paid-action charge, an optimistic assumption. If those same 100 actions are assumed to cost zero within a
finite allowance, the components are +$0.0099535, -$0.290093 and -$0.5901395.
That does not establish that the allowance suffices, that the exit can be
filled at the midpoint, or that those maker fees apply to the owner. Adding
the already-included $0.20 entry spread again would falsely turn the 1x paid
example into +$0.1599535.

The complete no-fill case incurs the specified paid-action amount
(-$0.05/-$0.10/-$0.15); per-filled-notional cost is undefined. Its missing
per-capital values are -0.25/-0.50/-0.75 bp, independently calculated; their
omission contradicts the registered reporting requirement. The case with
an unresolved order remains UNKNOWN in every cost scenario. All twelve cells
are retained in [results.json](results.json); none is a measured trade.

## Evidence and verification

The current public [Hyperliquid fee table](https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees)
shows a 1.5 bp base maker fee. Its [order-types](https://hyperliquid.gitbook.io/hyperliquid-docs/trading/order-types)
and [error documentation](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/error-responses)
support post-only mechanics and several independent rejection reasons, not
fill or queue guarantees. The [address-limit documentation](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits)
describes a finite initial buffer, volume-linked actions and a congestion
constraint. The Binance promotional announcement appeared in a cached
search excerpt but the direct page redirected to generic announcements, so
current account eligibility and the promotion remain unverified.

The source set, access limitations and exact scope are in [sources.json](sources.json).
The [wallet-identity paper](https://arxiv.org/html/2608.04373) reports incremental
short-horizon prediction, while the directly inaccessible SSRN paper's search
excerpt reports profitable anticipatory activity by the studied participants.
Neither is a fill-conditioned, fee-adjusted result for this account. The
195.3 GB dataset was not downloaded or independently checked. Wallet activity
must be available by our first-seen decision time; blockchain message times
alone do not establish that condition.

Before the constructed cases were run, spec, inputs and code were committed
in `e230f5b4d4ab2752791dad2d9ab451f6f9b4b7bf`. The 12 resulting cells
reproduced byte for byte and an independent rational checker passed **75
checks**. Twenty targeted guard/account tests passed but missed the adverse
conditions above. No strategy trial,
market request, order, actual fill or prospective day was added.

The decisive open inputs are synchronized first-seen CEX/Hyperliquid books
and wallet data; clock and block-publication availability; our empirical
arrival/cancel latency; order acknowledgments, partial fills and queue
position; actual fee tier, session access, funding and risk. Public book
movement or ALO acceptance alone cannot identify our passive fills. Until
these are available, executable expected net return remains unknown.
