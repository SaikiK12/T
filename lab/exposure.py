"""Options positioning: the Black-76 greeks of each listed option and the dealer exposures traders quote from them,
gamma (GEX), delta (DEX), vanna (VEX) and charm (CEX), the gamma profile over a grid of spot prices, the zero-gamma
("flip") level, and the call and put walls (docs/AUCTION_AND_FLOW.md).

Black-76 on the forward F with r = 0, as crypto venues quote mark IV: d1 = (ln(F/K) + s^2 T / 2) / (s sqrt(T)),
d2 = d1 - s sqrt(T), phi the normal density, N the normal cdf, T in years, s the implied vol as a decimal.
    delta   call N(d1), put N(d1) - 1
    gamma   phi(d1) / (F s sqrt(T))               the same for calls and puts
    vanna   d delta / d s = -phi(d1) d2 / s       the same for calls and puts
    charm   d delta / d t as time passes = phi(d1) d2 / (2 T), per year; the same for calls and puts

Exposures are in USD from the side dealers are assumed to hold, one sign per option type (+1 long, -1 short):
    GEX = sign gamma OI F^2 0.01    change in dealers' delta notional for a 1% move in F
    DEX = sign delta OI F           dealers' delta notional
    VEX = sign vanna OI F 0.01      change in delta notional when implied vol rises one point
    CEX = sign charm OI F / 365     change in delta notional over one day with nothing else moving
OI is in coins (Deribit and Binance options are one coin per contract). The default signs, dealers long calls and
short puts, are the equity convention (customers sell calls against stock and buy puts for protection). Open interest
does not say who is long, and crypto customers often buy calls, so the call sign may be the other way: a lane tests
the sign instead of assuming it. scripts/record_deribit_chain.py keeps its own gex() for the recorder's digest.
"""
import math

import numpy as np
import pandas as pd
from scipy.special import ndtr

YEAR_MS = 365.25 * 86_400_000
SQRT2PI = math.sqrt(2 * math.pi)


def greeks(f, k, t, s, call):
    """Delta, gamma, vanna and charm (per year) of each option; arrays broadcast. Rows with t <= 0, s <= 0 or a
    missing input are NaN."""
    f, k, t, s, call = np.broadcast_arrays(*(np.atleast_1d(np.asarray(x, float)) for x in (f, k, t, s, call)))
    call = call.astype(bool)
    with np.errstate(invalid="ignore", divide="ignore"):
        bad = ~((t > 0) & (s > 0) & (f > 0) & (k > 0))
        t, s = np.where(bad, np.nan, t), np.where(bad, np.nan, s)
        v = s * np.sqrt(t)
        d1 = (np.log(f / k) + 0.5 * v * v) / v
        d2 = d1 - v
        pdf = np.exp(-0.5 * d1 * d1) / SQRT2PI
        nd1 = ndtr(d1)
        return pd.DataFrame({
            "delta": np.where(call, nd1, nd1 - 1),
            "gamma": pdf / (f * v),
            "vanna": -pdf * d2 / s,
            "charm": pdf * d2 / (2 * t),
        })


def exposures(chain, sign_call=1.0, sign_put=-1.0, f=None):
    """GEX, DEX, VEX and CEX in USD for each row of `chain` (columns f, strike, t in years, iv as a decimal, oi in
    coins, call as bool), from the dealers' side under the given signs. `f` overrides the forward for every row (used
    for the gamma profile at a hypothetical price). Returns the chain with the greeks and the four exposures added."""
    x = chain.reset_index(drop=True)
    fx = x.f.to_numpy(float) if f is None else np.full(len(x), float(f))
    g = greeks(fx, x.strike, x.t, x.iv, x.call)
    sign = np.where(x.call.to_numpy(bool), sign_call, sign_put)
    oi = np.nan_to_num(x.oi.to_numpy(float))
    out = pd.concat([x, g], axis=1)
    out["gex"] = sign * g.gamma * oi * fx * fx * 0.01
    out["dex"] = sign * g.delta * oi * fx
    out["vex"] = sign * g.vanna * oi * fx * 0.01
    out["cex"] = sign * g.charm * oi * fx / 365
    return out


def by_strike(ex):
    """Exposures summed per strike, calls and puts apart and net: columns call_gex, put_gex, net_gex and the same for
    dex, vex and cex."""
    cols = ["gex", "dex", "vex", "cex"]
    side = np.where(ex.call, "call", "put")
    t = ex.assign(side=side).pivot_table(index="strike", columns="side", values=cols, aggfunc="sum", fill_value=0.0)
    out = pd.DataFrame(index=t.index)
    for c in cols:
        call = t[(c, "call")] if (c, "call") in t else 0.0
        put = t[(c, "put")] if (c, "put") in t else 0.0
        out[f"call_{c}"], out[f"put_{c}"], out[f"net_{c}"] = call, put, call + put
    return out


def gamma_profile(chain, grid, sign_call=1.0, sign_put=-1.0):
    """Net GEX of the whole chain if the forward were at each price in `grid`, implied vols and times held fixed
    (sticky strike). Returns a Series indexed by the grid price."""
    return pd.Series([np.nansum(exposures(chain, sign_call, sign_put, f=p).gex) for p in grid],
                     index=np.asarray(grid, float))


def zero_gamma(profile, spot):
    """The price where the gamma profile changes sign closest to `spot`, by linear interpolation between grid points;
    NaN when it never changes sign."""
    p, g = np.asarray(profile.index, float), np.asarray(profile, float)
    i = np.flatnonzero(np.sign(g[:-1]) * np.sign(g[1:]) < 0)
    if not len(i):
        return np.nan
    roots = p[i] - g[i] * (p[i + 1] - p[i]) / (g[i + 1] - g[i])
    return float(roots[np.argmin(np.abs(roots - spot))])


def walls(strikes):
    """Call wall and put wall: the strikes with the largest call and put gamma notional (absolute, sign-free), from
    by_strike() output. Traders read them as resistance and support."""
    return float(strikes.call_gex.abs().idxmax()), float(strikes.put_gex.abs().idxmax())


def taker_positions(flow, blocks=True):
    """Takers' net position in each option at the end of each hour it traded: the running sum of taker buys minus
    taker sells since its first trade in `flow` (scripts/fetch_deribit_trades.py's hourly rows). The makers hold the
    opposite; reading the makers as dealers is an assumption (M308). `blocks=False` leaves block trades out."""
    f = flow.sort_values(["instrument", "t"]).copy()
    net = f.buy - f.sell
    if not blocks:
        net = net - (f.block_buy - f.block_sell)
    f["taker_pos"] = net.groupby(f.instrument).cumsum().values
    return f


def positions_at(pos, t):
    """Each option's last taker position at or before time t, for options not yet expired at t (expiry_ms > t)."""
    x = pos[(pos.t <= t) & (pos.expiry_ms > t)]
    return x.groupby("instrument", sort=False).tail(1)
