"""R362 settleticks_v1: the seconds after a deep Binance funding settlement, from Binance's tick archive, frozen in
experiments/settleticks_v1/PREREG.md.

R356 closed R354's hops at minute closes after T and found the capture crowd's whole giveback inside the first minute.
This runner reads Binance's aggregated trades from T - 10 min to T + 15 min around each of R354's 221 θ 0.3%
settlements and asks two things:

- the path: how fast the price moves after T, second by second, against the side that received the lump;
- the scalp: a taker who trades against the receiving side once Binance's settlement is surely done, at T + 15 s
  (Binance: "There is a 15-second deviation in the actual funding fee transaction time"), and closes at T + 30, 60,
  120 or 300 s, at R354's 8.5 bp a side.

The scalp's position is d (R354's sign): short the coin when longs received the lump (d = -1), long when shorts did.
A taker's fill is the price of the first trade on its side at or after its order time: a sell fills at the first
seller-initiated trade (buyer_maker), a buy at the first buyer-initiated one. An entry with no trade on its side
before the exit time is no trade. An exit with no trade on its side within EXIT_WAIT takes the first trade of either
side within OTHER_WAIT, else the last trade before its time; both are flagged.

usage: python scripts/run_settleticks.py              the frozen run (verifies the PREREG, its inputs, and every tick
                                                      file against docs/provenance/settle_ticks.json)
       python scripts/run_settleticks.py --plumbing   counts only: hops, windows, settlement clusters, entries and
                                                      exits found and flagged; no price change is computed
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
import run_settlehop as base  # noqa: E402  R353's frozen runner: frozen_inputs, log
import settlehop_rule as rule  # noqa: E402  R355's frozen rule: CR1 t, trimmed and leave-two-coins-out means

LANE = ROOT / "experiments" / "settleticks_v1"
REGISTRY = "R362"
SRC = ROOT / "experiments" / "settlehop_pred_v1" / "results"     # R354's frozen outputs
BOOK = "binance+lighter th0.3%"                                  # R354's θ 0.3% Binance book: the events
SEEN = "binance+lighter th0.5%"                                  # R356's 87 hops, whose minute path was read
DATA = ROOT / "data" / "settle_ticks"
PROV = ROOT / "docs" / "provenance" / "settle_ticks.json"
S = 1000                                 # ms in a second
ENTRY = 15                               # seconds after T: past Binance's 15-second funding deviation
EXITS = (30, 60, 120, 300)               # seconds after T: the decided trials
PRIMARY = 60
EARLY = (1, 2, 5)                        # entries inside the deviation, reported only, each closed at T + PRIMARY
TRIALS = len(EXITS) + len(EARLY)         # every scalp computed counts
COST_BP = 8.5                            # R354's Binance API cost a side
MULTS = (1, 2, 3)
T_MIN = 2.0                              # the primary's CR1 t at 1x
BONF_T = round(float(norm.ppf(1 - 0.05 / len(EXITS))), 2)   # one-sided 5% over the four decided exits: 2.24
EXIT_WAIT = 5 * S                        # an exit takes a trade on its side within this, ...
OTHER_WAIT = 60 * S                      # ... else a trade of either side within this, else the last trade before
PATH = (-600, -300, -120, -60, -30, -15, -10, -5, -2, -1, 0, 0.25, 0.5, 1, 2, 3, 5, 10, 15, 20, 30, 45, 60, 90, 120,
        180, 240, 300, 600, 899)         # seconds of the reported path
FLOW = ((-600, -60), (-60, -10), (-10, 0), (0, 1), (1, 2), (2, 5), (5, 15), (15, 30), (30, 60), (60, 120),
        (120, 300), (300, 900))          # second ranges of the reported taker flow; the first is its base
log = base.log


# ------------------------------------------------------------------------------------------------------------ inputs
def check_data(prov=PROV, folder=DATA, root=ROOT):
    """The tick folder holds exactly the files the provenance lists, each with its sha256. Returns the count."""
    listed = {r["path"]: r["sha256"] for r in json.loads(Path(prov).read_text())["file_hashes"]}
    on_disk = {p.relative_to(root).as_posix() for p in Path(folder).rglob("*") if p.is_file()}
    if on_disk != set(listed):
        raise prereg.PreregError(f"{folder}: {len(on_disk ^ set(listed))} files differ from the provenance list")
    for rel, want in listed.items():
        if prereg.sha256_file(root / rel) != want:
            raise prereg.PreregError(f"{rel}: sha256 differs from the provenance")
    return len(listed)


def load_hops(src=SRC):
    """R354's θ 0.3% Binance hops in T order, with seen = True for the 87 in R356's book."""
    h = pd.read_csv(src / "hops.csv.gz")
    seen = {(c, int(t)) for c, t in zip(h.coin[h.book == SEEN], h["T"][h.book == SEEN])}
    h = h[h.book == BOOK].sort_values(["T", "coin"], ignore_index=True)
    h["T"] = h["T"].astype("int64")
    h["seen"] = [(c, int(t)) in seen for c, t in zip(h.coin, h["T"])]
    return h[["coin", "T", "d", "e", "f_hat", "interval_h", "seen"]]


def ticks(sym, T, folder=DATA):
    """One window's trades in time order: t (ms), price, buyer_maker (the seller took liquidity)."""
    w = pd.read_parquet(folder / "binance" / sym / f"{T}.parquet", columns=["t", "price", "qty", "buyer_maker",
                                                                           "agg_id"])
    w = w.sort_values(["t", "agg_id"], ignore_index=True)
    return {"t": w.t.to_numpy(np.int64), "price": w.price.to_numpy(float), "qty": w.qty.to_numpy(float),
            "bm": w.buyer_maker.to_numpy(bool)}


