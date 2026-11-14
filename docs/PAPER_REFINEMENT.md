# Refining edges on paper: what forward trading can and cannot show

From a literature subagent report (2026-10-19). The power numbers were re-simulated in this repo before R221 was
frozen. Grades:
- **A:** peer-reviewed and replicated;
- **B:** peer-reviewed;
- **C:** working paper;
- **D:** practitioner.

Most sources were read at the abstract level.

## 1. How long a paper record must be
I.i.d. normal daily returns, one-sided 5% test of Sharpe > 0, 365-day year:

| True annual Sharpe | Power at 90 d | 180 d | 365 d | 730 d | Days for 80% power |
|---|---|---|---|---|---|
| 1.0 | 13% | 17% | 26% | 41% | about 2,260 |
| 1.5 | 18% | 28% | 44% | 68% | about 1,000 |

- At 90 days, the smallest annual Sharpe detectable with 80% power is about 5.
- Daily autocorrelation of 0.1 / 0.2 / 0.3 multiplies the days needed by 1.22 / 1.50 / 1.86 (Lo 2002, FAJ 58(4);
  B).
- Overlapping 72 h slices make the flow books autocorrelated, so the real numbers are worse.

**Consequence.** `lab.gate.go_real()` at 90 days is a kill-or-continue screen, not proof:
- It catches a broken implementation, a sign flip or a disaster.
- It cannot confirm a Sharpe-1.5 edge.
- Statistical confirmation comes from the archive's out-of-sample windows plus a long forward record, judged at
  boundaries frozen in advance (R221).

