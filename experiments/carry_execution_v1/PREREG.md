# PREREG: carry_execution_v1, bounded carry depth and one-leg cash mechanics

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R417
- **Owner (single writer):** Codex, codex/france-carry-execution-20261106
- **Date registered (UTC):** 2026-11-06
- **Canonical method:** M485; M484 source plumbing is a separate blocked data task.
- **Claim:** issue #7, comments 6689565329 and 6690019898.

## Question
Can a fixed-quantity two-leg depth calculation and a segregated linear-perp cash
account preserve partial fills, supplied margin tiers, one-leg forced losses and
cash before recovery, without manufacturing a rebound profit after closure?

This is a bounded engineering measurement with **zero predictive trials**.
Snapshot arithmetic is gate 0 on old observed data; it neither selects a carry
rule nor tests expected return. Generic invented risk paths are not a replay of
OEM X-Perps' actual liquidation/negative-balance-protection terms.

## Universe
Exactly **BTC**, MEXC BTC_USDT and Lighter BTC market id 1, observations 0 and 1
from R312's closed 2026-10-24 public capture. Only its six BTC metadata/book bodies
and the request receipts are read. No other parent coin/body, gitignored data,
2020 row, MEXC-only reserved coin or `reserved/` path is authorized.

The existing source code for R404 and lighter_book was inspected before this
freeze: persisted rows contain costs through $10k rather than full price levels.
Those summaries cannot be extrapolated to the larger requested sizes. Their
unfinished window and every forward journal remain outside this run.

## Data
The complete direct input closure is `inputs.json` (**17 files**), including this
lane's fixed `cases.json`, code, checker, copied gate version, pinned runtime
files and the immutable parent source bodies/receipts. Every byte hash is checked
before and after measurement. The raw decompressed parent bodies must also match
their original receipt hashes. The exact freeze and every input must be present
in HEAD before the runner can measure; a sidecar alone is insufficient.

No network, acquisition, recorder, daemon, order, credentials or money movement.
Unit tests use invented fixtures and temporary directories only. Tests are not
inputs to the statistic and are not included in its frozen closure.

## Feature lineage and point-in-time availability

| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| Base depth | MEXC price/contracts/order-count triples, contractSize; Lighter price/remaining_base_amount | R312 immutable public BTC capture, quote per BTC and BTC | Two old snapshots, no inferred intervening levels | Parent request receipts retain separate UTC/monotonic receipt times | Historical conditional arithmetic only; native source-event age and actual arrival unproved | Fixed BTC control, current-listing capture on 2026-10-24 | Hash mismatch stops; missing/empty/crossed levels refuse; thin depth stays partial |
| Common lot | MEXC contractSize × volUnit, Lighter supported_size_decimals; minima | Venue metadata, BTC units | Quantity floored once to a rational common lot, same at all costs | Parent metadata receipts | No new trade decision | No cross-sectional universe or survival claim | Missing units/minimums stop; MEXC marketOrderMaxLevel limits levels |
| Entry friction | Sweep both directions relative to each own mid | Same BTC books | $10k/$25k/$50k/$100k MID notional per leg, not total capital | Computed in the sole run | Ex-post depth diagnostic | Existing observed scope; not a sample of current capacity | No inferred future exit, fill probability, owner fee or return |
| Fee sensitivity | Fixed MEXC API 0.08%, Lighter Standard 0% scenarios | Public schedule scenarios, quote currency | 1x/2x/3x spread-impact and fee stress, fixed inventory/depth | Assumptions fixed before run; owner report records the schedule sources | Account entitlement unverified | Not personalized, not inferred from UI zero fee | No missing fee becomes zero; supplied zero is an explicit scenario |
| Quote comparison | USDT = USDC = USD | Explicit scenario only | Both legs' arithmetic | Fixed now | Conversion unverified | Not an observed FX series | No capital/expected-return claim follows |
| Stress positions/cash | Entry and stage books, marks, two explicit tier ceilings/rates/deduction, cash funding | Invented USD-settled linear perps, separate wallets | Three fixed paths, four total account capitals, three cost levels | Fixed in cases.json before run | Illustrative, not a historical feature | All paths/depth/tiers/shock timing invented | Missing tier, funding or exit leaves net unknown; deficits never clamped |
| Named episode/outage | lab.stress.EPISODES[2025-10-10 liquidations]; 33-minute outage scenario | Existing named UTC window, public Binance incident duration as contextual reference | Invented events dated inside 2025-10-10..11 | No event-market history is read | No inference of actual venue state | Not a reconstruction of the cascade | No transfer before the stated expiry; failed transfer changes no wallet |

No predictor, fitted model, cross-sectional rank, p-value, survivor comparison or
alpha decision is generated. The fee and outage contextual sources are linked
in the existing carry intake; all numeric assumptions consumed by this run are
closed in cases.json.

## Rule or search space
Closed enumeration; no optimizer or winner selection:

