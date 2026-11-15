# prop (qwen3.7-plus)

Based on the evidence pack, neither edge can pass a standard funded-account challenge as currently configured. 

**Binding Constraints**
1. **Funding Carry (~1%/yr return, 0.07% max DD):** Binds strictly on the **10% profit target**. At 1% annualized return, hitting a 10% target would take a decade. Applying the leverage required to hit the target within a standard challenge timeframe would instantly violate the 10% max drawdown and 5% daily loss limits. The pack correctly concludes this is "not usable in a prop account."
2. **Event Edge / unlocks_v1 (+3.24% mean, -132% tail):** Binds strictly on the **5% daily loss** and **10% max drawdown** limits. The strategy’s tail risk is catastrophic for prop rules. A single historical event (RIVER at -132%)—or even the six events that lost >40%—would instantly blow past the 10% maximum drawdown threshold, failing the evaluation immediately.

**Is a Rules-Compliant Variant Conceivable?**
* **Carry Edge:** No. There is no mathematical way to accelerate a 1%/yr return to 10% without breaching strict drawdown limits.
* **Event Edge:** A compliant variant is *mathematically conceivable* but practically unviable. To survive the 10% max drawdown limit against the -132% tail, position sizing must be capped at roughly 3.8% of account equity per event (5% limit / 132% tail). At this micro-size, the +3.24% mean return yields a mere ~0.12% per event. Hitting the 10% profit target would require ~85 clean events. 
* **The Fatal Flaw:** Even if size-capped, the event edge cannot be deployed because it **lacks confirmed out-of-sample evidence**. The pack explicitly states the edge is only "PARTIAL" (passes gate 0) and has "no on-time forward day yet." Prop firms do not fund unconfirmed, un-forward-tested backtests. Furthermore, the pack warns that real-world execution requires manual-web trading, and we cannot assume the pack's numbers are tradable at size without severe liquidity impact.

**Conclusion**
The carry edge fails on return velocity; the event edge fails on tail-risk drawdown limits. No rules-compliant variant is viable because the only edge with acceptable drawdown (carry) lacks return velocity, and the only edge with return velocity (events) lacks out-of-sample confirmation and carries fatal tail risk.
