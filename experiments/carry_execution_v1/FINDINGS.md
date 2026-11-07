# FINDINGS: carry_execution_v1 (R417)

**ACCOUNTING_PASS; M485 remains PARTIAL. Zero predictive trials, gate-0 engineering.**

One offline run on **2026-11-06 16:51:23–16:51:24 UTC**, after freeze/input commit
[`1114da2a`](https://github.com/SaikiK12/T/commit/1114da2a) had been pushed. PREREG sha256
`503220858a4e28a77db784de63f3aaa50ff785b10c0055c0fddeb084e92f81f7`.
All **17 direct inputs** matched before and after the run. [Run log](run.log),
[complete report](results/report.json), [independent check](results/check.json),
[frozen protocol](PREREG.md). Read against **9,784,343** program trials from
`registry.program_trials("registry/rounds.csv")`; this round adds zero.

## Displayed BTC depth: old observations, not current capacity

Only the two **2026-10-24** R312 BTC MEXC/Lighter captures were read. Both
directions at four MID notional targets and three costs gave **24 paired groups /
48 directional rows**. Every requested quantity fit the *shown* depth in this
small closed scope. No new venue quote, other coin, reserved sample or gitignored
file was read. Receive skew was **95.549029 ms** and **272.232920 ms**; actual
source-event age, simultaneous liquidity and arrival-time fills remain unverified.

Entry friction below is the sum of the two legs relative to their own mids:
spread/impact plus the **stated MEXC API 0.08% / Lighter Standard 0% fee
scenario**. Ranges span both directions in both observations; they are descriptive,
not a selected strategy. USDT/USDC/USD parity is assumed. These are **one paired
entry**, not entry plus exit, funding, margin capital or return on an account.

| Target MID notional per leg | 1x entry friction ($) | 2x ($) | 3x ($) |
|---|---|---|---|
| 10,000 | 8.03–8.39 | 16.07–16.79 | 24.10–25.18 |
| 25,000 | 20.09–21.01 | 40.18–42.03 | 60.27–63.04 |
| 50,000 | 40.19–42.52 | 80.38–85.03 | 120.57–127.55 |
| 100,000 | 82.34–86.82 | 164.67–173.65 | 247.01–260.47 |

Quantities were floored once to the common lot and kept identical at 1x/2x/3x.
For the 100k target they were **1.2592 BTC** and **1.2591 BTC** in the two
observations. Higher-cost prices are sensitivity scenarios relative to the mid;
the displayed quantities are unchanged. Fees are not authenticated owner rates.
Current capacity, future exits, funding and executable expected net return remain
**unknown** (`null` in the report). The check’s `retained_unknowns=0` counts only
incomplete/blocked rows in these two small depth cases; it does not remove those
global unknowns. Synthetic unit tests separately exercise partial/unknown cases.

## Segregated cash under forced closure: explicitly invented

Exactly **36** worlds: three predeclared paths × total account capital
**$10k/$25k/$50k/$100k** × costs **1x/2x/3x**. Each account is split into
two equal cash wallets, with 1x MID notional on each leg. Thus a 10k account
has 5k cash/notional per leg. These capital budgets differ explicitly from the
order-notional targets in the depth table.

All prices, depth, tier thresholds/rates and liquidation penalties are invented.
The dates lie in `lab.stress.EPISODES["2025-10-10 liquidations"]`; the **33-minute**
no-transfer assumption takes the incident duration as context. This is **not a
historical reconstruction** of 10 October 2025 or a model of OEM X-Perps’ actual
margin-call/negative-balance-protection terms. Funding cash is explicitly zero
in these toy worlds, not imputed from absent venue history.

For **$10,000 total capital**, in dollars:

| Invented path | Costs | Net before recovery | Terminal net |
|---|---|---|---|
| flat | 1x | n/a | -24.00 |
| flat | 2x | n/a | -48.00 |
| flat | 3x | n/a | -72.00 |
| one_leg_liquidation | 1x | -6573.31 | -5579.81 |
| one_leg_liquidation | 2x | -6646.66 | -5659.65 |
| one_leg_liquidation | 3x | -6720.03 | -5739.51 |
| adl_then_further_drop | 1x | -2012.00 | +981.50 |
| adl_then_further_drop | 2x | -2024.00 | +963.01 |
| adl_then_further_drop | 3x | -2036.00 | +944.51 |

- The upward-gap path tries to transfer cash before the outage ends. It is
  refused. The short breaches its supplied maintenance tier and closes; its
  cash deficit remains. Its quantity stays zero through recovery. Terminal loss
  at 1x is **55.80% of initial combined capital**, not a recovery profit.
- The profitable-short ADL path closes only that leg before a further drop.
  The still-open long takes the intervening loss, separately exported before
  recovery. Its later rebound is the gain of inventory actually retained; it
  does not reopen the short. Its positive terminal toy outcome is no alpha claim.
- All supplied tier ceilings are honored; unsupported/missing tiers cannot
  become safe margin. Missing fees/funding/exit depth block a complete net result.
  Partial exits retain inventory and prevent a final-flat account label.

## Independent checks and validation

The prewritten Fraction checker, which does not import the Decimal kernel, passed **432 depth/fee equalities** and **1464 per-wallet cash/equity equalities**,
with the unchanged **$1e-12** tolerance. It checks raw input identities, maximal
lot sizing, displayed sweeps, actual supplied fee bases, cash conservation,
negative balances, no reopening after close and the pre-recovery loss. This is
independent arithmetic, not independent market/provider reconstruction.

- **26 new synthetic tests**: raw contract-unit conversion, aggregation and market
  depth limits; crossed books; lot/minimum boundaries; thin/partial pairs; unknown
  fees/margins/funding; cost tiers; liquidation/ADL; cash transfer; fixed inventory;
  and EEA 403/451/429/HTML/timeout/redirect/private-route/byte-budget refusals.
- **Full suite: 2,435 tests OK, 3 skipped**, clean process exit **0**, **384.050 s**
  under the same thread bounds as CI. The three errors described in the handoff
  did not reproduce in this Python 3.12.14 environment. The first full attempt
  also printed OK after 2,435 tests but exited **134** in native C++ teardown;
  this failure is preserved in [validation.json](validation.json). No test was
  suppressed or an old frozen file changed to make the repeat pass.
- Integrity: **0 errors, 14 existing warnings**; generated catalogs checked.
  CI is reported separately on the PR; these are local results.

## Queue outcome, missing data and operational handoff

**M485 PARTIAL** links this measured implementation. R404 and lighter_book store
cost summaries up to 10k without the levels needed for larger sweeps; their
ongoing measurement window was not consumed. The gitignored recorded tape is
absent in this worktree. A real successor needs an immutable, nonreserved matched
L2/metadata package, effective venue tier/haircut/fee/ADL rules, first-received
clocks and price/funding paths. Historical crash L2 remains absent; current
snapshots cannot recreate it. No broad carry grid or new prospective day.

**M484 BLOCKED** after the sole ordinary EEA instruments GET returned **403**.
The [existing carry intake note](../../research/intake/funding_notional_20261103/okx_eea_sources_20261106.md)
records documented three-month X-Perps funding history, EEA fee distinctions and
product terms. The new public capability probe is inactive, never scheduled and
was not run. No global SWAP proxy, alternate host, credentials or account.

**Registration history:** the rounds CSV retains its pre-run REGISTERED/PENDING
row, appended before measurement through `lab.registry.append`. It is not
rewritten, in accordance with the owner’s append-only rule. This FINDINGS is
the native completion/accounting verdict; M485’s mutable queue row links it.
No alternate registry was introduced and no forward task is attached to R417.

**Read-only monitoring at 16:47 UTC, base ec619682:** published hourly receipts
for R285/R406/R413/R415 stop around 14:23–14:35, over two hours old. This flags
committed-evidence freshness, not proof of dead processes. PANEL’s last receipt
also reports REC_LIGHTER FAILED. R278/R279/R390 have daily-output timestamps
around 01:45–02:09, which alone is not an hourly failure. R415 correctly has no
market day before its 2026-11-07 opening. R413/R406 have zero settled locks.
No first read or journal write was made. R413/R415 have no FINDINGS yet; their
protocols/status/statement supplied the handoff. Claude retains R367’s Nov 8
final, the R392 pre-Nov 17 batch freeze and R404/M469’s Nov 18 duty. The missing
R392 registration/freeze and freshness warning were posted on #7.
