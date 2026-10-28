"""R356 settlehop_exit_v1: R354's settlement hops closed minutes after the settlement, frozen in
experiments/settlehop_exit_v1/PREREG.md.

R354 held each hop (Binance against Lighter, entered one hour before Binance's settlement at T) to T + 1 h on hourly
bars. Its hedged price rose about 25 bp into T and gave about 45 bp back in the hour after, and Lighter's settlement
at T + 1 h cost about half of its two hours of funding. This runner takes the same 87 hops, with R354's entry,
direction, funding and costs, and closes both legs at the 1-minute close of T + k for k = 1, 2, 5, 15 and 30 minutes.
T + 60 is the control: rebuilt from the minute bars it must give R354's hourly price, and the close at T its price0.

A leg's price at T + j is the close of its last traded minute bar (close > 0, volume > 0) opening at or before
T + j - 1 min; the entry is the close of the last traded minute bar opening in [T - 2 h, T - 61 min], the minute form
of R354's close of the hourly bar ending at T - 1 h. A hop closed before T + 1 h keeps the funding settled in
(T - 1 h, T] (R354's fund0: Binance's lump at T and Lighter's settlement at T) and neither venue's settlement at
T + 1 h. Costs are R354's, per hop.

usage: python scripts/run_settlehop_exit.py              the frozen run (verifies the PREREG, its inputs, and every
                                                         minute file against docs/provenance/settlehop_1m.json)
       python scripts/run_settlehop_exit.py --plumbing   counts only: windows, entries, untraded exit minutes, and the
                                                         hops whose rebuilt T + 60 and T exits match R354's
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import run_settlehop as base  # noqa: E402  R353's frozen runner: describe, decide, book, net, frozen_inputs
import settlehop_rule as rule  # noqa: E402  R355's frozen rule: CR1 t, trimmed and leave-two-coins-out means

LANE = ROOT / "experiments" / "settlehop_exit_v1"
REGISTRY = "R356"
SRC = ROOT / "experiments" / "settlehop_pred_v1" / "results"     # R354's frozen outputs
BOOK = "binance+lighter th0.5%"                                  # R354's primary book
SYMBOLS = base.LANE / "symbols.csv"                               # R353's table: Binance key -> Lighter symbol
DATA = ROOT / "data" / "settlehop_1m"
PROV = ROOT / "docs" / "provenance" / "settlehop_1m.json"
H, DAY, MIN = base.H, base.DAY, 60_000
KS = (1, 2, 5, 15, 30)                   # exits after T, in minutes: the trials
CONTROL = 60                             # R354's exit
PRIMARY = 5
TRIALS = len(KS)
T_GAIN = 2.0                             # the primary's paired gain over the control: CR1 t at least this
BONF_T = round(float(norm.ppf(1 - 0.05 / TRIALS)), 2)   # one-sided 5% over the five exits: 2.33
PARITY = 1e-6                            # |rebuilt - R354| on price (T + 60) and price0 (T), every hop
PATH = tuple(range(-60, 61))             # minutes of the reported path; -60 is the entry
log = base.log


# ------------------------------------------------------------------------------------------------------------ inputs
def check_data(prov=PROV, folder=DATA, root=ROOT):
    """The minute folder holds exactly the files the provenance lists, each with its sha256. Returns the count."""
    listed = {r["path"]: r["sha256"] for r in json.loads(Path(prov).read_text())["file_hashes"]}
    on_disk = {p.relative_to(root).as_posix() for p in Path(folder).rglob("*") if p.is_file()}
    if on_disk != set(listed):
        raise prereg.PreregError(f"{folder}: {len(on_disk ^ set(listed))} files differ from the provenance list")
    for rel, want in listed.items():
        if prereg.sha256_file(root / rel) != want:
            raise prereg.PreregError(f"{rel}: sha256 differs from the provenance")
    return len(listed)


def day_ms(days):
    """'YYYY-MM-DD' strings to UTC day starts in ms."""
    t = pd.to_datetime(pd.Series(list(days)), utc=True)
    return ((t - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(milliseconds=1)).to_numpy(np.int64)


def load_hops(src=SRC, symbols=SYMBOLS):
    """R354's primary hops in its order, each with its coin's Lighter symbol, and the book's calendar (day starts)."""
    h = pd.read_csv(src / "hops.csv.gz")
    h = h[h.book == BOOK].reset_index(drop=True)
    lt = {r["key"]: r["lighter"] for r in base.read_symbols(symbols)}
    h["lighter"] = h.coin.map(lt)
    dl = pd.read_csv(src / "daily.csv.gz")
    return h, day_ms(dl.day[dl.book == BOOK])


