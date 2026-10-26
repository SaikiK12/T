# R322 — PARTIAL: encoded funding application located and modeled; API cash remains unknown

Freeze **3b46654c63962682c7580bf9a6eea6859fb4901d** was pushed before the production component
fixtures. PREREG SHA256 **9417528d4aefc3ae933700eafe12bf4b4fb1baee21982ae4358bc5844007ddd3**.
No market strategy, historical R311 result or R320/R321 inference is rerun.

The new component connects the located source equation to the existing common
PaperAccount, with segregated model buckets, persistent journal replay and
start-state deduplication. It is available through the same lab command:

```sh
.venv/bin/python -m lab account --funding-prefix --out /tmp/R322-reproduction
.venv/bin/python scripts/check_funding_prefix.py --directory /tmp/R322-reproduction
```

Use a fresh output directory. Existing outputs/journals are never overwritten.
No market/source download, secret or running service is needed to reproduce.

## What the primary code establishes

Four previously unreceived files under official prover tree object
`16c0f36d75f2306ee242e26e507e4c237f7f4074` locate the missing helpers:

`F_collateral = signed_size_integer * quote_multiplier * (old_checkpoint - market_prefix)`.

There is no second rate/index multiplication or division in the received
funding helper. The market prefix already includes encoded index weighting.
The separately written risk valuation has the same algebra. Trade code accrues
OLD inventory, routes funding, advances the checkpoint and THEN resizes it.
New size must not receive old funding, nor may a close/flip discard old accrual.
Isolated funding belongs to its allocated margin; adding it again to cross cash
would double count. The model preserves separate account/strategy/margin buckets.

Conditional `F/10^12` is a USDC collateral-unit amount. It is not the public
historical Funding.value definition, rounded wallet balance or authenticated
paid cash. The complete persistent cross-account caller, imported signed
arithmetic/overflow/division constraints, deployed-version correspondence,
authentic encoded state/public prefix history and decimal epochs remain absent.
The tree object is not claimed to be a deployed or historical commit.

The partial aggregate-margin component divides by10^6 before comparing old/new
values. In the explicit floor model, F=-1 internal collateral unit changes the
component by -1 micro-USDC when old margin=1,000,000, but by0 when old margin=
1,000,001. Both conditional collateral amounts are -10^-12 USDC. Prior remainder
matters; neither aggregate change is added as a second funding payment. Imported
helper semantics and the full aggregate route are not established by this model.

## Fixed component/account evidence

All **216** integer-product cases and **25** partial rounding cases match the
separate rational reconstruction exactly. All **48** account/path/cost/control
runs reopen identically. All **84** renamed funding receipt pairs are suppressed
as duplicates. Endpoint/size/mode revisions from the same start require
reconciliation; a genuine advanced start has a new economic identity. Provider
labels and receipt provenance are retained separately in observations.

The full fixed family includes two controls and1x/2x/3x fees. These are invented
flat-price fixtures:1,000,000 encoded size units per physical base, price100,
Q100 and2bp per filled notional are declared only for the harness. Total model
capital is10000, segregated5000/5000, with declared1:1 USDT/USDC quote equivalence.
These inputs are not actual API scales, owner fees, fills or comparable-risk
strategies. Source authenticity/exposure is not established by synthetic fills.

| Funding-component fixture | Net1x | Net2x | Net3x |
|---|---:|---:|---:|
| Long hold | -0.24 | -0.28 | -0.32 |
| Short hold | +0.16 | +0.12 | +0.08 |
| Increase | -0.38 | -0.46 | -0.54 |
| Flip | -0.08 | -0.16 | -0.24 |
| Close early | -0.14 | -0.18 | -0.22 |
| Isolated short | +0.16 | +0.12 | +0.08 |
| Missing prefix | unknown | unknown | unknown |
| Unverified encoding | unknown | unknown | unknown |

All24 no-funding controls are retained: long/short/close/isolated/missing/
unverified paths lose0.04/0.08/0.12 in their flat-price model; increase/flip lose
0.08/0.16/0.24. Cash reference has no activity/net0. Unknown funding never becomes
a known zero total. The short's positive invented payment is not an edge or
prospective day; the sign and amount were inputs, not predictions.

For the simple hold fixture, covering model round-trip fees alone requires
favorable funding exceeding0.04/0.08/0.12 at1x/2x/3x, or400/800/1200 encoded prefix
units for its declared q and Q. In general the component hurdle is
`q*Q*(C-P) > total_cost_USDC*10^12`. Actual entry/exit crossing, own impact,
financing, recovery and margin risks must also be supplied; these toy fees do
not replace R317/R318's original cost assumptions or improve R311 expectancy.

## Verification, received scope and limits

- Full required unittest discovery passed **1304 tests,2 skip entries** in
  179.724s. Ten new financial hand fixtures cover sign/units, old-size ordering,
  unknown clocks/epochs, domain/overflow, dedup/revisions and partial rounding.
- One bounded reviewer found duplicate-start and encoded-domain blockers; both
  were fixed and rechecked BEFORE freeze. Exact reviewed hashes and limitations
  are in math_review.md. Runner/full fixture family and full protocol were not
  independently signed off.
- The frozen rational checker reconstructs all216 products,25 partial margin
  cases and48 account decompositions/total-capital denominators/84 updates from
  saved inputs. It shares source interpretation and supplied inputs; it does not
  execute Rust, independently authenticate market state or prove a live route.
- **51 deterministic artifacts** reproduce byte-for-byte through the shared
  account CLI: results, observations, audit and48 append-only journals.
- Six distinct newly read source scopes and exact URLs/body/blob hashes,
  versions/access/BUSL headers/read/unread ranges are in sources.json and
  source_review.md. Cached constants/position snippets are distinguished from
  new reads. Four static GETs used322994 body bytes within the declared bounds;
  bodies remain ignored cache, not a mirrored repository.

R321's earlier "application not located" gap narrows to application helpers and
trade checkpoint ordering now read. Full API/persistence/authentic-state binding
remains unverified. Raw Funding.value strings are not coerced into encoded
prefixes. Even computable unverified observations post only pending cash to the
model ledger. No actual market net return is known at1x/2x/3x. No statistical
significance or market calibration is inferred from deterministic fixtures.

All407 prior source-method objects/alias bytes and old journal prefixes are
preserved; the existing M409 row/intake receives supplementary scope only.
This lane adds **0 predictive trials**: engineering cases are fully enumerated,
not a strategy sweep. Program trials remain9,478,938. R311 stays INCONCLUSIVE and
negative at2x/3x; R321 remains NOT_ACCEPTED. New prospective days0, activation0.
No orders, money movement, secrets, market/history/account/RPC acquisition,
weights, paywall/login bypass, merge, PR closure or permanent execution.
Historical approval remains7757/8000 requests and reported229.85/250MiB spent.