# ------------------------------------------------------------------------------------------------------------- rules
def last_before(tk, t):
    """Index of the last trade strictly before t, or -1."""
    return int(np.searchsorted(tk["t"], t, side="left")) - 1


def last_at(tk, t):
    """Index of the last trade at or before t, or -1."""
    return int(np.searchsorted(tk["t"], t, side="right")) - 1


def first_side(tk, t0, t1, sell):
    """Index of the first trade in [t0, t1) whose taker sold (sell=True) or bought, or -1."""
    i, j = np.searchsorted(tk["t"], t0, side="left"), np.searchsorted(tk["t"], t1, side="left")
    hit = np.flatnonzero(tk["bm"][i:j] == sell)
    return int(i + hit[0]) if len(hit) else -1


def taker_fill(tk, t, sell, wait=EXIT_WAIT, other=OTHER_WAIT):
    """An order that must fill at t: (index, flag). flag 0: a trade on its side within wait; 1: the first trade of
    either side within other; 2: the last trade before t; (-1, 3) when the window has no trade at all."""
    i = first_side(tk, t, t + wait, sell)
    if i >= 0:
        return i, 0
    j = int(np.searchsorted(tk["t"], t, side="left"))
    if j < len(tk["t"]) and tk["t"][j] < t + other:
        return j, 1
    k = last_before(tk, t)
    return (k, 2) if k >= 0 else (-1, 3)


def scalp(tk, T, d, entry_s, exit_s):
    """One scalp: position d (sell first when d = -1) from T + entry_s to T + exit_s. Returns (gross return, entry
    index, exit index, exit flag), or None when no trade on the entry's side comes before the exit time."""
    t_in, t_out = T + int(round(entry_s * S)), T + int(round(exit_s * S))
    sell_first = d < 0
    i = first_side(tk, t_in, t_out, sell_first)
    if i < 0:
        return None
    j, flag = taker_fill(tk, t_out, not sell_first)
    return d * (tk["price"][j] / tk["price"][i] - 1), i, j, flag


def path(tk, T, d, seconds=PATH):
    """The price at each T + s (last trade at or before it) against the receiving side, from the last trade before T:
    {s: d * (P(T + s) / P(T-) - 1)}, NaN where no trade precedes. None when no trade precedes T."""
    r = last_before(tk, T)
    if r < 0:
        return None
    p0 = tk["price"][r]
    out = {}
    for s in seconds:
        k = last_at(tk, T + int(round(s * S)))
        out[s] = d * (tk["price"][k] / p0 - 1) if k >= 0 else np.nan
    return out


def flow(tk, T, d, ranges=FLOW):
    """Taker quote volume in the scalp's direction (sold minus bought when d = -1), per second of each range, in units
    of the first range's mean quote volume a second. NaN when the base is 0."""
    q = tk["price"] * tk["qty"]
    sign = np.where(tk["bm"], -1.0, 1.0) * d         # +1 for a trade whose taker traded with the scalp
    rel = (tk["t"] - T) / S
    base_a, base_b = ranges[0]
    m = (rel >= base_a) & (rel < base_b)
    base = q[m].sum() / (base_b - base_a)
    out = {}
    for a, b in ranges[1:]:
        m = (rel >= a) & (rel < b)
        out[(a, b)] = (q[m] * sign[m]).sum() / (b - a) / base if base > 0 else np.nan
    return out


