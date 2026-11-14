# FINDINGS: linstart_v1 (R485). Too few linear-vesting starts to test

**Verdict: INSUFFICIENT** (recorded as NULL in `registry/rounds.csv`). The primary sample has 4 priced events, under
the frozen minimum of 20. The PREREG already said so before any price was fetched: OKX listing dates allowed at
most 4. Three of the five gates fail anyway (G1, G2, G5).
- **Registry:** R485, 1 trial. Program trials become 9,785,289 (`registry.program_trials()`). Read against that
  count, and against a null whose own mean is +7.35%, nothing here is evidence of an edge.
- **Reproduce:** PREREG sha256 `5fa103e2...`, frozen in commit `97870aff` before any candle was fetched. OKX bodies were
  fetched once in commit `d094fa9e` (`raw/manifest.json` sha256 `9b53b077...`). Then
  `python scripts/run_linstart.py` (about 10 s) needs `data/unlocks/2026-11-13/` (gitignored, from
  `scripts/fetch_unlocks.py`). The runner checks the PREREG, the frozen files, every snapshot file and every raw body,
  and rebuilds events.csv and symbol_map.csv byte for byte before it reads a candle.
- **Deviations (stated in the PREREG):** OKX USDT swaps instead of Binance (HTTP 451 here), and a 2026-11-13 snapshot
  instead of R265's 2026-10-20 one (not in this checkout).

## Primary: pure events, archive window (funding excluded)
| Cost (round trip) | n | Mean net per event | Median | Hit | Week-cluster t |
|---|---|---|---|---|---|
| 1x (20 bp) | 4 | +14.92% | +15.45% | 75% | 1.98 |
| 2x (40 bp) | 4 | +14.72% | +15.25% | 75% | 1.95 |
| 3x (60 bp) | 4 | +14.52% | +15.05% | 75% | 1.92 |

Gross +15.12% (t 2.00). Events (gross short return, D-7 to D+14): ETHFI 2025-03-13 +18.1%, SHELL 2026-02-12 -3.7%,
SOPH 2026-05-28 +32.9%, DATA 2026-08-14 +13.2% (`results/events_priced.csv`).

## Gates (1x)
| Gate | Rule | Result |
|---|---|---|
| G1 | week-cluster t >= 2 | **fail** (1.98) |
| G2 | matched random-date null p < 0.05 (2,000 reps, seed 485) | **fail** (p 0.259; null mean +7.35%, 95th pct +24.62%) |
| G3 | mean net at 2x > 0 | pass (+14.72%) |
| G4 | both halves positive (split at 2026-05-28) | pass (+6.98%, +22.86%) |
| G5 | positive without the top 3 swaps | **fail** (1 event left, SHELL, -3.92%) |

The null explains most of the mean: a short over any 21-day window on these young tokens earned +7.35% on average,
because they fell steadily after listing. The admissible null days per swap were 882 (ETHFI), 536 (SHELL), 446
(SOPH) and 46 (DATA).

## Counts and exclusions
- **Snapshot:** 374 protocols; 127 verified on OKX, 4 excluded (R265's list), 243 unmapped, 0 mismatch.
- **Events:** 15 archive (9 pure, 6 with_cliff), 1 pre_window (WOO 2020-10-29), 0 post_archive, 5 forward.
- **no_market (D-7 before the OKX listing):** 6. Pure: CVX 2021-05-17, LDO 2021-12-17, RAY 2022-02-21, KMNO
  2025-04-30, YB 2025-09-15. With_cliff: MORPHO 2024-11-20.
- **exit_early:** 0. Every priced event had candles at D-7 and D+14.
- **Funding:** OKX's funding history starts on 2026-08-10 for these swaps and covers no primary hold (DATA's hold
  began on 2026-08-08). One with_cliff
  event has it: 2Z 2026-10-02, -5.47% (the short paid).

## Reported, deciding nothing
| Sample | n | 1x | 2x | 3x | t (1x) |
|---|---|---|---|---|---|
| All archive (pure + with_cliff) | 9 | +13.66% | +13.46% | +13.26% | 1.81 |
| With_cliff | 5 | +12.64% | +12.44% | +12.24% | 0.97 |
| Pure, rate 0.25-0.5% of max supply a week | 3 | +13.93% | | | 1.32 |
| Pure, 0.5-1% | 1 | +17.88% | | | n/a |
| Pure, >= 1% | 0 | | | | |

With_cliff includes TRUMP 2025-04-19 at -30.1% gross and 2Z 2026-10-02 at +44.0%.

## Caveats
- **Survivorship:** OKX lists live swaps only, so tokens whose OKX swap was delisted are missing. The 4 events are all
  on tokens that still trade.
- **Not point-in-time:** the calendar is DefiLlama's 2026-11-13 view; later corrections can add, move or remove old
  streams (R265 caveat).
- **Venue coverage:** OKX listed most of these tokens after their first linear start, which removed 5 of 9 pure events.
  A venue with earlier listings (Binance, R265's archive) could give a larger sample. That would be a new lane.
- **Sample:** 4 events on 4 swaps in 4 weeks. The t-statistic and the null on 4 points are reported because the PREREG
  asks for them; they cannot carry a decision.

## What it means for LIT and M538
- LIT's team and investor stream starting 2026-12-29 (0.319% of max supply a week, label pure) is one forward instance.
  This round gives no historical support for shorting it, and no evidence against it either.
- M538 is marked TESTED with the native verdict INSUFFICIENT. The R447 watch note in
  `research/intake/lit_hype_unlocks_20261113.md` stands unchanged. No R447 return, and no LIT, HLP or LLP return
  after 2026-11-10, was read for this lane.
- A changed rule (lower threshold, other venue, other horizon) is a new lane with a new id.
