"""xfundint_v1 (R384): is R277's KuCoin carry an artifact of settlement intervals? As set out in
experiments/xfundint_v1/PREREG.md. Replays R277's frozen books (gate+kucoin, binance+kucoin; L14d th5% K20) with the
frozen engine twin lab/xfund.py, checks the replay against R277's saved daily and trades, then attributes each
position's gross, funding and costs to the settlement-interval class of its KuCoin contract (data/kucoin_hist/
contracts.csv), before and after KuCoin's scaling (2026-07-14/24), plus Binance's (2025-09-18) on Binance legs.

usage: .venv/bin/python scripts/run_xfundint.py          (about 5 minutes)
       .venv/bin/python scripts/run_xfundint.py --dev     (before the freeze only: prefix window, no statistics shown)
"""
import argparse
import hashlib
import json
import sys
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg, stats, xfund  # noqa: E402
from scripts.run_clockflow import check_inputs  # noqa: E402

LANE = ROOT / "experiments" / "xfundint_v1"
SRC = ROOT / "experiments" / "xfund_kd_v1"
SETS = ("gate+kucoin", "binance+kucoin")
L, TH, K = 14, 0.05, 20
CLASSES = ("1h", "4h", "8h")
FUND_MS = {3_600_000: "1h", 14_400_000: "4h", 28_800_000: "8h"}
# periods by the date label of a daily row (funding settled in (label - 1 day, label] is booked under the label)
KC = {"pre": ("0000-00-00", "2026-07-14"), "trans": ("2026-07-15", "2026-07-24"), "post": ("2026-07-25", "9999-99-99")}
BN = {"pre": ("0000-00-00", "2025-09-18"), "post": ("2025-09-19", "9999-99-99")}
YEARS = tuple(str(y) for y in range(2021, 2027))
NW_LAGS = 10
EXPECTED_CELLS = 56
R277_PARITY_TOL = 1e-9
RECON_TOL = 1e-12
_logf = None


def log(*a):
    line = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(line, flush=True)
    if _logf:
        _logf.write(line + "\n")
        _logf.flush()


