# risk (qwen3.8-max)

**Risk-model prereg: R265 unlock-short is blocked until these rules are frozen and logged.**

Let **E** = trading capital. Book stake **B ≤ 2% E** (Gate 4). All caps are on **B** unless stated.

1. **Position cap**: initial notional per event  
   **N ≤ c = 4% B** (= **0.08% E**).  
   Rationale: worst observed event = **-132% gross -45% funding = -177% of notional**.  
   Max single-event loss = **1.77 × 4% B = 7.1% B**, far below the **25% B** owner stop.

2. **Portfolio/cluster cap**:  
   **Gross unlock notional ≤ G = 8% B** (= **0.16% E**).  
   New entries are sized:  
   **N = min(4% B, remaining G, 8% B / n_after_entry)**.  
   **K ≤ 4 positions on the same unlock date**. If entry would breach G or K, skip.

3. **ADV/liquidity cap** (execution only, not the rejected unlock/ADV tail filter):  
   **N ≤ min($10k, 1% of prior-day perp quote ADV)**.  
   If ADV data are missing, no entry. This keeps size near the measured $10k cost regime.

4. **Funding veto**: skip if, at entry,  
   **trailing 72h funding APR > 50%**, or  
   **predicted 7-day funding cost > 2% of notional**.  
   This is live/forward-only: the pack has only realised hold funding, not entry trailing funding.

5. **Hard exits / squeeze circuit breakers**:  
   - Strategy exit remains **cover at unlock-day close**.  
   - If any daily mark shows **event loss + accrued funding ≥ 50% of N**, cover next bar.  
   - If **book drawdown ≥ 20% B**, flatten all unlock positions and halt; owner hard stop remains **25% B**.  
   These stops cannot be tested in the committed file because there is no intrabar/daily path.

**Survival arithmetic**  
Worst single event at cap:  
**-177% × 4% B = -7.1% B**.  

Worst observed concurrent cluster = **-179.5% of cluster notional**. Stress it by adding a RIVER-like funding shock (+45 points) → **-224.5%**. At gross cap:  
**-224.5% × 8% B = -18.0% B**.  

Even a rounded **-250%** cluster shock gives **-20% B**, below the 20% flatten trigger and below the 25% hard stop. In account terms, with **B=2%E**, worst stressed cluster loss ≈ **0.36%E**, versus **0.5%E** hard stop.

**Cannot know/test from pack**  
Point-in-time ADV; entry trailing/predicted funding; intrabar or daily MAE/MFE paths; MEXC maintenance margin/liquidation ladder; real fill/slippage beyond $10k; point-in-time unlock calendar.
