# PREREG: source-aware spot/perpetual quote costs and minimums

- **Registry id:** R325
- **Owner (single writer):** Codex; one bounded source reader/core reviewer
- **Date registered (UTC):** 2026-10-26

## Question and scope

Extend canonical M047/M134's missing input/economic-cost component. Do the
publicly advertised metadata permit both sides and the fixed modeled quantity,
and what conditional crossing/quote-commission cash must a later gross payment
cover? Compare full five-level with top-only depth at the SAME size; compare
explicit zero-charge and public-advertised quote-fee controls. No strategy
backtest, expected return, source-tradability relaxation or new empirical alpha.

R324 source/ledger/raw outputs remain frozen. R311 stays INCONCLUSIVE224/273,
selected2x/3xnegative; R321 stays NOT_ACCEPTED. No old dataset/winner/leverage/
missing-day rescue. M047 exact premium trigger/exit and M134 historical rule
remain open at these inputs; dated M244 and M170/R301 are not reinterpreted.

## Finite identities

- `code_inputs.json`: `4437ddb5106c1672e382cd3fe7430036982af23ed6138d7a1b1a537a88844889`.
- `inputs.json`: `29e83bfa3836ea6ad60c18e6bf1583f55cf610cadb55f18a622ec755d14d5bf2`.
- `fixtures.json`: `f715af66eb45f151cafb46aaf839513dff40a3aa923adf8672ce6160225eadd1`.
- `contract.json`: `d5a485d736d88c57330edd1266edb653e9816a02951651bf122a3d6a1194428a`.
- `sources.json`: `a8e42986b4e528a6ad0f230bf2ea24077a1a8e92ef9ba45f8a6897367ac5b684`.

Sources:6ordinary staticGETs184953bytes, exact read/unread/version receipts.
Official source says baseSizePrecision is minimum, NOT step; decimal precision
is not an actual increment. Public fees are not owner fees. REST depth has no
source quote clock; crossed official toy sample is invalid. Java ms example
and official proto link narrow earlier gaps but do not certify303/deployment.
Aggregate bootstrap ambiguity/finite-depth warning retained. No source GET is
left in this finite intake. Reuse old frozen perpetual metadata/depth units.

## One finite current input collection

Commit spec/code/contracts BEFORE dispatch. CURRENT public HTTP ONLY, up to
22GETs:1spot exchangeInfo CSV for BTCUSDT,WIFUSDT,SKRUSDT;3individual perpetual
metadata responses;3cycles x3fixed symbols x2depth books=18GETs. Do not replace
missing/unavailable symbols or fall back to another endpoint. Each depth limit5.
At most2simultaneous GETs (spot/perp pair),2second pause between cycles. Fixed
orderBTC/WIF/SKR. Max64KiB accepted body/attempt,2MiBcombined,6second absolute
response deadline plus up to1second cleanup reserved;22x7=154cumulative reserved
seconds. Max180seconds overall, no retry/redirect/reconnect. Stop future calls
on incomplete/access denial/redirect/429/451/5xx;400/404 remains unavailable.
Record request and completed-payload first-seen UTC/monotonic clocks BEFORE
JSON decoding. Preserve partial/error bodies and charged uncertain tails.
One durable attempt directory and acquisition budget; no refund or reset.

Seal+COMMIT raw inventory and hashes BEFORE offline costs. Replay verifies frozen
code and committed data, never collects or overwrites originals. Capturer reuses
existing bounded process worker, no foreign example code executed. No signed,
account/history/RPC/order request or real funds/secret access. No large download.
Original historical allowance stays7757/8000requests and reported229.85/250MiB
spent; exact remaining bytes unknown. New CURRENT scope is separately declared,
not a historical renewal. Transport/proxy/header/unread buffered bytes unknown;
accepted body bytes and conservative upper-bound reservations are distinct.

## Fixed cost, size and capital contract

