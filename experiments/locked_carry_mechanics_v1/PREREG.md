# R407: exact fee-aware sizing and terminal cash mechanics for inverse carry

- **Registry id:** R407
- **Owner:** Codex; [room claim](https://github.com/SaikiK12/T/issues/7#issuecomment-6662160492).
- **Date registered (UTC):** 2026-11-05
- **Canonical method:** M244, a component extension of R327/R328; R335/R406 unchanged.

code_inputs.json SHA256: ae87392f9cd2d93c027213aa98b954142e7aded896778711963028ba253fb552

Freeze with `lab.prereg.freeze()` and publish this protocol, its manifest,
invented inputs and code BEFORE the recorded audit. Development assertions use
invented facts only. Full Python tests precede the lab-code commit. Append one
final registry row after this recorded run; R407 was claimed before any outcome.

## Question and exact scope

Can a fixed-cash inverse carry plan size its two orders on the declared grids
after fees, retain both quantities across cost sensitivity, and distinguish
terminal cash from residual coin and a continuous-conversion reference?

This is engineering qualification:0 predictive trials,0 prospective paper days,
0 market requests. It reads only the12 fixed invented cases in fixtures.json,
source notes and the code/manifest. No historical/forward return, live offer,
R406 journal, reserved sample, account, credentials or private endpoint is read.
No new signal, calibrated distribution, portfolio or capital decision is tested.

The18 computational/input files in code_inputs.json include the runner, new
module/tests, existing inverse cash/walker, native R406 rule and transitive local
imports, plus locked Python environment declarations and invented fixtures.
Verify protocol and every manifest digest before and after the audit.

## Fixed cases and calculation

The fixture IDs are zero_fee, depth_and_fees, spot_quote_fee, spot_base_fee,
coarse_spot_grid, exit_dust_above_ceiling, unknown_exit, exit_ratio_breach,
quote_minimum_unproven, thin_spot, unknown_fee, entry_fee_without_depth.
The two incomplete/thin cases named thin_spot and unknown_fee must block.
All other cases get the same3 fee tiers and their3 declared delivery prices.
Unknown exit conversion remains unknown; a declared floor/ceiling breach is
reported, not silently removed. All numbers are invented demonstration inputs.

`lab.locked_carry.plan_carry` fixes the spot base order and maximum fee-covered
inverse face on the declared grids at3x fees. The inverse entry uses
`sum(face_i/price_i)`. The same two orders are evaluated at1x/2x/3x, with unspent
quote and residual coin tracked. This maximizes fee-covered shown face within
the declared input cap, not expected profit, real capacity or an owner's stake.
Spot fee debit asset/basis is explicit; missing fees never become zero.

`evaluate_carry` charges delivery fees in delivery coin, rounds spot sale size
down and applies base/quote minima. Unsold coin remains inventory; it is not
credited as cash or a completed cash return. A continuous payoff reference is
separate. A conditional grid-cash floor requires the explicit ratio floor and
delivery-price ceiling, plus the minimum-size checks derived in SOURCES.md.
These limits are assumptions, not observed or probabilistic guarantees.

For each known exit world, a separate existing InverseCashAccount posts the
walked fills, a daily realization and delivery. Compare its cash after the
declared grid sale and retained dust exactly with the pricer. The cross-check
shares the book walker and planned spot inputs; it is not an independent
end-to-end sizing audit. Check next-grid maximality whenever shown capacity
allows another contract. The two legacy comparisons call the unchanged R406
rule only on invented books and record its native face/residual/payoff figures;
they never rewrite its first-read decision or any historical verdict.

## Decision, reproduction and limits

DATA_PASS means all declared exact cash/dust, fixed-size, maximality and valid
conditional-bound checks pass, with both incomplete cases blocked. A failure
remains PARTIAL with its exception/log; do not change frozen code or relabel it
as an economic null. This verdict qualifies a mechanics component only.

Run `python scripts/audit_locked_carry_mechanics.py --run`. The results file is
created exclusively and never overwritten. Deterministic reproduction may use
another new `--output` path under the SAME frozen inputs; it consumes no market
sample and cannot change a method choice. Keep the original result/log.

Bounds assume complete future conversion at the supplied ratio and compliance
with unmodeled maximum order sizes, ticks, fee rounding and venue conditions.
Future depth, leg risk, account permissions/fees, custody, exchange margin/path
liquidation, stablecoin/FX effects and the benchmark convention are not resolved.
No result here demonstrates positive expected return or authorizes an order.
