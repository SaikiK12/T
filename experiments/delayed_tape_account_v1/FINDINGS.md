# R350 — PARTIAL: finalized data clocks and funded completed-subset accounting

The first-seen/finalized tape contract is implemented over the unchanged Tape.
The saved R348 trades now also pass a common-capital, native-account arithmetic
audit. **All six completed subsets lose at1x/2x/3x.** The primary's577completed
trades give **−44.468147 / −89.236161 / −134.004176 MODEL_QUOTE**, on the same
10000initial capital and1000entry-midpoint notional per trade. Its one missing
exit remains unknown; full-policy account PnL/NAV is NOT reconstructed.

Code/spec/input freeze **431087386a9bb1730453b812e699c61db955d2b8** was published
before new timing, row-cost or account calculations. PREREG SHA256:
`175de117a820ce54ea0adf5d5517f51d4bc51d29856be79c39d054f40bef6f9c`.
78local code/test files and118input identities remain bound. Publication used
the authorized connector after shell GitHub authentication expired; remote/local
Git trees and the imported commit SHA were verified identical. No credentials
were inspected or changed.

## Availability is a separate input

The old collector stores an exchange-second s and maximum book lag, but no
bucket-finalized clock. Trade aggregates have no receive clock. Tape's normal
drain waits2000ms after a second ends, record_tape flushes every600s, and terminal
drain(None) also writes unfinished seconds. Therefore a saved final row is not
certified available at s+1s. A future protocol may use a different provisional
feature, but must define and test that feature rather than silently substitute
the final aggregate.

New CausalTape retains original receive UTC/monotonic clocks for books AND
trades, contributing identities, connection, finalization and incomplete/error
states. Late arrivals never rewrite a released row. Exact duplicates retain
their original first receipt. Revisions, malformed data and late omissions
retain evidence and stop the connection's quality state. Later quality errors
cannot backdate knowledge. A copied/forged row is not this connection's issued
evidence. Terminal unfinished buckets stay incomplete; new connections start
with no inherited OFI/quote state. Actual execution readiness always remains
false: finalized feature availability is not fill/fee/session verification.

This was measured on the SAME archived R316 MEXC frames, with constructed1s
and600s replay processing schedules. They are not newly measured production
latencies and neither timer actually ran during the original capture. Both
end at the last actual received frame; no extra wait makes terminal data pass.

| Replay processing schedule | Distinct source buckets | Complete | Terminal incomplete | Median delay after exchange-second end |
|---|---:|---:|---:|---:|
| Every1s | 229 | 218 | 11 | 2925.785ms |
| Every600s, terminal at capture end | 229 | 218 | 11 | 33724.371ms |

Both use416accepted book updates,0invalid inputs, and0rows certified available
at their exchange-second end. These are the SAME229buckets under two schedules,
not458independent observations. Complete-row delay ranges2724.371–2925.785ms
for1s and2724.371–63724.371ms for the600s profile. Original first-seen clocks
are real retained receipts; processing clocks are replay constructions. No
source-effective-price, executable-depth, actual order or prospective inference
is made from this timing comparison.

## Exact exit-cost units and one capital budget

The new UTF8 exports contain5252saved completed trades across the same six
R348policies. Original absolute prices/base quantities and receive clocks are
absent. Each of18alternative PaperAccounts therefore explicitly normalizes
entry MID to100 and signed quantity to10:1000entry-midpoint notional.
Exit midpoint comes from the saved gross return. Entry/exit crossing is applied
once to its OWN midpoint, at the same1x/2x/3x costs. Source nominal0commission
remains a supplied scenario, not authenticated owner/API entitlement.

The old proxy subtracts both crossing costs in entry-midpoint bp. The native
account includes the small exit-price/return interaction. In the primary,
correcting that convention changes total PnL by only+0.000475/+0.000951/+0.001426
MODEL_QUOTE. It does not create an edge. Financial amounts, input ratios and
cash identities are checked exactly against independent rational arithmetic.

| Saved policy | Completed trades | Unknown exits in parent | Native completed-subset PnL1x | 2x | 3x |
|---|---:|---:|---:|---:|---:|
| theta0.5_h5 | 2586 | 7 | −178.928861 | −351.095344 | −523.261826 |
| theta0.5_h30 | 1457 | 13 | −117.276585 | −221.258566 | −325.240548 |
| **theta1_h5 primary** | **577** | **1** | **−44.468147** | **−89.236161** | **−134.004176** |
| theta1_h30 | 407 | 2 | −47.365998 | −80.917400 | −114.468803 |
| theta2_h5 | 122 | 0 | −10.309649 | −22.988980 | −35.668312 |
| theta2_h30 | 103 | 0 | −7.689123 | −18.622321 | −29.555519 |

