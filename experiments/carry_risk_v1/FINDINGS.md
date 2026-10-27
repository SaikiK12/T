# R346 — PARTIAL: carry can lose marked capital well before it breaches modeled margin

The same5000USD-face-per-coin R344 model has conditional marked PnL
**−8.99 / −18.06 / −27.13USDC** immediately after its hypothetical entries at
1x/2x/3x costs. If both futures marks rise2percent relative to unchanged spot
and index prices, the account shows **−203.55 / −212.62 / −221.69USDC** against
the SAME10000USDC initial capital. This2percent scenario remains inside the
previously documented adjustable default10percent mark/index band.

These are source-priced **conditional valuations, not observed losses or
executable exit proceeds**. The risk arithmetic is now linked to the original
native accounts and settlement currencies. It does not validate expected net
return, actual margin clearance or liquidation immunity. R344's separate
conditional terminal gain and its negative2x/3x excess versus the3percent cash
scenario remain unchanged. A promised terminal payoff is not smooth daily PnL.

## Frozen scope and received inputs

Code/spec/input freeze **6554939** was committed and pushed BEFORE all R346
market-derived calculations. PREREG SHA256:
`c7d9e1cd989d5edef8e0492153a762c6a0ed6d2b3c2d816bbfb78b4be16466b5`.
69local code/test files and36exact input identities are bound. The runner
verifies its committed identities and the parent's unchanged raw inventory.

Reuse all48 R344 model cells, all132 original financial journals and the same8
R343 public bodies; no market/history/account/private/order acquisition. No
original financial event, selector, cost, position size, depth rule, provenance,
frozen file or journal changes. All54 underlying R335 historical data files
are absent across available workspaces; no historical marked path was replayed
or downloaded. See historical_availability.json.

One separately declared official-source query and3ordinary static GETs closed
at3HTTP200/266298actual body bytes,3MiBreserved,3.379494s GETwall. Limits were
3GET/1MiBbody/3MiBtotal/15seach/60sGETwall;0redirect/retry/login. Exact source
hashes/read-unread scopes are in source_receipts.json and source_review.json.
The query's returned snippets are discovery, not proof that every result was
read. Raw HTML is retained in ignored cache, not publicly mirrored.

New documentation was received12:55UTC, AFTER R34307:07UTC prices. This is a
POSTHOC current-rule contract, not on-time risk evidence for those quotes and
not a historical risk schedule. The old historical allowance remains7757/8000
requests and reported229.85/250MiB; all old closed source/current scopes remain
unchanged. No future timestamp or another response's clock stamps these inputs.

## Current source mechanics narrow the margin gap

