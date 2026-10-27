# R345: account-specific fee documentation, not an owner fee response

Two new ordinary public STATIC documentation GETs returned200 on2026-10-27:
22,537bytes for the account-module index and47,905 for its directly linked
Get Fee Details page. Total70,442bytes,0.912s recorded wall, within declared
2attempts /2MiB total /1MiB per body /15s per attempt /40s wall. No redirect,
retry, alternate host, login, key, account, market, history or order call. Scope
is CLOSED; no prior source, R340, R343 or historical allowance is reused.

The bounded reader completed acquisition, then failed on its usage limit before
semantic review. Root verified both cached body hashes and completed this read.
The original acquisition receipts retain read_scope=pending; this later note
records the completed read without rewriting those capture-time receipts. Raw
HTML stays in ignored cache, not a public mirrored documentation corpus.

Index read: navigation/link identity for Get Fee Details only, not every account
API. New page read: complete HTTP method/path, permission/rate-limit statement,
request/response field tables and response example through the final field.
No linked authenticated page or API endpoint was followed.

Exact page: https://www.mexc.com/api-docs/futures/account-and-trading-endpoints/get-fee-details

SHA256 c5cb5380faaedb2596069d97d6604a7fc400e16be3f4d5bfb9794635dc205265.
Index SHA2564976b3b220bfbcbe551cfa52da78fad94f655036f89067301cb5eee0f0d356b3.
This is an unversioned received-page identity, not a historical or deployed fee
version. See source_receipts.json and source_link.json for exact URLs/clocks.

What the received page says:

- Documented method is GET /api/v1/private/account/tiered_fee_rate/v2. Required
  permission is View Order Details; stated limit20calls/2seconds. We read its
  DOCUMENTATION and made ZERO calls to that private method.
- Optional symbol asks for fee information under that exact contract. Public
  instrument metadata and an unscoped fee response cannot substitute for this
  account/instrument binding.
- originalMakerFee/originalTakerFee are labelled original fees;
  realMakerFee/realTakerFee actual fees. joinDiscount versus enjoyDiscount and
  joinDeduct versus enjoyDeduct are separate states. Do not multiply reported
  real* fees by discountRate or deductRate a second time.
- Modes NORMAL, LEVERAGE and TIERED have different schedules. Leverage entries,
  volume statistic mode ROLLING/FIXED, fixed start/end, tier amount/effective
  days, specified contract ids, zero-fee volume exclusion and leverage labels
  are separate fields. A top-level zero is not a proven future flat fee.
- Example: BTC_USDT, TIERED/FIXED, top-level realTakerFee0; first tier0 through
  amount10,000,000, next tier starts10,000,001 with realTakerFee0.0002. Its fixed
  timestamps1760544000000..1763049600000 precede this2026inspection. These are
  PUBLIC EXAMPLE values, never an owner balance, current promotion or paid fee.
  documentation_example.json retains only the small fee-focused subset.
- The table calls tieredContractIds a string but the example is an integer
  array; the exclusion field's name/prose are not a complete eligibility
  algorithm. Do not invent tier selection, volume charging or future validity.
- Rate fields say decimal; this page does not explicitly define fraction/bp
  scaling, fee-debit asset, an effective-value/as-of clock, future fee promise,
  independent API/UI exemption or current owner entitlement. The earlier R317
  fee-calculation guide supports a nominal fractional worked example, not proof
  that every field in this endpoint has authenticated owner-effective units.

Engineering consequence: decode only explicit fee fields. Never copy or read
walletBalance, KYC/account data or unknown sensitive fields into the adapter's
output. Public metadata, official examples and unverified redacted exports
cannot authenticate themselves. Keep their model hints separate from actual
fee evidence; missing proof sends None/state=unknown into the existing
opportunity and account-risk guards, without crediting account cash.

Remaining unread/unverified: actual owner fees, permission, route, region,
account type, fee-debit asset, charged fills, future quota/tier transitions,
precise endpoint scaling, settlement conversion and source effective time. No
private evidence was requested. This narrows R317's earlier unfetched-page
scope, while preserving its historical notes and all old source objects.

Economic scenarios0/4/8bp per side are explicit sensitivity assumptions:0 is the
old R336 spread-only convention,4 is R317's generic public-rate context,8 is the
existing lab API reserve in GATES. None is certified as the owner's current
API fee. R336's40missing original market inputs are not fetched; its published
three-decimal cost medians require numerical bounds and uncertain membership.
Do not claim an exact R336 reproduction, fresh holdout, actual account NAV,
calibrated confidence interval or prospective profit from this source reading.
