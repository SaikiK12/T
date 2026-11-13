# PREREG: carryhurdle_v1 (R483). Do the audited carry books beat holding sUSDe or lending USDC on Aave?

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R483
- **Owner (single writer):** Kiro sub-agent, task-websearch-pnl-wave FEAT-003, branch `claude/websearch-organization-and-maintenance`
- **Date registered (UTC):** 2026-11-13

Methods M478 (lending rate as the carry benchmark) and M481 (Ethena sUSDe yield as the benchmark), lens 5 (red team on
current leads). Gate 0 on seen carry rows.

## Question
Over each forward carry book's audited history, did its v2 daily net at 2x costs exceed the yield of holding Ethena's
staked USDe (sUSDe), with a Newey-West t of at least 2?

**Why it matters for the best-PnL objective.** sUSDe is paid mostly by perp funding, the same payer as the lab's
cross-venue carry books. If a passive token earns as much at lower operating load, running the books adds no value
over it. Aave v3 Core USDC supply (the same dollars lent) and the 4.13% bill hurdle of R437/R438 are reported.

## Universe
- The nine books in the committed daily nets (closed list, no other book):
  - `experiments/carry_v2_audit_v1/results/daily.csv` (R437): seven books.
  - `experiments/carry_v2_audit_kc_v1/results/daily.csv` (R438): two books.
- Columns `book, engine (v1|v2), date, net_1x, net_2x, net_3x`; daily return on book capital; costs 7, 14 and 21 bp
  per leg; dates to 2026-09-30. Current-survivor-only universes as in R275/R277.

## Data
- **Benchmarks.** DefiLlama yields `/chart/{pool}` bodies, public, no key:

| Benchmark | Pool | Role | Bytes | sha256 |
|---|---|---|---|---|
| sUSDe (ethena-usde, Ethereum) | 66985a81-9c51-46ca-9977-42b4fe7bc6df | decides | 160,643 | 4ad057baa24c7d6b18b02d7b66ca8f6832405127017e7ab19832ca8635073d06 |
| Aave v3 Core USDC (Ethereum) | aa70268e-4b52-42bf-a116-608b370f9501 | reported | 218,392 | 007e634e247ae349cd4c89b10b28a3b14b7f5a3a5229ed694adae1a377aaf87d |
| Aave v3 Core USDT (Ethereum) | f981a304-bb6c-45b8-b0c5-fd2f515ad23a | reported | 217,283 | 40bfab15bfda45d6a1cb00dd2baef6b5f8c4d1e9779b60a2de627802204babc7 |

- **Deviation from a live fetch, stated before the run.** DefiLlama's free yield endpoints stopped on 2026-11-13
  (the free OpenAPI spec: "The yield endpoints ... stop working on November 13, 2026"; re-fetched by the orchestrator
  at 2026-11-13 00:01 UTC). The three bodies were fetched once at 2026-11-12T23:41:27Z, before this PREREG, and sealed
  outside the repository (`/projects/sandbox/sealed_chart_20261112/`, backup `..._backup/`). Their hashes are the
  table above, committed in `research/intake/websearch_wave_20261112.md` (commit 3eff32c2) before this file.
  `scripts/fetch_carryhurdle.py` makes no request; it copies the bodies, their `.hdr` headers and `receipt.txt` into
  `experiments/carryhurdle_v1/raw/` (not `data/`, which is gitignored; these files are committed) and refuses any
  size or sha256 mismatch against the intake note. The 10.8 MB pools file is not copied.
- **What was inspected before this freeze:** the bodies' key names, timestamps, null counts and whether
  `apy == apyBase` (FEAT-002, recorded in the intake note), plus the first and last timestamp and the null count of
  `apyBase` of the sUSDe and Aave USDC bodies (this session). No APY or TVL value was read or printed.
- **Carry nets seen:** all nine books' daily nets, statistics and FINDINGS are public in the repo (R437, R438). Only
  the benchmark comparison is new. The author knows from general public commentary that sUSDe's yield was high in
  early 2024 and lower in much of 2025, without numbers for this series.

