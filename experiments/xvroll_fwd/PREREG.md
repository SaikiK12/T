# PREREG: xvroll_fwd (R482). Do trade.xyz's NATGAS longs keep paying more funding than Lighter's?

- **Registry id:** R482
- **Owner (single writer):** Claude, this session (cloud container, 2026-11-12); the reads are run by
  `.github/workflows/claude-xvroll.yml`
- **Date registered (UTC):** 2026-11-12

Method M533 (queued 2026-11-12 from R481's post hoc). This file is frozen by `lab.prereg.freeze()` and pushed before the
first forward mark (2026-11-16 20:00 UTC) and before any data of the forward window exists. After the freeze it is
never edited; a changed idea is a new lane.

## Question
trade.xyz and Lighter both list a NATGAS perp priced from NYMEX Henry Hub futures. Until 2026-10-22 both oracles rolled
the same contracts on business days 5-9 of each month. R481 measured the two rolls within 0.22% of notional of each
other per cycle. But the funding differed:
- On xyz, NATGAS longs paid about 1.3% of notional a cycle more than the roll they received (R478's post hoc).
- On Lighter they paid the roll and no more (R481, NULL).

A pair that is short xyz NATGAS and long Lighter NATGAS at equal notional is flat the commodity and, mostly, the roll.
It keeps xyz's funding minus Lighter's, plus the basis between the two perps, minus costs. It needs no futures broker:
both venues are perp DEXes margined in USDC.

**Arbitrage predicts NULL:** the funding difference closes, or is eaten by basis moves, costs and the bill on idle
margin.

## What the author had seen before the freeze
- **R481's post hoc (`experiments/ltroll_v1/posthoc/`):**
  - Over the 6 full roll cycles 2026-04-15 .. 10-14, xyz NATGAS longs paid +0.77% of notional a cycle more funding
    than Lighter's (sd 0.89). More in 5 of 6: +0.27, +0.02, −0.35, +1.46, +1.74, +1.46.
  - WTI −0.45 a cycle (2 of 7 positive) and BRENTOIL −0.01 (3 of 6). Three markets were looked at; NATGAS was chosen
    after seeing them, which this forward lane exists to test.
- R478 and R481 in full. xyz NATGAS funding by 4-week block from 2026-07-23 (M532: 28.7, 59.8, 123 and 141%/yr).
- R470 (`xvfund_v1`): the xyz-vs-Lighter funding pair on US-stock perps was NULL, too thin even before costs.
- **A plumbing run of this lane's fetchers on 2026-11-09 .. 11-11** (before the window). It printed row counts, spans
  and column names only: no gaps, all files present. No price, funding or PnL value was printed.
- **Lighter's documents and market metadata** (read 2026-11-12):
  - Since 2026-10-22, Lighter's WTI and NATGAS use RedStone prices. RedStone's roll for them is not documented (no
    public source found; RedStone advertises front-month, second-month and volume- or OI-weighted rollovers).
  - BRENTOIL is still on Lighter's own roll: business days 5-9 at 23:59 London.
  - Maintenance margin: NATGAS 6%, WTI and BRENTOIL 3%. Fees 0/0 on the Standard account.
  - RWA funding: premium multiplier 1/2; a base interest of 0.0032% per 8 hours inside a 0.05% clamp.

## The book (`scripts/run_xvroll.py`)
Per pair, with capital 1 at the first mark.
- **Size:** short the xyz perp and long the Lighter perp at equal notional N = L × equity, with L = 1.5. Each venue
  holds half the equity as USDC margin, so each leg's margin is N/3 (M = 1/3).
- **Hourly, on the grid of 1-hour bar ends from 2026-11-16 20:00 UTC:**
  - Each leg takes its price PnL (bar closes) and that hour's funding print.
  - xyz `fundingRate` and Lighter's signed rate are both + when longs pay. The short receives rate × qty × close; the
    long pays it.
  - Prints are matched to the nearest hour. A missing bar carries the last close and is counted.
- **Liquidation**, each hour before the close:
  - The xyz short is checked at the bar's high and the Lighter long at the bar's low, against maintenance: xyz
    NATGAS 5%, CL and BRENTOIL 2.5% (R478's values); Lighter NATGAS 6%, WTI and BRENTOIL 3%.
  - A liquidated leg loses its whole margin. The other leg is closed at that hour's close.
  - The book re-enters at the next daily mark, paying the transfer of half the equity to the venue that lost.
- **Daily marks, 20:00 UTC every calendar day.** The book re-splits when either leg's margin leaves [M/2, 1.5 M] of
  its notional, or the notionals drift more than 5% apart.
  - Re-split: both legs are resized to N = L × equity and the margins split equally, paying the transfer of the USDC
    moved.
  - Transfers between the venues (Hyperliquid and Lighter, both USDC) are assumed instant.
- **Costs per unit traded:**
  - xyz 4.9 bp: 2.9 bp taker in growth mode, as in R478 and R480, plus 2 bp half-spread.
  - Lighter 3 bp: Standard account 0 fee, plus 3 bp half-spread. No recorded book cost is read.
  - Transfers 10 bp of the USDC moved.
  - The 2x and 3x lines subtract the weekly cost once and twice more.
- **Hurdle:** idle USDC earns nothing. The hurdle is the 13-week bill (^IRX, the latest close on or before each day)
  on equity.
- **Pairs:** NATGAS (xyz:NATGAS against Lighter NATGAS) **decides**. WTI (xyz:CL against Lighter WTI) and BRENTOIL
  (xyz:BRENTOIL against Lighter BRENTOIL) are reported, with the same book.

## Data (fetched inside each read; `fetch` in the runner)
- xyz: funding history (`fundingHistory`, full) and 1-hour candles.
  - The venue keeps the latest 5,000 candles. They are merged with the 1-hour candles R480's recorder keeps on the
    data branch `claude/futroll-data` (`xyz/<NATGAS|CL|BRENTOIL>_1h.csv`, read only, never written here).
- Lighter: 1-hour candles with highs and lows, and hourly funding (full history), through `lab.carrylane`'s paced
  client.
- ^IRX daily from Yahoo.
- Each summary lists the sha256 of every input file and of every recorded file it read.

## Reads and decision (NATGAS; `run_xvroll.py --auto`, `.github/workflows/claude-xvroll.yml`)
**Statistic:** R478's and R480's: ISO weeks of equity against the bill, Newey-West t (lag 4), annualized × 52.

| read | weeks | runs after | rule |
|---|---|---|---|
| futility | 2026-11-16 .. 2027-05-14 (min 22 weeks) | 2027-05-15 00:00 UTC | NULL if excess < 0, else CONTINUE |
| final | 2026-11-16 .. 2027-11-12 (min 44 weeks) | 2027-11-13 00:00 UTC | PASS if excess ≥ 2 points/yr, NW t ≥ 2.0 and 2x excess > 0; PARTIAL if excess > 0; NULL otherwise |

- A read with fewer weeks than its minimum, or more than 10% of hours missing on either leg, is INCONCLUSIVE.
- A futility NULL stands: the final read still runs and reports, but its verdict is NULL.
- **Reported each read:**
  - Both funding legs, both price legs (their sum is the basis), costs, bill, liquidations, re-splits and final
    equity.
  - The funding difference in %/yr of notional, and the share of hours in which xyz longs paid more.
  - Every read reports 1x, 2x and 3x costs.
- **Trials:** 3 (three pairs computed). Program total after this round: 9,785,274.

## Power (before any value of the window)
- **At R481's post hoc NATGAS difference** (+0.77% of notional a cycle, about +9.2% a year):
  - L = 1.5 gives about +13.8% a year of capital before costs. Less about 0.5 point of costs and 3.7 points of bill:
    about +9.5 points a year.
  - The weekly sd is not known; it is the funding difference's noise plus the basis between two oracles. At a guessed
    1% a week, t ≈ 0.9 at the futility read and ≈ 1.3 at the final read: a PARTIAL, not a PASS.
- **At August-October's pace** (+1.55% a cycle): about +23 points a year, t ≈ 2.3 at 26 weeks and ≈ 3.2 at 52.
- **Under arbitrage** (no difference): about −4.2 points a year, NULL.
- The lane can confirm a large, lasting difference. It cannot separate a small one from zero within a year.

## What the result earns
- **PASS:** M533 CONFIRMED forward on paper. It earns a real-money proposal to the owner through
  `lab.gate.go_real()`, in small stakes placed by the owner, after their own check of both venues' terms.
- **PARTIAL:** monitoring only; no real money.
- **NULL:** M533 closed on NATGAS. R480 is untouched either way.

## Risks
- **RedStone's roll on Lighter** (WTI and NATGAS since 2026-10-22) is undocumented.
  - If it references a different contract than xyz for part of each month, the pair carries a calendar spread for
    those days.
  - That is part of the measured basis, not modelled separately. A large basis loss around roll days would show in
    the price legs.
- **Venues:**
  - Hyperliquid / trade.xyz: the oracle relayer, auto-deleveraging, halts, deployer changes.
  - Lighter: zk-rollup, LLP, auto-deleveraging, oracle changes like RedStone itself.
  - Both venues can change their funding formulas, as xyz did in December 2025.
- **Transfers** between the venues are assumed instant and cost 10 bp. In practice they take minutes to hours. A
  liquidation on one venue while USDC is in transit is not modelled.
- **Costs are assumed.** Fills are at the 1-hour close plus the half-spread, and the size is not limited by book
  depth.
- **Data:** xyz 1-hour candles beyond the venue's last 5,000 depend on R480's recorder. If it stops for more than 10
  days, the missing hours count against the 10% limit.

## Inputs (sha256)
```inputs
f6f743bf20c9d4509bca80c952405c8e2ce9373082b90e5d3905028e800a4e51  scripts/run_xvroll.py
5409ffc7a170904cd5e09247f9cdf0002f282c6c78af02f783fa1b86b37786c8  tests/test_xvroll.py
bff3e19e7ad5d89b0943424fd969024063f97bb79903e6994dc5ce7dfaf3bb66  .github/workflows/claude-xvroll.yml
12efdca302dfdbc1312dc7499a53de23af9276406e1934c547b9e8642622e895  lab/carrylane.py
bc323ae56d57077dcace41ea9e0af02dfc03c0d954cf7eb736979350a537ca34  lab/stats.py
04c45090be4113b9d9cf7d3c21c534ae8200363da3e5d4d55fe5a528801fdb9b  scripts/fetch_hip3stock.py
982455215c58232fda91a3193222f6afb268a87612685ab86848f1773d26dd1a  scripts/fetch_hip3carry.py
214ff732638a0ec29a1be56d54fb2ee1d341067cd01a8cf2f73196b8542b2d47  scripts/fetch_cryptomon.py
14c57f1aed3a392a3cdae5a906512cb68cf60e9d3ca0458f6192cf608519e3ee  scripts/run_xyzwknd.py
1a57429f9ecea80dacdb3722fd74386ff533eb13e99bf3463237da94e8491c29  scripts/record_futroll.py
```
