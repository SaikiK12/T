# PREREG: cde_carry_screen_v1, fixed CDE/Kraken net proxy economics

Freeze with `lab.prereg.freeze()` and commit before reading price or funding
outcomes. Frozen files never change. New direction/rule/window needs a new id.

- **Registry id:** R424
- **Owner (single writer):** Codex, codex/cde-carry-economics-20261107
- **Date registered (UTC):** 2026-11-07
- **Claim:** issue7 comment6708499870; canonical M488

## Question
For two fixed fully funded opposing-perp positions on BTC/ETH, how much of
the historical funding cash **proxy** remains after actual current fees,
recorded-depth cost sensitivities, observed trade/mark-price basis changes
and separate-wallet losses? This is an exploratory gate0 conditional model,
not exact settled cash, a forecast, executable historical fill or gate1 proof.

## Universe
Only BIP-20DEC30-CDE/BIPZ30 against PF_XBTUSD, and ETP-20DEC30-CDE/ETPZ30
against PF_ETHUSD. CDE lot0.01BTC/0.1ETH, Kraken base units. Two established
current contract families; no cross-sectional rank or inclusion/exclusion
search and no assertion of historical owner entitlement. All4arms retained:
shortCDE/longKraken and its reverse, for each asset. No winning-side selector.

## Data
Fixed period **2026-08-10T00UTC through2026-09-07T00UTC**, the first28full
UTC days after the previously saved MDA history beginsAug9T02. Coverage-only
choice made before new prices or rate differences. Latest-vintage original
MDA bodies and existing Kraken absolute hourly rates/marks; no new funding
history fetch. R423 already gives16/16 exact contemporary field mappings;
that does not certify this older history or actual cleared cash.

Documented public CDE candles were acquired counts-only:10calls/142468bytes
including2tiny probes,4pages and4leading page fragments. Actual large-page
cap300differs from doc350. Each asset has670of674expected trade bars, with
exact missing starts **Aug14/Aug21/Aug28/Sep4at21UTC**. All672required CDE
payment timestamps,672Kraken funding intervals and673Kraken marks exist.
No missing rate becomes0. The frozen source note/coverage/receipts record
each URL, organizationCoinbase/Kraken, undated API publication status and
exact UTC access dates. Conservative historical charge7806calls/247546845
bytes remains below the original8000/250MiB; no allowance renewed.

## Feature lineage and point-in-time availability

| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| CDE hourly cash proxy | MDA rate/event_time × common base quantity × last completed CDE trade close | Coinbase CDE BIP/ETP, hourly decimal × base × USD/base | payments t with start<t<=end; preceding trade bar closes by t | history first receivedNov7; computed once after commit | no historical availability/mark identity proof; fixed holdings use no rate selection | latest vintage; rate mapping sampled outside this period by R423 | reject absent/nonfinite rate; last trade proxy explicitly stale when declared prior bar absent |
| Hypothetical cash-price envelope | same rate × prior trade low/high, signed endpoints sorted | CDE trade range, NOT certified funding-mark bounds | same fixed payments; last completed bar may be2hours old | Nov7 source intake after modeled dates | conditional uncertainty display only, no decision feature | no quote/VWAP/fallback reconstruction | no interpolation or0; undeclared gap or longer staleness fails |
| Kraken funding cash | absolute fundingRate × common base quantity with opposite sign | Kraken linear PF_XBTUSD/PF_ETHUSD, USD/base/hour | [start,end); timestamp is period start; wholehour cash at t+1h | savedNov6 latest-vintage raw responses | no rate-picking or forecast; existing R418 has already examined these parent histories | latest vintage, fully observed in fixed window | reject missing/nonfinite; never relative-rate conversion or zero fill |
| Entry/exit and basis proxy | CDE trade open at start/end; Kraken mark open at start/end | ownvenue USD/base prices | one fixed entry and exit; no rebalance | historical candles receivedNov6/7 | not contemporaneous order books or assured fills | current-survivor pair, historical revisions unknown | missing endpoint fails; basis changes stay in PnL |
| Execution/fees | R4215k family raw displayed drag/ownmid fractions; CFSE .02%+.12/contract/side; Kraken .05% | current European published tariff and Nov7 matched books | worst fraction per venue and side over both size-unit hypotheses and initial/delayed phases; reused proportionally at all model fills | observed/published after modeled period | **hypothetical historically**, no past tariff/book claim | current Tier1, no VIP or maker assumption | incomplete parent fill/family fails; costs1x/2x/3x all retained |
| Fixed quantity / wallet capital | totalcash10000 split5000/venue, common lot floor sized at3x worst entry cost | segregated USD, matched fixed base risk | same Q across directions and three costs; no notional rescaling | computed after freeze at first price proxy | fixed once, no future-rate choice or transfers | each venue funded independently; no borrow/yield | source prices positive, entry costs reserved, reject zero lot |
| Conservative liquid resources | ownwallet capital−entryfee+ownMTM+all negative funding, positive credits locked until exit | per-venue cash and CDE stale trade/Kraken mark proxies | every hourly boundary, no opposite-wallet collateral | exact policy timings unknown; deliberately no positive credit reuse | no claim actual CFSE liquidation rules or intrahour solvency | hourly proxy only, no margin tier/clearing admission | any wallet<=0 stops immediately; report pre-recovery state, no terminal recovery PnL |

