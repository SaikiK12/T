# R259 unlocks_funding_bounds_v1: fixed unlock accounting and collateral envelope

- Registry id R259, claimed in issue #7 before work; single writer Codex.
- Runner SHA-256: `12b16153065b78863ba1c4293cb1a0beedaa4cd873b19cf0aa8f0896bd22c31e`
- Inputs SHA-256: `fd6c20d862b43b899f56bc5425359793953ce2a7cee0aea28005871a576667b7`
- Source acquisition/package committed in c17f240 (#31), stacked on R258 (#29).

Freeze and commit/push this specification, INPUTS and runner before calculating
any new funding-adjusted or mark-risk outcome. Verify all hashes on every run.

## Question and prior exposure

The exact R258 daily-price event diagnostic is already known: 421/530 priceable,
positive price-only mean after fixed 20/40/60bp, six losses over40%, and the STO
traded-high excursion of +1622.8%. We have also read timestamp-only coverage from
the newly acquired funding/mark files: a common missing mark date2026-06-29 and
other gaps. Acquisition parsed numeric schema/ranges but calculated no funding
contribution or mark return. This is an accounting continuation on spent data,
not a fresh signal, original R265 replication, independent confirmation or search.

Two fixed logged variants, no selection: (1) the existing seven-day event short;
(2) the existing equal-entry-notional BTC long hedge. Do signed, changing-notional
funding and fees erase the observed price effect? What necessary isolated cash
floor follows from archived mark highs even with unrealistically generous funding
credits? No new horizon, side, stop, leverage choice, coin filter or grid.

## Finite pinned inputs

Exactly the R265 frozen source rows with venue=binance, window=archive and check
verified/unverified; order by day_ms then perp.530 rows, same421 R258 priceable
events. Exact daily closeD-7 entry and closeD exit, both positive traded volume;
retain the109 price exclusions. Do not replace missing endpoints or change map.
Entry time=(D-6 UTCmidnight)-1ms; exit=(D+1 UTCmidnight)-1ms.

INPUTS.json pins both complete external manifests, helper code, event/map bytes,
the original R258 outputs and the acquisition protocol/inventory/catalogs.
Reverify each publisher checksum, size, member, schema and timestamp uniqueness.
Use only the existing98-contract Binance2021-01..2026-09 bundle; no new network
request, calendar refresh, protected2020 or MEXC outcome read. Missing fields or
changed bytes abort. CSV/source bytes and previous results remain unchanged.

## Funding envelope, time ambiguity and missing windows

Use observed settlement times in exact milliseconds; never floor them or assume
8h. For a fixed base quantity q=1/entry, short credit=q*mark*rate; BTC long cash
has the opposite sign. Rate is a fraction, not an APR. Each public daily mark
candle bounds that day's unknown settlement mark under the archive model: for
coefficient c=sign*rate/entry, cash lies between min(c*low,c*high) and
max(c*low,c*high). Sum these per settlement. This is an archive-consistent
envelope, conditional on settlement marks lying in the published daily range;
it is not proof of exact cash settlement or a guaranteed real-account bound.

The current primary sources describe up to15 seconds of settlement-time
uncertainty. Include every nominal settlement within [entry-15s,exit+15s]. A
settlement strictly inside (entry+15s,exit-15s) is mandatory. Every other included
settlement may apply or not: widen its contribution to [min(0,lower),max(0,upper)].
Keep counts of observed and optional settlements. This symmetrical envelope is
deliberately conservative; it is not a historical account transaction timestamp.

Require a funding observation strictly before the enlarged interval and one
strictly after it. For every adjacent pair across those anchors require elapsed
time equal to the LATER row's recorded interval_hours, within60 seconds (clock
jitter tolerance). A discrepancy, missing series/anchor or absent mark candle on
any included settlement date makes that leg UNKNOWN. No zero fill, rate carry,
interpolation, incomplete-window dropping or alternative source. Continuity is
conditional on the recorded interval metadata; it cannot prove unseen history.
The BTC pair is known only if BOTH legs are known. Retain each unknown and reason
in the event output, distinct from the109 original price exclusions.