def minute_bars(venue, sym, T, folder=DATA):
    """One leg's 1-minute bars opening in [T - 2 h, T + 1 h): open time, close, traded (close > 0 and volume > 0)."""
    if venue == "binance":
        days = sorted({pd.Timestamp(x, unit="ms").strftime("%Y-%m-%d") for x in (T - 2 * H, T + H - MIN)})
        k = pd.concat([pd.read_parquet(folder / "binance" / sym / f"{d}.parquet", columns=["t", "close", "volume"])
                       for d in days], ignore_index=True)
    else:
        k = pd.read_parquet(folder / "lighter" / sym / f"{T}.parquet", columns=["t", "close", "volume"])
    k = k[(k.t >= T - 2 * H) & (k.t < T + H)].drop_duplicates("t").sort_values("t", ignore_index=True)
    c, v = k.close.to_numpy(float), k.volume.to_numpy(float)
    return {"t": k.t.to_numpy(np.int64), "close": c, "traded": np.isfinite(c) & (c > 0) & np.isfinite(v) & (v > 0)}


# ------------------------------------------------------------------------------------------------------------- rules
def last_traded(bars, t_open_max, t_open_min):
    """Index of the last traded bar opening in [t_open_min, t_open_max], or -1."""
    t, tr = bars["t"], bars["traded"]
    i = int(np.searchsorted(t, t_open_max, side="right")) - 1
    while i >= 0 and t[i] >= t_open_min:
        if tr[i]:
            return i
        i -= 1
    return -1


def entries(sb, hb, T):
    """Each leg's entry bar: the last traded minute opening in [T - 2 h, T - 61 min], or -1."""
    return last_traded(sb, T - H - MIN, T - 2 * H), last_traded(hb, T - H - MIN, T - 2 * H)


def hop_path(sb, hb, T, d, minutes):
    """One hop at each minute T + j, j in minutes: {j: (hedged price, Binance part, Lighter part, Binance stale,
    Lighter stale)}. The hedged price is d times Lighter's return minus Binance's, from the entry to the close of each
    leg's last traded bar opening at or before T + j - 1 min; a leg is stale when that bar is not the one opening at
    T + j - 1 min. None when a leg has no traded entry bar."""
    i_s, i_h = entries(sb, hb, T)
    if i_s < 0 or i_h < 0:
        return None
    out = {}
    for j in minutes:
        tj = T + (j - 1) * MIN
        x_s, x_h = last_traded(sb, tj, sb["t"][i_s]), last_traded(hb, tj, hb["t"][i_h])
        r_s = sb["close"][x_s] / sb["close"][i_s] - 1
        r_h = hb["close"][x_h] / hb["close"][i_h] - 1
        out[j] = (d * (r_h - r_s), -d * r_s, d * r_h, bool(sb["t"][x_s] != tj), bool(hb["t"][x_h] != tj))
    return out


def rebuild(h, folder=DATA, minutes=PATH):
    """Every hop at each minute (PATH holds 0 and CONTROL): a frame indexed like h, with columns (field, minute) for
    field in price, bin, lit, stale_s, stale_h."""
    rows = []
    for r in h.itertuples(index=False):
        T = int(r.T)
        p = hop_path(minute_bars("binance", r.coin, T, folder), minute_bars("lighter", r.lighter, T, folder), T,
                     int(r.d), minutes)
        if p is None:
            raise prereg.PreregError(f"{r.coin} {T}: no traded entry minute on a leg")
        rows.append({(f, j): v[n] for j, v in p.items() for n, f in enumerate(("price", "bin", "lit", "stale_s",
                                                                                 "stale_h"))})
    return pd.DataFrame(rows, index=h.index)


