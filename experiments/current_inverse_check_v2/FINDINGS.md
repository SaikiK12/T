# R341 — PARTIAL: exact fee-reserve and whole-capital hurdles verified

**37,228 independent checks PASS.** Checker freeze `6b93e42` preceded the corrected
audit of unchanged R340 bytes. The original R340 type failure, code, economic
results, source failures and nulls remain intact. No economic reporter or market
strategy was rerun to obtain this pass. Executable expected net return UNKNOWN;
predictive trials0, prospective days0, activation false.

## Economic result

An inverse carry's ideal one-times argument needs NET coins after fees to cover
the summed inverse entry cost. With short USDface Q and residual coins D, model
coin equity is Q/M+D. The same exact-coin hedge can lose that property when fees
are paid from the collateral. Across all129published rounded R335 ticket metadata
rows at1x/2x/3x, both spot fee-debit conventions are retained. The old-rate control
has774negative unreserved residuals; the774zero-charge controls have zero residual.
Each negative residual has a literal positive-mark counterexample in the oracle.
This is not an observed liquidation or a prediction that such a price will occur.

Explicit exact prefunding gives0model-coverage failures in those algebra cells.
For base-debit spot fees, the amount to buy is `(hedge+future coin fee)/(1-spot
rate)`; quote-debit fees instead increase quote expenditure. The guard handles
upward step rounding and unknown fee currency without inventing a source rule.
R335's assumed fees stay10bp spot each way and5bp future at fixed1x/2x/3x; no
zero-fee entitlement or new lower rate is selected. Its actual venue/debit terms
remain unverified. R335's original annual return and DATA_PASS are not rescored.

The new sale hurdle compares the same ENTIRE capital, including idle cash once,
against the final delivered-coin sale. Delivery/TWAP, executable sale and
USD/quote conversion remain distinct. A residual from rounding leaves a future
price dependency. Unknown actual fee/settlement/sale inputs keep actual cash and
return unknown even if the conditional algebra is positive.

R340's72old R328 guard slots retain54known conditional inputs and18missing
ETH top-depth slots, across fixed1x/2x/3x and original settlement-price scenarios.
These are old Deribit inputs, not current Binance quotes. The actual future
sale/settlement ratio remains unknown for every row. The cash control is
uninvested same-quote cash, not a new T-bill result or equal-risk certification.

## Current input blocker and precise scope

All12BTC/ETH × current/next-quarter ×1x/2x/3x current-input slots remain unknown.
The one attempted Binance documentation page returned302, not followed; its
COIN-M exchange-information API returned451. No spot/depth endpoint, other page,
history, order or account was requested. No Binance contract-count/depth parser
or unit/margin certification is claimed after that access failure.

New finite budget CLOSED at2attempts/362actual body bytes,1MiB/16s conservative
charges.14unused slots stay closed; no replacement, retry, redirect or region
bypass. Historical7757/reported229.85MiB and the old66-request source batch are
unchanged. The source-access manifest preserves received/unread scope and hashes.
No new semantic primary method was extracted from access-denial bodies.

## Correction and validation

The frozen R340 oracle's zero-charge arithmetic creates exactly1.0 via integer
division. Its otherwise exact hurdle then becomes a float and fails equality
against a Fraction. R341 canonicalizes the original helper's numeric arguments
to exact Fractions; noninteger/nonfinite floats are rejected, not rounded. It
invokes the literal original helper with every original exact assertion. There
is no tolerance, selected-row skip, gate change or frozen-file edit.

- Before R340's lab commit: **1,537tests PASS,three skips,194.312s**.
- R341:13relevant targeted tests PASS, including two new tests reproducing the
  original failure and rejecting wrong ratios/noninteger floats/NaN/infinity.
  No claim that a1,539test full local suite was rerun for this checker-only change.
- All1,548normalized algebra cells,72held guard slots and12current nulls remain.
  The corrected oracle performs37,228checks with no failure.
- Two fresh reports produced identical compressed R340 result and summary bytes.
  Two corrected audits produced identical JSON:
  `166a04242a6a5707ce448ab3ef395e39bd96cd8643b7b15033596d17f497dab9`.
  R340 result SHA256:
  `bdd17375854913a1c42e150b0a80304ea1423aa3c5eeba9be372bf55bc480cfc`.

```sh
python scripts/run_current_inverse.py --out .cache/r340-fresh
python scripts/check_current_inverse_v2.py --out .cache/r340-fresh
```

Use fresh output paths and the pinned runtime/closures. The original
`check_current_inverse.py` still fails as preserved. `audit.json` is the corrected
independent result; parent `oracle_failure.txt` is the original failure.

The bounded reader supplied the core invariant but did not deliver a full note
after the environment restart; it was interrupted without a completed-review or
executed-probe claim. Independent verification here is the separately written
standard-library oracle. No authenticated source, actual owner fee, margin rule,
matched realized risk, market net return or new prospective evidence was verified.
Program9,479,013 unchanged; no new policy/coin/threshold selection or method queue.
No orders, money, secrets, historical/model download, merge/closure or scheduler.
