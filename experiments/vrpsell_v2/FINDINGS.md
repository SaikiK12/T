# FINDINGS: vrpsell_v2 (R409). The premium is there before costs; hourly delta hedging at taker cost eats it

**Verdict: NULL for BTC and for ETH by the frozen rule. 2 trials, gate 0.**

The rule: sell one at-the-money straddle each Friday on the next weekly Deribit expiry, delta-hedge it every hour on
the perp, and hold it to expiry. Window: Fridays 2021-01-01 to 2026-09-18.
- The run: `run.log`, 2026-11-05 20:41 UTC, PREREG `0023daa679d5`, 10 inputs matched. One run.
- Results: `results/summary.json` and `results/weeks.csv`.
- **Coverage:** BTC 295 of 299 weeks, ETH 296 of 299. The skipped weeks have a gap in the perp minute prices
  (`no_price_path`: 4 for BTC, 3 for ETH). Every entry used the 08:00 hour.

## Net result (r = net P&L as a fraction of one coin's notional, per week)

| Coin | m | Mean bp/wk | NW t | %/yr | Hit | Worst wk bp | Max DD % | Halves bp (21-23 / 24-26) | 5% trimmed bp | Without best 10 bp |
|---|---|---|---|---|---|---|---|---|---|---|
| BTC | 0 (gross) | +44.0 | 4.66 | +22.9 | 67% | −608 | 14.7 | +56.4 / +30.4 | +47.9 | +31.3 |
| **BTC** | **1** | **−12.2** | **−1.27** | **−6.3** | **46%** | **−663** | **50.8** | **+1.1 / −26.7** | **−7.8** | **−24.8** |
| BTC | 2 | −68.4 | −7.00 | −35.5 | 28% | −717 | 201.6 | −54.2 / −83.8 | −63.6 | −81.0 |
| BTC | 3 | −124.5 | −12.46 | −64.7 | 17% | −771 | 367.3 | −109.5 / −140.9 | −119.4 | −137.2 |
| ETH | 0 (gross) | +40.8 | 3.50 | +21.2 | 60% | −886 | 21.3 | +41.0 / +40.7 | +45.6 | +27.7 |
| **ETH** | **1** | **−18.0** | **−1.53** | **−9.3** | **46%** | **−973** | **54.3** | **−16.8 / −19.3** | **−12.6** | **−30.9** |
| ETH | 2 | −76.8 | −6.49 | −39.9 | 30% | −1,061 | 227.2 | −74.5 / −79.2 | −70.7 | −89.6 |
| ETH | 3 | −135.6 | −11.34 | −70.5 | 20% | −1,149 | 401.2 | −132.3 / −139.2 | −128.7 | −148.2 |

- **Gross (m = 0)** still pays Binance funding. It drops every scaled cost: the half-spread, the option and delivery
  fees, and the hedge fee. It is reported, not decided on.
- **The maximum drawdown** is the peak-to-trough of the summed weekly r, in % of one coin. Above 100% the book has lost
  more than the coin.

## The six checks at 1x (PASS needs all six)

| Check | Bar | BTC | ETH |
|---|---|---|---|
| 1. Mean at 1x | > 0 | −12.2 bp, no | −18.0 bp, no |
| 2. NW t at 1x (lag 2) | ≥ 2.24 | −1.27, no | −1.53, no |
| 3. Mean at 2x | > 0 | −68.4 bp, no | −76.8 bp, no |
| 4. Mean at 1x in each half | > 0 | +1.1 / −26.7, no | −16.8 / −19.3, no |
| 5. 5%-trimmed mean at 1x | > 0 | −7.8 bp, no | −12.6 bp, no |
| 6. Mean at 1x without the 10 best weeks | > 0 | −24.8 bp, no | −30.9 bp, no |

Both coins fail every check.

## Reported, not decided on
- **Unhedged at 1x:**
  - BTC: +10.4 bp/wk (t 0.34); worst week −2,531 bp; drawdown 80%.
  - ETH: −28.0 bp/wk (t −0.68); worst week −5,229 bp; drawdown 142%.
  - Both 5%-trimmed means are positive (+56 and +30 bp), but once the tails are back in, the means are no better than
    zero.