1. **Displayed BTC depth:** two parent observations × four requested sizes ×
   three cost levels = **24 paired groups**, each with both directions (up to
   **48 directional rows**). Normalize units, aggregate same-price orders and
   respect the MEXC level bound. Compare the same base quantity. Report each
   side's filled amount/VWAP/quote cost, fee scenario, unmatched base inventory
   and complete-entry cost only if both sides are complete. All partial/blocked
   rows remain. Quotes are asynchronous conditional observations, not fills.
2. **Invented paths:** flat round trip; one-leg short liquidation after an upward
   gap with an attempted transfer during the outage; profitable-short ADL before
   a further drop and recovery. Total account capital is fixed at
   **$10k/$25k/$50k/$100k**, split equally into the two wallets. Three paths ×
   four account capitals × three costs = **36
   worlds**. There is no resampling or performance statistic.
3. **Capital and risk:** for account capital C, each virtual perp wallet is
   initially funded with N=C/2 and holds MID notional N (1x per leg, total funded
   capital C=2N). This differs explicitly from the per-order notional targets in
   the depth section. Quantity is chosen
   once. Entry/exit costs reduce wallet cash. Initial/maintenance rates and
   maintenance deduction come only from the supplied invented tier schedule;
   unsupported tiers remain unknown. A maintenance breach closes through the
   supplied book with the explicit penalty; ADL uses its specified settlement
   price. The partner wallet never recapitalizes a failed one implicitly.
4. **Cash order:** marks and explicit funding cash, permitted transfer attempt,
   forced/maintenance closure, then state report. Closed quantity stays zero at
   every later stage. Funding after closure earns nothing. Preserve all realized
   losses, negative cash and open residual quantities. Terminal net is available
   only if both legs are flat and margins/funding/exits were known.
5. **Before recovery:** export the separately labelled stage's net cash-plus-mark
   equity, each venue's cash and insolvency, then the later terminal value. A
   recovery cannot erase a previous forced close or create new inventory.

## Splits and cost
No training/test split or new strategy signal. Old BTC source data is seen and
selected diagnostically. The named 2025 episode supplies a date label, not an
unseen sample. At costs 1x, 2x and 3x, multiply each observed book price's deviation
from its own mid and each supplied fee/penalty rate; base inventory and displayed
capacity remain fixed. Reject a nonpositive stressed execution price. Funding
cash is not multiplied as an execution cost.

The synthetic venue rates/tiers are explicit assumptions, not MEXC/Lighter/OEM
risk-tier or account calibration. The snapshot fee scenario is likewise distinct
from authenticated fees. No historical margin, current capacity, executable net
return or future exit is filled in from a missing input.

## Gates
The prewritten independent `scripts/check_carry_execution.py` uses Fraction
arithmetic and raw BTC orders; it does not import the new Decimal kernel.
**ACCOUNTING_PASS** requires every predeclared depth/fee and per-wallet
cash/quantity/equity equality to agree within **$1e-12**, every closed position
to remain closed, the outage transfer to leave cash unchanged, and all partial
depth/unknowns to remain explicit. Any failed identity is ACCOUNTING_FAIL and
the run stops without selecting a replacement case.

Even ACCOUNTING_PASS leaves **M485 PARTIAL**: no qualified real matched tape and
venue tiers, current owner fees, actual fills, historical crash L2 or prospective
capital evidence. It earns only a bounded handoff for a new fully qualified
replay protocol. M484's EEA 403 is not an economic verdict.

## Null
Algebraic identities and missing-input controls, not a statistical null.
No random replicas, inference or significance claim. ACCOUNTING_PASS does not
mean SIGNAL, a profitable strategy, safety or current gate eligibility.

## Multiplicity
Zero predictive variants/trials. All 24 snapshot groups and 36 synthetic worlds
are reported without selection. Program trials before this freeze:
**9,784,343**, from `registry.program_trials('registry/rounds.csv')`. Report the
current program sum again with the result. This bookkeeping count is not an
effective independent-test count or a cross-family correction.

## Evidence lineage and admission (future lanes only)
Canonical M485, parent R312 conditional quote inputs and the owner's 2026-11-06
carry evidence review. R404's ongoing window, M469's future test and R413/R406
settlements are not consumed. The copied gate version is included in inputs.json.
No new prospective sample, strict-on-time day, calibrated null, power claim,
reserved read, admission, account or live order is authorized by this lane.

## Stop rules
One invocation after the freeze/input commit. Creating `results/` is exclusive
and preserves a failed sole attempt. A changed frozen runner, input or idea
requires a new R-id; no retry or extended set after reading an output. The checker
checks the saved result without running the measurement kernel again.

The rounds registration is append-only: its REGISTERED/PENDING row records
pre-run state and will not be rewritten. The native FINDINGS will carry the
completion/verdict and the M485 queue note will link it. This explicitly preserves
the owner's append-only rule instead of silently rewriting a historical row;
no competing registry or inferred status updater is introduced.

## Frozen input manifest

26db7b57f8a03e429e10f738005a89c341ce74ee228984a638c62a96da76a01a  experiments/carry_execution_v1/inputs.json
