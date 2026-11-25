# Open questions that only an experiment can settle (the register; `CLAUDE.md` rule 13)

- **How it works.** Each question is refined in its source file (hypothesis and opposite, why it is not known, the
  mechanism, the data, the cheapest experiment, the kill result, the value).
- **This register keeps:**
  - the status;
  - the prediction written before the experiment;
  - the result.
- **Each cycle picks by value × probability ÷ cost.** The first 30 questions and their scoring come from the room
  (`room_20261125b/open_questions.md`, citations checked with `scripts/verify_citations.py`: 3 verified, 13 located,
  2 to review).

| Id | Question (short) | Source | Status | Prediction (written first) | Result |
|---|---|---|---|---|---|
| Q26 | Do the gap books become correlated in crash months? | room Q26 | **answered 2026-11-25** | Mean pairwise correlation in stress months about 0.35: above the full-period median, below the 0.6 that would change sizing | **0.35 on average; H1 (>0.6) not supported.** Sizing unchanged; shared-venue pairs move together |
| Q19 | Does the euro P&L of the dollar legs move with EUR/USD? | room Q19 | **answered by reasoning** | — | The exposure is on the **principal**, not the P&L. A dollar collateral moves one for one in euros, and the strategy's dollar P&L is a few % of it. Use euro collateral where accepted (Kraken); count Hyperliquid's USDC principal as currency risk |
| Q16 | Does lot rounding leave hedges more than 2% off on R509's coins at €1-5k? | room Q16 | **answered 2026-11-25** | (none written: answered the same hour) | Legs of $50 / $100 / $250: 9% / 4% / 0% of 107 coins have a hedge more than 2% off. At stake 1's about $150 a leg, about 3%, and `stake_ticket.py` already skips any hedge more than 5% off. H1 (at least 10%) not supported |
| Q20 | Do venue deposit and withdrawal halts precede 10%+ gaps? | room Q20 | open | — | — |
| Q01 | Variational's frozen weekend index: is the gap to xyz above 100 bp on at least 20% of weekends, and closed by the open? | room Q01; `room_20261125/synthesis.md` | **recording** (from 2026-11-25) | P ≈ 0.25 that its quotes stay near the frozen index | first weekend 11-28/29 |
| Q25 | Are my written forecasts calibrated? | room Q25; `reflection_20261125_calibration.md` | **ledger started 2026-11-25** (`registry/forecasts.csv`, 19 forecasts, 7 resolved) | Brier below the base-rate reference at 30 resolved | **First score: Brier 0.249 against 0.204** for a constant (n 7). The high bin is overconfident: mean p 0.70, hit 0.25 |
| L1 | Does a floor venue's perp funding (about 10.95%/yr in calm markets) exceed the same coin's dated-futures or options-implied rate by more than costs, with convergence forced at expiry? | lead researcher, 2026-11-25 (cf. M170, M244: neighbours, not this pair) | **read 2026-11-25 23:35** (held data; 0 trials) | Read: for BTC and ETH, 2023-01..2026-09, daily, the next quarterly with 20-100 days left; annualized basis = (quarterly close / COIN-M perp close − 1) × 365 / days left; funding = Binance USD-M 8-hour rate × 3 × 365, daily mean. Spread = funding − basis, by year. **Prediction:** the 2023-26 mean spread is at least +2%/yr on BTC, with at least 3 of 4 years positive: P ≈ 0.40 (logged in `registry/forecasts.csv` as L1-spread) | **No rent: the spread averages about −0.2 to 0.0%/yr** depending on the bars (mine: +1.96, −0.24, −1.64, −0.21; the critic's independent run: +1.77, −0.53, −1.72, −0.30); positive in 1 of 4 years. ETH: +3.79, +0.70, −1.28, −0.58; mean +0.73, below the cost of two legs and four rolls a year. Binance's funding itself averaged 3-5%/yr in 2025-26: the 10.95% "floor" is a clamp that holds only while the premium is small. Prediction (P 0.40) resolved 0 |
| S1 | Cost-aware thresholds: at 3x costs (R508's real costs are 2-3× its 1x), does R275's book with entry 10%/yr (exit 5%) beat entry 5% (exit 2.5%) on R525's 12 pairs, 2024-26? | R531 FINDINGS (the filter won only at 3x, by trading less); R508's secondary th10% +24.84 vs +24.28 at 1x | **read 2026-11-26** (`scripts/measure_threshold_s1.py`, held data, 1 trial) | th10% ahead at 3x by ≥ 0.5%/yr with NW t ≥ 2: P ≈ 0.30 | **No difference.** th10 − th5 on the 12-pair portfolio, 2024-01..2026-09: 1x −0.18%/yr (t −1.36), 2x −0.06 (t −0.42), 3x +0.06 (t 0.41). The book is robust to its entry threshold. The th5 column reproduces R531's frozen rule exactly (6.49 / 5.19 / 3.89). Forecast (P 0.30) resolved 0 |
| S2 | ML on the exit, not the entry: among open trades, can past-only features predict which will keep paying over the next 14 days (the fat right tail: the best 10% of trades earn 123% of R531's net)? | R531 FINDINGS | open: needs a holding-period label design first | Out-of-sample AUC ≥ 0.60 with a positive book-level lift at 2x: P ≈ 0.15 | — |
| K1 | Upbit/Bithumb delisting clock: after an end-of-support notice (30-day clearing, then 30 days of withdrawals), does the coin's global perp drift down over the 30 days, against a matched control? | sweep `room_20261125d/scout_korea.md`, `triage.md` | open: needs a notice history (aggregator, terms first) | Mean notice-to-clearing-end return of the global perp below the control by 5% or more, on at least 30 notices: P ≈ 0.20 (M060's Binance delisting short was NULL; sibling forward lane R268, a MEXC spot delisting short, is running) | — |
| K2 | Korea's amended FX act (overseas crypto transfers must register, effective about 2026-12-03, from a secondary source): does the USDT/KRW premium over the official rate leave its 2026 band in the 4 weeks around the date? | `triage.md` (USDT premium measured: median +1.4% in 2024-25, −0.04% in 2026) | open, forward: knowledge only (no KRW account) | Out of its 2026 5-95% band on more than half of the days in the window: P ≈ 0.25 | — |
| O1 | SPX charm: is ES up from Thursday 16:00 to Friday 09:00 New York before 3rd-Friday SOQ expiries in 2022-26, after the paper's sample? | `reflection_20261125_greeks.md` §2; Baltussen-Terstegge-Whelan 2024 | **parked** (2026-11-25; first written "closed at Fermi", corrected after the critic: the spike sits in the a.m. auction, whose volume I did not measure) | If measured: at most +6 bp over other Thursday nights (square-root impact on $29-82bn of overnight ES), and t < 1. Worth under 2%/yr on notional even at the paper's 18 bp | not tested: the 2022-26 standard error (about 9 bp) cannot tell 5 bp from 0 |
| O2 | Single-stock gamma (TSLA, NVDA weekly and 0DTE call OI): is dealer gamma per 1% above 2% of the stock's daily volume, where pinning or squeezes can move the price xyz perps follow? | §2 | **undecided** (2026-11-25, one day; first written "alive at Fermi", corrected) | Ratio above 2% for TSLA on at least half of expiry Fridays: P ≈ 0.5 | **One expiry Friday (2026-11-13; OPRA open interest, $0.077).** 5.95M contracts. Gamma per 1% move at 45-60% vol: $2.3-2.5bn gross over all expiries, $1.2bn within 7 days, $0.7bn expiring that day. The calls-minus-puts net is $0.8-0.9bn. **Against the measured $13.2bn a day** (Yahoo, 20 sessions): **about 18% gross, 6.5% calls-minus-puts.** Crypto's gross is about 8% (M308 snapshot) while its dealer net is 0.13%. So gross with gross, TSLA is about 2× crypto, and the decisive dealer net is unknown. The dealer sign is unknown (retail buys TSLA calls, so the GEX convention may be backwards). **But the measured single-stock effect is on volatility, not direction:** Barbon-Buraschi find −12 bp of \|R\| per SD of imbalance, and the 30-minute autocorrelation effect is 1% of an SD. Pearson-Poteshman-White find about 12% of \|R\|. A directional trade on xyz needs the dealer's sign, which open interest does not give. A year of open interest (about $17 per stock) is therefore not worth buying until a sign source or a volatility use (sizing R530's single-stock weekends) is named |
| O3a | Weekend clock: does Deribit price Saturday like a weekday? | §3 | **superseded by O3b's read** (rich over 2022-25, about fair on BTC in 2026; this row's snapshot text stands as history) (2 snapshots + 2023-26 realized; the O3b read re-measures it) | (none written: answered in the same step) | **Not like a weekday:** implied Sat→Sun forward vol is 18-21%. For a straddle to expiry (75-86 bp) against a mean move of 77-81 bp, it is priced right. On variance it is cheap: close-to-close 24.9%, a ratio of 1.4-1.9 from the tails |
| O3b | Is the Sunday 08:00 → Monday 08:00 UTC day underpriced? (one-day BTC option IV on Sunday 08:00-10:00, trade-flow IV nearest the money, against that window's realized move, 2022-26) | §3 | **data fetching** (`data/deribit_trades` BTC from 2022-01, started 2026-11-25) | Written before the data: the mean Sunday straddle premium is at least 90% of the mean Sunday move, so no underpricing beyond costs. P(underpriced by more than 16 bp) ≈ 0.2. Weekday one-day VRP positive (implied above realized) on at least 4 of 5 weekdays; Saturday within ±10%. **Added before the read** (the data is still downloading, unopened): the 10-30 snapshot alone gives a ratio of 0.77-0.80, against this prediction | **Read 2026-11-25** (`docs/reviews/o3b_daily_vrp.md`, 1,733 days):
- **Sunday:** +21 bp (t 1.83); the premium is 88% of the move. **Not underpriced beyond costs**, but just under my 90% line.
- **Saturday was overpriced:** −48 bp a day (t −7.3; premium 125 bp against a mean move of 77). By year: −118, −57, −22, −40, then **+15 in 2026**. The gap closed in 2026.
- **Weekdays:** implied above realized on 3 of 5.
- **Score of my four predictions: 1 right** (Sunday not beyond costs); 3 wrong (the 90% line, 4 of 5 weekdays, Saturday ±10%).
- **Post hoc, checked:** Saturday takers were mostly sellers (44% buys; 35% in 2022). Sell-side IV was 29.9% against 31.0% for buys, so a taker seller at the bid earned the gap.
- **Audited** (`room_20261125c/audit_o3b.md`): reproduced exactly. At ±0.5% moneyness the Saturday gap is −32 bp (t −4.6), with the same pattern by year |
| O7b | ETH on Deribit: did its Saturday rent close when BTC's did? (O3b rule, `--coin ETH --min-amount 100`) | `reflection_20261125_o7.md` §6 | **read 2026-11-25 22:24** | Saturday 2022-26 ≤ −30 bp with t ≤ −3: P ≈ 0.75. 2026 within ±20 bp: P ≈ 0.55. Sunday not beyond costs: P ≈ 0.75 | **Read 2026-11-25 22:24** (`o7_eth_daily_vrp.md`): Saturday −40.6 bp (t −3.9; by year −109, −44, −3, −42, **+8**). **Sunday +52.1 (t 3.0; +77, +9, +38, +128, −2).** Predictions 2 of 3 (the Sunday one wrong). On both coins the weekend gap (Saturday rich, Sunday cheap) ran 2022-25 and is about zero in 2026 |
| O7 | Is the weekend gap Deribit closed in 2026 still open on younger option books (Deribit's SOL/XRP/HYPE dailies; OKX, Bybit, Binance, Derive)? | O3b read | **answered: no independent younger book** (2026-11-25) | Saturday one-day IV above 0.55 × the weekday IV on at least one younger book: P ≈ 0.4 | **Snapshot 2026-11-25 18:37 UTC (Deribit, public):**
- BTC prices Sat→Sun at 33% forward against 59% for Fri→Sat (0.56), consistent with a closed gap.
- SOL, XRP, HYPE, AVAX and TRX list Thursday and Friday dailies and weeklies only, with no Saturday or Sunday expiry. Their weekend sits inside the weekly, and one snapshot cannot separate it from the term structure.
- Next: implied-vs-realized on their weeklies from trade history. The fetcher holds BTC/ETH only, so it needs a USDC-options extension, or other venues' weekend dailies.
- **Reader + my check:** only BTC and ETH have weekend dailies (Deribit, OKX, Aevo), and OKX's weekend weight equals Deribit's (BTC 0.59 against 0.60; ETH 0.80 against 0.79). One shared model, so no younger independent book |
| O7c | Tripwire: does the weekend gap reopen? (O3b and O7b reads extended monthly with new public trades) | `reflection_20261125_o7.md` | **monitoring, redesigned** (critic: the 3-month rule had about 20% power and about 61% false-trip odds over two years) | Rolling 12 months, read quarterly, with a power target of at least 60% against a −30 bp gap computed before the first look | — |
| O7d | Is BTC's Sunday one-day straddle still rich after 2026? (2026 in-sample: −35 to −49 bp in every robust statistic, n 38-39; makers' Sunday weight 0.91) | `reflection_20261125_o7.md` corrections §5 | open: forward only; the 2026 figure is post hoc | Forward 2027 H1 BTC Sunday mean (move − premium) ≤ −16 bp at ±0.5%: P ≈ 0.35 | — |
| O4 | Crypto vanna (M310): does an IV fall after FOMC push perps up? | §4 | **closed at Fermi** | Null: R292's dealer book is 0.13% of perp volume per 1% move, and its vanna scales with it | not tested |
| O5 | Vomma: does DVOL's own variance forecast realized vol beyond HAR? | room Q10 | open, low priority (a sizing input, not a payer) | — | — |
| O6 | Mix: do single stocks pinned at a strike on Friday move away from it on xyz over the weekend? | §4 | idea; waits for O2's ratio | — | — |

## Results
### Q26 (2026-11-25; R525's seen daily nets at 1x, `experiments/gap_breadth_v1/results/pair_daily_net_1x.csv`)
- **Full period:** mean pairwise correlation 0.20, median 0.04, over 66 pairs.

| Stress month | Live pairs | Mean pairwise correlation | Equal-weight portfolio that month |
|---|---|---|---|
| 2021-05 (crash of 05-19) | 3 (all Bitfinex) | 0.92 | +1.45% |
| 2022-05 (LUNA) | 6 | 0.05 | −0.10% |
| 2022-11 (FTX) | 6 | 0.24 | +0.77% |
| 2024-08 (08-05) | 8 | 0.42 | +0.21% |
| 2025-10 (10-10) | 8 | 0.11 | −0.20% |
| any month | — | median 0.24, 90th percentile 0.65 | median +0.45% |

- **Stress months average 0.35. The prediction held, and H1 (above 0.6) is not supported.** The portfolio did not lose
  more than 0.2% in any of these months.
- **The 0.92 of 2021-05 is three pairs sharing one floorless venue (Bitfinex).** The risk that binds is a shared
  venue, not a shared crash.
  - This agrees with the framework note's caveat, and with the stake rule's 50% venue cap proposed by the room.
- **Limits:**
  - in-sample nets on R525's engine, with last-trade valuation;
  - daily, not intraday;
  - five events.

### Q16 (2026-11-25; Kraken and Hyperliquid instrument lists, live; Hyperliquid mids)
- 107 of R508/R509's coins have both lot rules. Each leg is rounded down to its venue's step at the same dollar size.

  | Leg size | Coins more than 2% off | Worst |
  |---|---|---|
  | $50 | 10 (9%) | XMR 7.2% |
  | $100 | 4 (4%) | BTC 3.6% |
  | $250 | 0 | — |

- **Limit:** the 1000x-unit coins (PEPE, BONK) use one mid for both venues, so their flags may be a unit artifact.
  The ticket handles units per venue.

