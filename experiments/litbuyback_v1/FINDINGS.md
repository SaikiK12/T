# FINDINGS: litbuyback_v1 (R486). Lighter's buyback share does not predict LIT's next week

**Verdict: NULL.** All three gates fail. The rank correlation of the day's buyback share with LIT perp's next 7-day
return is +0.149 (n 306), one-sided circular-shift p 0.154. The weekly long-or-flat book earns less than holding LIT
long over the same blocks.
- **Registry:** R486, 2 trials (the correlation and the book). Program trials become 9,785,291
  (`registry.program_trials()`). Against that count, and against its own null, nothing here is evidence of an edge.
- **Reproduce:** PREREG sha256 `4c9ce7fe...`, frozen in commit `9d6cc3f6` before any buyback-vs-price statistic. Then
  `python scripts/run_litbuyback.py` (about 1 s). The runner checks the PREREG, the inputs block (three exchangeMetrics
  bodies and the runner), and the lit/ tree hashes at `claude/okx-xperp-data` commit `0364bbc6`, and reads lit/ by
  `git cat-file` at that commit. One run (`run.log`); results in `results/verdict.json`, `results/blocks.csv`,
  `results/pairs.csv`.
- **Sample end:** nothing dated after 2026-11-10 was read (files chosen by date name, rows checked against the cut,
  `tests/test_run_litbuyback.py` covers both). Buyback points for 2026-11-11 and 11-12 in the body were dropped.

## Data used
- Signal: buyback USDC on UTC day t over LIT perp plus LIT/USDC spot quote volume on day t (both on lit/).
  Exchange-wide exchangeMetrics volume was not used. Median share 0.40% (10th percentile 0.14%, 90th 0.87%).
- Perp 313 daily bars 2026-01-02..2026-11-10, spot 314 from 2026-01-01, funding 7,485 hours, buyback 316 days
  2025-12-30..2026-11-10. Correlation days t 2026-01-02..2026-11-03.

## Primary correlation (trial 1)
| Signal | Target | n | Spearman rho | Shifts | p one-sided | p two-sided | Null mean rho |
|---|---|---|---|---|---|---|---|
| share s_t | close(t+7)/close(t) - 1 | 306 | +0.149 | 279 | 0.154 | 0.341 | +0.004 |

The overlapping 7-day targets make the series autocorrelated; the circular shift keeps that structure, which is why
a rho of +0.149 sits inside the null.

## Book (trial 2): long LIT perp for 7 days when the 7-day mean share is above its prior-60-day median
34 non-overlapping blocks 2026-03-13..2026-10-30 (earlier blocks lack 60 days of history); long in 15, flat in 19.
Net = price return minus funding paid by the long minus the round trip. Every block had 167 or 168 funding hours.

| Cost (round trip) | Book mean net per block | Book t | Always-long mean net per block | Always-long t |
|---|---|---|---|---|
| 1x (20 bp) | +2.86% | 1.43 | +4.17% | 1.45 |
| 2x (40 bp) | +2.77% | 1.39 | +3.97% | 1.38 |
| 3x (60 bp) | +2.68% | 1.35 | +3.77% | 1.31 |

Book gross (no cost) +2.94% per block (t 1.48). Always-long earned +6.47% per block at 1x in the 15 long blocks and
+2.35% in the 19 flat ones (medians +1.30% and +1.67%): the long blocks' mean rests on a few large weeks, and 8 of the
15 long blocks were positive. Both books ride LIT's +331% recovery from its 2026-03-30 low; neither t reaches 2.
Funding paid by the long averaged 0.24% per block (0.18% in the long blocks).

## Gates
| Gate | Rule | Result |
|---|---|---|
| G1 | rho > 0 and one-sided circular-shift p < 0.05 | **fail** (rho +0.149, p 0.154) |
| G2 | book mean net at 2x > 0 with t >= 2 | **fail** (+2.77%, t 1.39) |
| G3 | book 1x beats always-long 1x | **fail** (+2.86% vs +4.17%) |

## Reported, deciding nothing
| Variant | n | rho | p one-sided | p two-sided |
|---|---|---|---|---|
| share s_t vs next-day return close(t+1)/close(t) - 1 | 312 | +0.033 | 0.344 | 0.642 |
| change s_t - s_{t-7} vs next 7-day return | 299 | +0.023 | 0.404 | 0.746 |

## Limits
- One token, about 300 days, one venue's own token; the buyback body is one fetch (2026-11-13), so later revisions
  of past days are not visible; buyback units are as read in the intake (UNVERIFIED in Lighter's docs).
- Timing: the entry is at the close of day t, when day t's buyback total is just complete. If Lighter publishes the
  point later, a live book would enter later; that version was not run.
- Not tested (a new lane each): other denominators (exchange-wide volume, market cap), horizons, thresholds, the LIT
  amount instead of USDC, and the buyback against the insider unlock that starts 2026-12-29 (about 11 to 23 times the
  buyback). Not checked: how the buyback TWAP is split between perp and spot, and whether it trades on Lighter at all.
