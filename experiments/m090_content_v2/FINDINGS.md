# R374: signed content captured and replayed; forecast qualification remains blocked

Native outcome: **DONE / DATA_PASS for content/input engineering only**.
There is no eligible forecast, UTC interval, gate pass or PnL. Strategy trials
are zero; program trials remain 9,479,252 at this read. M090 stays BLOCKED for
prospective inference. Costs 1x/2x/3x: N/A, no trade or loss/PnL score.

## Actual execution and byte evidence

The exact code, public trust material, input manifest and PREREG were frozen
and pushed at `a843681f0a7dc94bd66ad7c5bd515024760c6a82` before the first
M090 market request. PREREG SHA256:
`cc863a87960278eaa08db4a2e4f513479fff80196367b037d555d5757b026ace`.

One five-request capture completed on Nov 2: two fresh CRLs, displayed funding,
history page one and the RFC3161 checkpoint. The selected DigiCert signer/policy
verified with exact nonce, imprint, CMS signature, EKU/chain and CRLs at signed
genTime. Reported genTime is `Nov 2 22:24:29 2026 GMT`; Accuracy is
**unspecified**, so no independently verified UTC precision is established.
This implementation supplies no UTC bound even if Accuracy were reported.

The raw responses preserve target `1793664000000` (Nov 3 00:00 UTC) and
provider-reported prior event `1793635200000` (Nov 2 16:00 UTC), without
rounding or assuming a cycle. Displayed/previous rates are 0.0001/0.000091
fractions per reported settlement. No target label, forecast loss, paired
comparison or trading return was computed. Page one is not schedule completeness.

The 11-file archive is 14,800 bytes, retained at data/m090_content_v2. Its
[9,792-byte public packet bundle](evidence/packet.tar.gz) has SHA256
`233bdd9f1b2530210fe97c1deee65726907a9219d30b0a5c01c50fe815e99d26`.
Extracted bundle bytes independently pass the same head-pinned archive audit.
The [bundle receipt](evidence/bundle.json) records sizes and hashes.

Retain this journal head outside the mutable archive to detect replacement:
`5141d37cceb267bb6e9c64ec62b24fdd009ad18e8aceca656403768e329f7aa1`.
The [first result](runs/first_read/result.json) and
[offline reproduction](runs/offline_reproduction/result.json) are byte-identical,
SHA256 `71d2ab3336ff334c1d8895d408ae46891403c89fd2ca1efcc92677dae112be01`.

Completed-archive restart was also executed with a network callback that raises
on every invocation. It returned identical result fields, zero network calls
and unchanged raw hashes ([restart receipt](restart_guard.json)). No retake,
background collector, hourly automation, reserved read, order or money action.

## Validation and exact limits

Full current local suite before the code commit: **1,987 tests OK, 3 skips**.
The 18 new offline tests use real ephemeral signing keys/chains and cover
nonce replay, wrong imprint/policy/signer, altered signatures, missing/revoked
CRLs, unspecified and explicit Accuracy, exact source ids/types, malformed
responses, overwritten local inventory, interruption/tail retention, writer
locks, symlinks/size bounds, frozen inputs and byte-identical replay. The
[validation receipt](validation.json) preserves command and full-log hash.
Metadata integrity: 0 errors / 14 legacy warnings; all 169 frozen specs verify.

A signature proves content under the authority's key, conditional on that
operator. It does not prove exchange truth, first availability, public
dissemination, physical storage survival or truthful UTC/key security. CRL
checks here apply at signed genTime, not a later revocation audit. Local wall
request times remain unverified; no observation is admitted by a deadline.

R374 changes the interrupted [R373](../m090_publication_v1/FINDINGS.md) scope:
it uses native OpenSSL ASN.1/CMS and a single post-publication seal. It does
not recover the lost code/manifest, implement R373's pre/post UTC intervals,
or qualify its candidate/label cohort. R373's exact frozen text is preserved
and must not be run against substitute inputs.

Still missing for a funding comparison: qualified source/UTC evidence and
previous-event completeness, fixed prospective cohort/schedule, on-time ticket
and later-label admission, dependent inference and power/stopping/family rules,
then a new frozen forecast protocol. This archive supplies none of those by
implication. R332's metrics-leak NULL, Claude's R380-R389 ownership and the
Nov 3/5 scheduled reads are unchanged.

## Replay

On the fixed source commit, with the raw archive restored and verified from
the public bundle, use a fresh receipt id:

```sh
python scripts/record_m090_content.py --lane experiments/m090_content_v2 \
  --action audit --run-id reviewer \
  --expected-head 5141d37cceb267bb6e9c64ec62b24fdd009ad18e8aceca656403768e329f7aa1
```

Audit makes no network calls. Preserve the expected head and pinned code/trust
inputs; a valid older prefix alone cannot reveal a missing later history.
The result's program-trials field reflects the checkout's register, so receipt
byte equality above is claimed for the recorded fixed checkout.