## Rule or search space
4fixed economic arms ×3cost sensitivities =12cases. Q is the whole common lot
floor affordable from each5000USD wallet at3x worst entry price drag+fees;
the same Q is used across both directions and1x/2x/3x costs. Fixed Q, no
constant-notional rescaling, borrowed margin, transfer, re-entry, stop fitting,
rebalance, cash yield, fee-tier upgrade or adaptive best side.

CDE payment at t: position_sign_inverse ×Q×published_rate(t)×Pproxy(t),
where Pproxy is the close of the latest CDE trade hour ending by t. The
same bar's low/high gives an **assumed** envelope only; true funding marks
can lie outside it through midpoint/fallback rules. Declared missing bars
retain the older trade proxy (at most one extra hour), explicitly labeled.
This is neither a zero fill nor a freshness assertion. Kraken absolute
funding interval t-1h is credited/debited at t. CDE credits are also tracked
at t, but **all positive funding on both venues is unavailable for margin
until exit**; negative charges consume own cash immediately. This does not
claim broker posting times or permission to spend accrued credits.

Entry/exit trade proxies receive adverse ownvenue price drag from R421.
At costmultiple m, multiply drag and tariff rates/fixedcharges bym, with
percent fees charged on the resulting execution notionals. Add both CDE
fixedcontract fees. Separate signed basis-PnL, slippage, percentage/fixed
fees and funding; do not call crossvenue price level a profit. Terminal
wallet addition must equal the reported net. Hourly conservative negative
cash+MTM cannot be subsidized by the other wallet. If a wallet falls to0,
stop before later recovery and suppress terminal PnL. No inference that a
positive wallet satisfies actual venue maintenance or intrahour risk.

## Splits and cost
No out-of-sample, holdout, prospective score or newly independent days.
Existing Kraken parents already examined by R418; CDE values newly consumed
after freeze but ex-post history remains exploratory. **Costs1x/2x/3x** all
reported on10000USD total cash, not a single leg or minimum margin. No APR
extrapolation, Sharpe, p-value, confidence-of-profit or strategy selection.
Price envelopes are conditional scenario ranges, not confidence intervals.

## Gates
Full synthetic suite, integrity, staged catalogs and committed closure before
source price/rate measurement. One exclusive run marker before value load.
Native verdict is always **PARTIAL_PROXY_ECONOMICS_ONLY**, independently of
profit sign: true cash marks, historical book/fee/vintage, actual maintenance
and France owner entitlement are unqualified. Any wallet<=0 is terminal
CONDITIONAL_CAPITAL_DEFICIT with no recovered profit. Any source/parse failure
is consumed ERROR and cannot be repaired/rerun. Independent Decimal checks
of rounded account identities use fixed1e-8USD display tolerance, never a
fitted field-matching tolerance. No live paper or real admission.

## Null
No statistical null/p-value; the economic diagnostic is whether each fixed
conditional net is above or below zero after every cost level. Report every
case, never a selected or aggregate winning strategy. Conditional positives
require new prospective evidence and cash/execution qualification. Conditional
negatives reject only this defined proxy/cost scope, not all possible carry.

## Multiplicity
**4economic arms** count in registry; cost sensitivities and display envelope
endpoints are not independent strategies. Program trials before registration
**9784345**, after adding this lane **9784349**, reported again through
`registry.program_trials('registry/rounds.csv')`. Raw total is bookkeeping, not
an independent-test count or across-family correction. No significance claim.

## Evidence lineage and admission
M488. Parents R418 (Kraken cash mechanics/current fees and examined histories),
R419/R420/R421 (recorded paired inputs/cost arithmetic), R423 (sampled exact
rate-field identity). Owner objective is net cash, not a gross funding chart.
This lane adds a bounded cost/basis/segregated-cash diagnostic while leaving
source cash/mark, capacity, legal and one-leg stress admission unresolved.
No claim of a fresh family or unseen Kraken holdout. No dependent-null,
strict on-time prospective days, trimming, leave-two-coins-out or80%power
calculation; these requirements are **unmet**, not waived. Copied GATES SHA:
e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926. No reserved sample, across-family selection or future-date read.

## Stop rules
One window, two named assets, two fixed sides and three costs. No subsequent
lag, scale, mark proxy, fee, capital, source, holding-window or direction fit
on these outputs. New idea needs new id/sample. No HTTP in runner, native
forward tick/journal write, paid/large download, protected2020/MEXC/reserved
row, denied-resource retry, account/credential/order or subagent. Acquisition
markers are consumed and cannot be reset. Preserve nulls/errors/deficits.

## Frozen input manifest

7666b1f080bdf2232eadaa3802e62567c3236b4a28bb6ce196213e8472011096  experiments/cde_carry_screen_v1/inputs.json