## Feature lineage and point-in-time availability
| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| Book net `net_c(b, D)` | R437/R438 v1, v2 daily nets | lab engines, book capital, fraction a day | UTC day D | committed 2026-11-10 | seen rows (gate 0) | current survivors (R275/R277) | none missing in the files; a NaN would be dropped |
| sUSDe daily rate `r_s(D)` | `apyBase` of the row dated D-1 | DefiLlama, Ethereum sUSDe, percent a year | snapshot near 23:01 UTC of D-1 | DefiLlama daily snapshot | yes, before D starts | latest-vintage capture of 2026-11-12 (DefiLlama may have recomputed history) | row missing or `apyBase` null: drop D, never fill |
| Aave daily rate `r_a(D)` | `apyBase` of the row dated D-1 | DefiLlama, Aave v3 Core USDC/USDT supply, percent a year | as above | as above | yes | as above | as above |
| Bill `r_b` | 4.13%/yr | R275's hurdle | constant | n/a | n/a | n/a | n/a |

- Benchmarks are latest-vintage: the capture is of 2026-11-12, and DefiLlama's history may have been recomputed.
  Known adaptor break: before 2025-04-08 sUSDe TVL was priced at USDe, which inflates `apyBase` if those rows were
  not recomputed (unchecked). The 2025-04-09+ sub-window is reported for this reason.
- No cross-sectional feature; lab.coverage's survival comparison does not apply.

## Rule (the statistic, `scripts/run_carryhurdle.py`)
- **Field:** `apyBase` (percent a year; equal to `apy` in every captured row).
- **Conversion to a daily simple rate (follows the field's meaning, intake note):**
  - Aave (`liquidityRate`, an APR, simple interest, 365-day year): `r = apyBase / 100 / 365`.
  - sUSDe (weekly-compounded annualisation of the latest 8-hour payment): `r = 52 x ((1 + apyBase/100)^(1/52) - 1) / 365`,
    the exact inverse of DefiLlama's formula. The `(1 + APY/100)^(1/365) - 1` wording of the plan is replaced by
    these two conversions.
  - Bill: `r = 0.0413 / 365`.
- **Alignment:** the book's net for UTC date D is compared with the rate from the benchmark row dated D-1 (the row's
  UTC date of its timestamp). A body with a duplicated UTC date is refused. A missing D-1 row or null `apyBase` drops
  D; nothing is filled.
- **Excess:** `e(D) = net_c(b, D) - r_k(D)` per book b, engine (v1, v2), cost c (1x, 2x, 3x) and benchmark k.
- **Window:** each book's dates from the benchmark's first usable date (sUSDe 2024-02-17, Aave USDC 2023-02-07, Aave
  USDT 2023-02-14) or the book's first date, if later, to 2026-09-30. Reported sub-windows: 2025-01-01+ and
  2025-04-09+.
- **Statistics per cell:** annualised mean excess (daily mean x 365, points a year); Newey-West t with 10 calendar
  lags and Bartlett weights (`lab.stats.newey_west_t`, the rule of R437/R438; dropped days are gaps); daily and
  annualised sd of e; max drawdown of the cumulative sums of the book, the benchmark and e; the share of the book's
  sum carried by its 10 best days; book and benchmark %/yr on the same days.
- Capital: both sides are returns on one unit of capital. The book nets are on total book capital (both venues'
  margin), so the comparison is like for like in capital, not in risk.

## Splits and cost
No split is searched. Costs are R437/R438's frozen 7, 14 and 21 bp per leg (1x, 2x, 3x); 2x decides. The benchmark
side carries no cost: no swap, gas or cooldown cost is charged to sUSDe or Aave. That favours the benchmark; it is
stated, not repaired.

## Gates (decision, frozen)
- **Deciders (6), from R437's and R438's FINDINGS:** the forward books
  - `gate+hyperliquid L14d th5% K20` (R278 A)
  - `binance+mexc L14d th10% K20` (R278 B)
  - `gate+mexc L7d th10% K20` (R278 C)
  - `binance+gate L14d th10% K20` (R390 A)
  - `gate+kucoin L14d th5% K20` (R279 A)
  - `binance+kucoin L14d th5% K20` (R279 B)
  - Not deciders: `binance+hyperliquid L14d th10% K20`, `binance+gate+hyperliquid+mexc L14d th10% K20` and
    `hyperliquid+mexc L3d th5% K20` (not forward). R294 (mexc+lighter) has no committed audited daily net and is
    out of scope.
