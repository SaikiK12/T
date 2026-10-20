# Prop firms: rules, economics, and fit with the lab's books

A subagent researched this on 2026-10-20. It did not touch the repository. It ran small stylized simulations in the
scratchpad: daily steps, normal, skewed and fat-tailed returns, no intraday path.

- **O** means the firm's own page, read that day.
- **3P** means a review or affiliate site. Several 3P sources are affiliates or rival firms.
- Most firm sites blocked the agent (Apex, Breakout, E8, FundingPips and TPT returned 403, 404 or 503).
- **Every 3P cell must be checked on the firm's own site before any fee is paid.** The fee is real money: the owner
  pays it, and only after `docs/GATES.md`.

## Firms (100K account unless noted)

| Firm / product | Fee | Target | Daily / max drawdown | Days / consistency | Split | Notes |
|---|---|---|---|---|---|---|
| [HyroTrader](https://www.hyrotrader.com/) 2-Step (O) | $579, refunded at first payout | 10% + 5% | 5% of day-start equity (00:00 UTC) / 10%; FAQ says static, one 3P says trailing | 5+5 days; no day over 40% of target | 80-90% | Crypto perps (700+), all demo. Own API bots allowed. Banned: martingale, cross-account hedging, copy trading, HFT. Coins under $100M cap limited to 5% of balance. Closes after 30 idle days |
| HyroTrader 1-Step / Zero (O) | $749 / $949 | 10% | 4%/6% and 3%/5% | 5 days / 1 day; 40% day, 50% trade | 80-90% / 80% | Zero's fee is not refunded |
| [Breakout (Kraken)](https://cryptoslate.com/prop-firms/breakout-review/) 1-Step (3P) | $330-800 | 9-12% | 3% (balance at 00:30 UTC) / static 3-6% | none | 80% (90% for +20% fee) | Costs 0.04% per side plus 0.033%/day swap. 5x BTC/ETH, 2x alts, 62 pairs. Firm may internalize orders. Kraken owns it since 2025-09 |
| Bitfunded (3P, a rival's blog) | $799 | 8% + 5% | 5% / 8-10% end-of-day trailing | 5 days | 80-90% | 1:5, bots allowed. Payouts not verifiable on-chain |
| [Topstep](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit) Combine 50K (O) | $49/mo + $149, or $85/mo | $3k | $2k loss limit trailing the end-of-day balance but enforced intraday; locks at start; **resets to $0 after the first payout** | best day at most 55% of target | 90%, caps $2-6k per payout | Futures. Bots allowed with conditions; no HFT, no VPS. Flat by 3:10 pm CT |
| Apex (3P, rules changed 2026-03-01) | $249-490 one-time | $3k | $2k trailing; daily $1k | 50% at payout | first payout capped $1.5k; 6 payouts max | Automation and hedging banned |
| [FTMO](https://ftmo.com/en/trading-objectives/) 2-Step (O) | about EUR 540 (3P), refunded | 10% + 5% | 5% (00:00 CET) / 10% static | 4 days | 80% | CFDs incl. crypto. EAs allowed. News and weekend limits only on funded Standard; Swing exempt |
| FTMO 1-Step (O) | not refunded | 10% | 3% / 10% end-of-day trailing | best day at most 50% of profit (from 2026-10-12); delays the pass rather than failing it | | |
| [The5ers](https://the5ers.com/high-stakes/) (O) | $249 1-step | 10% + 5% / 10% | 5%/10% (2-step); 3%/6% (1-step) | 3 profitable days | 80-100% | 1:100 |
| MyFundedFutures, Tradeify, Take Profit Trader, FundedNext, E8, FundingPips | various | | | | | Low-confidence data. FundingPips changed payout rules at least 5 times in June-Sept 2026 |

**Closed or troubled firms:**
- MyFundedFX's prop arm shut in 2026-02.
- OANDA Prop Trader was removed in 2026.
- FundingTicks wound down in 2026-01.
- SurgeTrader closed in 2024-05.
- The Funded Trader paused in 2024-03.
- Finance Magnates estimates [80-100 firms closed](https://datalab.financemagnates.com/market-insights/tracked-prop-firm-crypto-payouts-doubled-to-115m-in-q1-2026)
  between 2024 and Q1 2026.

## Economics
- **Firm-stated pass and payout rates:**
  - Topstep 2025: 16.8% of Combines passed, 33.3% of funded traders were paid, 0.71% reached Live.
  - FPFX Tech (300k accounts): 14% pass and 7% paid.
  - Take Profit Trader 2025: 36% of tests passed.
- **How firms earn:**
  - Mostly from challenge fees on simulated accounts (HyroTrader says so; Breakout's terms say it earns when traders
    fail and rebuy).
  - A consistent winner is a cost to them. That is what payout caps, consistency tests and "risk model" reviews are for.
- **Working papers (2026, not peer-reviewed; SSRN pages seen only as snippets):**
  - [Hall, arXiv 2609.14859](https://arxiv.org/abs/2609.14859): sizing alone passes about 40%, against a measured 16.8%,
    and no setup broke even.
  - Lim: zero-edge two-step pass is about 30%, and 29 of 31 contracts have negative expected value.

## What the rules reward
- **A zero-edge pass is a coin flip set by the rules.**
  - The pass probability per phase is D / (D + T): the drawdown room divided by drawdown plus target. It does not depend
    on volatility.
  - FTMO 2-step: 10/20 x 10/15 = 33%. The agent's simulation gives 32%, R202 gives 28-32%, and Lim gives 30%.
  - **So a pass says nothing about skill.**
- **Size.** Pass probability is flat near the best daily volatility: about 0.5-1% of the account for a 10% static
  drawdown, and 0.5-0.75% for 5%.
- **FTMO 2-step pass probability at the best size, by annual Sharpe:** 32% at 0, 64% at 1, 89% at 2, 98% at 3.
  - Flow book A (+22 bp/day, Sharpe about 1, about 4% daily vol at size 1) would run at size 0.12-0.25, as R202 found.
- **Skew matters.** At Sharpe 2:
  - negative skew cuts the pass from 84% to 68%;
  - positive skew lifts it to 87%.
  - A 40% best-day rule costs 7-11 points for lumpy books at 1.5% daily vol.
- **Traps:**
  - Intraday trailing drawdown punishes unrealized peaks.
  - Topstep's floor resets to $0 after the first payout, so the funded cushion vanishes.
  - Some firms switch from end-of-day to intraday trailing in the funded stage.
  - Changing size between stages is treated as gambling.

## Fit with the lab's books
- **Flow book A** (unconfirmed) fits HyroTrader and Breakout, with three things to check:
  - Its holdout gross is about 68% BEAT and LAB: small caps that hit HyroTrader's 5% cap.
  - Breakout's fee plus swap is not modelled.
  - Bitfunded's end-of-day trailing floor fails a book with a 20-47% drawdown.
- **top_vs_crowd:** a hypothesis only. Its MEXC replay is about zero.
- **Carry:** cannot reach a 10% target, and it needs a spot leg.
- **Cross-asset trend (forex, indices) on FTMO or The5ers CFDs:** fits the rules (EAs allowed, no time limit) but takes
  months to reach 10% at low drift.
- **Overnight index drift:** impossible at futures firms, which require being flat by the close.

## How much edge a challenge needs (synthetic map, M211 first pass, 2026-10-20)
`scripts/prop_edge_map.py` writes `experiments/propsim_v1/edge_map.csv`. It is a model with no market data, so it is
not a trial and has no registry row.
- **Setup:** a 20-year synthetic daily stream (1% daily vol at size 1, normal or Student t4) at each annual Sharpe from
  -1 to 3. It runs through each `lab/propfirm` preset, at the size with the best expected value (or break-even fee where
  the fee is unknown). Challenge horizon 365 days, then 180 funded days.

| Annual Sharpe | -1 | -0.5 | 0 | 0.5 | 1 | 2 | 3 |
|---|---|---|---|---|---|---|---|
| HyroTrader 2-step, paid (normal) | 6% | 11% | 24% | 41% | 59% | 68% | 83% |
| HyroTrader 2-step, EV USD (normal / t4) | -147 / -363 | +366 / -32 | +1,538 / +855 | +3,975 / +2,839 | +7,337 / +6,076 | +16,811 / +14,442 | +30,464 / +22,620 |
| FTMO 2-step, paid (normal) | 7% | 13% | 21% | 31% | 58% | 69% | 84% |
| FTMO 2-step, EV USD (normal / t4) | -66 / -83 | +649 / +404 | +1,928 / +1,361 | +4,114 / +3,306 | +7,366 / +6,557 | +18,166 / +14,383 | +31,709 / +23,019 |
| Topstep 50K, paid (normal) | 8% | 7% | 13% | 25% | 42% | 67% | 85% |
| Topstep 50K, EV USD (normal / t4) | +155 / +159 | +274 / +261 | +414 / +413 | +726 / +707 | +1,247 / +1,385 | +3,264 / +3,387 | +6,192 / +6,329 |

Breakout Pro and CFT have no captured fee, so only their break-even fee is in the CSV: at Sharpe 0 it is about USD 1,100
(Breakout) and 2,500 (CFT); at Sharpe 1 it is 4,400 and 8,500.

**Reading:**
- **The model is too kind to the trader.** At the 100K firms it breaks even between Sharpe -1 and -0.5; at Topstep it
  stays positive even at -1. So even a losing trader looks profitable.
  - It assumes no trading costs, every payout honoured, i.i.d. days, one fee per attempt and the best size, chosen
    with hindsight.
  - None of the rule features listed below is modelled yet: payout caps, consistency in the funded stage, intraday
    breaches, recurring monthly fees and resets.
  - The positive EV at negative Sharpe is the option in the contract: the loss is capped at the fee, while variance can
    still reach a payout. At negative Sharpe the best size is large (1.5-2x), which is that option being priced.
- **The paid rates firms publish sit at the model's Sharpe -1 to 0.**
  - Topstep: 16.8% pass x 33% paid is about 5.6% of Combines. FPFX: 7%.
  - Typical buyers therefore trade like a Sharpe -1 book *after* everything this model leaves out. The firms' own
    numbers, not this map, say what the average attempt is worth.
- **What the map does say:**
  - The chance of being paid roughly doubles from Sharpe 0 to Sharpe 1 (HyroTrader 24% to 59%, FTMO 21% to 58%).
  - At Sharpe 1, the modelled EV per 100K attempt is about USD 7k. That is an upper bound, not a forecast.
  - Fat tails (t4) cut EV by 11-44% at the 100K firms for Sharpe 0-3; Topstep's small account barely moves.
- **The constraint is having the edge, not the firm.** A book with Sharpe ≥ 1 *after* costs, confirmed on unseen data,
  is the entry ticket. The lab has none confirmed: flow book A is unconfirmed (holdout t 1.22).

## Simulations to run (queue M211)
`lab/propfirm.py` needs these rule features first:
- Breakout's balance-based daily loss reset at 00:30 UTC;
- a per-side cost plus daily swap;
- hourly paths, so intraday breaches show;
- Topstep's intraday-enforced end-of-day trailing floor with lock, its reset after payout, and payout caps;
- FTMO 1-Step's delaying consistency rule;
- a funded-stage consistency rule;
- 30-day inactivity expiry;
- the low-cap exposure cap;
- a haircut for payouts that never arrive, calibrated to 7% of accounts paid.

Then, ranked:
1. HyroTrader 2-Step and 1-Step x flow book A (size 0.15-0.25), at 2x and 3x costs.
2. Breakout 10K x flow book A and top_vs_crowd.
3. FTMO Swing x cross-asset trend.
4. Topstep 50K x an intraday-flat micro-futures book.
5. Bitfunded as a stress test of end-of-day trailing.

**Never do these:**
- martingale or size escalation to pass;
- cross-account hedges or copy trading;
- VPNs or VPSs to get around rules;
- "instant funded" shortcuts;
- firms without verifiable payouts or that change rules mid-account.
