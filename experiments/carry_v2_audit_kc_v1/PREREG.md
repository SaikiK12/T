# PREREG: carry_v2_audit_kc_v1, R277's two KuCoin carry books on the M468 engine (accounting audit)

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R438
- **Owner (single writer):** Claude, session on `claude/yo-9a1k5w` (hunt mode, 2026-11-10)
- **Date registered (UTC):** 2026-11-10

## Question
Do R277's two replicating KuCoin carry books, forward on paper as R279 A (`gate+kucoin L14d th5% K20`) and R279 B
(`binance+kucoin L14d th5% K20`), keep NW t >= 2.5 at 1x, a positive 2x mean and two positive halves when the same
frozen rule is run on the same archive with the three accounting fixes of the 2026-11-04 hidden-edge audit
(`lab/xfund_v2.py`, M468)?

**Why this test now.** R437 (CONFIRMED) ran this audit on R275's seven headline books, which cover the forward lanes
R278 A/B/C and R390 A. R279's two KuCoin books are the other forward carry lanes, and nobody has run them on the
corrected engine. KuCoin prices are daily bars, the case where the audit's freshness defect (H1) and the fixed-quantity
marks (H2) can differ most from Gate's and Binance's hourly bars. R294 (mexc+lighter) and the dYdX sets are left to M469,
which waits for R404's measured book costs. Cost: one run on held data.

## Universe
- `experiments/xfund_kd_v1/symbols.csv` (R277's frozen manifest, sha256 below): Binance-listed coins mapped to Gate,
  KuCoin and dYdX symbols. Current-survivor-only as in R277.
- No reserved row is read: the window starts 2021-01-01 (2020 is reserved) and KuCoin's long tail without a Binance
  perp (reserved by `docs/GATES.md`, read by R391) is not in the manifest.

## Data
- R277's archive, exactly as R277 read it (`experiments/xfund_kd_v1/spec.toml`): Binance `klines_1h` and
  `fundingRate`; Gate `gate_hist/open/candlesticks_1h` and `gate_hist/open/funding_applies`; KuCoin
  `kucoin_hist/open/candles_1d` and `kucoin_hist/open/funding`. Window 2021-01-01 to 2026-09-30. dYdX is not read.
- **Data identity check (binding):** before any v2 statistic, the runner replays both books with `lab/xfund.py` and
  requires its 1x daily net to equal R277's frozen `results/daily.csv` to 1e-9. The plumbing run on 2026-11-10 passed
  this (recorded below). A mismatch stops the run.
- No mark-price files are used on any venue (v2 values legs at the last trade, the same way on all venues), as in R437.

## Feature lineage and point-in-time availability
| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| Trailing funding spread (annualised) | funding rate, t | each venue, perp, fraction per settlement | settlements in (d - 14 days, d] | settled before 00:00 UTC of d | yes | current-survivor-only (R277) | none; as `lab/xfund.py` |
| Fresh (v2) | bar t, volume | each venue, perp | any bar with volume ending in (d - 1, d] | bar close | yes | as above | no traded bar: not fresh |
| Identity guard | daily closes on fresh days | both venues | 30 days, >= 20 observations, corr >= 0.9 | 00:00 UTC | yes | as above | as `lab/xfund.py` |
| Leg valuation (v2) | last traded close | each venue | close carried forward to 00:00 UTC | bar close | yes | as above | an interval where a leg did not trade gets no price gain (a loss is kept) |

## Rule
- **Books (closed list, 2):** `gate+kucoin L14d th5% K20` (R279 A) and `binance+kucoin L14d th5% K20` (R279 B), R277's
  frozen rule.
- **Engine:** `lab/xfund_v2.py` as committed (sha256 below), exactly as in R437: v1's funding windows, identity guard,
  pair choice and entry rule; fresh = a traded bar in the day; fixed-quantity legs; no price gain on an unobserved
  interval; a pair exits as `dead` when a leg stops trading and as `blowout` when the legs' price ratio moves more than
  20% from entry.
- **Runner:** `scripts/run_carry_v2_audit_kc.py` calls R437's frozen runner functions (`scripts/run_carry_v2_audit.py`,
  unchanged) with this lane's book list, R277's spec and R277's daily output.
- **Window and costs:** each book from its own v2 window start to 2026-09-30; costs R277's 7, 14 and 21 bp per leg
  (1x, 2x, 3x); returns on total book capital as `lab/xfund.net`.

