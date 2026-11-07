# FINDINGS: announce_v1 (R271). No Binance announcement type passes as a family. Two candidates go forward

**Verdict: NULL (gate 0).** 64 strategies were tested: 8 announcement types × long/short × +1/24/72/168 h, 2021-01..2026-09,
40/80/120 bp. None clears the family reality check.
- **Registry:** R271, 64 trials. Program trials become 9,477,627.
- **Engine:** the first lane run on `qx` (Rust). The whole family takes 7 s.
- **Reproduce:** prereg sha 4ac89c69, frozen in commit 666d1b2 before any price was read. Then run
  `python scripts/qx_run.py experiments/announce_v1` at that commit; the engine source is among the frozen inputs.
- **Sample:** 1,881 archive legs. 1,219 were priced (618 Binance perp, 107 MEXC, 494 Binance spot), and 662 had no
  traded instrument at the notice hour.
  - **Clusters:** perp_launch 270, earn_add 143, margin_add 116, pairs_add 92, upgrade 85, prelist 45, fund_freq 35,
    spot_list 31. holder_drop has 3 and is out.
  - spot_list has only 31 priced clusters: most coins Binance lists had no perp yet.

## The frozen reality check broke on one data error, and the verdict holds anyway
- **The data error:** COCOS's 2021-01 token swap and 1:1000 redenomination appears in the spot series as a 1,290×
  price jump. One "upgrade long 168 h" leg reads +129,000%.
- **How it broke the check:** after demeaning, every bootstrap draw without that leg has a t near 684 for the mirror
  strategy. So the family null's 95th percentile is t 684, and no strategy can pass.
- **The verdict does not depend on it.**
  - The best strategy is fund_freq long +1 h, at t 3.31 with n 35. Its one-sided p is about 0.001, so Bonferroni
    over 64 gives about 0.07. It fails at 0.05.
  - A post-hoc rerun with the leg dropped and observations winsorized at 1% (below; not counted) still gives no
    survivor: null 95th percentile t 11.4, best p_RC 0.24.
- **Engine fix for later lanes (default off, so R271 and R269 parity are unchanged):**
  - `max_bar_jump` drops a leg whose instrument moves more than a given factor in one bar;
  - `winsor` winsorizes the cluster observations for the reality check.
  - New specs use `max_bar_jump = 20` and `winsor = 0.05`.

## Top 10 by t (1x, one observation per notice cluster)
| Strategy | n | 1x mean | Median | t | Halves | 2025+ (n) | 2x | 3x |
|---|---|---|---|---|---|---|---|---|
| **fund_freq long +1 h** | 35 | **+3.59%** | **+3.97%** | **3.31** | +5.43 / +1.86 | +1.86% (18) | +3.19% | +2.79% |
| **prelist short +168 h** | 45 | **+11.48%** | **+18.05%** | 2.03 | +9.12 / +13.74 | +14.43% (37) | +11.08% | +10.68% |
| earn_add short +168 h | 143 | +3.85% | +8.68% | 1.75 | +2.84 / +4.86 | +6.72% (12) | +3.45% | +3.05% |
| margin_add short +72 h | 116 | +2.14% | +3.09% | 1.63 | +3.50 / +0.78 | none | +1.74% | +1.34% |
| fund_freq long +24 h | 35 | +11.43% | +0.21% | 1.55 | +5.97 / +16.60 | +16.60% (18) | +11.03% | +10.63% |
| fund_freq long +72 h | 35 | +18.31% | -1.32% | 1.31 | +1.93 / +33.78 | +33.78% (18) | +17.91% | +17.51% |
| fund_freq long +168 h | 35 | +81.49% | -1.92% | 1.29 | +2.64 / +155.96 | +155.96% (18) | +81.09% | +80.69% |
| earn_add short +24 h | 143 | +1.45% | +1.29% | 1.26 | +0.26 / +2.61 | +2.79% (12) | +1.05% | +0.65% |
| earn_add short +72 h | 143 | +2.11% | +4.84% | 1.20 | +0.99 / +3.20 | +3.63% (12) | +1.71% | +1.31% |
| margin_add short +24 h | 116 | +1.14% | +1.75% | 1.10 | +2.17 / +0.11 | none | +0.74% | +0.34% |

- **The full table is `results/strategies.csv`; `results/SUMMARY.md` is written by the pipeline.**
- **Spot listings, perp launches, new pairs and upgrades** show nothing after the first hourly open at any horizon,
  in either direction. Whatever the listing pump is, it is over within the notice's hour.

## Post-hoc diagnostics (computed after the run, not gates, not counted)
These come from the same family with the COCOS leg dropped, 1% winsorizing, and the matched null on every strategy.

| Strategy | Matched null p | Null mean | Observed (kept clusters) |
|---|---|---|---|
| fund_freq long +1 h | 0.0005 | -0.39% | +3.36% |
| prelist short +168 h | 0.0005 | -4.59% | +13.81% |
| earn_add short +168 h | 0.0045 | | |
| margin_add short +72 h | 0.0005 | | |
| earn_add short +24 h | 0.70 | | |

**What the two candidates are:**
- **fund_freq long +1 h.** Binance moves a perp to 4-hourly or hourly funding when its rate hits the cap. In the next
  hour the price rose in most cases (median +3.97%).
  - The longer horizons are dominated by squeezes, such as ALPACA in 2025-04: +2,000% in a week.
  - The type pools both funding signs. A signed rule (long when funding is negative, short when positive) is the
    obvious refinement, and it would be a new lane.
- **prelist short +168 h.** Tokens Binance introduces through HODLer Airdrops, Launchpool or Launchpad fall in the
  week after the notice: median +18% for the short, with 37 of the 45 clusters from 2025-26.
  - The mean is cut by squeezes, which is why t is only 2.03.
  - This is the airdrop sell pressure the literature and traders describe.

## Reading
- **Against program trials (9,477,627):** nothing here is close. The best t is what 64 tries give by chance, and
  Bonferroni p is about 0.07.
- **Pre-committed:** since nothing passed, the top 3 by t go to the first reserved 2020 batch:
  - fund_freq long +1 h. It has no 2020 notice (the first is 2021), so it cannot be read there.
  - prelist short +168 h, with 23 notices in 2020.
  - earn_add short +168 h, with 11 notices in 2020.
- **Next:**
  - Forward paper lanes on MEXC for fund_freq long +1 h and prelist short +168 h. The notice recorder already sees
    both types.
  - A signed funding-frequency lane on the archive.
  - Both need new ids, frozen before their first read.
