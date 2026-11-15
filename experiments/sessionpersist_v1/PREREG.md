# PREREG: sessionpersist_v1 (R493). Does an imposed UTC session split carry return persistence in the altcoin-perp cross-section?

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R493
- **Owner (single writer):** OpenHands agent, branch `openhands/session-persistence-factor-report`
- **Date registered (UTC):** 2026-11-15

Method M541, lens: scheduled/clock-driven flow. Prior art and exact read scopes:
`research/intake/session_split_20261115.md` (WS-S01..WS-S04). Low prior; a null is the expected
outcome and is a result.

## Question
In the cross-section of liquid USDT altcoin perpetuals, does the trailing 7-day return earned inside
a fixed UTC session predict the **next day's total return** with the same sign (continuation), and
does the unsplit 7-day return do worse?

**Mechanism and sign, fixed before any data.** Lou-Polk-Skouras (2019, abstract read) document
same-component overnight/intraday continuation with an offsetting cross-component reversal in
equities; Hendershott-Livdan-Rösch (2010, abstract read) document continuation at trading-day
multiples. Both rely on a real close/open and time-separated clienteles. **Crypto perps trade 24/7
with no close and no opening auction**, so the transfer is the question, not an assumption. The
tested direction is **continuation: long the top quintile of the trailing same-session return**
(positive expected next-day return). The opposite sign is reported, never re-tested as a new
variant. Bogousslavsky (2021) is the named anchor; its abstract and full text were **not obtained**
(bot-walled, no bypass), so no number from it is used.

## Universe
- Frozen manifests: `docs/provenance/klines_1h.json` and `docs/provenance/fundingRate.json`
  (both committed, hashed below). Candidate rule: a USDT perp present in **both** manifests whose
  **first hourly bar is before 2024-01-01**, minus R216's frozen TradFi list
  `experiments/venue_gap_v1/results/tradfi_symbols.json`. This yields **263 candidates**, computed
  from metadata only before any price was read; the list is frozen in `universe.json`.
- **Delisted contracts are included** (the Vision archive keeps them). 29 of the 263 candidates stop
  trading before the archive end. The pre-2024 first-bar filter excludes later listings by design;
  it also excludes the 2025-2026 TradFi waves by construction. The result is bounded to **seasoned**
  perps, not the full listing universe.
- Traded universe: the **top 50** candidates by trailing 30-day quote volume at 2026-09-30
  (latest-vintage selection, declared as a caveat, computed in `run` before any factor).