Every alternative starts with ONE10000MODEL_QUOTE, never summed across policies.
Cash minus existing entry-notional reservations must cover a new entry. There
were0capital-blocked completed rows. The largest peak reservation across all
cases is7000.845729; the primary at3x peaks at4001.439014. This is the existing
unlevered model reservation, not an exchange-margin or equal-risk attestation.
All coin/time/cost controls remain; no winner, size or holding period changes.
No new leverage, compounding of size, deposit or second cash ledger.

The original unknown-exit trades are not in these completed tables. Their
timings/positions cannot be placed back into the account from a count. Thus
known-subset cash is not full-policy NAV, even if it ends flat. All whole-policy
PnL and actual expected-net fields stay unknown, including cases with0reported
unknown exits: actual prices/fills/fees, input clocks and moment-of-trade depth
remain unverified. No R348bootstrap, p-value, selection or source verdict was
rerun. The original NULL is retained.

Six separate invented native controls retain known flat exits versus missing
exits at all three costs. Flat-mid crossing loses0.08/0.16/0.24. Missing exit
keeps the position and1000.04/1000.08/1000.12entry-notional reservation, leaves
NAV unknown, and stops new entries through persistent PaperRisk. It never
manufactures a close or resets flat after a gap. These are financial contract
fixtures, not market returns or new prospective observations.

## Received scope, failures and checks

The original12GET transfer stays closed with six binary/nonUTF8 failures
preserved. After Claude supplied new files, a separately declared8GET scope
received the directory, six UTF8CSVs and hash manifest at ec1bb00. The seven
files contain990786normalized UTF8bytes; limits2MiB/body/12MiBtotal/120s tool
time. Both scopes are CLOSED. No raw tape, market, private/history endpoint,
model weight, login or secret acquisition. These metrics describe connector
returns, not measured physical HTTP bytes. Source SHA256/file lengths and Git
identities match. Original gzip correspondence is the producer's retained
claim; its bodies were not independently received. No full35-input R348source
reproduction is claimed.

- Required final suite **1597tests PASS**,3existing skips,225.782s. The earlier
 1594test pass is retained; the later suite includes the new UTF8account tests
 and final clock fix.17focused tests pass.
- Independent stdlib checker **170668checks PASS**: original receipt clocks,
 contributor identity, packet count/book/OFI, all5252rows at three costs, native
 per-event cash/reservation chronology, unknowns and six persistent fixtures.
 Clocks/financial values are exact; inherited floating book/OFI comparisons use
 the predeclared tolerances. It imports no production financial/tape/reporter.
- Fresh-run results, journal pack and audit are byte-identical. Runtime recorded:
 Python3.12.14,pandas2.2.3,numpy2.3.5,pyarrow26.0.0,websockets16.0. Python and
 file identities are enforced; the lockfile and actual package versions are
 recorded, not a claim that every package version is runtime-enforced.
- The test-only ownership context reproduces the two original read-only errors
 under pandas2.2.3+copy-on-write, then runs all10original financial assertions
 successfully on owned fixture arrays. Original test/market bytes, assertions
 and pandas options remain unchanged. Actual pandas3 was NOT tested; plain
 discovery there still needs the explicit wrapper or a future integration.
- A bounded reviewer found5material proof/clock/duplicate/error issues before
 freeze. Original/intermediate failures remain. Root regressions cover the
 fixes, including nonregressed error receipt time; the reviewer hit its usage
 limit before a final signoff, which is not claimed. A later reproduction-
 metadata attempt used the wrong interpreter; it failed before writing output
 and was corrected without rerunning financial results. See receipts.

R350 adds0new predictive variants. The six saved policies are R348's already
counted trials, not six new discoveries. Local registered trials stay9479022;
the disjoint upstream trials must also be considered before any future
inference. No old R33114-variant reservation is silently reduced to force a
branch-total match. No new calibrated uncertainty, dependent-null inference,
statistical CI or profitable expected-return claim follows from these identities.

R310/R311 and all original financial/collector/forward bytes remain intact.
Historical acquisition remains7757/8000requests/reported229.85/250MiB. No orders,
money, secrets, merge/closure, permanent service or prospective strategy day.

Reproduce offline in the recorded runtime, with fresh directories:

```sh
python scripts/run_delayed_tape_account.py --out /fresh/R350
python scripts/check_delayed_tape_account.py --out /fresh/R350
python scripts/check_level_fixture_ownership.py --out /fresh/R350-fixture-check
```

Use the availability wrapper only through a separately frozen future recorder/
strategy protocol with actual emitted clocks. Current collectors were not
automatically switched. Full account reconstruction still requires the missing
exposure chronology, original price/quote/depth clocks and actual fee/account
contract. This lane validates a data/accounting bridge, not an activated edge.
