# R316: prestarting workers fixes much of request latency; index coverage still blocks altcoins

**PARTIAL implementation/input result, no demonstrated net return.** On the same
fixed grids, prestarted fair workers reduced median parent-dispatch-to-full-body
latency from **1,194.701 ms cold to217.311 ms warm**. Own-grid receipts improved
from **5/36 to35/36 immediate**, and13/36 to36/36 by+300ms. This makes the MEXC
input materially more available without changing its clock or economic guards.
All five immediate altcoin displayed-cost rows have individually fresh MEXC
warm publications, versus one cold and zero WS; **none has a fresh Lighter
index**. Zero joint altcoin rows and zero funding cash remain scored.

R311 remains INCONCLUSIVE on224/273 common validation days; its calibration-
selected policy still loses at2x/3x costs. No historical rescore, validation-winner
switch, leverage increase or paper activation. These are216 dependent descriptive
profile rows, **zero predictive variants/new prospective days**. Program trials
remain9,478,782. No confidence interval, significance or net-return inference.

## Frozen specification and exact acquisition

[PREREG](PREREG.md), the36-file [code/source identity](code_inputs.json), tests and
independent checker were frozen/committed/pushed in **3c3d49c** before collection.
Exact [raw input identity](evidence_inputs.json) was committed/pushed in **938abb5
before outcomes**. One attempt, no retry/reconnect/replacement. Anchor UTC:
**2026-10-25 07:22:59.925785**. Every216 row and all72 planned fair slots survive.

| Input / cap | Actual | Frozen upper bound |
|---|---:|---:|
| Metadata GETs / retained and conservative body bytes | 7 /404,145 | 7 /2MiB |
| Fair GETs / retained and conservative body bytes | 72 /7,233 | 72 /288KiB |
| Combined GETs / body bytes | 79 /411,378 | 79 /2MiB+288KiB |
| Warm workers / commands | 6 /36 | 6 /36, no replacement |
| WS handshakes | 2 | 2, no reconnect |
| MEXC messages / decoded payload bytes | 526 /141,634 | 20,000 /8MiB |
| Lighter messages / decoded payload bytes | 1,531 /885,703 | 20,000 /8MiB |
| Read-start window / total duration | 65s /73.288s | 65s /120s |

All72 fair replies HTTP200, no failed bodies, capture errors or overrun. Both
streams completed their duration. Warm readiness issued no GET; each worker used
six explicit commands. Actual first-seen readiness occurred1.019–1.151s after
its process start, **before the anchor**. Startup cost moved outside the deadline;
it did not disappear. Raw files/receipts occupy **298,009 compressed bytes**,
excluding seal. Application body/payload counters exclude transport overhead.

The separate bounded source reading used8 static GETs,7HTTP200 and1HTTP302 not
followed,1,142,975 body/read-upper-bound bytes,4.437s; limits8requests/4MiB/120s.
No market/history calls by that reader. Raw copyright material remains ignored
cache, with only compact identities/extractions in Git. The single R310/R311
historical allowance stays **7,757/8,000 requests,229.85/250MiB**; this separate
small current diagnostic neither resets nor extends it.

## Matched timing and causal availability

Cold is unchanged R315 code, executed alongside the warm path in this new time
window. WS_change is the same original fair-change feed. Every profile shares
identical decision books/q/costs; delayed profiles retain immediate q. Comparing
R315's old cost/timing count directly with this window is not a matched experiment.
The concurrent cold/warm paths share platform and transport contention. These
figures do not isolate venue latency or guarantee performance elsewhere.

| REST path | Full-body latency min /median /max ms | Own-grid receipt0ms | Receipt+300ms | Parsed bodies |
|---|---:|---:|---:|---:|
| Cold | 823.065 /1,194.701 /1,714.453 | 5/36 | 13/36 | 36/36 |
| Prestarted | 194.007 /217.311 /496.751 | 35/36 | 36/36 | 36/36 |

The latency starts at actual **parent dispatch**, not the earlier planned slot.
Cold dispatch lag after planned time has median3.770ms/max674.363ms; warm
median104.936ms/max720.375ms. XPD/grid40 is the one warm own-grid late reply, with
720.375ms parent dispatch lag. All raw planned/parent/worker GET/first-seen/close
clocks remain available. Receipt availability is not automatically source/value
freshness. No future reply or cross-profile fallback enters an earlier decision.

For each pair below, cost count is identical across WS/cold/warm. Joint counts
add valid reference publication age, receive/source skew and book identity, with
unchanged0..1s receive,−100ms..2s source,1s skew and50ms UTC-step guards.

| Pair | Cost rows immediate /delayed (each /6) | Joint immediate WS /cold /warm | Joint delayed WS /cold /warm |
|---|---:|---:|---:|
| BTC | 6 /6 | 4 /1 /6 | 4 /3 /3 |
| WIF | 3 /3 | 0 /0 /0 | 0 /0 /0 |
| SKR | 0 /0 | 0 /0 /0 | 0 /0 /0 |
| ROBO | 1 /1 | 0 /0 /0 | 0 /0 /0 |
| MEGA | 1 /1 | 0 /0 /0 | 0 /0 /0 |
| XPD session control | 0 /0 | 0 /0 /0 | 0 /0 /0 |
| Total | 11 /11 | 4 /1 /6 | 4 /3 /3 |

