# PREREG: carry_v2_audit_v1, R275's headline carry books on the M468 engine (accounting audit)

Freeze with `lab.prereg.freeze()` before running anything. After that this file is never edited.

- **Registry id:** R437
- **Owner (single writer):** Claude, session on `claude/yo-9a1k5w` (hunt mode, 2026-11-10)
- **Date registered (UTC):** 2026-11-10

## Question
Do R275's seven headline cross-venue carry books (the best book per venue set in `experiments/xfund_v1/FINDINGS.md`,
four of which are forward on paper as R278 A/B/C and R390 A) keep NW t >= 2.5 at 1x, a positive 2x mean and two
positive halves when the same frozen rule is run on the same archive with the three accounting fixes of the
2026-11-04 hidden-edge audit (`lab/xfund_v2.py`, M468)?

**Why this test now.** Carry is the lab's only family that passed gate 0, a blind 2020 read (R286 C14) and a
reserved long-tail read (R391, R392 GLT). The audit found three accounting defects in the frozen engine that the
forward lanes share: freshness that depends on bar length (H1), constant-notional marks (H2) and dead legs valued at a
stale last trade (F4). It re-checked only the dYdX and KuCoin sets (H2 cut KuCoin+dYdX from +10.52 to +4.13%/yr) and
estimated F4 at about +1.1%/yr of fake P&L on K20 books. Nobody has run R275's own books on the corrected engine. If
they fail, the forward carry lanes are measuring a rule whose backtest edge was partly an accounting artifact, and the
next decision changes. Value of information is high and the cost is one run on held data.

## Universe
- `experiments/xfund_v1/symbols.csv` (R275's frozen manifest, sha256 below): 867 Binance-listed coins mapped to Gate,
  Hyperliquid and MEXC symbols. Current-survivor-only as in R275; delisted contracts present in the archive are kept.
- No reserved row is read: R275's window starts 2021-01-01 (the 2020 rows are reserved) and its symbols are Binance
  listings (the Gate long tail reserved by R391/R392 is not in it).

## Data
- R275's archive, exactly as R275 read it (`experiments/xfund_v1/spec.toml`): Binance `klines_1h` and `fundingRate`;
  Gate `gate_hist/open/candlesticks_1h` and `gate_hist/open/funding_applies`; Hyperliquid `hyperliquid/candles_1d` and
  `hyperliquid/funding`; MEXC `mexc_hist/klines_1h` and `mexc_hist/funding`. Window 2021-01-01 to 2026-09-30.
- **Data identity check (binding):** before any v2 statistic, the runner replays every book with `lab/xfund.py` and
  requires its 1x daily net to equal R275's frozen `results/daily.csv` to 1e-9. The plumbing run on 2026-11-10 passed
  this for all seven books (recorded below). A mismatch stops the run: the data or the code moved.
- No mark-price files are used on any venue (v2 values legs at the last trade, the same way on all four venues).

## Feature lineage and point-in-time availability
| Feature / formula | Parent fields | Provider, venue, instrument, units | Measurement window and close rule | Published / first-received / computed time | Available by decision time? | Membership and coverage vintage | Revision / missing-value rule |
|---|---|---|---|---|---|---|---|
| Trailing funding spread (annualised) | funding rate, t | each venue, perp, fraction per settlement | settlements in (d - L days, d], L in {3, 7, 14} | settled before 00:00 UTC of d | yes | current-survivor-only (R275) | none; as `lab/xfund.py` |
| Fresh (v2) | bar t, volume | each venue, perp | any bar with volume ending in (d - 1, d] | bar close | yes | as above | no traded bar: not fresh |
| Identity guard | daily closes on fresh days | both venues | 30 days, >= 20 observations, corr >= 0.9 | 00:00 UTC | yes | as above | as `lab/xfund.py` |
| Leg valuation (v2) | last traded close | each venue | close carried forward to 00:00 UTC | bar close | yes | as above | an interval where a leg did not trade gets no price gain (a loss is kept) |

## Rule
- **Books (closed list, 7):** `gate+hyperliquid L14d th5% K20` (R278 A), `binance+hyperliquid L14d th10% K20`,
  `binance+mexc L14d th10% K20` (R278 B), `binance+gate+hyperliquid+mexc L14d th10% K20`, `gate+mexc L7d th10% K20`
  (R278 C), `binance+gate L14d th10% K20` (R390 A), `hyperliquid+mexc L3d th5% K20`.
- **Engine:** `lab/xfund_v2.py` as committed (sha256 below): v1's funding windows, identity guard, pair choice and entry
  rule; fresh = a traded bar in the day; fixed-quantity legs; no price gain on an unobserved interval; a pair exits as
  `dead` when a leg stops trading and as `blowout` when the legs' price ratio moves more than 20% from entry.
- **Window and costs:** each book from its own v2 window start to 2026-09-30; costs R275's 7, 14 and 21 bp per leg
  (1x, 2x, 3x); returns on total book capital as `lab/xfund.net`.

## Decision (per book, frozen)
- **SURVIVES** when, on the v2 1x daily net: NW t (10 lags) >= 2.5, the 2x mean > 0, and both halves' means > 0.
- **FAILS** otherwise.
- Reported, not gating: v1 vs v2 %/yr at 1x/2x/3x, 2025+ bp/day, max drawdown, top-10-day share, funding share,
  average pairs held, exit counts by reason and the share of gross from `dead` and `blowout` exits, unobserved
  pair-days, and whether the 1x %/yr beats R275's 4.13% T-bill hurdle.
- **What follows:** a forward book that FAILS gets a note on its lane's FINDINGS when it is read (the frozen lane keeps
  its accounting); a corrected forward lane would be a new id. If the four forward books all SURVIVE, the carry family
  is accounting-robust on its own archive and the forward lanes stay the decider.

## Null
None is built: this is a re-measurement of seven frozen books under corrected accounting, decided on the frozen t
threshold. R275's reality-check p values are not recomputed.

## Multiplicity
- 7 trials (one per book). No variant, threshold or engine option is tried; the 20% blowout and the no-mark choice are
  fixed here.
- Program trials before this lane: 9,784,972 (`registry.program_trials`). The seven books were themselves selected as
  the best per set out of R275's 560 (best by 1x t); this audit does not undo that selection and inherits it.

## Evidence lineage and admission
- Canonical method ids: M468 (engine), new row M497 (this audit). Parent rounds: R275 (xfund_v1), R286 C14, R278, R390.
- Samples already seen: all of 2021-01..2026-09 by R275 (this is gate 0 on seen rows; it can only lower confidence).
- Prior exposure, disclosed: the 2026-11-04 audit recomputed H2 on dYdX/KuCoin books and estimated F4 at about
  +1.1%/yr on K20 books. `lab/xfund_v2.py` has never been run on R275's data (M468: "No data run yet"). The 2026-11-10
  plumbing run read only v1 statistics (already published by R275) and fresh coin-day counts under v1 and v2; no v2
  return was computed.
- `docs/GATES.md` SHA-256 at registration: e7dd02fa43747598959838677cb413578ce8f7cfee59704bd20e4fdfca15a926. This lane
  is a gate-0 accounting audit; it is not a gate pass and admits nothing to real money.

## Plumbing record (2026-11-10, before the freeze)
PLUMBING_RECORD

```inputs
INPUTS_BLOCK
```