def parity(h, px):
    """Hops whose rebuilt T + 60 price and T price match R354's price and price0 within PARITY."""
    ok60 = (px[("price", CONTROL)] - h.price).abs() <= PARITY
    ok0 = (px[("price", 0)] - h.price0).abs() <= PARITY
    return int(ok60.sum()), int(ok0.sum())


def at_exit(h, px, k):
    """The hops closed at T + k: price at T + k, the funding they keep, and the exit's stale flag (either leg)."""
    if k == CONTROL:
        return h.assign(stale=px[("stale_s", k)] | px[("stale_h", k)])
    return h.assign(price=px[("price", k)], fund=h.fund0, stale=px[("stale_s", k)] | px[("stale_h", k)])


def gain(hk, h):
    """Each hop's net gain over the control, the same at every cost multiple: price and funding only."""
    return (hk.price + hk.fund) - (h.price + h.fund)


def describe(hk, h, days, k):
    """R353's description of the exit's book plus the per-hop statistics GATES asks for and the paired gain."""
    d = base.describe(hk, days, "binance", f"exit T+{k}m")
    n1 = base.net(hk, 1)
    mu, t = rule.decide_stats(n1.to_numpy(), hk["T"].to_numpy())
    d.update({"k": k, "fund_kept_bp": float(hk.fund.mean() * 1e4), "hop_cr1_t": t,
              "trim10_net1_bp": rule.trimmed(n1.to_numpy()) * 1e4,
              "l2co_net1_bp": rule.leave_two_coins_out(n1.to_numpy(), hk.coin.tolist()) * 1e4})
    if k != CONTROL:
        g = gain(hk, h)
        gm, gt = rule.decide_stats(g.to_numpy(), hk["T"].to_numpy())
        d.update({"gain_bp": gm * 1e4, "gain_t": gt, "gain_hit": float((g > 0).mean()),
                  "gain_price_bp": float((hk.price - h.price).mean() * 1e4),
                  "gain_fund_bp": float((hk.fund - h.fund).mean() * 1e4)})
    return d


def decide(d):
    """R354's four checks on the primary exit's daily book, and its paired gain over T + 60 at a CR1 t of at least
    T_GAIN."""
    checks = dict(base.decide(d)["checks"])
    checks["gain_t"] = bool(np.isfinite(d.get("gain_t", np.nan)) and d["gain_t"] >= T_GAIN)
    return {"checks": checks, "verdict": "PASS" if all(checks.values()) else "NULL"}


