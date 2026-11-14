# New-edge scan: the lab is saturated; one genuinely-new lead (intake, 2026-11-14)

The owner asked for work that improves results. A read-only research subagent (S5) searched primary sources
(papers, SSRN, arXiv, exchange/protocol docs) for new executable edges and checked each against the registry. This
page records the lead it judged worth keeping and why the rest are not. It adds method M539. It is not evidence of a
return; no backtest was run and no data was acquired.

**Headline:** the surface is saturated. Of the promising new papers, three map onto already-registered methods
(15-min reversal -> M055, BLOCKED; Hyperliquid wallet markout -> M429; the quarter-hour effect -> M082, BLOCKED).
The only genuinely-new, feasible, low-turnover lead is **session-decomposed MAX**, now **M539**.

## M539 - Session-decomposed MAX on 24/7 altcoin perps [new]
- **Claim (source):** in 24/7 crypto the maximum *intraday* return over the past week positively predicts next-week
  *intraday* returns, and overnight MAX predicts overnight returns, while **cross-period** predictability is absent
  (intraday MAX does not predict overnight and vice versa). -- Haichen Yang, "Max Effect in Crypto Market: Evidence
  from Intraday and Overnight Trading", PhD dissertation, University of Hawai'i at Manoa, May 2026. Not
  peer-reviewed; uses CoinMarketCap VWAP, not perp data.
- **Why it is not M144:** the lab already has the MAX factor (M144; R222 NULL, MAX_POS +3.0 bp/day t 0.27) and the
  session split (M492, MEXC stock perps; R435 NULL). It has never combined them, and the paper's distinctive claim
  is a **positive same-session (momentum) sign** -- the opposite of the lottery/reversal prior M144 tested -- plus a
  falsifiable zero cross-period structure. New hypothesis, not a re-run.
- **Data:** Binance Vision `data/futures/um/monthly/klines/{SYM}/1h/...zip`, top-50 USDT perps by trailing 30-day
  quote volume; the lab already builds `data/klines_1h`. No new source, no key. (The local `data/` folder is empty
  in this checkout, so the lane needs the standard fetch before it can run.)
- **Bounded gate-0:** signal `MAX_intra` = max over past 7 d of the 14:00-20:59 UTC return; `MAX_over` = max over
  21:00-13:59 UTC; rank cross-sectionally, long top quintile / short bottom quintile, dollar-neutral, weekly
  rebalance, 7 d hold. Costs 1x/2x/3x of MEXC's measured round trip (R224). Nulls: (a) within-day permutation of
  session labels; (b) the matched 24 h-MAX book (M144) as the no-split control. Pass: net 1x > 0, NW t > 2.0, and
  > the M144 book by >= 1 bp/day on discovery 2021-23, then one frozen holdout.
- **Limits:** the 09:00-16:00 EST session is an arbitrary cut in a 24/7 market (robustness to other windows
  unverified); R222 already found the 24 h MAX null in perps, so the edge rests on the split surviving transfer;
  the CMC universe has survivorship; capacity is modest (top-50, weekly).

## Leads not kept
- **Funding-anchored basis mean reversion, half-life ~3.5 h** (SSRN 7143718; Cao et al., IREF 2026): weakest
  novelty (M047/M171/M267/M402 already cover basis reversion) and likely **cost-negative** -- at the lab's ~9 bp
  MEXC round trip a 3.5 h half-life basis must exceed ~12 bp to pay.
- **HIP-3 mark-oracle divergence** (trade.xyz / Hyperliquid): novel signal (`grep oraclePx` -> 0 in methods) but on
  stock/commodity perps, off the MEXC-altcoin constraint, thin history.
- **Leverage/OI/funding crash-risk gate** (IJEBMR 2026, DOI 10.51505/ijebmr.2026.10315): a de-risking conditioner
  (nearest M176/M233/M287), not a directional book; AUROC 0.76 is weak and crash prediction is not tradable alpha.
- **Extreme negative funding -> BTC spot return** (AIJMR 2026): low novelty; the extremity direction already failed
  here (R273 `fundext_v1`, survivors none).

## Sources
READ (abstract/body): Yang dissertation; SSRN 7143718; Cao et al. IREF DOI 10.1016/j.iref.2026.105967; IJEBMR DOI
10.51505/ijebmr.2026.10315; Zhivkov MDPI Math 14(2):346; AIJMR DOI 10.62127/aijmr.2026.v04i04.1493; trade.xyz
funding changelog + hyperliquid.gitbook.io. Reachability probed keyless (MEXC contract/spot klines and funding,
Binance Vision, Hyperliquid `info`, dYdX indexer, Lighter orderbook) -- all 200, no bulk pull.
UNREAD: any paywalled full text; the MDPI body; SSRN 7205749 (deadband funding, abstract blocked -- an unverified
lead, `grep deadband` -> 0 in the registry); MEXC `realClose` semantics.