- **IV minus realized volatility over the hold** (mean, frozen output): BTC +0.85 vol points, ETH −1.89.

## Where the cost goes (post-hoc diagnostic, not pre-registered)
`results/cost_decomposition.json` recomputes each week with the frozen runner's own functions, unchanged, and splits
the m = 1 cost. It decides nothing. Figures are mean bp of the entry price per week.

| | BTC | ETH |
|---|---|---|
| Premium sold (at mid IV) | 594.1 | 753.9 |
| Payoff paid | −566.4 | −762.5 |
| Hedge P&L | +22.5 | +59.3 |
| Funding paid by the hedge | −6.3 | −9.9 |
| **Gross (m = 0)** | **+44.0** | **+40.8** |
| Half-spread on the sale | −9.8 | −11.9 |
| Option fee (2 legs) | −6.0 | −6.0 |
| Delivery fee | −1.5 | −1.5 |
| **Hedge fee (5 bp per change, hourly)** | **−38.8** | **−39.4** |
| **Cost of one m** | **56.2** | **58.8** |
| **Break-even cost multiple** | **0.78** | **0.69** |

- **The net is linear in m**, with steps of 56.2 bp for BTC and 58.8 bp for ETH. So the edge vanishes at 78% and 69%
  of the frozen costs.
- **The hedge is 69% (BTC) and 67% (ETH) of the cost.** The median turnover of the hourly 2N(d1) − 1 hedge is 7.8
  coins a week for BTC and 7.9 for ETH; at 5 bp, that is 39 bp a week.
  - Even at Deribit's listed 3.5 bp perp taker fee, the hedge alone would be about 27 bp.
  - The option side (spread plus fees) costs 17-19 bp, under half the gross.
- **Median IV minus realized volatility:** +4.3 vol points for BTC (positive in 64% of weeks) and +2.4 for ETH (57%).
  - The means are near zero (+0.85 and −1.89) because a few weeks of extreme realized volatility pull them down.
  - That is the short-volatility shape: a premium in most weeks, paid back in the tails.

## Reading
- **A premium is paid to sellers before costs.** The gross delta-hedged short straddle earns +44 bp/wk on BTC
  (t 4.66) and +41 bp/wk on ETH (t 3.50), positive in both halves. This is the first time the lab has measured an
  option premium.
- **It is not a discovery against the program.** The read is against `registry.program_trials()` = 9,784,334
  trials, and the gross t is neither a decision criterion nor large enough to survive that count.
  - It is an economic premium the literature expected and R209 hinted at (DVOL above trailing realized volatility on
    82% of BTC days), not a searched pattern.
  - The forward test, not this backtest, is what would have to show it.
- **At executable cost, as frozen, it is negative,** mainly because of the hedging frequency, not the option spread.
  Hourly rebalancing at taker cost buys away the premium that the sale earned.
- **Unhedged is no answer:** the tails make its mean noise.

## What would change the answer (a new lane, never this one)
Every idea below is post-hoc: it was formed after this gross series and cost split were seen. A lane built on them is
gate 0 on seen data at best, and its PREREG must say so. The honest test of such a rule is forward on paper.
- **A lower-turnover hedge,** such as a no-trade band around the delta (Whalley-Wilmott), daily rebalancing, or a hedge
  only when |delta| passes a threshold. The hedge fee is the binding cost, but a wider band adds path variance.
- **A sale at better than the bid** (maker on the option book), which needs queue and fill evidence first (item 11,
  M474). Deribit's option fee is the same for maker and taker, so only the 10-12 bp spread term is at stake.
- **A hedge on Deribit's own perp at its maker fee,** which needs Deribit's maker fee and fill evidence, not assumed.

## Limits (as stated at freeze)
- **The sale price is a proxy:** the hour's amount-weighted IV minus one half-spread from a single snapshot.
- **Settlement is a proxy:** the perp at 08:00 UTC stands in for Deribit's 30-minute index average.
- **One strike and fixed hourly hedging:** no wing protection and no sizing.
- **Margin and path risk on the short legs are not modeled.** The worst weeks (−6.6% BTC, −9.7% ETH of one coin at
  1x) and the drawdowns above are the visible part of that risk.