def nets(gross, m):
    return gross - 2 * m * COST_BP / 1e4


def calendar_days(T):
    """Days from the first hop's UTC day to the last's, both included."""
    day = np.asarray(T, np.int64) // base.DAY
    return int(day.max() - day.min() + 1)


def halves(T):
    """True for the hops in the first half of the calendar (two equal runs of days from the first hop's day to the
    last's)."""
    day = np.asarray(T, np.int64) // base.DAY
    return day < day.min() + calendar_days(T) / 2


def describe(x, name, days):
    """One scalp's statistics over the hops it traded (x: gross, flag, coin, T, seen), with bp a day over the
    calendar of every hop (days)."""
    g = x.gross.to_numpy(float)
    out = {"scalp": name, "hops": len(x), "coins": int(x.coin.nunique()), "times": int(x["T"].nunique()),
           "gross_bp": g.mean() * 1e4, "gross_median_bp": float(np.median(g)) * 1e4,
           "exit_other_side": int((x.flag == 1).sum()), "exit_stale": int((x.flag == 2).sum())}
    for m in MULTS:
        n = nets(g, m)
        mu, t = rule.decide_stats(n, x["T"].to_numpy())
        out.update({f"net{m}_bp": mu * 1e4, f"t{m}": t, f"hit{m}": float((n > 0).mean())})
    n1 = nets(g, 1)
    first = halves(x["T"].to_numpy())
    best = x.assign(n1=n1).groupby("coin").n1.sum().idxmax()
    unseen = ~x.seen.to_numpy(bool)
    out.update({"half1_net1_bp": n1[first].mean() * 1e4, "half2_net1_bp": n1[~first].mean() * 1e4,
                "best_coin": best, "wo_best_net1_bp": n1[x.coin.to_numpy() != best].mean() * 1e4,
                "unseen_hops": int(unseen.sum()), "unseen_net1_bp": n1[unseen].mean() * 1e4,
                "unseen_t1": rule.decide_stats(n1[unseen], x["T"].to_numpy()[unseen])[1],
                "seen_net1_bp": n1[~unseen].mean() * 1e4,
                "trim10_net1_bp": rule.trimmed(n1) * 1e4,
                "l2co_net1_bp": rule.leave_two_coins_out(n1, x.coin.tolist()) * 1e4,
                "day1_bp": n1.sum() * 1e4 / days,
                "sd1_bp": float(n1.std(ddof=1)) * 1e4 if len(n1) > 1 else np.nan})
    return out


def decide(d):
    """The primary scalp: PASS when all five checks hold."""
    checks = {"t1": bool(np.isfinite(d["t1"]) and d["t1"] >= T_MIN),
              "net2_positive": bool(d["net2_bp"] > 0),
              "both_halves": bool(d["half1_net1_bp"] > 0 and d["half2_net1_bp"] > 0),
              "without_best_coin": bool(d["wo_best_net1_bp"] > 0),
              "unseen_positive": bool(d["unseen_net1_bp"] > 0)}
    return {"checks": checks, "verdict": "PASS" if all(checks.values()) else "NULL"}


# -------------------------------------------------------------------------------------------------------------- main
def run_all(h, folder=DATA):
    """Every hop's scalps, path and flow: (scalps frame, path frame, flow frame, counts)."""
    rows, paths, flows, n = [], [], [], {"windows": 0, "no_trade_before_T": 0}
    for r in h.itertuples(index=False):
        T, d = int(r.T), int(r.d)
        tk = ticks(r.coin, T, folder)
        n["windows"] += 1
        p = path(tk, T, d)
        if p is None:
            n["no_trade_before_T"] += 1
            continue
        paths.append({"coin": r.coin, "T": T, "seen": r.seen, **{f"p{s:g}": v for s, v in p.items()}})
        flows.append({"coin": r.coin, "T": T, **{f"f{a}_{b}": v for (a, b), v in flow(tk, T, d).items()}})
        for name, (a, b) in scalp_set().items():
            x = scalp(tk, T, d, a, b)
            if x is not None:
                g, i, j, flag = x
                rows.append({"scalp": name, "coin": r.coin, "T": T, "d": d, "e": r.e, "seen": r.seen, "gross": g,
                             "entry_ms": int(tk["t"][i]) - T, "exit_ms": int(tk["t"][j]) - T, "flag": flag})
    return pd.DataFrame(rows), pd.DataFrame(paths), pd.DataFrame(flows), n


