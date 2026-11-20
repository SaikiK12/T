# FINDINGS: xfund_kokx_v1 (R515). The design gap carries on the regulated pair Kraken + OKX Europe, but thinly

**Verdict: PASS (R391's rule, gate 0).**
- All four checks hold: the one-sided NW p is 0.003, the 2x mean is above 0, the 10% trimmed mean is above 0, and so
  is the mean without the two best coins.
- But the level is a fraction of R508's, and costs at 3x leave nearly nothing.

- **Registry:** R515, 1 trial. Program trials become 9,785,756.
- **Reproduce.** The PREREG (sha 9011f2f1) was frozen in commit 5d05d06 before any Kraken-OKX spread was computed.
  `run_xfund_kokx.py run` ran once on 2026-11-20. All 8 inputs and 505 data files matched; OKX branch commit 4d5d5c0.

## Primary book: kraken + okx, L14d th5% K20, 2026-08-31..2026-11-15
| Cost | %/yr on book capital | Same days, R508's Kraken + Hyperliquid book |
|---|---|---|
| 1x (7 bp a leg) | **+5.23** | +9.96 |
| 2x | +2.97 | +7.77 |
| 3x | +0.71 | +5.58 |

- **Book days and t.** 77 book days, NW t 2.73. The trimmed mean is +2.12 bp/day; without BIO and MOODENG,
  +1.04 bp/day.
- **Halves:** +1.63 and +1.24 bp/day.
- **Risk.** Max drawdown -0.29%. But the top 10 days hold 134% of the total: the rest of the days lose on net.
- **Where the return comes from.** Funding share 1.17: the price legs cost 17% of gross.
- **The book.** All 20 slots were held; 68 trades on 49 coins, 27 of them positive; mean hold 23 days.
  - Long Kraken in 43 trades, long OKX in 25.
- **By Kraken liquidity:** coins under $100k a day on Kraken gave +1.9%/yr of the book; the others +0.9%/yr.
- **Secondary (th 10%):** +4.41 / +1.93 / −0.56 %/yr, NW t 1.84.

## What it means
- **The regulated route exists, and it is thin.** At the 2-3x cost levels measured on Kraken's thin legs
  (2026-11-18/19), the book makes about 1-3%/yr: below cash.
- **Passive Kraken entries could change that.** R513 cut the Kraken leg's cost by about 8 bp a side at a 1 h
  fallback. They would move it toward the 1-2x lines, about 3-5%/yr. That is still modest.
- **Hyperliquid paid more on the same days** (+10%/yr at 1x). The unregulated leg is where the larger spread was in
  this window.
- **The window is short (77 days), and the data is partly seen:**
  - OKX funding was read by R430 and R443;
  - Kraken funding was read by R508 for 82 of the 91 coins.

## What this does not show
- **Persistence.** The PASS rests on 77 days, and the top 10 days carry more than all of it.
- **OKX costs.** Its books are recorded on the data branch (`books/*.csv`) but were not used here.
- **Access.** OKX Europe's retail terms for France were not read beyond its regional page (R430/M484 notes). Under
  ESMA's 2026 statement, X-Perps to retail likely fall under the CFD caps (2:1).

## Next
- **Earned, not urgent:** a forward lane (a new id) on Kraken + OKX. It would charge OKX's recorded book costs and
  Kraken's passive costs.
- **Its value:** it is the only fully regulated version of the carry, but its expected return is near cash. Worth
  building after R510/R512 read, unless the owner wants a regulated-only route first.
