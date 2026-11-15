# risk (qwen3.7-plus)

**Sizing & Squeeze-Protection Model**

**Pre-Registerable Rules**
1. **Position Cap:** 2% of total trading capital per event (aligns with Owner Gate 4 limits).
2. **Notional vs ADV:** Only enter if the unlock dose is ≥ 0.82 days of ADV. (All six >-40% gross losses in the archive occurred below this threshold).
3. **Funding Veto:** Reject entry if trailing 72h funding is < -20% APR. (Shorts pay funding; extreme negative funding, like RIVER's -45%, destroys the edge).
4. **Hard Exit:** Liquidate the position if the unrealized loss hits -25% of position notional (equating to a -0.5% hit to total equity).

**Survival Arithmetic**
The worst observed squeeze (RIVER) yielded -132% gross and -45% funding, totaling a -177% loss on position notional. 
* **Max Single-Event Hit:** At the 2% equity position cap, a -177% notional loss results in a -3.54% hit to total equity (matching the pack’s computed -3.55%).
* **Book Survival:** A -3.54% equity drawdown is well below the 25% book-level hard stop. 
* **Sequential Compounding:** Even if the worst-case -177% event repeats and no stops are triggered, fixed-fraction sizing over the historical 422 events yields a terminal wealth of 1.286x with a maximum drawdown of only -4.04%. The book mathematically cannot be ruined by a single event or the historical tail.

**Missing Data Requirements**
To fully operationalize and backtest this model, the following data is required but absent from the evidence pack:
1. **Intrabar Price Paths (Hourly OHLC):** The committed event file lacks high/low/MFE/MAE data. Hourly bars are strictly required to simulate, validate, and execute the -25% hard exit stop-loss rule.
2. **Real-Time Funding Feeds:** While 72h trailing funding is in the pack, live, high-frequency funding rate monitoring is needed to enforce the funding veto at the exact moment of execution.
3. **Point-in-Time ADV:** To enforce the ≥ 0.82 ADV filter in live trading, historical and real-time rolling ADV must be mapped point-in-time to avoid look-ahead bias on the volume denominator.
