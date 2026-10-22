"""Stress-day report (M324): what a book earned on the market's worst days, beside its mean.

A mean-reverting or liquidity-providing book is short volatility. It earns a little on ordinary days and gives it back
when volatility spikes and liquidity leaves (the owner's reel DbIlAc1g0LM, docs/REELS_TRANSCRIPT.md). A mean over all
days hides that, so every FINDINGS can carry this report next to its 1x/2x/3x table.

It reads only the daily PnL series it is given and, optionally, a market-volatility series. It decides nothing and
adds no trials.
"""
import numpy as np
import pandas as pd

# Named crypto stress episodes (UTC days, inclusive). Days before 2021 are left out: 2020 is reserved (docs/GATES.md).
EPISODES = {
    "2021-05-19 crash": ("2021-05-19", "2021-05-19"),
    "2021-12-04 flash crash": ("2021-12-04", "2021-12-04"),
    "LUNA": ("2022-05-09", "2022-05-12"),
    "Celsius / 3AC": ("2022-06-13", "2022-06-14"),
    "FTX": ("2022-11-08", "2022-11-10"),
    "USDC depeg": ("2023-03-10", "2023-03-11"),
    "2024-08-05 carry unwind": ("2024-08-05", "2024-08-05"),
    "2025-10-10 liquidations": ("2025-10-10", "2025-10-11"),
}


def _days(x):
    """A DatetimeIndex of UTC-naive days."""
    idx = pd.to_datetime(pd.Index(x))
    if idx.tz is not None:
        idx = idx.tz_convert("UTC").tz_localize(None)
    return idx.normalize()


def market_vol(panel, top=50):
    """Per day: the equal-weight mean absolute daily return of the top `top` perps by 30-day volume. `panel` is the
    long daily panel (`day`, `ret` = close over the previous close - 1, `rank_qvol30`)."""
    p = panel.loc[(panel.rank_qvol30 <= top) & panel.ret.notna(), ["day", "ret"]]
    v = p.ret.abs().groupby(_days(p.day)).mean()
    return v.sort_index()


def report(pnl, vol=None, q=0.99, episodes=EPISODES):
    """`pnl`: daily PnL (any unit, e.g. bp) indexed by day. Days with no position should be absent or 0.

    Returns a dict:
    - `days`, `mean`, `sum` over all days;
    - `episodes`: per named episode with at least one day in `pnl`, its days, sum and mean, and `in_mean_days` (the
      sum in units of the book's mean day: -40 means the episode gave back 40 average days);
    - with `vol`, `vol_top`: the round((1 - q) x n) days of highest market volatility among the n days `pnl` covers
      (at least one): their count, mean and sum, their share of the total, and the other days' mean;
    - `worst`: the 5 worst days with their PnL.
    """
    s = pd.Series(np.asarray(pnl, float), index=_days(pnl.index)).dropna().sort_index()
    out = {"days": int(len(s)), "mean": float(s.mean()) if len(s) else float("nan"), "sum": float(s.sum())}
    unit = abs(out["mean"]) if len(s) and out["mean"] != 0 else float("nan")
    ep = {}
    for name, (a, b) in episodes.items():
        x = s.loc[pd.Timestamp(a):pd.Timestamp(b)]
        if len(x):
            ep[name] = {"days": int(len(x)), "sum": float(x.sum()), "mean": float(x.mean()),
                        "in_mean_days": float(x.sum() / unit) if np.isfinite(unit) else None}
    out["episodes"] = ep
    if vol is not None and len(s):
        v = pd.Series(np.asarray(vol, float), index=_days(vol.index)).reindex(s.index)
        ok = v.notna()
        if ok.sum() >= 10:
            k = max(1, int(round((1 - q) * ok.sum())))
            top = v[ok].nlargest(k).index                  # ties at the cut are broken by order, not all taken
            hi = s.index.isin(top)
            cut = float(v[top].min())
            out["vol_top"] = {"q": q, "cut": cut, "days": int(hi.sum()), "mean": float(s[hi].mean()),
                              "sum": float(s[hi].sum()),
                              "share_of_total": float(s[hi].sum() / s.sum()) if s.sum() != 0 else None,
                              "other_mean": float(s[ok.to_numpy() & ~hi].mean())}
    w = s.nsmallest(5)
    out["worst"] = [(d.strftime("%Y-%m-%d"), float(x)) for d, x in w.items()]
    return out


def table(rep, unit="bp"):
    """A short markdown table of `report`'s episodes and volatility tail, for a FINDINGS file."""
    rows = [f"| Days | Value ({unit}) | In mean days |", "|---|---|---|",
            f"| All {rep['days']} days, mean | {rep['mean']:+.1f} | 1 |"]
    for name, e in rep["episodes"].items():
        m = "" if e["in_mean_days"] is None else f"{e['in_mean_days']:+.0f}"
        rows.append(f"| {name} ({e['days']} d), sum | {e['sum']:+.1f} | {m} |")
    if "vol_top" in rep:
        t = rep["vol_top"]
        rows.append(f"| Top {100 * (1 - t['q']):.0f}% volatility days ({t['days']} d), mean | {t['mean']:+.1f} | |")
        rows.append(f"| Other days, mean | {t['other_mean']:+.1f} | |")
    return "\n".join(rows)