## 2. Looking more than once
- **Fixed looks with alpha spending** (O'Brien & Fleming 1979; Lan & DeMets 1983; A). This is the cheapest way to
  check at set dates:
  - three looks at 30/60/90 days need z of 3.47 / 2.46 / 2.00;
  - the final look costs about 2% more than a single test.
  - **R221 uses this:**
    - futility at 90 on-time days (stop if t <= -2);
    - efficacy at 182 days (z >= 3.558);
    - final at 365 days (z >= 2.397);
    - Bonferroni over 3 books.
- **Always-valid confidence sequences** (Howard, Ramdas, McAuliffe & Sekhon 2021, Ann. Stat.; Waudby-Smith & Ramdas
  2024, JRSS-B; B). These allow monitoring at any time. They are about 1.9x wider than a fixed test at day 90 and
  assume independent or martingale-difference data. Use them for dashboards only; never promote a book on them.
- **SPRT** (Wald 1945; A). Optimal for i.i.d. data. For Sharpe 0 vs 1.5 its expected stopping time is about 630 days
  when the edge is real and about 380 when it is not.

## 3. Choosing among variants (champion vs challengers)
- The literature tests whether the best of many variants beats a benchmark:
  - White's Reality Check (2000);
  - Hansen's SPA (2005);
  - the Romano-Wolf stepdown (2005);
  - the Model Confidence Set (Hansen, Lunde & Nason 2011).
  All are graded A. `lab/inference` already has SPA and MCS.
- **Winner's curse:** the chosen variant's estimate is biased upward (Andrews, Kitagawa & McCloskey 2024, QJE; B).
- **Protocol:**
  - At most one champion and three challengers.
  - Each challenger is one economic change, not a grid.
  - Test the challenger-minus-champion daily difference, in non-overlapping 3-day blocks, at the same frozen looks.
  - A challenger replaces the champion only if all four hold:
    1. it crosses its boundary;
    2. Romano-Wolf rejects at family level;
    3. the difference is positive at 2x and 3x costs;
    4. the deflated Sharpe, with N = `registry.program_trials()`, is at least 0.95.
- **Bandits** (Garivier & Moulines 2011; Besbes, Gur & Zeevi 2019; B) are for allocating capital, not for inference.
  Stationary bandits lock onto the early leader. Do not use them to choose between paper books.

## 4. Shrinking what paper shows
- **Skeptical prior.** With a prior SD of 1.0 on annual Sharpe, the posterior mean is
  w x observed, where w = 1 / (1 + 365 / T):
  - after 90 days, w = 0.20, so an observed Sharpe of 2.0 shrinks to 0.4;
  - after 365 days, w = 0.50, so 2.0 shrinks to 1.0.
  The prior is the owner's call.
- **Published decay** (McLean & Pontiff 2016, JF; B): predictors lose 26% of their return out of sample and 58%
  after publication.
- **Incubation bias** (Evans 2010, JF; B): the best of privately run variants looks better before launch than after.
- **Multiple-testing hurdles:**
  - t > 3.0 for a new factor (Harvey, Liu & Zhu 2016, RFS; B);
  - about 3.4-3.8 with full multiple-testing control (Chordia, Goyal & Saretto 2020; B, numbers from a summary).
  - The lab already reads every result against `program_trials()` with the deflated Sharpe.

## 5. Making paper honest
- **Fills.** Passive fills count only when price trades through the limit. Add a latency haircut. Report costs at
  1x/2x/3x, as the lab does.
- **Gap between paper and live.** No peer-reviewed measurement exists (D only). Assume paper overstates results.
- **Labels.** Label every null with the power it had, for example "inconclusive, 19% power at Sharpe 1.5". Never
  retune after a null.

## 6. What this lab does with it
| Edge | Paper lane | Decision | Power note |
|---|---|---|---|
| Carry | R220, Binance + MEXC | 90 on-time days: total > 0, t >= 2, go_real on invested days; INCONCLUSIVE under 20 invested days | Smooth returns (holdout Sharpe 2.5), but still about 8 months for 50% power |
| Flow A, X2 | R215, R218 (90-day screen); R221 (182/365-day test) | as above | 19% at Sharpe 1.5, 73% at Sharpe 3, by day 365 |
| top_vs_crowd crypto (B) | R221 | as above | same |

**Not verified:** the Harvey-Liu haircut formula; the minimum track record length formula (Bailey & López de Prado
2012), quoted from memory by the subagent; the Chordia et al. figures. The group-sequential constants were
re-derived here with `scipy` for R221's own looks.

## 7. Loss at the proposed size (engineering, 2026-11-05)

New linear-futures paper consumers can construct `PaperSession` with an
[`EntryLossPolicy`](../lab/paper_entry_risk.py). This additional veto joins the
existing forecast/cost/error threshold, capital reservation and gross exposure
controls. It does not change historical lanes or their frozen risk engine.

The policy names separate (venue, settlement asset) loss limits and the exact
required scenario identifiers **before any session activity**. Its declaration
is durable: reopening cannot omit it, raise its budget or replace its required
scenario identifiers. Economic stress assumptions still need their frozen lane
protocol; an identifier alone does not authenticate a scenario's severity.
Every proposal supplies `EntryScenario` inputs for its exact instrument, signed
base quantity and settlement asset. Missing scenarios, quantities, entry/exit
prices, either fee, funding or additional loss remain unknown and block entry.
There is no probability or win-rate multiplier.

For each scenario and requested cost tier `k` in {1, 2, 3}:

```
price_pnl   = q * (exit_price - entry_price)
terminal_pnl = price_pnl + funding
               - k * (entry_fee + exit_fee) - extra_loss
cash_debits  = max(0, -price_pnl) + k * (entry_fee + exit_fee)
               + max(0, -funding) + extra_loss
loss_budget_used = max(0, -terminal_pnl, cash_debits)
```

Requiring at least the cash debits avoids financing fees with a future favorable
move or funding receipt. Every scenario must fit the registered incremental loss
budget and stay strictly inside the native account's remaining loss/drawdown
room, and cannot exhaust current cash, liquidation NAV or available capital.
Withdrawals reduce current solvency room even when flow-adjusted trading PnL is
unchanged. Native high-water marks are those recorded in the risk journal; a deposit
or restart does not reset them. The proposed reserve also covers the highest
declared entry price and the larger of intent costs or scenario fee/funding/extra
cash debits. Price loss is separately constrained by the loss budget; this
entry-notional reservation does not model the intratrade margin path.

This mode requires the target settlement account to be flat. Concurrent positions
need a joint portfolio stress design; independent single-entry scenarios cannot
establish their combined downside. Other venues/assets cannot fund the account.
Admission remains an intent, not a fill. Received fills and fees outside declared
entry bounds are still booked, with a durable reconciliation issue blocking new
entries. Partial-fill fees consume the full-size fee allowance cumulatively;
later fee resolutions are checked against the same allowance.

Run the finite invented example, with no market reads or orders:

```sh
.venv/bin/python scripts/demo_paper_entry_risk.py --demo
```

The example's three sizes share a declared 50% price-gap stress and are checked
at all three fee tiers. The largest passing **evaluated** size is not a maximum
safe size; no interpolation or extrapolation of liquidity is supported. Scenario
selection and supplied forecasts/fees are not authenticated here. Full price
paths, exchange margin/liquidation, actual fills, predictive evidence and the
owner's capital decision still require their own gates. Legacy sessions without
this policy explicitly report `loss_at_size_required: false` on new proposals;
they do not acquire a new sizing claim.

Receipt timing is separately tightened: both economic execution and first-seen
receipt must follow the persisted decision `asof`, using its anchored UTC time.
A stale observation clock within the receive-age allowance cannot move that
decision backward. Predecision receipts remain accounted exposure and cannot
discharge the later intent, including after restart.
