# FINDINGS: capsizing_v1 (R496, M545). Entry-spread sizing does NOT beat fixed size at measured cost

**Verdict: NULL by the frozen rule.** PREREG `07b313b4187a` verified before and after; 6 inputs matched.
Discovery 1,445 trades (entry < 2024), **validation 1,711 trades read once**. Gate 0: a split of R277's
already-published archive, not a fresh sample. No reserved read, no orders.

Reproduce: `python scripts/record_kucoin_costs.py` then `python scripts/run_capsizing.py`.

## The frozen rule and its result

Size each trade by `n* = (g_hat/(a(1+β)))^(1/β)` where `g_hat = k · spread_in_ann · hold/365`, `k`
fitted on discovery only (**k = 0.6791**, median hold 30 d), charged the **worse** of the trade's own
two measured venue curves, clipped to the fit range, shown depth and a $10k cap. Baseline: fixed $10k.

| cost | rule total | baseline total | difference | 95% CI of mean diff | verdict |
|---|---|---|---|---|---|
| **1x** | $209,575 | $332,655 | **−$123,081** | **[−107.14, −41.92]** | **fails** |
| 2x | $159,515 | $103,795 | +$55,719 | [−3.13, +62.94] | positive, CI touches 0 |
| 3x | $109,455 | −$125,064 | +$234,519 | [+100.57, +167.75] | positive |

The gate required **1x difference > 0 with a CI excluding zero, and 2x > 0**. At 1x the difference is
negative with the CI entirely below zero — the rule is **worse**, decisively. **NULL.**

## Why, and what is actually true

The rule sizes down: median chosen notional **$3,493** vs the $10,000 baseline (844 trades bound by
depth, 826 at an interior optimum, 41 with a non-positive forecast). Sizing down saves cost but
forfeits gross. At **measured 1x cost the gross is worth more than the cost saved**, so shrinking
loses. At 2x and 3x the arithmetic flips and shrinking wins — at 3x the fixed-$10k baseline loses
$125k while the rule still makes $109k.

So the honest statement is narrow and useful: **capacity sizing is cost insurance, not alpha.** It
protects against a cost regime worse than today's measurement, and it costs return in today's regime.
It is not an edge, and this lane does not claim one.

The signal itself is real but weak: on discovery, Spearman(entry spread, realised gross) = **+0.161**
(p 6.9e-10), top quintile gross 0.0298 vs bottom 0.0094. A ρ of 0.16 is not enough to beat a fixed size
through a sizing map. That is the quantitative reason the idea fails, and it is worth recording.

## Measured cost curves (new: KuCoin and dYdX)

Every R277 trade touches KuCoin or dYdX, which R495 did not cover — the venue mismatch an audit
flagged. Measured here, 428 book rows over 364 coins, 222 errors (delisted or unlisted symbols):

| venue | contracts | half-spread | $1k | $5k | $10k | β | median depth |
|---|---|---|---|---|---|---|---|
| KuCoin | 353 | 11.36 bp | 22.34 | 57.63 | **169.15 bp** | **0.828** | $5,748 |
| dYdX | 75 | 75.64 bp | 83.12 | 101.03 | **122.36 bp** | **0.160** | **$600** |

KuCoin's β = 0.83 is far steeper than square-root impact; dYdX's 0.16 is far flatter, because its
median shown depth is only **$600** — the book is already exhausted at $1k, so cost barely grows after
that. Together with R495 (Binance 0.404, Gate 0.567) the four venues span **0.16 to 0.83**, which is a
stronger argument against a single global cost multiple than anything measured here before.

## Prior art — the novelty claim is withdrawn

The closed form is **standard**: Almgren (2003), *Applied Mathematical Finance*,
DOI `10.1080/135048602100056`, abstract read: impact is "a power law function of the trading rate,
with an arbitrary positive exponent... includes... the square root law". The earlier claim that this
was "a thing nobody has done" was wrong and is corrected in `research/CAPACITY_EQUATION_20261115.md`.
What this lane tested was never the formula — it was whether an **ex-ante** forecast is good enough
to exploit it. It is not.

## Limits

- **One snapshot per venue.** R224 needed 102 for a stable cost surface; β will move.
- 222 of 728 symbol-venue probes errored (delisted coins, dYdX naming). Those trades fall back to a
  venue median curve, which is a real approximation.
- Gate 0 on a split of an already-read archive. This cannot confirm anything out of sample in the
  program's sense, and it does not try to.
- The forecast is one linear map from the entry spread. A better forecast is a new lane, not an edit.
- Tests sizing **within** R277's frozen entry rule; it is not a new entry signal.

## What a result earns

**NULL.** M545 is tested. The 2x/3x reversal is reported, not traded on: choosing the cost multiple
after seeing which one wins would be selection. If someone wants the cost-insurance version, it is a
new lane with a pre-declared cost regime, not a re-reading of this one.
