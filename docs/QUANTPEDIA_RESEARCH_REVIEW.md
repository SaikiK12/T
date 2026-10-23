# Three research mechanisms: sources, adaptations and exclusions

Reviewed 2026-10-19. This is a source review and research proposal, not a preregistration or an edge claim. No market outcome was calculated. Quantpedia is a discovery index; the primary paper, executable accounting and new data determine what can be tested. Public summaries were used without subscription access or a paywall bypass.

The duplication check covered `MAP.md`, `CLAIMS.md`, `NEXT_SEARCH_SPACE.md`, `ALTCOIN_LEADS.md`, relevant preregistrations and `registry/rounds.csv`. It cannot exclude a study missing from the original project's transcript. Historical dates already inspected by the project remain exploratory for a new adaptation.

## 1. Stateful daily trend across crypto assets

**Sources.** Zarattini, Pagani and Barbon, *Catching Crypto Trends*: [author page](https://www.abarbon.com/papers/catching-crypto-trends), [public primary PDF](https://concretumgroup.com/wp-content/uploads/2026/02/Catching-Crypto-Trends.pdf), [SSRN record](https://ssrn.com/abstract=5209907). Quantpedia's [May-22 digest](https://quantpedia.com/quantpedia-premium-update-may-22nd/) surfaced the paper; its premium entry was not used as evidence.

**Source definition, Sections 4-5.** For daily close `C[t]`, each horizon `n` uses the following current-inclusive channel and state:

```text
U[n,t] = max(C[t-n+1:t+1]); D[n,t] = min(C[t-n+1:t+1])
M[n,t] = (U[n,t] + D[n,t]) / 2
position[t] = 1 if C[t] == U[n,t], else 0 if C[t] <= T[t], else position[t-1]
T[t+1] = max(T[t], M[n,t]) for a continuing position
new entry: initialize its stop to M[n,t]; discard the previous trade's stop
```

Horizons: `5,10,20,30,60,90,150,250,360` days, equally weighted. Sizing: `min(0.25 / sigma[t], 2) * position[t]`; page 9 specifies 90-day annualized volatility. These are daily crypto observations. Returns use lagged weights. The 20% threshold affects volatility-induced rebalancing only; entries/exits bypass it. The diversified universe rotates monthly using prior liquidity.

**Version and ambiguity.** The PDF identifies itself as 9 April 2025; SSRN reports a later revision. Preserve the chosen version. Freeze unspecified volatility conventions, threshold denominator and tie precedence as implementation choices. Today's exit uses previously fixed `T[t]`, not today's raised stop. Do not substitute 63 equity sessions for 90 daily observations.

**Proposed adaptation.** A small fixed-coin daily futures screen can test this mechanism cheaply. Freeze one ensemble, complete UTC-day construction, volatility convention, arrival delay, futures funding, costs and passive comparator before calculation. Label a fixed surviving-coin set as a selected-universe adaptation. The paper's diversified spot study does not validate it. A six-coin screen is not a replication of the full rotating universe.

**Inputs and test.** Complete hourly closes, contract metadata and exact funding events suffice for that adaptation. Historical spot universes would require additional point-in-time coverage. Credit returns only after the executable post-close arrival; lagged-weight algebra does not establish a same-close fill. Compare net performance and market exposure with the identical-universe passive portfolio, including its real turnover; report 1x/2x/3x costs. Do not tune horizons after seeing results.

**Why distinct.** R203 tests first-hour/last-hour intraday momentum; R222 tests cross-sectional rankings; the atlas studies shorter-horizon features and contexts. Their nulls do not settle this stateful daily portfolio question. Its contribution still has to survive market-beta attribution and fresh evaluation.

**Completed bounded test, 2026-10-20.** [R229](../experiments/slow_trend_v1/FINDINGS.md) tests a fixed six-coin spot adaptation with no leverage, a full daily execution delay and a discovery-risk-scaled passive comparator. It fails its frozen validation comparison. This result applies to that adaptation; the futures and full rotating-universe questions above remain untested.

## 2. Slower execution of an unchanged slow flow target

**Sources.** [Quantpedia's cost-optimization review](https://quantpedia.com/transaction-costs-optimization-for-currency-factor-strategies/) summarizes Melvin, Pan and Wikstrom's [primary FX study](https://www.ifo.de/DocDL/cesifo1_wp8143.pdf). Gârleanu and Pedersen's [Journal of Finance paper](https://doi.org/10.1111/jofi.12080), with a [public manuscript](https://archive.nyu.edu/bitstream/2451/28346/2/DynamicTrading.pdf), derives partial adjustment when signals decay and trading incurs costs. FX or commodity findings do not establish a crypto result; their liquidity and cost structures differ.

**Proposed adaptation, not the papers' exact strategy.** Keep one existing flow formula and target construction unchanged. Compare exact adjustment with one fixed rule, `new_holdings = 0.75 * drifted_old_holdings + 0.25 * target_holdings`. Freeze the coefficient instead of searching a grid. Use identical arrival timing and gross limits; mandatory contract/unavailability exits remain immediate. The quadratic-cost theory does not make this rule optimal under proportional exchange fees.

**Inputs and test.** Existing target holdings, prices, funding and fee assumptions suffice. First check whether current code already nets expiring and incoming slices. Charge costs to net executed changes, not gross paper tickets. Test the paired difference in net daily PnL, cost savings, foregone gross returns, turnover and risk at 1x/2x/3x. Reduced turnover alone is not success: the source paper linked in [this Quantpedia ML review](https://quantpedia.com/the-expected-returns-of-machine-learning-strategies/) illustrates that cost reduction can be outweighed by lost gross return.

**Why distinct.** R213 studies entry delay; R217 changes sizing; R186-R187 select composite signals. None is this fixed partial-adjustment comparison. Changing execution must not rewrite their frozen journals or revive their claims as confirmed.

**Completed bounded test, 2026-10-20.** [R231](../experiments/partial_execution_v1/FINDINGS.md) tests half/quarter daily adjustment on the exact frozen R229 spot target. Both new policies are retained; the discovery-selected half adjustment fails its validation comparison because forgone gross return exceeds cost savings at 1x/2x. This is not a test on the original flow targets, which remain unavailable here.

## 3. Rebalancing versus letting identical holdings drift

**Sources.** [Quantpedia's public profile](https://quantpedia.com/strategies/rebalancing-premium-in-cryptocurrencies) and Hanicova and Vojtko's [primary working-paper record](https://ssrn.com/abstract=3982120). The profile discloses an in-sample short-weight comparison and unreported transaction costs. Its static universe includes a stablecoin; its selected 100%-long/70%-short illustration retains long market exposure. Neither a source rating nor its best parameter is independent confirmation.

**Proposed adaptation.** At each month boundary, choose eligible coins using only past liquidity and initialize two baskets identically. Reset one to equal weights daily; let the other drift until the common next monthly reset. The tradable combined target is `equal_weight_basket - drift_basket` with equal notionals. Net opposing holdings before calculating costs. This is a new dollar-neutral adaptation, not the source's selected 70% hedge. Dollar neutrality does not ensure beta neutrality.

**Inputs and test.** Complete closes, volume ranks, lifecycle records and funding suffice for a perpetual screen. Charge both scheduled and forced changes; preserve failed/delisted names and missing-data exclusions. Report net spread returns at 1x/2x/3x, market beta, concentration and turnover. Persistent winners can make contrarian rebalancing harmful; correlated prices and funding can remove its appeal. Lower geometric volatility does not guarantee positive arithmetic alpha.

**Why distinct and priority.** This is a portfolio-rule question, rather than R222's momentum rankings, but it may amount to another costly reversal exposure. Prioritize the daily trend screen and execution comparison ahead of it. All three require new frozen specifications and honest trial accounting before measurement; none authorizes deployment or treats reused historical dates as fresh confirmation.

**Completed bounded test, 2026-10-20.** [R232](../experiments/rebalancing_v1/FINDINGS.md) tests fixed daily/weekly/monthly long-only equal-weight spot resets against fixed-unit buy-and-hold, using the existing six-coin cache and full 1x/2x/3x accounts. Discovery selects monthly, but validation Sharpe gain and paired uncertainty requirements fail. The original full-universe long/short construction above remains untested.