The current [Standard Margin](https://support.deribit.com/hc/en-us/articles/25944811528477-Standard-Margin)
and [instrument table](https://support.deribit.com/hc/en-us/articles/39858424876829-Standard-Margin-Requirements-by-Instrument)
(updated2026-10-13) specify BTC/ETH **dated inverse** Tier4, USD-face size,
75MUSD maximum,25x maximum IM leverage through2.25MUSD. Within that exact
flat segment, IM=1/25 and MM=2/75 of position value. The displayed2.67percent
is rounded. The old2025 search result's additive coin-size formula is stale;
it was not implemented as the current rule. Above the flat segment remains
unimplemented/unknown, without interpolating the nonlinear curve.

[Margin types and usage](https://support.deribit.com/hc/en-us/articles/25944811317149-Margin-types-and-usage)
(updated2026-10-21) distinguishes settlement-asset segregation, cross collateral
and portfolio margin. In S:SM, USDC idle cash cannot automatically cover BTC
or ETH inverse requirements. Futures unrealized/realized PnL belongs in margin
balance; open-order IM is additional. Margin availability is distinct from
settled/spot-spendable cash and withdrawal balance. The0.8IM expression belongs
to the **portfolio-margin table column**, not this standard-margin MM rule.
The last30min projected-margin transition remains unknown in this component.

The pages do NOT establish the inverse USD-to-coin denominator (mark versus
index), risk-size aggregation across expiries/open orders, actual owner mode,
complete account obligations, settled/eligible collateral, exact liquidation
trigger or engine. INDEX and FUTURE_MARK are explicit conditional controls.
The original-snapshot UNKNOWN control withholds every actual margin amount;
all48 aggregate margin states remain unknown under that control.

## Same capital and collateral counted once

Original journals reopen through unchanged SpotCashAccount/InverseCashAccount;
no new financial events are posted. For signed face q, coin cash B, reciprocal
entry a and future mark M, UPL=q*(a−1/M) and total coin equity=B+UPL. That total
is converted to USDC once. The original bought spot holdings are NOT added a
second time. Realized settlement changes coin cash and resets the unrealized
baseline; it cannot create a second gain. Tests cover that identity.

Each alternative uses10000USDC, the same fixed original lot-rounded positions,
actual displayed entry crossing and original supplied fee/debit controls. Cost
multiples are1x/2x/3x and never position-leverage multipliers. USDC cash is counted
once at portfolio level and never credited to a BTC/ETH segregated margin bucket.
Actual owner fees/asset/minimum/rounding and fills are still unknown.

For the fixed5000full/public-standard/base-debit illustration:

| Conditional value in USDC | 1x | 2x | 3x |
|---|---:|---:|---:|
| Idle cash after original model entries | 50.53 | 50.43 | 50.34 |
| Original-snapshot marked PnL | −8.99 | −18.06 | −27.13 |
| Futures marks +2%, spot/index unchanged: PnL | −203.55 | −212.62 | −221.69 |
| Futures marks +10%, spot/index unchanged: PnL | −911.04 | −920.11 | −929.18 |
| Maximum common mark increase for a2% capital-loss floor | 1.96281% | 1.86788% | 1.77312% |
| Maximum common mark increase for a5% capital-loss floor | 5.20606% | 5.10500% | 5.00412% |

The +10percent scenarios put both mark/index ratios outside the source's
adjustable default10percent band; they remain labeled adverse/outage states,
not asserted reachable normal-market prices. The +2percent scenario is within
the default band. Neither scenario has an estimated probability or horizon.
Marks/midpoints exclude the unobserved cost of an actual forced close.

Under the explicit INDEX control at1x, modeled BTC equity is0.06243024BTC versus
MM0.00167676BTC; ETH equity2.16436480ETH versus MM0.05797782ETH. FUTURE_MARK gives
slightly different requirements. This is ample **conditional** maintenance
buffer, while the2percent capital-loss floor can already fail. Margin coverage
therefore cannot substitute for a capital-loss budget. It is not an attestation
that the actual account is safe or may open a position.

The1000full/base control marks −1.76/−3.54/−5.32USDC at the original snapshot.
5000top-only remains incomplete: BTC entry depth failed in R344, so full NAV and
loss frontiers remain unknown despite its known partial ETH account. No resizing
or partial-portfolio rescue. All quote-debit, zero-charge, top-depth and cost
controls are retained in results.json.gz; no better-looking control is selected.

The matched spot-only control owns the same initial bought coins/spot fees and
idle cash, without paying inverse fees or receiving UPL. At1x, a common coin
price scale.25/1/4 gives NAV2536.63/9994.93/39828.12, versus the carry's
9977.55/9991.01/10044.84 with unchanged relative futures basis. The small carry
change comes from its explicit residual coin. Cash is10000 in every immediate
state. These show arithmetic exposure differences, not equal realized risk,
future stablecoin parity or historical drawdown distributions.

## All states, uncertainty and verification

All48parent cells ×5coin scales ×5future-mark factors ×2denominator controls
produce2400dependent conditional states: **1800 numeric,600 incomplete**.
The two denominator controls repeat the same NAV and are not independent
observations. All1800 numeric states have conditional maintenance coverage
under their supplied assumptions. Of these,720 are outside the documented
default mark band; all flags and incomplete states stay in the artifact.

All720predeclared loss frontiers remain:540numeric/180withheld. Exact
NAV(beta)=idle+lambda*R+H/beta solves each boundary; none is chosen as a new
trading stop. No model refit, expected-return estimate, CI, p-value, calibrated
loss probability, dependent-null inference or new strategy variant is derived
from a fixed grid. R335's6trials and R345's9 remain counted; this engineering
lane adds0predictive trials, program9479022unchanged.

- Full required suite **1580tests PASS**,3existing skips,207.242s before freeze.
- One bounded source reviewer independently reproduced8published formula/table
  examples;11targeted tests and13invented financial/state checks passed. The
  reviewer found UNKNOWN margin aggregated as FALSE; it was fixed and rechecked
  before freeze, with both before/after receipts preserved.
- Independent stdlib checker **126298exact checks PASS**, reconstructing source
  identities, journal hashes, cash/coin state, every marked equity/IM/MM, whole
  capital once, all2400worlds and720frontiers. It imports no production financial,
  risk, selection or reporting module; it still shares supplied input/source
  interpretation, not an independently authenticated venue risk engine.
- Fresh-directory compressed results, journal pack and audit are byte-identical.
  Every132copied journal has the original byte content. See reproduction.json.

Actual account risk readiness is FALSE, actual margin certification and expected
executable net return remain UNKNOWN.0new prospective strategy days/activation.
R310/R311, R335, R337/forward, all old financial files and provenance stay intact.
No order, money movement, secret inspection, PR merge/closure or permanent job.

Reproduce offline with Python3.12.14 and a fresh output directory:

```sh
/workspace/T-consolidation/.venv/bin/python scripts/run_carry_risk.py --out .cache/r346-fresh
/workspace/T-consolidation/.venv/bin/python scripts/check_carry_risk.py --out .cache/r346-fresh
```

Next required evidence is the authentic account/margin contract and complete
settled collateral obligations, the inverse conversion/trigger rule, and on-time
executable observations under a separately frozen finite prospective protocol.
This risk component cannot repair R311's absent historical execution evidence
or turn a conditional carry payoff into a validated net edge.