Thus **22/72 distinct book/deadline cost rows**, duplicated unchanged over three
profiles (66/216 labelled rows). Of the five altcoin cost rows per deadline,
individually fresh MEXC WS/cold/warm counts are **0/1/5 immediate** and **0/2/4
delayed**; Lighter index freshness is **0/5** at both deadlines. No synchronization
or cash was inferred from active flags, a fresh REST receipt or other-market data.
Every raw Lighter trading_hours string is empty; sessions stay uncertified.

Warm is also **not uniformly better at the delayed deadline**. Three BTC warm
references pass immediately but exceed the fixed1s receive-age limit by+300ms;
the same happens to one delayed altcoin warm value. Earlier successful receipt
can age out. These rows remain failed, without moving dispatch times, widening
guards or resampling. The method has improved one binding input, not all inputs.

## Conditional economics, unchanged capital and all costs

$10,000 segregated $5,000/venue, equal common-lot base q chosen from immediate
books against a $250 leg target. The fixed10/4bp **per-side charge reserve PLUS
displayed crossing** is multiplied together at1x/2x/3x. These are conditional
charges, not measured account fees or exact R311 all-in replay. Ranges below use
distinct book/deadline rows; profile duplication creates no extra opportunity.
Break-even bp uses mean one-leg midpoint notional, with current entry+unwind
quotes rather than a guaranteed future exit.

| Pair | Distinct cost rows | Round-trip USD1x /2x /3x | Hurdle bp1x /2x /3x |
|---|---:|---|---|
| BTC | 12 | 0.7002–0.7094 /1.4004–1.4188 /2.1006–2.1283 | 28.04–28.40 /56.07–56.80 /84.11–85.21 |
| WIF | 6 | 1.1572–1.3378 /2.3144–2.6757 /3.4716–4.0135 | 46.38–53.63 /92.77–107.27 /139.15–160.90 |
| ROBO | 2 | 1.3660–1.4031 /2.7321–2.8062 /4.0981–4.2093 | 54.67–56.15 /109.34–112.30 /164.00–168.45 |
| MEGA | 2 | 1.1214 /2.2427 /3.3641 | 44.89 /89.78 /134.67 |
| SKR,XPD | 0 | unavailable at every tier | unavailable at every tier |

Altcoin hurdles **44.89–56.15 /89.78–112.30 /134.67–168.45bp**. No funding benefit
or expected PnL is compared to them because actual settlement value, exposure,
rate units/asset and effective-value coverage are unverified. Own impact,
financing, liquidation, failed-leg recovery and future exit conditions are not
included. All rows remain execution_ready=false and funding cash unscored.

## New source findings and retained weak alternatives

[Exact versions/read-unread scopes](sources.json) refine existing M409 dependencies:

1. Public orderBookDetails and the pinned SDK serializer expose index/mark but
   no source/as-of value timestamp. Market creation time or HTTP Date cannot fix it.
2. Newly inspected priceOracleInfo (document modified2026-10-07) has computed_at_ms
   and source/median/internal/cap **policy**, not current index/mark. Its cap formula
   is reference*(1 ±bps/10,000). Its clock cannot stamp another response's price;
   atomic joining/cache/effective/funding-engine equality is not documented.
3. marketPriceCharts contains last24h hourly **marks for perps,index for spot**.
   It remains an untested weak input alternative, not current perps-index evidence.
4. Funding-rate numeric fields/wrapper supply no authoritative API scaling,
   settlement asset or realized event clock. Official real-time advice points
   to market_stats; that does not establish heartbeat or effective-value age.
5. Cached Market Stats prose does not strengthen subscription snapshots into
   idle-market/effective-value or account settlement proof. No resubscription was
   attempted. The weak snapshot alternative remains explicitly untested.

/reference/info returned302; destination remains unread/not followed. No SDK
installation/full code audit, full book/API corpus reading, oracle-provider
implementation audit, live chart/policy data or private account access occurred.
The missing authoritative object is a symbol-bound current index with its own
meaningful effective/source clock and cache/idle/event semantics.

## Verification and decision

The independent reviewer resolved warm command-counter/attempt consistency,
actual-close ordering and child/parent readiness-clock checks before freeze.
All12 focused tests passed independently, including the actual worker with
in-memory HTTP200/429, trickle/hang/cap/exhaustion/no-replacement, source-selection
and matched economic fixtures. Full local suite: **1,165 tests run,2 skipped,
successful**. New unit tests do not establish market latency or alpha.

The pre-outcome-frozen [independent Decimal checker](check_warm.py) imports no
production replay/cost modules. It verified **216 rows,72 fair receipts,425 causal
value receipts,198 cost scenarios and42 sampled notional sensitivities**, with
maximum absolute numerical difference **3.23e-12**; see[audit.json](audit.json).
These counts include fixed profile duplication and are not independent samples.
Summary and compressed observations reproduce byte for byte in a separate folder.
Canonical integration retains all346 prior method objects and old alias/journal
byte prefixes, adding six exact engineering/value-source records:352 aliases,
54 provider entries,328 unchanged queue rows and10 source manifests. Intake has
0 errors/warnings; integrity verifies129 frozen local specs plus one planned
draft, with0 errors/13 pre-existing legacy/planned warnings. Every tracked byte
of R310–R315 evidence remains unchanged.

```bash
python experiments/warm_values_v1/check_warm.py
python scripts/probe_warm_values.py report --out /path/to/new-empty-report-folder
```

Retain M409 PARTIAL and all original policy/null evidence. Use the bounded
prestarted worker component for a separately justified future finite collector;
do not choose a new dispatch policy from this sample and call it validated.
Synchronized Lighter effective index, session and actual cash/fill mechanics
remain binding. This result supports an implementation fix, not positive net
expectancy, a strategy activation or new prospective paper evidence.
