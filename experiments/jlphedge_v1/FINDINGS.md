# FINDINGS: jlphedge_v1 (R449), gate 0

**Both books: CONTINUE to gate 1**, by the frozen rule. Gate 0 only stops a book whose 1x excess is below 0. Public
APYs were known in general, so gate 0 cannot pass a book.

**The main reading is the decay:**
- Hedged JLP earned **+43.9%/yr in 2024**, +16.2% in 2025 and **+5.6% in 2026** (to 2026-11-10).
- Hedged GM ETH-USDC went from +19.4% to +9.5% and then **+7.2%**.
- The high return was 2024's. In 2026 neither book beats what France can already reach: HLP and LLP earn about
  +10.7 and +10.8%/yr in 2026 (R446), and HYPE spot-perp carry about +10% (R445).

- **Frozen:**
  - PREREG sha256 `7ae66e56…`, commit `67555d5`, before any pool or book return was computed.
  - The run checked the 4 pinned code files and the 8 gate-0 input files.
- **Run:** `python scripts/run_jlphedge.py --window gate0` on 2026-11-11 00:40 UTC. Output in `results/gate0/`:
  `daily.csv` and `report.json`.
- **Inputs:** the input files stay out of git (`experiments/*/data/` is lane data). Their sha256 are in the PREREG.
  `--window fetch` rebuilds them from DefiLlama and Hyperliquid, but DefiLlama may revise a point, so a rebuilt file
  is checked against the hash.

## Gate 0: 2024-02-01..2026-11-10, 1,014 days, ex-ante hedge, Hyperliquid closes and funding
| Book | Cost | Net, %/yr | Excess over 4%, pts | NW t (lag 10) | Max DD | Worst span |
|---|---|---|---|---|---|---|
| **J (JLP)** | 1x | **+22.08** | +18.08 | 4.48 | −5.88% | −3.59% (2024-04-13) |
| J | 2x | +21.63 | +17.63 | 4.37 | −5.90% | |
| J | 3x | +21.18 | +17.18 | 4.27 | −5.93% | |
| **G (GM ETH-USDC)** | 1x | **+12.03** | +8.03 | 4.75 | −2.14% | −1.07% (2026-01-18) |
| G | 2x | +11.72 | +7.72 | 4.57 | −2.16% | |
| G | 3x | +11.42 | +7.42 | 4.39 | −2.17% | |

**By year, 1x:**
| Year | J net, %/yr | J excess (t) | J max DD | G net, %/yr | G excess (t) | G max DD |
|---|---|---|---|---|---|---|
| 2024 (from 02-01) | +43.92 | +39.92 (4.26) | −5.88% | +19.39 | +15.39 (4.89) | −1.02% |
| 2025 | +16.24 | +12.24 (2.21) | −3.28% | +9.46 | +5.46 (1.91) | −1.50% |
| 2026 (to 11-10) | **+5.58** | +1.58 (1.37) | −0.62% | **+7.17** | +3.17 (1.54) | −2.14% |

**JLP's net by quarter, % of capital:**
- 2024: +9.4, +14.2, +9.1, +7.7;
- 2025: +7.4, +3.8, +4.0, +1.1;
- 2026: +0.6, +1.6, +1.8, then +0.8 over the first 41 days of Q4.

This is the reading post hoc, from `daily.csv`.

**Parts, 1x, %/yr of capital over the window (J / G):**
- the pool token: +24.4 / +13.8;
- the shorts' price leg: −5.0 / −5.3;
- funding received by the shorts: +3.1 / +3.8;
- costs: −0.45 / −0.31.

Costs barely matter. Going from 1x to 3x costs removes 0.9 point (J) and 0.6 point (G).

**The hedge:**
- J's mean ratios per unit of JLP were SOL 0.34, ETH 0.06 and BTC 0.11. The mean capital was 1.51.
- G's ETH ratio averaged 0.46 (range 0.38-0.54). The mean capital was 1.47.
- The books' residual correlation with their hedge coins is small: J 0.13 with SOL, 0.06 with ETH and 0.07 with BTC;
  G 0.02 with ETH.
- Other regression windows (diagnostics only, 1x): J earns +17.8%/yr with 30 spans and +18.9% with 120. G earns
  +12.3% and +11.7%.

## Power and what gate 1 can decide
- **J:**
  - The daily sd is 0.46%. It is inflated by 63 stale DefiLlama JLP points: 46 in 2024 and 17 in 2025. A stale point
    moves a day's pool return to the next day while the hedge moves on both.
  - The excess detectable at t 2.5 with 80% power is +60 points at 90 days and +42 at 180.
- **G:** the daily sd is 0.17%. The detectable excess is +22 points at 90 days and +16 at 180.
- At 2026's level (excess +1.6 for J, +3.2 for G), neither book can reach EARNED at 90 days or CONFIRMED at 180. The
  expected answer is CONTINUE at 90 days, then **NULL** at 180, unless the forward days look like 2024.
- Gate 1 runs anyway, by the frozen rule. `claude-flow-paper.yml` writes the tickets from 2026-11-11 (for 11-12) on.

## Reading
- **Does the trade work?** Yes, in the sense that the hedge holds: the books keep the pool's income and shed most of
  the crypto risk.
- **Is it a high return now?** No. The income was large in 2024, when perp volumes and trader losses were large. It
  has fallen year by year since. In 2026, JLP's hedged excess over the 4% hurdle is +1.6 points with t 1.37.
- **France:** Jupiter's terms do not name France, as read. GMX's terms were not found. The hedge is on Hyperliquid.
  A France-reachable book at about +6-7%/yr is below HLP, LLP and HYPE carry in 2026, and it adds two venues' tail risk
  (pool drains, oracles, bridges).
- **Next:** this lane adds no new high-return candidate. The forward read stays open by the rules and costs nothing.
  The vault-selection lane (R450, Hyperliquid user vaults) is the next France-reachable test.

## Program
- Two trials. Program total 9,784,995 (`registry.program_trials()`).
- Gate 0 is a seen window (public APYs known). Its t of 4.5 is not evidence by the lab's rules, and the window is
  dominated by 2024.

## Limits
- **DefiLlama's daily points, not on-chain prices.** JLP's stale points shift returns between adjacent days; over the
  window they net out. GM shows none.
- **The shorts are margined 1:1.** With 3x leverage on the shorts the capital would be about 1.17 instead of 1.51.
  Post hoc, JLP's 2026 net would then be about +7%/yr. That is still below the vaults, and it adds liquidation risk on
  Hyperliquid (R280).
- **Midnight rebalancing only;** cross-chain transfers are assumed free.
- **Tail events.** The window holds 2024-04-13 (J's worst span) and the 2025-10-10 crash, but no pool drain.