## Decision (per book, frozen)
- **SURVIVES** when, on the v2 1x daily net: NW t (10 lags) >= 2.5, the 2x mean > 0, and both halves' means > 0.
- **FAILS** otherwise.
- Reported, not gating: v1 vs v2 %/yr at 1x/2x/3x, 2025+ bp/day, max drawdown, top-10-day share, funding share,
  average pairs held, exit counts by reason and the share of gross from `dead` and `blowout` exits, unobserved
  pair-days, and whether the 1x %/yr beats the 4.13% T-bill hurdle. As in R437, a post-hoc descriptive split (funding,
  price, costs; v2 without blowout and dead-leg trades) may be added to FINDINGS, labelled post hoc, with no decision.
- **Registry verdict:** CONFIRMED if both books SURVIVE, PARTIAL if one does, NULL if none.
- **What follows:** a forward book that FAILS gets a note on R279's FINDINGS when it is read (the frozen lane keeps its
  accounting); a corrected forward lane would be a new id.

## Null
None is built: this is a re-measurement of two frozen books under corrected accounting, decided on the frozen t
threshold. R277's reality check is not recomputed.

## Multiplicity
- 2 trials (one per book). No variant, threshold or engine option is tried; the 20% blowout and the no-mark choice are
  R437's, fixed here.
- Program trials before this lane: 9,784,979 (`registry.program_trials`). The two books were chosen by R277's
  replication rule (2 of 4 sets passed); this audit inherits that selection.

## Evidence lineage and admission
- Canonical method ids: M468 (engine), M497 (the accounting audit; R437 was its first run). Parent rounds: R277, R279,
  R437.
- Samples already seen: all of 2021-01..2026-09 on these venues by R277 (gate 0 on seen rows; it can only lower
  confidence).
- Prior exposure, disclosed: R437's results on R275's books (v2 raised 1x %/yr on five of seven books through
  fixed-quantity funding drift and blowout exits). The hidden-edge audit recomputed only dYdX sets with KuCoin
  (kucoin+dydx), not these two books. The plumbing run read only v1 statistics (already published by R277) and fresh
  coin-day counts; no v2 return on these books was computed.
- `docs/GATES.md` SHA-256 at registration: e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926. This lane
  is a gate-0 accounting audit; it is not a gate pass and admits nothing to real money.

## Plumbing record (2026-11-10, before the freeze)
Run `python scripts/run_carry_v2_audit_kc.py --plumbing` at about 08:55 UTC: 873 coins x 4 venues (dYdX not read),
2,100 days loaded in 59 s. For both books v1's 1x daily net equals R277's `results/daily.csv` (max |diff| 5.0e-11),
and v1's %/yr and NW t equal R277's FINDINGS (gate+kucoin +11.76% t 11.41; binance+kucoin +10.80% t 11.17). Fresh
coin-days over each book's venues, v1 -> v2 (counts only, no return): gate+kucoin 1,024,595 -> 1,065,291;
binance+kucoin 1,013,384 -> 1,013,557. The synthetic dry run and 3 runner tests (plus R437's 4) passed.

```inputs
1e39f5c093fa8bd84657e88de4f11b145071e81edf275e9e8bc65ccca6d9d853 scripts/run_carry_v2_audit_kc.py
0c3a6b84b6329d5d3cd200bf2668a1992c56c851ab8291c349be2028529bed46 tests/test_run_carry_v2_audit_kc.py
1ba92fe3df40a0eac920e47c69ac4b7b9024750d4ba13f94edcfbe8f4550b7e5 scripts/run_carry_v2_audit.py
d34e99a05241899543feacc4f443a0115dfd779c61f134b9880e241101dafe1d lab/xfund.py
fa85ef56885a1d6736dd92e73f8bce44e97ce9ee001739526caef86ae1ba62cd lab/xfund_v2.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34 lab/stats.py
3eb47ec2ae78a6531a71f4f564ceac71987d1616097c50cdd8d2913009bd5dba scripts/run_clockflow.py
03abb3bf671c018c38b641ebe3c7ccefa573e087a69212fb07fa491e0e584056 experiments/xfund_kd_v1/spec.toml
15c8054f7e10f921bd9a797fbf2b9ac927c99fdfbc2388a54199be0cace6fb3b experiments/xfund_kd_v1/symbols.csv
0ab7db847cb9e0e51c93d59ad205a64888664a067fb8255a4093494c48d6b7ab experiments/xfund_kd_v1/results/daily.csv
55e45182aade91c169b5a58b94ea9c831a64bc7753828fd276b7c94ed26e8de6 docs/provenance/klines_1h.json
84a3aadbf5ac0439b99209714c85ab0484b775f1258701835a64029c1ec3e4de docs/provenance/fundingRate.json
e496f80737a33ccffd3be5fb2d119310d91930021f7477338e124290950563c0 docs/provenance/gate_hist.json
bc5abe62d763042bd2e01fe88f7b5bf367bdda263200c1cec67486fed19a4b13 docs/provenance/kucoin_hist.json
```
