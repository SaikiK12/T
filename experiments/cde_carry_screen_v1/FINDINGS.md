# R424: static CDE/Kraken carry fails this conditional cost screen

**Native verdict: PARTIAL_PROXY_ECONOMICS_ONLY. Economic diagnostic: all4fixed
arms are negative at1x,2x and3x costs**, including every upper endpoint of
the stated hypothetical trade-bar cash-price envelopes. No side, period,
mark proxy or fee was changed after this result. This is evidence against
this static pair/window under the stated model, not proof of no carry edge.

The fixed period is **2026-08-10T00UTC to2026-09-07T00UTC**,28days and672
funding hours. Total initial capital **$10,000**, segregated **$5,000/venue**,
matched fixed **0.07BTC** or **2.6ETH**. Quantity was sized once at3x worst
entry costs and is identical across both directions/all three cost levels.
These are opposing linear futures, no borrowed spot or constant-notional
resizing. No cash yield, transfer, re-entry or changing strategy.

All values below are **USD per $10,000 total cash**, conditional model values,
not realized broker returns. Basis changes remain included.

| Fixed arm | Funding proxy | Gross basis PnL | Net1x | Net2x | Net3x | Net3x hypothetical range |
|---|---:|---:|---:|---:|---:|---|
|BTC short CDE / long Kraken|3.14|-1.48|-8.26|-18.17|-28.08|-28.20 to -27.99|
|BTC long CDE / short Kraken|-3.14|1.48|-11.58|-21.50|-31.42|-31.52 to -31.31|
|ETH short CDE / long Kraken|8.83|2.60|-5.72|-22.87|-40.03|-40.24 to -39.84|
|ETH long CDE / short Kraken|-8.83|-2.60|-28.60|-45.76|-62.93|-63.12 to -62.71|

For shortCDE/longKraken, BTC's funding proxy is **$3.135583458315** over the
whole period, versus **$8.794834133482fees +$1.117437443395price drag** at1x
and **−$1.482111419264basis PnL**. ETH's funding proxy is
**$8.833212971100**, versus **$14.291861148076fees +$2.861232828249drag** and
**+$2.599605095334basis PnL**. The economic surplus is too small to pay the
modeled execution costs. No annualization or statistical significance claim.

## Independent wallets and what this does not prove

All12cases completed the hourly proxy checks without a capital-to-zero stop.
There are **16,128 individual hourly wallet checks**. Positive funding was
withheld for the entire hold; negative funding immediately consumed its own
wallet. No gain or credit on the opposite venue could finance a losing leg.
For example, ETH shortCDE at3x has a minimum conservative CDE wallet of
**$3,355.672319834747**, despite matched opposing base exposure. A combined
delta hedge therefore does not remove the separate liquidity requirement.
This proxy is not an observed liquidation, actual maintenance check or an
intrahour worst-case bound. No10Oct2025one-leg/ADL stress was added to this
2026screen; M485/R417's separate stress scope remains partial.

The CDE cash mark is **last completed trade close**, and low/high is only an
**assumed** scenario envelope. Four missing prior trade bars retain a one-
hour-staler reference per asset/case, all flagged in the report. True funding
marks can lie outside the range through the documented midpoint/fallback
rules. No missing payment rate was filled with0. Kraken funding uses the
qualified absolute USD/base/hour rate without another mark multiplier; its
period-start hour is credited/debited at the next hour boundary.

Current CFSE regular fees **.02%notional +$.12/native contract/side** and
Kraken Tier1 **.05%taker/side** are applied to all modeled fills. Source fees,
organizations, dates and exact earlier quoted clauses are in the frozen
[parent source notes](../../research/intake/funding_notional_20261103/).
Adverse ownvenue price drag is the worst per-side fraction from R421's fixed
5k-depth family across both unit hypotheses and both initial/delayed books.
That Nov7depth and current tariff are **hypothetical historically**; neither
old execution/fill quality nor August fees are certified. Percentage fees
are charged on slipped execution notionals, fixed CDE fees on both sides.
**1x/2x/3x** multiply both fees and drag; no maker, VIP or fee-tier assumption.

## Scope, evidence and admission

**Out-of-sample/live: no. Costs: partly, current real tariff and recorded
friction under historical execution assumptions. Evidence grade C, conditional
backtest model only.** Existing Kraken parent histories have already been
examined by R418. New CDE prices were consumed after registration, but they
are latest-vintage ex-post data, not prospective strategy days or guaranteed
point-in-time owner access. R423's16exact contemporary field pairs qualify
one sampled rate mapping, not historical paid funding or mark cash.

Capacity is **not admitted** even at10k, and25k–100k accounts were not tested
by this economic lane. R421's displayed-depth/cost cases remain separate,
not inferred fills. CFSE cash-mark/posting rules, historical revisions,
actual margins/liquidation/ADL, historical depth and owner France eligibility
remain open. This result meets no gate1/real threshold; **M488 stays PARTIAL**.
It supplies no reason to promote this static pair to a trading account.
A changed rule must use a new id and appropriately fresh sample.

## Reproduction and consumed run

The **241-input** closure was frozen as
`7f07dddd39592cecb76e66b5bd09579eabc71c58b321b3054e2e13fb328cecbd`,
committed/pushed **3760ae21** before one measurement.
[Run marker](results/RUN_STARTED.json) and [complete report](results/report.json)
retain all12cases, signed cash/fee/basis components, each hourly wallet
and every stale reference. Report SHA256:
`3107c377406c9e19e2535dbc1b25613eba025d078bc78f75e9eb372ec524799c`.
An [independent Decimal check](results/independent_accounting.json) passes
**96account identities** at the frozen1e-8USD display-rounding tolerance;
this checks arithmetic, not realism or alpha. No second strategy run.

[Validation](validation.json): **2,563tests OK,3skipped,373.575seconds**,
12new synthetic tests including cash units, ownwallet failure before recovery,
missing/stale source handling, current-depth worst-case selection and source
receipt hashes; integrity0errors/14legacy warnings; staged catalogs match.
**4economic arms** registered; read against
`registry.program_trials('registry/rounds.csv')` = **9,784,349** at the run.
The cost/envelope endpoints are sensitivities, not independent alpha trials.

The [source intake](../../research/intake/funding_notional_20261103/coinbase_carry_candles_20261107.md)
keeps every primary URL, access time, raw hash and premeasurement coverage.
Only10bounded GETs/142468client bytes were added, all before freeze with
counts-only inspection. Original historical allowance was not renewed:
conservative total7806calls/247546845bytes remains below8000/250MiB.
The runner and accounting check make **no HTTP**; no native journal, order,
account, credential, reserved data or subagent was used.
