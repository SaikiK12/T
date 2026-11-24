"""How much of the owner's investable money a design-gap stake should take, by Thorp's growth-optimal (Kelly) rule
with the jump that matters here: a venue failing and keeping its deposit. A calculation on stated assumptions; it reads
no lane result and decides nothing by itself.

Thorp (2006, "The Kelly criterion in blackjack, sports betting, and the stock market", section 7):
- growth of a fraction f in a drift m, volatility s, cash r: g(f) = r + f (m - r) - s^2 f^2 / 2, so f* = (m - r) / s^2;
- assume the true edge is below the estimate (at m_true = m_est / 2, full Kelly grows at zero);
- prices jump, so real leverage stays well under f*; half Kelly keeps 3/4 of the growth.

Here, with a stake fraction phi of wealth in a book at leverage L (net drift L m, volatility L s), and each venue v
failing with intensity lam a year and losing a share d_v of the stake (times 1 - recovery):
    g(phi) = r + phi (L m - r) - phi^2 L^2 s^2 / 2 + sum_v lam ln(1 - phi d_v (1 - rec)).
At phi -> 0 the stake adds growth only if L m - r > lam (1 - rec) sum_v d_v = lam (1 - rec): the break-even failure
rate is lam* = (L m - r) / (1 - rec), whatever the split across venues. The split changes the optimum's size.

usage: python scripts/stake_kelly.py   (prints the table)
"""
import math
import sys

import numpy as np

R_CASH = 0.0413                 # the lab's 13-week bill hurdle (%/yr as a fraction)
BASES = {  # in-sample nets at 1x (R525's daily nets): drift and volatility a year
    "12 pairs": {"m": 0.0777, "s": 0.0777 / 5.5},           # 2021-01..2026-09, Sharpe 5.5
    "3 forward pairs": {"m": 0.0667, "s": 0.0199},          # R509 + R520 + R524 pairs, 304 common days, Sharpe 3.4
}
# deposit shares from the dry-run ticket at leverage 2 (2026-11-23): Hyperliquid holds two lanes' short legs
SHARES = {"hyperliquid": 0.377, "binance": 0.178, "bitfinex": 0.156, "kraken": 0.146, "deribit": 0.144}


def growth(phi, L, m, s, lam, shares, rec=0.0, r=R_CASH):
    """Log growth a year of wealth with a fraction phi staked; -inf if a failure could take everything.
    lam: failures a year, one number for every venue or {venue: rate}."""
    jump = 0.0
    for v, d in shares.items():
        x = 1.0 - phi * d * (1.0 - rec)
        if x <= 0:
            return -math.inf
        jump += (lam.get(v, 0.0) if isinstance(lam, dict) else lam) * math.log(x)
    return r + phi * (L * m - r) - (phi * L * s) ** 2 / 2 + jump


def best(L, m, s, lam, shares, rec=0.0, r=R_CASH, grid=2001):
    """(phi*, g(phi*)) on [0, 1]: no borrowing outside the book."""
    phis = np.linspace(0.0, 1.0, grid)
    g = np.array([growth(p, L, m, s, lam, shares, rec, r) for p in phis])
    i = int(np.argmax(g))
    return float(phis[i]), float(g[i])


# Venue closure rates a year, from the exchange-closure hazard models (Mukherjee & Moore 2022; Moore, Christin &
# Szurdi 2018): a median exchange (16 coins) closes about 10% a year (75% survive 3 years, median life about 7);
# the Cox hazard ratio is 0.995 per coin traded, 1.39 for crypto-only (no fiat) and 1.52 for allowing US customers.
# Coins traded here are rough counts on 2026-11-24; Hyperliquid (an on-chain venue) is outside the models and is given
# the crypto-only rate of a 200-coin venue. Recovery given closure: about 47% where known (6 of 16 closures paid
# nothing, 5 in full, 5 in part).
BASE_HAZARD, HR_COIN, HR_CRYPTO_ONLY, HR_US = 0.10, 0.995, 1.39, 1.52
VENUES = {"kraken": (350, False, True), "binance": (400, False, False), "bitfinex": (200, False, False),
          "deribit": (100, True, False), "hyperliquid": (200, True, False)}    # (coins, crypto only, US customers)
