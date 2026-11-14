# R324 — physical spot and perpetual accounting; public input compatibility

**PARTIAL.** Physical spot cash/inventory now joins the existing segregated
linear-futures account. All24constructed cost cases match a separate literal
cash-flow oracle;139new public messages establish short-window spot/perp wire
compatibility for BTC/WIF/SKR. **No executable market edge or new prospective
strategy day is validated.** Missing unit/snapshot/metadata/fee/funding contracts
still block actual market PnL. M047/M134 retain their original rule/result scope.

## Reproducible sequence and scope

1. Code/contracts/source/finite fixture freeze `e19414231ea7f2696927dfa8a9174e124425b0e5`
   preceded collection/outcomes. PREREG73664cc9f7868a6bc053021f176fcc0314dfd71f5947e948b2fb19d7306e5e9c;
  26pinned code/import/test files. Full1350tests passed with2skipentries before commit.
2. One bounded current capture; exact raw `data_inputs.json` and receipts committed
   at `94d8b43` BEFORE offline calculations. No historical cache was rescored.
3.24registered accounting paths,48native journals/168chained rows; independent
   literal cash, cost decomposition, base-fee exposure and total-capital audit
   matches. All4compact outputs byte-reproduce in a fresh directory; reproduction
   made0network calls. No frozen input or existing output was overwritten.

Use `python -m lab account --spot-perp --out /fresh/output`, then
`python scripts/check_spot_perp_account.py /fresh/output/results.json`.
Replay verifies the committed original raw inventory and frozen implementation.
It cannot initiate collection. Packed journals retain the native local append-only
records, which remain locally intact. Native config/chain alone does not pin code;
the external frozen closure supplies that binding.

## What the component fixes

- A physical spot buy spends its quote principal. Held inventory contributes its
  prudent liquidation value to NAV; principal is not reserved or deducted twice.
  A linear-futures opening reserves notional without spending that principal.
- Both5000USDT model wallets count in the10000capital denominator. Gains cannot
  silently move between wallets; no USDT/other-currency parity is inferred.
- Quote commissions enter cash/acquisition cost once. Base commissions reduce
  available inventory; a gross-sized short leaves modeled orphan exposure
 0.001/0.002/0.003base at1x/2x/3x. Net-owned sizing explicitly records that effect.
- Unknown/third-token spot fees block new spot fills and withhold complete NAV.
  Unknown normalized perpetual funding also withholds total NAV. Rejected closes
  and unclosed inventory remain visible. No MX conversion, owner fee or funding
  settlement is guessed. Spot borrowing is forbidden.
- Opening spot/perp premium is not immediate cash profit, and a perpetual has
  no dated-futures maturity that guarantees convergence.

Eight declared cases ×3fixed cost tiers are engineering controls, not a fitted
policy or unseen empirical sample. Spread is embedded in the supplied fills;
quote fees use stressed fill notional. Base-fee and hedge rules are fixed in the
spec. Cash reference is flat with the same10000capital; risk equivalence is not
asserted. Selected exact model results (USDT model units,1gross base bought):

| Constructed case | 1x | 2x | 3x |
| --- | ---: | ---: | ---: |
| Unchanged basis, zero supplied funding | -0.604 | -1.208 | -1.812 |
| Supplied basis convergence plus0.25funding/base | +1.646 | +1.042 | +0.438 |
| Basis widens despite0.25funding/base | -3.357 | -3.964 | -4.571 |
| Unknown funding / unknown spot fee / third fee token | unknown | unknown | unknown |

Favorable and unfavorable paths are known by construction. The positive fixture
is not an observed trading gain. The decomposition in audit.json independently
checks gross midpoint price movement + supplied funding − crossing − quote
commissions − base commission value = final net. Fee diagnostics are not charged
again. Every case/tier, including failures/nulls, remains in observations.json.gz.

## Actual bounded public capture

Two normal public WS handshakes succeeded,4subscription messages,12seconds of
observation per connection, max14.048seconds including handshake/close. No REST,
retry/reconnect/redirect, history/account/RPC access or symbol substitution.
139messages:73spot including72binary depth packets,66perp including63depth packets.
All72spot packets structurally decoded against the pinned two-proto tree, each
with5asks/5bids; no decode failure. Exact first-seen UTC/monotonic clocks precede
parsing. This establishes actual wire receipt/structure, not exchange permission,
continuous availability, complete snapshot semantics or a filled order.

| Fixed symbol | Spot structural depth packets | Perp structural depth packets | Certified executable pairs |
| --- | ---: | ---: | ---: |
| BTC control | 24 | 43 | 0 |
| WIF | 24 | 8 | 0 |
| SKR | 24 | 12 | 0 |

Every spot packet retains three blocking flags: timestamp unit unverified,
quantity asset unverified, complete-snapshot semantics unverified. No source
clock is synthesized from receive/create/last-order time or a13digit example.
Metadata/minimum lot/status, owner commission/fee asset, execution delay, exit
depth and actual event-notional funding remain unverified. Certified market net
is therefore **unknown at1x/2x/3x**, not zero. These new raw observations are not
backfilled historical data or on-time prospective strategy scoring.

Accepted application payload:43865bytes (spot24174,perp19691),0budget violations,
0pending reservations. Conservative journal charged both4MiB/25second reservations
without refund:2requests/8MiB/50cumulative reserved seconds, so that scope cannot
be reused. Those are upper-bound reservations, not measured wire bytes. Transport/
handshake overhead and unread buffered wire bytes are unknown. The original
R310/R311 historical allowance remains7757/8000requests and reported229.85/250MiB
spent; exact historical remaining bytes unknown, no reset or enlargement.

## Primary-source and review boundary

Nine separately declared static GETs118731bodybytes: two complete pinned proto
files/tree metadata and base WS/partial-depth/Introduction visible content;
market503,account404 and wrong-path integration404 retained without retry. Exact
URLs, versions, hashes and read/unread scope are in sources.json/source_receipts.
The Introduction's milliseconds rule concerns SIGNED requests; it does not
resolve WS timestamp units. Correct integration/local-book/market/fee pages
remain unread. No broad strategy corpus or full copyrighted book was mirrored.
Five input/source mechanics supplement six existing aliases, with0new methods
or alias rows. M047's premium rule and M134's historical trailing funding rule
are not rerun or promoted; dated M244 and M170/R301 remain distinct.

One separate reviewer checked exact spot_cash.py hash7ab221fd and finite financial
probes with no concrete blocker found at that scope. Pair/wire/collector/full
runner/final literal oracle are not fully independently peer reviewed. Parent
functional tests and the separate literal audit do not expand that peer-review
claim. No authentic exchange balance, fill/rounding/fee, tax lot, margin/liquidation
or general cash-integrity proof is supplied by invented accounts.

Program trials remain9478970:0predictive/optimization trials added;24cost/account
paths and all139raw messages are explicitly counted. No sample-based uncertainty,
dependent-null acceptance or calibrated positive expected return is claimed.
R311 remains INCONCLUSIVE224/273 and negative at2x/3x; R321 remains NOT_ACCEPTED.
Strict new prospective strategy days0. Owner100 frozen coverage is unchanged;
this is a bounded implementation/input advance, not all100enhancements complete.
No orders, money, secrets, large data/weights, activation, merge or closure.