Exactly9pair slots,36cost-control cells,108tier slots; retain ALL failures/nulls.
One q per pair from250/max(spotmid,perpmid), rounded DOWN to perpetual quantum
contractSize*volUnit and declared spot10^-baseAssetPrecision decimal grid. This
is an illustrative convention, not verified spot lot/tick or base-quantity
contract. q is unchanged by profile/fee/tier; top insufficient depth stays None,
never smaller size.250 is a reference MID budget, not guaranteed gross ordercash.

Current minimum base and both actual hypothetical spot buy/sell MARKET quote
amounts must pass their advertised bounds. Public status/API/direction/market
order availability must be explicitly open; unknown/false blocks numeric cells.
Perpetual must be linear USDT,int0state,apiAllowedTrue, within min/maxVol and grid.
Each wallet has5000model USDT, total10000. Check spot principal+entry fee <=5000
and futures1xmid reservation+entry fee <=5000. No transfers/FX or leverage-up.
Shared helpers use floats, so require distance>1e-8quote from min/max/cash boundary;
near-boundary ambiguity is unknown. Independent raw rational audit tolerance1e-8.

At pair receipt epoch require both request/availability ages<=2s, arrival skew
<=1s, UTC-versus-monotonic discrepancy<=50ms. No source clock fallback from
receive/version/system time. Passing local guards does NOT prove source age,
current report-time freshness, real session/fill or actual market availability.
ALL actual executable-pair eligibility staysFalse even if costs compute.

For supplied same-book ideal taker fills, spotBUY/SELL and perpSHORT/COVER,
quote crossing=spotbuy-spotsell+perpbuy-perpsell. Fee scenarios: zero-charge
floor or public takerCommission/takerFeeRate, both ONLY hypothetical quote fees.
Missing advertised rate stays unknown. It is not actual owner commission/asset,
promotion, rounding, latency or partial-fill evidence. Require exactly same q.
Cost tiers1/2/3 multiply crossing+scenario commissions without reselection. They
are cash hurdles, not actual stressed fills or a reoptimized policy. Reference
one-leg notional=q*mean(midprices); total-capital denominator10000. Do not book
entry basis as futures cash PnL, infer perpetual maturity/convergence or count
spread twice. No holding horizon, forecast or funding persistence is fitted.

For every computable1xcell, reuse frozen physical SpotCashAccount, PaperAccount
and pair snapshot under INVENTED model clocks. Four ideal quote fills/assumed
fees post once; source receipt hashes bind their underlying quoted inputs. Post
explicit UNKNOWN normalized funding so full NAV and net PnL remain unknown even
after model close. Only known four-fill price-fee component equals negative
conditional1xcost within1e-8. Reopen append-only journals identically; preserve
native local originals and immutable packed copies. Cash reference same total
10000has0four-fill component; no realized risk-equivalence/alpha claim.

## Verification, trial count and limits

Full required discovery passed1364tests/2skipentries in180.098s, including14new
functional/financial tests. Separate reviewer found status/grid bypasses before
freeze; correction checked in full earlier kernel at e7f2eac8 with8handcases.
Final bc682b8d boundary diff read plus2minimum-boundary cases checked. Review
scope is exact and NOT full collector/report/oracle/source authenticity approval.
No current market values/outcomes inspected by the reviewer.

After sealing data: run fixed36control cells, preserve108cost tier slots, reconcile
computed1xcells with common journals, independently rationally reconstruct raw
quotes/sizing/cost/capital and audit every journal chain. Reproduce packed outputs
via lab account --spot-costs in fresh directory without network. Any mismatch is
retained; changed frozen code requires a new lane. PARTIAL is bounded source/
conditional cost accounting only. No p-value/CI, calibrated positive expectancy,
dependent-null acceptance, strategy selection or prospective paper day is claimed.
Program entering9478970;0predictive/optimization strategy trials added. All36cells
and108tier slots counted as cost diagnostics, not independent market hypotheses.
Actual funding/fair notional, spot units/increments, owner fees/permissions,
source quote freshness, exit/latency/partials/margin and genuine future protocol
remain blockers. No activation/merge/closure or permanent execution guarantee.