RECOVERY = 0.47


def venue_hazard(coins, crypto_only, us, base=BASE_HAZARD, median_coins=16):
    return base * HR_COIN ** (coins - median_coins) * (HR_CRYPTO_ONLY if crypto_only else 1.0) * (HR_US if us else 1.0)


LAM_VENUE = {v: venue_hazard(*x) for v, x in VENUES.items()}
# The models know neither age, owner nor regulation. Deribit has been Coinbase's since 2025-08-14 (Coinbase's release),
# so the adjusted set gives it Kraken's rate. Hyperliquid's on-chain risks (contracts, validators, oracle) are not
# modelled anywhere here.
LAM_ADJUSTED = {**LAM_VENUE, "deribit": LAM_VENUE["kraken"]}


def break_even_lam(L, m, rec=0.0, r=R_CASH):
    """The venue failure rate a year at which a small stake stops adding growth (negative: never worth it)."""
    return (L * m - r) / (1.0 - rec)


def table(base="3 forward pairs", edges=(1.0, 0.5, 0.25), leverages=(1.0, 2.0), lams=(0.01, 0.03, 0.10),
          recs=(0.0, 0.5)):
    rows = []
    for k in edges:
        m, s = BASES[base]["m"] * k, BASES[base]["s"]
        for L in leverages:
            for rec in recs:
                for lam in lams:
                    phi, g = best(L, m, s, lam, SHARES, rec)
                    rows.append({"edge": k, "L": L, "rec": rec, "lam": lam, "phi_star": phi, "half_kelly": phi / 2,
                                 "growth_gain_pct": 100 * (g - R_CASH),
                                 "half_gain_pct": 100 * (growth(phi / 2, L, m, s, lam, SHARES, rec) - R_CASH),
                                 "break_even_lam_pct": 100 * break_even_lam(L, m, rec)})
    return rows


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="3 forward pairs", choices=sorted(BASES))
    ap.add_argument("--m", type=float, help="one scenario: drift a year at 1x (e.g. a forward estimate, 0.04)")
    ap.add_argument("--s", type=float, help="its volatility a year at 1x")
    ap.add_argument("--L", type=float, default=2.0)
    ap.add_argument("--lam", default="0.03", help="failures a year per venue, or 'models' / 'adjusted' for the per-venue rates")
    ap.add_argument("--rec", type=float, default=0.0, help="share of a failed venue's deposit recovered")
    a = ap.parse_args(argv)
    lam = {"models": LAM_VENUE, "adjusted": LAM_ADJUSTED}.get(a.lam) or float(a.lam)
    if a.m is not None:
        s = a.s if a.s is not None else BASES[a.base]["s"]
        phi, g = best(a.L, a.m, s, lam, SHARES, a.rec)
        out = {"phi_star": phi, "half_kelly": phi / 2, "gain_over_cash_pct_at_half": 100 * (
            growth(phi / 2, a.L, a.m, s, lam, SHARES, a.rec) - R_CASH),
            "break_even_lam_pct": 100 * break_even_lam(a.L, a.m, a.rec),
            "expected_loss_pct_a_year_at_phi_1": 100 * sum((lam.get(v, 0) if isinstance(lam, dict) else lam) * d
                                                          for v, d in SHARES.items()) * (1 - a.rec)}
        print(out)
        return out
    rows = table(a.base)
    print(f"Base: {a.base} (m {100 * BASES[a.base]['m']:.2f}%/yr, s {100 * BASES[a.base]['s']:.2f}%/yr at 1x); "
          f"cash {100 * R_CASH:.2f}%/yr")
    print("| Edge (share of in-sample) | Leverage | Recovery | Venue failures a year | phi* (share of wealth) | "
          "Half Kelly | Gain over cash at phi* | at half Kelly | Break-even failure rate |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['edge']:.2f} | {r['L']:g} | {100 * r['rec']:.0f}% | {100 * r['lam']:g}% | {r['phi_star']:.2f} | "
              f"{r['half_kelly']:.2f} | {r['growth_gain_pct']:+.2f}%/yr | {r['half_gain_pct']:+.2f}%/yr | "
              f"{r['break_even_lam_pct']:.1f}% |")
    return rows


if __name__ == "__main__":
    main(sys.argv[1:])
