# FINDINGS: flow_hl_v1 (R448), gate 0

**Book A: CONTINUE to gate 1. Book B: NULL (stop).** These are the frozen rules: a book continues if its 1x mean on
Hyperliquid is above 0. Gate 0 can only stop a book. It decides nothing in favour, because R198 read these days on
Binance.

**The main reading is about coverage, not prices.**
- On the coins both venues list, Hyperliquid's books match Binance's almost exactly (daily correlation 0.9996 for A and
  0.9998 for B).
- The flow books' crypto profit in this window came from small coins that Hyperliquid does not list. Two of them carry
  it all: LAB and BEAT, both shorted while they fell.
- On the coins a French resident can trade on Hyperliquid, A makes +17.9%/yr with a t of 0.91. B loses.

- **Frozen:**
  - PREREG sha256 `e87e3aed…`, commit `f26f920`, before any Hyperliquid return was computed.
  - The run checked all 15 pinned files and the 380 Hyperliquid files in `hl_inputs.json`.
- **Run:** `python scripts/run_flow_hl.py --window gate0` on 2026-11-11 00:17 UTC. Output in `results/gate0/`:
  `daily.csv` (sha256 `4dec288b…`, the null sample for gate 1's final read) and `report.json`.

## Gate 0: 2026-04-01..2026-09-30, 183 days, entry one bar late, Hyperliquid closes and funding
| Book | Cost | Net, bp/day | Net, %/yr | NW t (lag 10) | Max DD | Worst day | Hit |
|---|---|---|---|---|---|---|---|
| **A** | 1x | **+4.90** | +17.9 | 0.91 | 8.4% | −5.92% | 54.1% |
| A | 2x | +2.51 | +9.2 | 0.47 | 10.4% | −5.94% | 51.4% |
| A | 3x | +0.12 | +0.4 | 0.02 | 12.6% | −5.95% | 49.7% |
| **B** | 1x | **−0.72** | −2.6 | −0.22 | 6.1% | −2.23% | 50.3% |
| B | 2x | −1.32 | −4.8 | −0.40 | 6.8% | −2.24% | 48.1% |
| B | 3x | −1.91 | −7.0 | −0.58 | 7.8% | −2.25% | 47.0% |

**Book A at 1x, by part over the 183 days (fractions of capital):**
- shorts, price plus funding: +1.5%;
- hedge (the long basket): +10.8%;
- costs: −3.4%;
- funding, already inside the shorts' figure: −4.7%. The shorted coins mostly had negative funding, so the shorts paid
  it.

**A's net by month:** Apr +1.1%, May −0.2%, Jun +3.4%, Jul −0.9%, Aug −2.0%, Sep +7.5%. September alone is more
than the whole window's net.

**Other measures, reported only:**
- Trimmed mean (10 best and 10 worst days removed): A +8.2 and B −0.8 bp/day.
- Gross without the two largest-contributing coins (leave-two-coins-out): A −5.4 and B −5.9 bp/day.
- A's largest coins by gross: HEMI +7.5%, ACE −8.0%, CHIP +3.8%, TRUMP +2.6%, KAITO +2.6%.

## Where the Binance profit was
Same window, same rule and cells, net at 1x:

| Universe | A, bp/day (t) | B, bp/day (t) | Signal coverage, A / B |
|---|---|---|---|
| Hyperliquid prices, coins Hyperliquid lists | +4.90 (0.91) | −0.72 (−0.22) | 42% / 68% |
| Binance prices, the same coins | +4.99 (0.93) | −0.62 (−0.19) | 42% / 68% |
| Binance prices, every eligible crypto coin | **+47.1 (1.41)** | **+25.3 (2.27)** | 100% |

- **Prices cost nothing.** Hyperliquid against Binance on the same coins differs by less than 0.1 bp/day.
- **Coverage costs it all.** 133 crypto symbols were eligible in the window. 54 map to a Hyperliquid coin. Of the 79
  that do not, 6 are on Lighter.
- **Two coins.** This diagnostic was run after the frozen read; it was not in the PREREG. In the Binance all-crypto
  books:
  - LAB: +0.44 of A's gross and +0.25 of B's;
  - BEAT: +0.35 of A's and +0.15 of B's.

  Together they exceed B's whole gross of +0.37. Neither is listed on Hyperliquid or Lighter. Without its two largest
  coins, B's Binance gross is −1.4 bp/day.
- **R216 agrees, from another angle.** It found that R200's forward profit came from stock and commodity perps, and
  its registry note already put BEAT and LAB at about 68% of A's holdout gross. Here, the archive's crypto profit
  comes from a few collapsing small caps.

  Either way, the flow books' high returns have not come from coins the owner can trade from France. The cells may
  carry a real effect on illiquid, fast-falling coins, but nothing here shows it is reachable.

## What happens next
- **Book A:** forward from 2026-11-12, by the frozen rules. `claude-flow-paper.yml` ticks it hourly after R200.
  - The futility screen comes at 90 strict on-time days, the final read at 365.
  - With gate 0's +4.9 bp/day and its daily SD of 0.83%, the 365-day t would be about 1.1, short of what the
    final read needs. **The expected answer is NULL.**
- **Book B:** stopped. The forward script still writes B's tickets, but they are descriptive and decide nothing.
- **R200's decision (2026-12-29) is unchanged.** If R200 passes, its forward gain will need the same split (stock perps,
  small caps, Hyperliquid-listed coins) before it says anything about a stake from France.

## Program
- Two trials. Program total 9,784,993 (`registry.program_trials()`).
- Gate 0 is a seen window: A's t of 0.91 is not evidence.

## Limits
- Gate 0's Hyperliquid files list the coins listed on 2026-10-20. A coin Hyperliquid listed and later delisted inside
  the window would be missing. That would lower coverage further, not raise it.
- Hourly closes; no Hyperliquid depth was measured. Tier costs are the lab's, not Hyperliquid's measured spreads.
- The hedge is idealized, as in every flow lane.