## Changing-notional cost stress and controls

Fixed base convention10bp per side per current filled notional, multiplied by
k=1,2,3. A leg costs .001*k*(1+exit/entry) per unit of its entry notional. This
corrects R258's fixed20bp when exit notional differs. The BTC pair pays for BOTH
legs and is reported per unit short-leg entry notional (two units gross entry),
not per account equity. Costs are a diagnostic stress, not measured MEXC fees or
realistic fills/capacity; funding is NOT multiplied by k.

For each variant/cost retain price-only gross minus these fees, and net lower and
upper after funding. Summarize all priceable price-only rows and the identical
complete-funding subset's price-only/lower/upper rows. Also report the unhedged
short on the EXACT complete BTC-pair cohort, so coverage cannot manufacture a
hedge increment. Use R258's ISO-unlock-week clustered summary function unchanged.
No new random-date test: this measures accounting of an already-screened signal,
not incremental predictiveness. R258's null and price findings remain preserved.

## Necessary isolated collateral floor, not a liquidation simulator

Require mark close at entry plus every later daily mark candleD-6..D. Peak is
max(entry mark close, all seven later highs); zero mark volume is irrelevant.
If the path or funding is unknown, cash requirement stays UNKNOWN.

Give the short ALL possible positive funding credits from its entire envelope
before the peak, even future credits, and omit ALL debits, exit/liquidation fees,
maintenance margin and margin tiers. With one unit short entry notional, the
optimistic necessary collateral floor is
max(0,peak/entry-1-sum(max(0,each_cash_upper))+.001*k).

Report counts above20%,50%,100% and the maximum/event at all three costs. These
are fixed diagnostic levels, not leverage selections or proposed stakes. If the
floor exceeds a collateral amount, that isolated fixed-quantity short cannot
maintain nonnegative equity even under these generous assumptions, without cash
addition/early exit. Below the floor is impossible in this model; above it is NOT
proof of survival. No exact liquidation date/fill, cross-margin netting, hedge
rescue, account return, portfolio concurrency or stop optimization is inferred.

## Fixed reporting decision, limitations and trial count

At least30 complete primary events are needed for a conditional historical
screen. PASS iff all four hold: lower means positive at1x/2x/3x; lower1x week t>=2;
both date-ordered lower1x halves positive (odd extra in second); lower1x mean
positive after removing three symbols with largest summed lower1x (alphabetical
ties). This uses the known R258 screen conventions; t on adversarial envelopes is
descriptive, not a statistical test of actual executable PnL. PASS maps to
registry PARTIAL only. FAIL maps to NULL; insufficient data maps to explicit
INSUFFICIENT/PARTIAL, never PASS. No upper bound or hedge rescues primary failure.

If ANY of the421 original priceable events lacks funding, label the full cohort
funding conclusion INCONCLUSIVE_MISSING_WINDOWS independently of that conditional
screen; its full mean is not identified. Do not present the observed subset as
the original cohort. Risk counts are separate necessities, not a gate3 pass.
Two trials (short and logged hedge); costs, bounds and cash diagnostics are not
independent strategies. Report against the branch's program-trial denominator,
not only a t threshold. Calendar revision, hindsight mapping, overlapping events,
weekly dependence and the spent sample persist. No gate1/MEXC/live-ready claim.

Write events/excluded/summary CSV, verdict JSON, hash/version manifest, FINDINGS
with all1x/2x/3x and nulls. Fresh output only; require a byte-identical second run.
Append one DONE row with2 trials through lab.registry.append, preserving the old
journal prefix. Update existing M057 exact tested/open scope only; keep PARTIAL
for the overall mechanism and original aliases. No new queue/panel or modification
to original frozen files, forward lanes or journals. No subagents, trades,
credentials, PR merge/close or external execution. A point-in-time MEXC paper
protocol and finer settlement/fill/margin evidence remain future work.

Primary sources and interpretation limits: [SOURCES.md](SOURCES.md), inspected
2026-10-20. Current documentation is not proof of every historical contract rule.