# -------------------------------------------------------------------------------------------------------------- main
def plumbing(h, folder=DATA):
    """Counts only: hops, windows, entries, exits on an untraded minute at each decided minute, and parity with R354.
    No return at T + 1 .. T + 30 is computed."""
    n = {"hops": len(h), "coins": h.coin.nunique(), "times": h["T"].nunique(), "entries": 0}
    stale = {k: [0, 0] for k in (0,) + KS + (CONTROL,)}
    for r in h.itertuples(index=False):
        T = int(r.T)
        sb, hb = minute_bars("binance", r.coin, T, folder), minute_bars("lighter", r.lighter, T, folder)
        i_s, i_h = entries(sb, hb, T)
        if i_s < 0 or i_h < 0:
            continue
        n["entries"] += 1
        for k in stale:
            tk = T + (k - 1) * MIN
            stale[k][0] += int(sb["t"][last_traded(sb, tk, sb["t"][i_s])] != tk)
            stale[k][1] += int(hb["t"][last_traded(hb, tk, hb["t"][i_h])] != tk)
    log(f"{n}; exits on an untraded minute [Binance, Lighter] by k: {stale}")
    p60, p0 = parity(h, rebuild(h, folder, (0, CONTROL)))
    log(f"rebuilt within {PARITY:g} of R354: price (T + 60) {p60}/{len(h)}, price0 (T) {p0}/{len(h)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true")
    a = ap.parse_args()
    h, days = load_hops()
    if a.plumbing:
        plumbing(h)
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = base.frozen_inputs(LANE / "PREREG.md")
    n_files = check_data()
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match; {n_files} minute files match their provenance")
    if h.lighter.isna().any() or len(h) != 87:
        raise prereg.PreregError("R354's primary book is not the 87 hops with a Lighter symbol each")
    px = rebuild(h)
    p60, p0 = parity(h, px)
    log(f"parity with R354: price {p60}/{len(h)}, price0 {p0}/{len(h)}")
    if p60 != len(h) or p0 != len(h):
        raise prereg.PreregError("the minute rebuild does not reproduce R354's hourly exits")
    res = LANE / "results"
    res.mkdir(exist_ok=True)
    books, per_hop, daily = [], [h[["coin", "T", "d", "e", "cost_s_bp", "cost_h_bp", "price", "fund", "price0",
                                    "fund0"]].copy()], []
    for k in KS + (CONTROL,):
        hk = at_exit(h, px, k)
        d = describe(hk, h, days, k)
        books.append(d)
        per_hop.append(pd.DataFrame({f"price_{k}": hk.price, f"stale_{k}": hk.stale, f"net1_{k}": base.net(hk, 1)}))
        daily.append(pd.DataFrame({"k": k, "day": pd.to_datetime(days, unit="ms").date,
                                   **{f"net{m}_bp": base.book(hk, days, m) for m in base.MULTS}}))
        log(f"T+{k}m: net1 {d['net1_bp']:+.1f} bp a hop, {d['day1_bp']:.2f} bp/day t {d['t1']:.2f}"
            + (f", gain {d['gain_bp']:+.1f} bp t {d['gain_t']:.2f}" if k != CONTROL else ""))
    bk = pd.DataFrame(books)
    dec = decide(next(b for b in books if b["k"] == PRIMARY))
    fam = {"bonferroni_t": BONF_T, "gain_t_at_or_above": int((bk.gain_t >= BONF_T).sum()),
           "gain_t2": int((bk.gain_t >= T_GAIN).sum()),
           "four_checks": int(sum(base.decide(r)["verdict"] == "PASS" for r in books if r["k"] != CONTROL)),
           "exits": TRIALS}
    path = pd.DataFrame({"minute": PATH,
                         "hedged_bp": [px[("price", j)].mean() * 1e4 for j in PATH],
                         "hedged_median_bp": [px[("price", j)].median() * 1e4 for j in PATH],
                         "binance_bp": [px[("bin", j)].mean() * 1e4 for j in PATH],
                         "lighter_bp": [px[("lit", j)].mean() * 1e4 for j in PATH],
                         "stale_binance": [int(px[("stale_s", j)].sum()) for j in PATH],
                         "stale_lighter": [int(px[("stale_h", j)].sum()) for j in PATH]})
    bk.to_csv(res / "books.csv", index=False, float_format="%.6g")
    pd.concat(per_hop, axis=1).to_csv(res / "hops.csv.gz", index=False, float_format="%.8g")
    pd.concat(daily, ignore_index=True).to_csv(res / "daily.csv.gz", index=False, float_format="%.6g")
    path.to_csv(res / "path.csv", index=False, float_format="%.6g")
    if check_data() != n_files:
        raise prereg.PreregError("the minute files changed during the run")
    summary = {"lane": LANE.name, "registry": REGISTRY, "trials": TRIALS, "primary_k": PRIMARY,
               "decision": dec, "verdict": dec["verdict"], "family": fam, "parity": [p60, p0],
               "costs_bp": base.COST_BP, "inputs": shas, "minute_files": n_files}
    (res / "summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    log(f"verdict {dec['verdict']} {dec['checks']}; family {fam}")


if __name__ == "__main__":
    main()
