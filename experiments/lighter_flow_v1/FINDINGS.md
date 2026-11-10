# R433 lighter_flow_v1: NULL as a trade. Lighter's informed taker accounts stay informed out of sample, but a follower 1.3 s late keeps less than the touch costs

**Registry:** R433, 24 trials (program total 9,784,709).

**Run:** once, 2026-11-10 02:54 UTC, by the frozen runner `scripts/run_lighter_flow.py`.
- PREREG `e7c75548…`. The 4 inputs and all 3,482 data files in `data_manifest.json` matched.
- Outputs are in `results/`: `summary.json`, `cells.csv`, `trades_primary.csv`. Log: `run.log`.
- Freeze commit e5b6fe2, before the run.

FINDINGS was written by the orchestrator from the lane agent's text. The harness does not let subagents write it.

## Verdict
**NULL.** The primary cell follows the 10 best-scored accounts.
- **How the accounts were scored:** train days 10-28 and 10-29, by a shrunk mean signed markout at 60 s, from
  101 eligible accounts.
- **How the cell trades:** it enters 1.3 s after each account's trade, at the touch, on a Standard account with 0
  fee. It exits 60 s later at the opposite touch.
- **The result:** on the test days (10-30, 11-02..11-06), 570 trades earned +0.95 bp gross against a 1.49 bp
  round-trip touch cost.

| Cost | Mean net per trade | 95% interval (1x, 39 hour blocks) |
|---|---|---|
| 1x touch | −0.54 bp | −1.51 to +0.65 bp |
| 2x | −2.02 bp | |
| 3x | −3.51 bp | |
| Premium account (1x + 2 × 2.8 bp) | −6.14 bp | |

- **Placebo:** 200 random sets of 10 eligible accounts averaged −1.02 bp. The informed set beat 95% of them, at the
  edge of the bar but with a negative mean and an interval that includes zero.
- **By market (net at 1x):**
  - WTI −0.10 bp (435 trades);
  - BRENTOIL +0.16 bp (71);
  - NATGAS −4.32 bp (64).
- **By day (net at 1x):** every test day is negative, from −0.11 bp on 10-30 (330 trades) to −3.26 bp on 11-06 (34).
- **Thin touch:** 77% of primary fills met a touch under $1,000, so even these prices flatter the trade.
- **Concentration:** four accounts made 85% of the primary signals (30%, 27%, 15% and 14%).

## Part A: the information is real and it persists
Train scores against test-day markouts, per account (accounts eligible in train with ≥ 10 test trades):

| Horizon | Accounts | Spearman | Permutation p | Informed − rest, test markout |
|---|---|---|---|---|
| 10 s | 89 | 0.51 | < 0.0005 | +3.36 bp (2.73 to 4.11) |
| 60 s | 89 | 0.42 | < 0.0005 | +3.29 bp (2.14 to 4.51) |
| 300 s | 83 | 0.16 | 0.15 | +0.96 bp (−1.30 to +3.02) |

- **Accounts that were informed on 10-28 and 10-29 stayed informed on later days.** This is M441's first
  out-of-sample answer: on Lighter, the account id predicts the markout of its next trades.
- **The informed accounts' edge is measured from their own fill price, and most of it arrives within the first
  second.** That part is not available to a follower.

## The frontier: the edge decays before a slow follower arrives
Follow the informed set, mean gross and net at 1x (bp):

| Hold | Delay 0.3 s (counterfactual) | Delay 1.3 s (primary) | Delay 5.3 s |
|---|---|---|---|
| 10 s | +0.85 / −0.69 | +0.28 / −1.24 | +0.22 / −1.30 |
| 60 s | +1.54 / +0.09 | +0.95 / −0.54 | +0.93 / −0.53 |
| 300 s | +0.78 / −0.72 | −0.11 / −1.66 | −0.35 / −1.93 |

- **Only one cell is above zero.** At a 0.3 s delay (Lighter's taker delay alone, with zero reaction time) and a
  60 s hold, the net is +0.09 bp, with an interval of −0.84 to +1.24. It is inside noise, and no order from this
  container can arrive that fast.
- **Fading the worst-scored accounts does not pay.** Their trades are not reliably wrong: the gross is about 0 at 10 s
  and 60 s, and the net about −2.0 bp. At 300 s, +0.04 bp at best, on 115 trades.
- **Following everyone (control):** gross +0.05, +0.20 and +0.58 bp at 10, 60 and 300 s; net about −1.4 bp. The
  selection adds about +0.75 bp of gross at 60 s, which is not enough.
- **Break-even:** the follower needs a round trip under about 0.95 bp at 60 s. The recorded touch costs 1.49 bp.

## What this means
- **Flow information exists on Lighter's public tape, and it lasts across days.** The informed accounts impose about
  +3.3 bp of adverse selection a trade on whoever fills them, at 10-60 s.
- **A taker cannot follow them profitably from here.** Most of their gain comes in the first second, and the touch
  costs more than what is left. A Premium account's fee makes it far worse.
- **The open use is the maker's side (M474).** A maker cannot see who will hit it before the fill. But after an
  informed account trades, it could skew or pull its quotes for the next 10-60 s, avoiding the next fills from the
  same accounts. That needs a quote replay with a queue model, and a new id.
- **No path to execution yet:** Lighter refused the native runner's jurisdiction (R428), and the owner's eligibility
  is unknown.

## Read against the program
- **Program total:** 9,784,709 trials.
- **The verdict:** a NULL, and no multiplicity correction could make it a pass. The primary mean is negative.
- **Part A:** permutation p < 0.0005 at two horizons out of 24 trials. It survives the lane's own count, but it is a
  fact about information, not a strategy.
- **Prior lanes:** it agrees with R348 (Lighter's book closes a Binance-led gap within a second) and with R431 (the
  gross edge decays within milliseconds to a second). Speed is the constraint again, not the idea.

## Limits
- **Sample:**
  - Six test days, and 10-30 holds 58% of the primary trades. The November days have only 1.4-3.2 recorded hours
    each.
  - One regime, late October and early November 2026.
- **Fills:** touch only. There is no depth, queue, rejection or impact, and 77% of primary fills met a touch under
  $1,000. All of these flatter the trade.
- **Clock:** lookups use Lighter's own clock. The local clock is offset by about ±1.5 s and is used only for session
  tags and filters.
- **Concentration:** four accounts dominate the signals. One entity may run several accounts, so the 89 accounts in
  Part A are not 89 independent bets.
- **Account tiers:** fees differ by account tier and were read only as public fields. The follower is assumed to be a
  Standard account.
- **Not tested:**
  - a maker using the signal (M474);
  - lead-lag of informed Lighter aggression into other venues (M443);
  - liquidation flow.