- Daily eligibility is **point-in-time**: at day d, rank by trailing 30-day mean daily quote volume
  through **d-1**, among names with a close at both d-1 and d; take the top 50. A day needs >= 15
  scored eligible names (R222's minimum) or it is skipped.

## Data
- **Backtest data:** `data.binance.vision` USD-M hourly klines and `fundingRate`, fetched after this
  freeze by `lab.data.build(..., strict=True, end="2026-09-30")` into
  `experiments/sessionpersist_v1/raw/`, with `raw/manifest.json` (sha256 of every file). The runner
  verifies every file's sha256 before and after the statistics.
- **Trade venue for costs:** MEXC. Costs are R224's **measured** median $10k API all-in per side:
  **9.3635 bp** = 8 bp API taker (MEXC notice, since 2026-06-01) + 0.6765 bp half-spread + 1.3635 bp
  impact (`experiments/mexc_costs/journal/status.json`, `median_over_coins.api_10k`, 37 coins,
  102 snapshots). R224 reports **all 37** coins above the assumed 8 bp at $10k, so 1x is not
  conservative. Binance prices are the signal source; MEXC is the execution venue, and the
  Binance/MEXC price agreement for these books is R216's finding, not re-tested here.
- Window read: **2020-10-01 .. 2026-09-30** hourly (92 warm-up days before the discovery start).
  Everything at or after **2025-07-01** is dropped before any statistic; the holdout is unread.
- **Seen before this freeze:** the provenance manifests' symbol lists and first/last bar timestamps
  (metadata), R216's TradFi symbol list, R224's cost summary numbers, R222's published FINDINGS
  conventions, and the abstracts in the intake note. **No candidate's price, volume, funding rate,
  session return or factor value has been read or computed.**

## Feature lineage and point-in-time availability

| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| close(d) | `open` of the hour-0 bar | Vision, Binance USD-M perp, USDT | the 00:00 UTC bar opening of day d (equals prior close on a continuous book) | exchange bar, hourly | yes, known at 00:00 UTC of d | point-in-time; delisted included | NaN if the hour-0 bar is absent; never filled |
| r_h | log(close_h / close_{h-1}) | Vision `close` | each hourly bar | exchange bar | yes | point-in-time | NaN on the first bar and across gaps |
| sess_A(d), sess_B(d) | r_h | as above | sum of r_h over hours [00,14) and [14,24) UTC of day d | computed | yes, at 00:00 UTC of d+1 | point-in-time | sum is NaN if any hour in the session is missing; hours counted separately |
| S_A(d), S_B(d) | sess_A, sess_B | as above | trailing **7** days ending at d inclusive | computed | yes: uses only data through the close of d, acts on d+1 | point-in-time | NaN unless >= **150** of 168 session hours present in the 7 days |
| MOM24(d) | daily log return of close(d) | as above | trailing **7** daily returns ending at d | computed | yes | point-in-time | NaN unless >= **6** of 7 daily returns finite |
| qvol(d) | `quote_volume` | Vision, USDT notional | sum of the day's hourly quote volume | exchange bar | yes | point-in-time | NaN if fewer than **20** of 24 bars that day |
| elig(d) | qvol through d-1, close(d-1), close(d) | as above | trailing 30-day mean qvol through **d-1**, top 50 | computed | yes (ranking uses d-1; the close(d) requirement is existence, not its value) | point-in-time membership | a name with no close at d-1 or d is ineligible |
| fwd(d) | close(d+1), close(d) | as above | log return from 00:00 UTC d to 00:00 UTC d+1 | computed | **target, not an input** | point-in-time | NaN if either close missing |

Every input is **point-in-time** except the one declared **latest-vintage** choice: the top-50
candidate ranking at 2026-09-30. Coverage is reported as survivor vs later-delisted book-leg
mentions in FINDINGS (`lab.coverage`'s concern); eligibility itself never reads the future.

## Rule or search space
**Closed list, three factors, no search:** `S_A`, `S_B`, `MOM24`. One lookback (7 days), one session
cut (00-14 / 14-24 UTC), one quintile count (5), one hold (1 day), one direction (long top quintile,
short bottom, dollar-neutral, each leg gross 1, equal weight within a leg). Weights are recomputed
daily from the factor and eligibility; no parameter is tuned. Rank IC (Spearman, average ranks) is
reported against `fwd` for each factor, plus the quintile means and the top-minus-bottom spread.

## Splits and cost
`lab/config.py` program version **1**: discovery **2021-01-01..2023-12-31**, validation
**2024-01-01..2025-06-30**, holdout from **2025-07-01 (never read)**. Cost **9.3635 bp per side** at
1x, with **2x and 3x** reported for every factor and window. Net = gross - turnover x cost, where
turnover = sum|w_d - w_{d-1}| / 2 (both legs' traded notional; entry trades from cash).

## Gates
Per factor, on the daily net series, Newey-West t with **10** lags:
- **Discovery gate:** 1x mean > 0 **and** NW t >= **2.0**.
- **Validation gate:** 1x mean > 0 **and** NW t >= **1.5**. Validation is read for **all three**
  factors; there is no selection of a winner before reading it.
- **Lane verdict:** **NULL** if no factor passes discovery. **PARTIAL** (gate 0, in-sample) if at
  least one discovery passer also passes validation. Nothing here is CONFIRMED: no reserved sample
  and no forward day is read.
- Reported, deciding nothing: gross means, 2x/3x nets, rank IC and its t, quintile means, the
  quantile spread, mean one-way turnover, coverage counts, and the funding diagnostic.

## Null
Moving-block bootstrap of each factor's **discovery daily gross book return**, mean removed, block
**20** days, **200** replicas, seed **20261115** (`numpy.default_rng`). Each replica's NW t (10 lags)
is recomputed. Reported: the per-factor 95th-percentile null t, and the **family-max** distribution
across the three factors' replicas (same seed, same blocks) with its 95th percentile and the
family-wise p = share of family maxima >= the real discovery 1x t. The bootstrap null is a
dependence-preserving reference for the t statistic; it does not by itself create a fresh sample.

## Multiplicity
**Trials: 3** (S_A, S_B, MOM24 — all three deciding, all three reported). No failed, skipped or
retained variants: nothing was searched. Program trials before this round: **9,785,313**
(`registry.program_trials()`); **9,785,316** with it. The three factors share one universe, one
window and overlapping returns (S_A + S_B is close to MOM24), so they are far from independent; the
family-max bootstrap is the within-lane control and the program total is bookkeeping, not an
effective independent-test count.

## Evidence lineage and admission
- Canonical method id: **M541**. Parent rounds: **R222** (cross-sectional conventions),
  **R216** (TradFi classification, crypto/TradFi split), **R224** (measured MEXC costs).
  Related nulls: **R435/M492** (stock-perp overnight), **M539** (crypto MAX session split).
  No parent tested cumulative session-return persistence in the altcoin cross-section.
- One decision group: a cross-sectional daily alt-perp selection signal. The three factors are one
  session-split question plus its unsplit control, not three independent chances.
- Samples already seen by parents: R222 read the same archive window for its own factors. This lane
  adds no reserved read. Proposed fresh sample: **none** (gate 0 only).
- `docs/GATES.md` SHA-256 at registration:
  `e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926`.
  Met: pre-registration before statistics, frozen inputs, cost sensitivity at 1x/2x/3x, a
  dependence-aware null, honest coverage labels, holdout untouched. **Unmet for gate 1:** no strict
  on-time forward clock, no 10-day trimmed mean, no leave-two-coins-out, no 80%-power calculation,
  no reserved-sample read. This lane therefore admits nothing to real money.
- Across-family selection control: **none**; the result is exploratory.
- **Order:** this PREREG is frozen and the R493 rounds row appended in one commit;
  `scripts/run_sessionpersist.py run` fetches and computes only after that commit; the raw manifest
  and results are committed; the runner verifies the freeze and every hash before and after.

## What a result earns
- **NULL:** M541 is marked tested. A different session cut, lookback, hold or target is a **new lane
  with a new id**, not an edit here.
- **PARTIAL:** a candidate for a *prospective* forward paper check on days after the holdout start,
  with its own frozen PREREG and on-time clock. Not a book, not a go-real signal.

## Stop rules
One `prepare` (metadata + freeze) and one `run`. No new features, cuts, lookbacks, directions,
splits or thresholds after seeing any result. A crash fixed after the freeze is documented in
FINDINGS with the changed sha. The holdout is not read for any reason in this lane.

## Inputs (frozen)
```inputs
c3ce0ca9b02c859d69ac3216e9f9f738c12057fa8433cd6f20c00d478ae86148 experiments/sessionpersist_v1/universe.json
55e45182aade91c169b5a58b94ea9c831a64bc7753828fd276b7c94ed26e8de6 docs/provenance/klines_1h.json
84a3aadbf5ac0439b99209714c85ab0484b775f1258701835a64029c1ec3e4de docs/provenance/fundingRate.json
af7b1a0fbf99471720f765ece0b16734b88247aa84feb7f21137103500d983ea experiments/venue_gap_v1/results/tradfi_symbols.json
```
