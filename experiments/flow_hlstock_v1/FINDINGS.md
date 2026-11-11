# FINDINGS: flow_hlstock_v1 (R451), gate 0

**Both books: CONTINUE to gate 1**, by the frozen rule. Gate 0 only stops a book whose 1x mean daily net on xyz is
0 or below. R200 and R216 had read these days on Binance's prices, so gate 0 cannot earn anything.

**The main reading is fidelity:**
- Hyperliquid's xyz perps reproduce R200's TradFi books on Binance almost exactly. The daily nets correlate 0.9998
  (A) and 0.9997 (B) with the same coins on Binance's closes.
- Over 41 days, book A made +13.4% on xyz against +13.3% on Binance, and book B +7.6% on both.
- Hourly price returns differ by about 2 bp a coin-hour on average (TSLA 1.9, gold 1.9, S&P 1.4, MSTR 5.0;
  diagnostic, read after the freeze).
- A France-reachable venue can therefore execute what R200 measures, at xyz's 9 bp taker fee.
- Whether the signal itself holds is still open: R200's own forward and this lane's gate 1 decide.

- **Frozen:**
  - PREREG sha256 `89eceed0…`, commit `a54cf2f`.
  - The gate-0 inputs were fetched at 01:01-01:03 UTC on 2026-11-11, after the last hour closed, and frozen before
    any return on xyz was computed.
- **Run:** `python scripts/run_flow_hlstock.py --window gate0` on 2026-11-11 01:03 UTC. It checked the 8 pinned code
  files and the 23 gate-0 input files. Output in `results/gate0/`: `daily.csv` and `report.json`.
- **Inputs:** they stay out of git (`experiments/*/data/` is lane data). Their sha256 are in the PREREG.
  `--window fetch` rebuilds them.

## Gate 0: 2026-10-01..2026-11-10, 41 days, one bar late
| Prices | Book | Cost | Total | Mean, bp/day | NW t (lag 10) | Max DD | Trimmed mean, bp/day |
|---|---|---|---|---|---|---|---|
| **xyz** | **A** | 1x | **+13.4%** | +32.8 | 1.81 | 3.4% | −0.4 |
| xyz | A | 2x | +12.0% | +29.4 | 1.62 | 3.5% | −3.6 |
| xyz | A | 3x | +10.6% | +26.0 | 1.44 | 3.7% | −6.7 |
| **xyz** | **B** | 1x | **+7.6%** | +18.6 | 1.26 | 2.5% | −2.7 |
| xyz | B | 2x | +7.2% | +17.4 | 1.18 | 2.6% | −3.9 |
| xyz | B | 3x | +6.7% | +16.3 | 1.10 | 2.7% | −5.2 |
| Binance, same coins | A | 1x | +13.3% | +32.5 | 1.81 | 3.4% | +0.4 |
| Binance, same coins | B | 1x | +7.6% | +18.5 | 1.27 | 2.5% | −1.9 |
| Binance, all 24 TradFi | A | 1x | +17.9% | +43.7 | 1.84 | 5.0% | +1.2 |
| Binance, all 24 TradFi | B | 1x | +10.3% | +25.0 | 1.29 | 4.2% | −1.7 |

- **Coverage on xyz:** 87% of book A's signals and 91% of B's. QQQ, SKHYNIX and SOXS have no xyz market.
- **Funding received** by the shorts on xyz: +0.66% (A) and +0.37% (B) over the window.
- **Parts of A at 1x:** short gross +52.0%, hedge −37.6%, costs −0.9%.

## What the gain rests on (diagnostics, read after the freeze)
- **A few days.** The trimmed mean (10 best and 10 worst days removed) is about zero or negative for both books.
  - A's three best days sum to +15.0%, more than its whole net.
  - The best day is 2026-11-05 (+7.4% for A, +3.9% for B); the worst is 11-06 (−1.8%, −1.3%).
  - A: 20 of 41 days are positive. Its first 20 days made +8.7% and the next 21 +4.8%; B's made +7.2% and +0.4%.
- **Leveraged ETF perps.** The largest gross contributors to A are SOXL (+18.5 points), KORU (+10.8) and SNXX
  (+8.8): 3x leveraged ETFs, whose prices decay in volatile markets. Leaving the two largest coins out still leaves
  A's gross at +55 bp/day, so no single coin carries it.
- **Power:** A's daily sd is 160 bp. At gate 0's mean, a t of 2.5 needs about 150 counted days (iid approximation),
  and B (sd 104 bp) about 196. The 365-day final read can decide if the mean holds; the 90-day futility screen only
  stops a book at or below 0.

## Reading
- **Execution, from France:** xyz tracks Binance's TradFi perps to a few bp an hour, has its own funding, and
  charges 9 bp taker at tier 0 (growth mode would be less). The paper result on Binance's prices therefore transfers
  to a venue whose terms do not name France. Depth on xyz was not measured. A real order of a few thousand dollars on
  a small xyz market could pay more than 9 bp.
- **The signal:** these 41 days are R200's own seen window, driven by a few days in early November and by shorts on
  leveraged ETFs. They are not evidence. Gate 1, from 2026-11-12 on tickets written live, decides.
- **Next:** the hourly `claude-flow-paper.yml` run writes this lane's tickets from 2026-11-11 on, right after R448.

## Program
- Two trials. The program total is 9,784,997 (`registry.program_trials()`).
- The decision group is R200's: a pass here stays conditional on R200 passing on the signal.

## Limits
- **Short, seen window:** 41 days. The gate-1 bootstrap threshold rests on this short null.
- **Off-hours prices:** stock prices outside US hours come from xyz's oracle fallback and its own book. The
  correlation with Binance holds over all hours of the window.
- **Fees:** the standard HIP-3 fee is assumed for every coin (9 bp taker). Growth mode was not checked per market.
- **Jurisdiction:** trade.xyz's terms do not name France, as read. Equity-linked perps offered to EU retail may fall
  under rules that no venue's terms cover. This is not legal advice; the owner checks.