- **Decision cell:** engine v2, cost 2x, benchmark sUSDe, full window.
- **Per decider:** BEATS if annualised excess > 0 and NW t >= 2.0; LOSES if excess < 0 and NW t <= -2.0; TIES
  otherwise (an undefined t is a tie).
- **Lane verdict:** PASS if at least half of the deciders (3 of 6) BEAT and none LOSES; NULL if at least half LOSE;
  PARTIAL otherwise. Registry verdict: PASS = CONFIRMED, PARTIAL = PARTIAL, NULL = NULL.
- Reported only, no decision: Aave USDC, Aave USDT, the bill, 1x and 3x, engine v1, the three non-forward books and
  both sub-windows.

## Null
None is built. The benchmark is the null: holding the passive token instead of the book. The verdict is the frozen
rule above. Power, from the published R437/R438 figures (SE of a book's annual mean is about its %/yr / NW t): 1.5
points a year for R278 A over 3.35 years, 1.3 for R278 B over 1.4 years, 3.9 for R390 A over 5.7 years. Over the
shorter sUSDe window (about 2.6 years at most) a BEATS or LOSES needs an excess of roughly 3 to 8 points a year,
so TIES are likely when the book and sUSDe are close.

## Multiplicity
- Trials: 6 deciders x 2 benchmarks named by M478/M481 (sUSDe, Aave USDC) = **12**. Aave USDT, the bill, the
  sub-windows, other costs and engine v1 are descriptive and add no trial.
- Program trials before this lane: 9,785,274 (`registry.program_trials`). The books were selected by R275's search
  (best of 560) and R277's replication rule; this lane inherits that selection.

## Evidence lineage and admission
- Canonical method ids: M478, M481. Parent rounds: R275, R277, R278, R279, R390, R437, R438.
- Samples already seen: every book net (gate 0 on seen rows). Fresh: only the benchmark series, not read before the
  freeze.
- `docs/GATES.md` SHA-256 at registration: e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926. This
  is a gate-0 benchmark comparison; it is not a gate pass, admits nothing to real money and changes no forward lane's
  frozen rule.
- No across-family selection control; the result is exploratory beside the forward lanes.
- **Risk is not equal on the two sides, and no number here prices it:**
  - sUSDe: USDe depeg (about 0.65 on Binance on 2025-10-10, venue-specific), 7-day cooldown (admin can set up to 90),
    sanctions freezes, Ethena's exposure to negative funding (Reserve Fund), custody and smart-contract risk, and
    sUSDe is not offered to EU/EEA residents, so it is a benchmark only for the owner.
  - Aave: contract and oracle risk, withdrawal limits at high utilisation.
  - Books: leg and venue risk (ADL, liquidation of a leg, venue failure, collateral haircuts), none priced by the
    archive.
  - The benchmark rate is DefiLlama's spot snapshot, not the realised sUSDe:USDe exchange-rate change.
- **Order:** this PREREG is frozen and the R483 registry row appended in one commit; the importer runs only after
  that commit; the imported raw files and receipt are committed; then the runner runs once. The #7 CLAIM is posted by
  the orchestrator, not by this agent, and is not posted before the run.

## Stop rules
One run. No new benchmark, window, conversion, alignment, lag or threshold after reading. If the runner fails on an
input check, the failure is reported; a changed input is a new lane. Post-hoc diagnostics may be added to FINDINGS,
labelled post hoc, with no decision.

```inputs
362b1342789a53dc0883efb916adcf1d355fb9a1a370a7cb6d610dd533804b58 scripts/fetch_carryhurdle.py
60d319f742467a6af287c120199419d2cbee16079be2a7261299dde17e394619 scripts/run_carryhurdle.py
70d00742773b3ed9e59e07cb4c6db7dd521930464f8aa9d8eb387d3169cb2913 tests/test_carryhurdle.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 lab/stats.py
3574d23d3218e86f32305e670c492091bc2d6aa65d2e8a72675be3971b66c508 lab/prereg.py
3de6b7f29a3a3d786474b3e48444b004357c6cf2e78715e1d963f9ffe6f5fa08 experiments/carry_v2_audit_v1/results/daily.csv
8a803454b473f2fdfdbf41eff19085f053c9f208518b928cf21561a17b47004e experiments/carry_v2_audit_kc_v1/results/daily.csv
13b6699d5cb07860fcea7d494e4f133458c6a032a09653d38945353281ca994b research/intake/websearch_wave_20261112.md
```
