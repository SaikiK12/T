# Reflection, 2026-11-25 (cycle 11): does the Kraken 1.5x rule survive the book's short legs?

## How I approached the last subject, and what I would change
- **Self-review 3 found the stake's leverage rule was argued for the wrong account.**
  - The rule, "Kraken lane at 1.5x if maintenance is 5%", came from down-wicks on long-alt accounts.
  - R508's sign-agnostic book is short Kraken alts in 120 of 238 trades, and that direction earned 63% of the
    funding.
- **What I would change:** a risk rule is a statement about an account's actual positions. Before reusing one, look
  at what the account holds. In the November reasoning I described the account from the story (long the floorless
  venue), not from the trades.

## 0. What the lab already knows
- **`stake_dhl_20261123.md`:**
  - distance to liquidation with every leg against = (1/L − mm)/(1 + mm): 59% at L 1.5 and mm 5%;
  - Kraken's mark low on 2025-10-10 averaged −43.8% over 126 coins.
- **`stake_ticket.py`'s `worst_move`** covers mixed accounts, but only for a uniform move with every leg against.
  It does not use the venue's real path.
- **R525's engine** replays the kraken + hyperliquid book (`scripts/check_exec_gap.py` shows how). Kraken's charts
  API serves hourly mark candles (open, high, low, close).

## 1. The economic question
For the Kraken account of the sign-agnostic book (about 20 thin coins, long some and short others), what is the
worst loss within a day on Kraken's own mark? Does 1.5x keep a safe distance from liquidation?

## 2. The mechanism
- **Kraken liquidates on its mark:** the spot index plus a 30-second EMA of the premium, capped at 1%.
- **A short leg loses on an up-spike:** a squeeze, a listing pump or news. A long leg loses on a down-spike.
- **In a mixed account a market-wide move partly cancels.** The risk is single-coin spikes against a leg, plus the
  account's net exposure in a correlated move.
- **Kraken's multi-collateral account margins all positions together,** so the account is the unit. The Hyperliquid
  account is separate and must survive alone.

## 3. The cheapest decisive observation, with the prediction first
- **Data:**
  - the R525 engine's kraken + hyperliquid trades (seen, 2025-12 .. 2026-09);
  - Kraken hourly mark candles for every coin the book held, from the public charts API.
- **The measure.** Each day, the Kraken account holds equal notional in its open legs: long +1, short −1, weight
  1/n.
  - Path within the day: hourly marks against the day's open, summed with the weights.
  - The worst hour gives the account's worst intraday loss, as a fraction of notional.
  - An upper bound, each leg's own worst hourly high or low (not simultaneous), is reported too.
- **Prediction:** the worst intraday account loss is under 15% of notional. That is far inside 1.5x's 59% distance,
  because of diversification and the long/short mix. The worst single-coin up-spike may exceed +100%, but at about
  1/20 weight it costs under 10%.
- **What would refute it:** a worst account loss above about 30% of notional, or an upper bound near 59%. Either
  would put 1.5x in doubt and make the stake rule 1x for the Kraken account.

## 4. The observation (`scripts/check_kraken_shortleg.py`; R525's kraken+hyperliquid book, seen)
- **The account:** 206 Kraken legs (101 long, 105 short) over 2025-12-01 .. 2026-10-01; 304 days with an open account,
  about 20 legs a day, 46% short on average. Marks were fetched for all 52 coins.

| Worst intraday loss of the Kraken account, % of notional | Median day | 95% | 99% | Worst |
|---|---|---|---|---|
| hourly path (legs simultaneous) | 0.6% | 2.5% | 3.6% | **4.4%** |
| upper bound (each leg's own worst hour, not simultaneous) | 3.7% | 6.7% | 9.5% | **12.6%** |

- **The largest single-leg moves are up-spikes on short legs, as the self-review feared:** ACE +88% (2025-12-15),
  BOME +83%, BIO +69%, SUPER +59%, NOT +59% within a day. At about 1/20 of the account each, they cost 3-4.4%.
- **The worst account days were long-heavy** (20-25% short, June 2026), not squeeze days.
- **The prediction held:** under 15% of notional, against a liquidation distance at 1.5x of 59% (maintenance 5%) or
  33% (maintenance 25%).

## 5. A stress the window does not contain (arithmetic, not data)
- **The window starts after 2025-10-10.** On that day Kraken's mark fell 43.8% on average across 126 coins.
- **A mixed account's loss in such a crash is its net long share times the move.**
  - The most long-heavy composition seen was 80% long / 20% short: (0.8 − 0.2) × 44% ≈ 26% of notional.
  - That is inside 1.5x's 59% at 5% maintenance. At 25% maintenance it is thin (33%).
- **So the rule stands as written:** 1.5x on Kraken only at 5% maintenance (the EEA schedule), otherwise 1x.

## 6. What it changes
- **The leverage rule is confirmed, not changed.** The sign-agnostic book is safer per unit of leverage than the
  long-alt account the rule was argued for, because a market-wide move partly cancels inside the account.
- **The account's risk is set by its net long/short imbalance,** not by its gross. A check for the stake ticket:
  report the Kraken account's net long share each day. If the net exceeds about 60% of gross, treat the account as a
  long-alt account and use the stricter long-alt distance.
- **Not measured:**
  - the Hyperliquid account, which holds the opposite legs and is symmetric in kind (its marks use a different
    rule);
  - the hours of an actual crash on a long-heavy day, which the window lacks;
  - auto-deleveraging.

## Correction (room critic, 2026-11-25)
- The daily table resets each leg to the day's open. Legs are held a median of about 19 days, and liquidation
  depends on the cumulative move since entry unless margin is topped up.
- The critic's cumulative-from-entry figure is **8.7% of notional at worst**, still far inside 59% at 1.5x (5%
  maintenance). The rule stands.
- The stake's daily check should track the cumulative move per leg since its entry, not only the day's move.

