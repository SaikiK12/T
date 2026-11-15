# Capacity-optimal sizing: an equation the lab has not had (2026-11-15)

`lab/capacity.py` · 12 tests in `tests/test_capacity.py` · derived from R495's measured books.

## The gap, stated precisely

Every lane in this program asks the same question: **is mean gross bigger than cost?** — at a *fixed*
size, with cost scaled 1x/2x/3x. M006 tested square-root impact as *cost realism*. No lane has treated
**size itself as the decision variable**. That is a free parameter nobody optimised, and it is the one
that R495's measurement showed matters most: Gate costs 17 bp at $1k and 66 bp at $10k on the same
contract.

## The equation

Cost per side, fitted from the measured book walk:

```
cost_bp(n) = a · n^β
```

Dollar profit per trade at notional `n`, with `g` the gross fraction:

```
P(n) = n·g − a·n^(1+β)
P'(n) = g − a(1+β)·n^β = 0
```

```
        ⎛      g       ⎞^(1/β)
n* =    ⎜ ───────────  ⎟
        ⎝  a · (1+β)   ⎠
```

**The invariant that makes it useful.** Substitute `n*` back:

```
cost(n*) / g  =  1 / (1+β)
```

At the optimum you always spend exactly `1/(1+β)` of gross on cost — **a venue constant, independent
of the signal**. Verified numerically to 1e-12 across gross from 0.1% to 20%, and the derivative
vanishes at `n*` with `P(n*) > P(n*/2)` and `P(n*) > P(2n*)`.

## Fitted on real books (R495, 1,400 rows)

| venue | a | β | R² | median shown depth | invariant 1/(1+β) |
|---|---|---|---|---|---|
| Binance | 0.4388 | **0.4036** | 0.9991 | $50,810 | **0.712** |
| Gate | 0.3309 | **0.5670** | 0.9832 | $7,846 | **0.638** |

The exponents **bracket square-root impact theory (β=0.5)**: Binance is flatter, Gate steeper. That is
a measured, venue-specific fact this repo did not have, and it is why a single global cost multiple
was always the wrong model.

## What it says on real trades

R277's 3,156 executed carry trades, median gross **0.44%**:

| venue | n* | binding constraint | net/trade | break-even notional |
|---|---|---|---|---|
| Binance | $10,000 | fit range (wants more) | +$26.16 | $91,936 |
| Gate | **$2,543** | **interior optimum** | +$4.07 | **$5,615** |

**On Gate, $10k is past break-even ($5,615) — the same trade that profits at $2.5k loses at $10k.**
That is the concrete, new, actionable statement: the venue's capacity, not the signal, decides.

## Honest limits — including one application I rejected

- **The unconstrained optimum is often untradable.** At 2.45% gross the formula asks for $2.7M on
  Binance. The shown book cannot fill it. So `constrained_notional` clips to the fit range (1k–10k),
  the shown depth, and an optional capital cap, and **names which one bound**. On Gate the median
  shown depth is $7,846 and only 41% of contracts show $10k, so depth binds constantly.
- **The aggregate gain is small.** Sizing each trade individually gave $591k vs $579k at fixed $10k —
  **1.02x, not a new edge.** Most trades have high gross and want *more* size, so they hit the depth
  cap. The equation's value is per-trade risk control and knowing when to say no, not a profit multiplier.
- **I rejected one tempting application.** Using each trade's *realised* gross to skip the 37.9% of
  trades that "cannot pay cost" appeared to save $147k. That is **look-ahead**: realised gross is not
  known at entry. It is exactly the post-hoc trap rejected elsewhere today, so it is not claimed. A
  legitimate version needs an *ex-ante* gross forecast, which is its own frozen lane.
- **One snapshot, current listings, shown book only.** β is fitted on three sizes from one pass;
  R224 needed 102 snapshots for a stable cost surface. The exponent will move.
- **The gross distribution is another venue's.** R277's trades are gate+kucoin / binance+kucoin; the
  cost curves here are Binance and Gate. The pairing is indicative, not a re-score of R277. A proper
  test joins each trade's own two venues and is the obvious next lane.

## Why this is a real contribution rather than another indicator

It changes the question from *"is there an edge?"* to *"at what size does this edge exist, and which
constraint stops it?"* — and it answers with a closed form, a venue-specific measurable exponent, and
an invariant that holds regardless of the signal. It also explains the program's central pattern:
fifty nulls were mostly **size-infeasible**, not signal-free.

Nothing here is a verified trading edge. It is a sizing equation with measured inputs, tested
calculus, and explicitly stated limits. Gate 0; no reserved read; no orders.
