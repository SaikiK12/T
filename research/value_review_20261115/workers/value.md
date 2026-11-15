# value (qwen3.7-max)

**Theatre**
R493 session-splits (NULL, family-wise p=1.000), prop-firm carry (R202 explicitly bans it), and R265 historical variant mining (the calendar is "today's snapshot, not point-in-time"). The 2025-07..2026-09 holdout is spent; mining it is p-hacking. 

**Top 3 Work Items**

**1. R266 Forward Unlock Validation (unlocks_fwd)**
*   **Binding constraint removed:** Look-ahead bias. R265’s +3.24% return is unconfirmed out-of-sample because it relies on a non-point-in-time calendar. 
*   **Cheapest decisive test:** Run the active R266 forward lane to 120 scored tickets (futility at 60). 
*   **Falsification:** Hitting futility at 60 tickets, or failing the gate at 120 tickets (week-cluster t<2, or mean at 2x costs ≤0).

**2. Carry Execution Optimization (Web Maker vs. API)**
*   **Binding constraint removed:** Execution costs. The only confirmed edge (~1%/yr carry) is crushed by 9.3635 bp/side API taker costs. Web maker is 0 bp on 1106/1200 contracts.
*   **Cheapest decisive test:** Execute the proposed 20-30 tiny live calibration orders using web maker to measure real fill rates against paper.
*   **Falsification:** Web maker fill rates are too slow to capture the trailing 72h >20% APR funding window, or effective slippage exceeds the ~7.36 bp API premium.

**3. Unlock Tail-Risk Sizing & Squeeze Plan**
*   **Binding constraint removed:** Ruin risk. R265 has a 16.7% per-event standard deviation and six historical squeezes >-40% (RIVER -132%). The old "no event loses >40%" rule already failed six times.
*   **Cheapest decisive test:** Simulate the proposed Gate 4 limits (2% max stake, 25% hard stop) against the 422 historical events to measure stop-out drag.
*   **Falsification:** The 25% hard stop triggers so frequently on normal noise that it destroys the +3.24% edge, or the 2% stake yields absolute returns too small to justify the operational overhead of manual-web execution.