def scalp_set():
    """Every scalp computed: {name: (entry s, exit s)}; the decided ones first."""
    out = {f"in{ENTRY}_out{x}": (ENTRY, x) for x in EXITS}
    out.update({f"in{e}_out{PRIMARY}": (e, PRIMARY) for e in EARLY})
    return out


def plumbing(h, folder=DATA):
    """Counts only: hops, windows, settlement clusters, and per scalp the entries found and the exits flagged. No price
    change is computed."""
    log(f"{len(h)} hops on {h.coin.nunique()} coins at {h['T'].nunique()} settlement times; "
        f"{int(h.seen.sum())} in R356's book, {int((~h.seen).sum())} outside it")
    cnt = {k: [0, 0, 0] for k in scalp_set()}
    miss = 0
    for r in h.itertuples(index=False):
        T, d = int(r.T), int(r.d)
        p = folder / "binance" / r.coin / f"{T}.parquet"
        if not p.exists():
            miss += 1
            continue
        tk = ticks(r.coin, T, folder)
        for name, (a, b) in scalp_set().items():
            i = first_side(tk, T + a * S, T + b * S, d < 0)
            if i < 0:
                continue
            cnt[name][0] += 1
            _, flag = taker_fill(tk, T + b * S, not d < 0)
            if flag in (1, 2):
                cnt[name][flag] += 1
    log(f"missing windows {miss}; per scalp [entered, exit on the other side, exit stale]: {cnt}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true")
    a = ap.parse_args()
    h = load_hops()
    if a.plumbing:
        plumbing(h)
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = base.frozen_inputs(LANE / "PREREG.md")
    n_files = check_data()
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match; {n_files} tick files match their provenance")
    if len(h) != 221 or int(h.seen.sum()) != 87:
        raise prereg.PreregError("R354's θ 0.3% Binance book is not the 221 hops holding R356's 87")
    sc, pa, fl, n = run_all(h)
    res = LANE / "results"
    res.mkdir(exist_ok=True)
    books = []
    for name in scalp_set():
        x = sc[sc.scalp == name]
        d = describe(x, name, calendar_days(h["T"]))
        books.append(d)
        log(f"{name}: {d['hops']} hops, gross {d['gross_bp']:+.1f} bp, net1 {d['net1_bp']:+.1f} (t {d['t1']:.2f}), "
            f"net2 {d['net2_bp']:+.1f}, net3 {d['net3_bp']:+.1f}; unseen {d['unseen_net1_bp']:+.1f}")
    bk = pd.DataFrame(books)
    prim = next(b for b in books if b["scalp"] == f"in{ENTRY}_out{PRIMARY}")
    dec = decide(prim)
    decided = bk[bk.scalp.isin([f"in{ENTRY}_out{x}" for x in EXITS])]
    fam = {"bonferroni_t": BONF_T, "t1_at_or_above": int((decided.t1 >= BONF_T).sum()),
           "t1_at_or_above_2": int((decided.t1 >= T_MIN).sum()), "decided": len(EXITS), "trials": TRIALS}
    cols = [f"p{s:g}" for s in PATH]
    path_out = pd.DataFrame({"second": PATH,
                             "mean_bp": [pa[c].mean() * 1e4 for c in cols],
                             "median_bp": [pa[c].median() * 1e4 for c in cols],
                             "mean_unseen_bp": [pa[c][~pa.seen].mean() * 1e4 for c in cols],
                             "mean_seen_bp": [pa[c][pa.seen].mean() * 1e4 for c in cols],
                             "share_positive": [float((pa[c] > 0).mean()) for c in cols]})
    fcols = [c for c in fl.columns if c.startswith("f")]
    flow_out = pd.DataFrame({"range_s": [c[1:] for c in fcols], "mean": [fl[c].mean() for c in fcols],
                             "median": [fl[c].median() for c in fcols]})
    bk.to_csv(res / "scalps.csv", index=False, float_format="%.6g")
    sc.to_csv(res / "hops.csv.gz", index=False, float_format="%.8g")
    path_out.to_csv(res / "path.csv", index=False, float_format="%.6g")
    flow_out.to_csv(res / "flow.csv", index=False, float_format="%.6g")
    if check_data() != n_files:
        raise prereg.PreregError("the tick files changed during the run")
    summary = {"lane": LANE.name, "registry": REGISTRY, "trials": TRIALS, "primary": prim["scalp"],
               "decision": dec, "verdict": dec["verdict"], "family": fam, "counts": n, "cost_bp": COST_BP,
               "inputs": shas, "tick_files": n_files}
    (res / "summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    log(f"verdict {dec['verdict']} {dec['checks']}; family {fam}")


if __name__ == "__main__":
    main()