def ms(day):
    return int(pd.Timestamp(day, tz="UTC").value // 10**6)


def day_class(s, day):
    """Interval class of a leg on a day, from the number of settlements the recorded funding file holds that day."""
    n = int(s.cumn[day] - s.cumn[day - 1])
    return "8h" if n <= 3 else "4h" if n <= 8 else "1h"


def verify_files(spec, sym, need):
    """sha256 of every data file the replay reads, against docs/provenance/<folder>.json (only the files read)."""
    prov, jobs = {}, []
    for v in spec["venues"]:
        if v["name"] not in need:
            continue
        for key, p in (("prices", v["prices"]), ("funding", v["funding"])):
            parts = p.split("/")
            pj = prov.setdefault(parts[0], {r["path"]: r["sha256"] for r in json.loads(
                (ROOT / "docs" / "provenance" / f"{parts[0]}.json").read_text())["file_hashes"]})
            for s in sym[v["name"]]:
                s = s.strip()
                if s and (ROOT / "data" / p / f"{s}.parquet").exists():
                    rel = "/".join(parts[1:] + [f"{s}.parquet"])
                    jobs.append((ROOT / "data" / p / f"{s}.parquet", pj.get(rel), f"{p}/{s}"))

    def one(j):
        path, want, name = j
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return name if want is None or h.hexdigest() != want else None

    with ThreadPoolExecutor(4) as ex:
        bad = [x for x in ex.map(one, jobs) if x]
    if bad:
        raise SystemExit(f"{len(bad)} data files differ from docs/provenance (or are not listed): {bad[:5]}")
    return len(jobs)


def load_universe(spec, sym, need, end):
    t0 = ms(spec["start"])
    nd = int((ms(end) + xfund.DAY - t0) // xfund.DAY + 1)

    def one(row):
        out = []
        for v in spec["venues"]:
            s = row[v["name"]].strip()
            if not s or v["name"] not in need:
                out.append(None)
                continue
            out.append(xfund.load_daily(ROOT / "data" / v["prices"] / f"{s}.parquet",
                                        ROOT / "data" / v["funding"] / f"{s}.parquet", v["vol"], v.get("bar_h", 1),
                                        t0, nd))
        return out

    with ThreadPoolExecutor(8) as ex:
        series = list(ex.map(one, [r for _, r in sym.iterrows()]))
    return xfund.Universe(sym.key.tolist(), [v["name"] for v in spec["venues"]], series, t0, nd, spec["corr_days"],
                          spec["corr_min"], spec["corr_obs"])


def restrict(u, vk, kcls, keep):
    """The universe without the KuCoin series of contracts outside the class `keep`."""
    ser = [[None if (v == vk and kcls.get(key) != keep) else s for v, s in enumerate(row)]
           for key, row in zip(u.keys, u.series)]
    return xfund.Universe(u.keys, u.names, ser, u.t0, u.nd, u.corr_days, u.corr_min, u.corr_obs)


def attribute(u, book, w0, vk, kcls):
    """xfund.replay's loop with each position's gross, funding and legs booked to the class of its KuCoin contract.
    Also the other leg's funding by that leg's day class and the KuCoin leg's static-vs-implied class agreement."""
    n = u.nd - 1 - w0
    cls = {c: {k: np.zeros(n) for k in ("gross", "fund", "legs", "fundK")} for c in CLASSES}
    oth = {c: np.zeros(n) for c in CLASSES}
    held = np.zeros(n, int)
    agree = {"days": 0, "same": 0}
    recs, live = [], {}
    for d in range(w0, u.nd - 1):
        i = d - w0
        for p, forced in book.exits(u, d):
            cls[live[id(p)]["cls"]]["legs"][i] += 2.0
            live.pop(id(p))["exit_day"] = d
        for p in book.entries(u, d):
            c = kcls[u.keys[p.coin]]
            cls[c]["legs"][i] += 2.0
            r = {"coin": u.keys[p.coin], "long": u.names[p.lo], "short": u.names[p.hi], "entry_day": d, "exit_day": None,
                 "cls": c, "price": 0.0, "fund": 0.0, "fundK": 0.0}
            live[id(p)] = r
            recs.append(r)
        held[i] = len(book.open)
        for p in book.open:
            a, h = u.series[p.coin][p.lo], u.series[p.coin][p.hi]
            r = live[id(p)]
            price = a.ret(d) - h.ret(d)
            fs, fl = h.fund_on(d + 1), a.fund_on(d + 1)         # the short leg earns fs, the long leg pays fl
            f = fs - fl
            c = r["cls"]
            cls[c]["gross"][i] += price + f
            cls[c]["fund"][i] += f
            kc_short = p.hi == vk
            fk = fs if kc_short else -fl
            fo, so, kleg = (-fl, a, h) if kc_short else (fs, h, a)
            cls[c]["fundK"][i] += fk
            oth[day_class(so, d + 1)][i] += fo
            agree["days"] += 1
            agree["same"] += int(day_class(kleg, d + 1) == c)
            r["price"] += price
            r["fund"] += f
            r["fundK"] += fk
    for p in book.open:
        cls[live[id(p)]["cls"]]["legs"][n - 1] += 2.0
    return cls, oth, held, agree, recs


def ann(x):
    return float(np.mean(x) * 365 * 100) if len(x) else float("nan")


def nwt(x):
    return float(stats.newey_west_t(np.asarray(x, float), NW_LAGS)[2]) if len(x) > 1 else float("nan")


def label(a, b, c):
    """The frozen labelling rule for one set: robust (C) first, then interval-artifact (A and B), else inconclusive."""
    return "robust" if c else "interval-artifact" if (a and b) else "inconclusive"


def lead_label(labels):
    return labels[0] if len(set(labels)) == 1 else "inconclusive"


def build_cells(name, cls, oth, dates, costs, k, other_name, eight, eight_dates):
    """The reported cells of one set. `eight` = net rows of the 8h-only replay (3 cost arrays) and its date labels."""
    rows = []
    allg = sum(cls[c]["gross"] for c in CLASSES)
    allf = sum(cls[c]["fund"] for c in CLASSES)
    alll = sum(cls[c]["legs"] for c in CLASSES)
    net = lambda g, l, m: (g - costs[m] * l) / (2.0 * k)

    def full(fam, per, mask):
        r = {"set": name, "family": fam, "period": per, "cls": "all", "days": int(mask.sum())}
        for m in range(3):
            r[f"net{m + 1}x"] = ann(net(allg[mask], alll[mask], m))
        r["nw_t_1x"] = nwt(net(allg[mask], alll[mask], 0))
        r["share"] = float("nan")
        rows.append(r)

    def part(fam, per, mask, c, series, with_net):
        r = {"set": name, "family": fam, "period": per, "cls": c, "days": int(mask.sum()), "nw_t_1x": float("nan")}
        tot = allf[mask].sum()
        r["share"] = float(series[mask].sum() / tot) if tot != 0 else float("nan")
        for m in range(3):
            r[f"net{m + 1}x"] = ann(net(cls[c]["gross"][mask], cls[c]["legs"][mask], m)) if with_net else float("nan")
        rows.append(r)

    inr = lambda per, tab: (dates >= tab[per][0]) & (dates <= tab[per][1])
    for y in YEARS:
        full("year", y, np.char.startswith(dates, y))
    for per in KC:
        full("period_kc", per, inr(per, KC))
    for per in ("pre", "post"):
        for c in CLASSES:
            part("class_kc", per, inr(per, KC), c, cls[c]["fund"], True)
    for per in ("pre", "post"):
        for c in CLASSES:
            part("otherleg_kc", per, inr(per, KC), c, oth[c], False)
    rows.append({"set": name, "family": "implied_vs_static", "period": "all", "cls": "all", "days": len(dates),
                 "share": float("nan"), "nw_t_1x": float("nan"), "net1x": float("nan"), "net2x": float("nan"),
                 "net3x": float("nan")})                      # filled by the caller (agreement)
    for per, mask in (("all", np.ones(len(eight_dates), bool)), ("post", (eight_dates >= KC["post"][0]))):
        r = {"set": name, "family": "only8h_replay", "period": per, "cls": "8h", "days": int(mask.sum()),
             "share": float("nan")}
        for m in range(3):
            r[f"net{m + 1}x"] = ann(eight[m][mask])
        r["nw_t_1x"] = nwt(eight[0][mask])
        rows.append(r)
    if other_name == "binance":
        for per in BN:
            full("period_bn", per, inr(per, BN))
        for per in BN:
            for c in CLASSES:
                part("class_bn", per, inr(per, BN), c, oth[c], False)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", action="store_true", help="before the freeze only: window to 2021-06-30, nothing written")
    a = ap.parse_args()
    global _logf
    if a.dev:
        if prereg.sidecar(LANE / "PREREG.md").exists():
            raise SystemExit("--dev is for the time before the freeze")
        dev_end = "2021-06-30"
    else:
        log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
        shas = check_inputs(LANE / "PREREG.md")
        log("inputs match:", len(shas))
        (LANE / "results").mkdir(exist_ok=True)
        _logf = open(LANE / "run.log", "a")
        dev_end = None
    spec = tomllib.loads((SRC / "spec.toml").read_text())
    costs = spec["costs"]
    sym = pd.read_csv(ROOT / spec["symbols"], dtype=str).fillna("")
    need = {"binance", "gate", "kucoin"}
    log("data files verified against docs/provenance:", verify_files(spec, sym, need))
    end = dev_end or spec["end"]
    u = load_universe(spec, sym, need, end)
    names = u.names
    vk = names.index("kucoin")
    con = pd.read_csv(ROOT / "data" / "kucoin_hist" / "contracts.csv", dtype={"symbol": str})
    cmap = {r.symbol: FUND_MS.get(int(r.funding_ms), "oth") for r in con.itertuples()}
    kcls = {r.key: cmap.get(r.kucoin, "unk") for r in sym.itertuples() if r.kucoin}
    log("KuCoin contracts in the table by class:", {c: sum(1 for x in kcls.values() if x == c) for c in (*CLASSES, "oth", "unk")})
    t0d = pd.Timestamp(spec["start"])
    day = lambda d: str((t0d + pd.Timedelta(days=int(d))).date())
    eng_t = pd.read_csv(SRC / "results" / "trades.csv")
    eng_d = pd.read_csv(SRC / "results" / "daily.csv")
    cells, parity, extra, daily_out, recs_out = [], {}, {}, [], []
    ok = True
    for sname in SETS:
        t = time.time()
        vset = [names.index(v) for v in sname.split("+")]
        other = [v for v in sname.split("+") if v != "kucoin"][0]
        lab = f"{sname} L{L}d th{round(TH * 100)}% K{K}"
        w0 = xfund.window_start(u, vset, L)
        rows, trades = xfund.replay(u, xfund.Book(vset, L, TH, K), w0)
        mine = [(x["coin"], x["long"], day(x["entry_day"]), "" if x["exit_day"] is None else day(x["exit_day"]))
                for x in trades]
        e = eng_t[eng_t.strategy == label_str(lab)]
        theirs = list(zip(e.coin, e.long, e.entry, e["exit"].fillna("")))
        diffs = []
        for m in range(3):
            mynet = xfund.net(rows, K, costs[m]).to_numpy()
            eng = eng_d[(eng_d.strategy == lab) & (eng_d.cost_multiple == m + 1)]
            en = eng.net.to_numpy()
            if dev_end:
                diffs.append(float(np.abs(mynet[:-1] - en[:len(mynet) - 1]).max()))
            else:
                diffs.append(float(np.abs(mynet - en).max()) if len(mynet) == len(en) else float("inf"))
        dates = np.array([day(d + 1) for d in rows.day])
        eng1 = eng_d[(eng_d.strategy == lab) & (eng_d.cost_multiple == 1)]
        dates_ok = bool((dates[:len(eng1) - (1 if dev_end else 0)] == eng1.date.to_numpy()[:len(dates) - (1 if dev_end else 0)]).all()) \
            and (dev_end is not None or len(dates) == len(eng1))
        same = (dev_end is not None or mine == theirs) and max(diffs) < R277_PARITY_TOL and dates_ok
        ok &= same
        parity[sname] = {"trades_mine": len(mine), "trades_r277": len(theirs), "trades_identical": mine == theirs,
                         "days_mine": len(rows), "days_r277": len(eng1), "max_net_diff_1x_2x_3x": diffs,
                         "dates_identical": dates_ok, "ok": same}
        log(f"parity {lab}: trades {len(mine)} vs {len(theirs)} identical {mine == theirs}; days {len(rows)} vs "
            f"{len(eng1)}; max|net diff| {max(diffs):.1e}; dates {dates_ok}; {'OK' if same else 'MISMATCH'}")
        if not same:
            continue
        cls, oth, held, agree, recs = attribute(u, xfund.Book(vset, L, TH, K), w0, vk, kcls)
        rec = {
            "gross": float(np.abs(sum(cls[c]["gross"] for c in CLASSES) - rows.gross.to_numpy()).max()),
            "fund": float(np.abs(sum(cls[c]["fund"] for c in CLASSES) - rows.funding.to_numpy()).max()),
            "legs": float(np.abs(sum(cls[c]["legs"] for c in CLASSES) - rows.legs.to_numpy()).max()),
            "held": int(np.abs(held - rows.held.to_numpy()).max()),
            "other_leg_plus_kucoin_leg_vs_fund": float(np.abs(sum(oth[c] for c in CLASSES) + sum(cls[c]["fundK"] for c in CLASSES)
                                                          - rows.funding.to_numpy()).max())}
        extra[sname] = {"reconcile_attribution_vs_replay": rec, "unk_or_oth_trades": sum(r["cls"] not in CLASSES for r in recs)}
        if max(rec.values()) > RECON_TOL:
            log("attribution does not reconcile with the replay:", rec)
            ok = False
            parity[sname]["ok"] = False
            continue
        if not dev_end:
            key = {(r["coin"], r["long"], day(r["entry_day"])): r for r in recs}
            dd = [(abs(key[(x.coin, x.long, x.entry)]["fund"] - x.funding_pnl),
                   abs(key[(x.coin, x.long, x.entry)]["price"] - x.price_pnl)) for x in e.itertuples()]
            extra[sname]["trade_pnl_vs_r277_trades_csv_max_abs_diff_funding_price"] = [max(z[0] for z in dd), max(z[1] for z in dd)]
        eight_u = restrict(u, vk, kcls, "8h")
        w8 = xfund.window_start(eight_u, vset, L)
        rows8, _ = xfund.replay(eight_u, xfund.Book(vset, L, TH, K), w8)
        eight = [xfund.net(rows8, K, costs[m]).to_numpy() for m in range(3)]
        d8 = np.array([day(d + 1) for d in rows8.day])
        sc = build_cells(sname, cls, oth, dates, costs, K, other, eight, d8)
        for r in sc:
            if r["family"] == "implied_vs_static":
                r["share"] = 1.0 - agree["same"] / agree["days"] if agree["days"] else float("nan")
        cells += sc
        for c in CLASSES:
            for i, dt in enumerate(dates):
                daily_out.append({"set": sname, "date": dt, "cls": c, **{k_: cls[c][k_][i] for k_ in ("gross", "fund", "legs", "fundK")}})
        for r in recs:
            recs_out.append({"set": sname, **r, "entry": day(r["entry_day"]),
                             "exit": "" if r["exit_day"] is None else day(r["exit_day"])})
        log(f"{sname} done in {time.time() - t:.0f}s")
    if not ok:
        if not dev_end:
            (LANE / "BLOCKED.md").write_text("# BLOCKED: the replay does not reproduce R277's frozen output\n\n```json\n"
                                             + json.dumps({"parity": parity, "extra": extra}, indent=1) + "\n```\n")
        raise SystemExit("BLOCKED: parity or reconciliation failed")
    ncell = len(cells)
    log("cells:", ncell, "expected", EXPECTED_CELLS)
    assert ncell == EXPECTED_CELLS, ncell
    cdf = pd.DataFrame(cells)
    if dev_end:
        log("dev run: structure checks passed; reconcile", json.dumps({s: extra[s]["reconcile_attribution_vs_replay"] for s in extra}))
        return
    # decision
    dec = {}
    for sname in SETS:
        g = cdf[cdf.set == sname]
        pre = g[(g.family == "class_kc") & (g.period == "pre")].set_index("cls")
        post8 = g[(g.family == "class_kc") & (g.period == "post") & (g.cls == "8h")].iloc[0]
        postf = g[(g.family == "period_kc") & (g.period == "post")].iloc[0]
        share = float(pre.loc[["1h", "4h"], "share"].sum())
        A = bool(share > 0.5)
        B = bool(post8.net1x <= 0)
        C = bool(postf.net1x > 0 and postf.nw_t_1x >= 2.0)
        dec[sname] = {"pre_share_1h4h_of_net_funding": share, "A": A, "post_8h_class_net1x_ann_pct": float(post8.net1x), "B": B,
                      "post_full_net1x_ann_pct": float(postf.net1x), "post_full_nw_t": float(postf.nw_t_1x),
                      "post_days": int(postf.days), "C": C, "label": label(A, B, C)}
    dec["lead_label"] = lead_label([dec[s]["label"] for s in SETS])
    dec["trials"] = ncell
    cdf.to_csv(LANE / "results" / "cells.csv", index=False, float_format="%.8g")
    pd.DataFrame(daily_out).to_csv(LANE / "results" / "daily_class.csv", index=False, float_format="%.10g")
    pd.DataFrame(recs_out).to_csv(LANE / "results" / "positions.csv", index=False, float_format="%.10g")
    (LANE / "results" / "parity.json").write_text(json.dumps({"parity": parity, "extra": extra}, indent=1))
    (LANE / "results" / "decision.json").write_text(json.dumps(dec, indent=1))
    log("decision", json.dumps(dec))


def label_str(x):
    return x


if __name__ == "__main__":
    main()
