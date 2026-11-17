"""Draft for M549, not yet registered (cmeterm_v1): commodity term-structure carry on CME futures, 2010-09..2026-10,
at daily settlements. Blocked on a Databento key; register and freeze a PREREG before any in-window pull.

The book (Gorton-Hayashi-Rouwenhorst backwardation, Koijen-Moskowitz-Pedersen-Vrugt carry), with CME specifics:

- 13 roots: CL HO RB NG (energy), GC SI HG PL (metals), ZC ZS ZW (grains), LE HE (livestock).
- Each month's first CME settlement day D, per root, the two contracts with the most open interest (Databento
  continuous n.0 and n.1, ranked on the previous day's open interest) give the curve's slope:
      carry = ln(F_near / F_far) x 365.25 / (expiry_far - expiry_near in days)
  positive = backwardation. Expiries, ticks and tick values come from the instrument definitions, never from a calendar
  rule.
- Long the k roots with the highest carry, short the k lowest, k = floor(valid roots / 3) (4 of 13); no book when
  fewer than 9 roots are valid.
- The held contract is the farther of the two (it does not reach delivery inside the month); a root is skipped when
  that contract expires within 40 days of D.
- Weights: inverse volatility inside each leg (63 trailing same-contract daily returns of the n.1 contract, at least
  40), each leg 0.5 of capital: gross 1.
- Entry at the settlement of the next CME day after D (E), not at D's: the signal's settlement is never traded.
  Weights are held constant until the next month's E.
- Costs per contract side, in bp of the contract's notional (price x unit of measure, in dollars): an all-in fee (exchange,
  clearing, NFA and a retail commission) plus a slippage of whole ticks against the settlement. A changed contract
  pays both sides (close the old, open the new); a held contract pays only the change in weight.
- Returns are futures excess returns: the collateral's interest is not counted (the book is read against zero, which is
  the cash hurdle for a futures book whose margin earns the bill rate).

Data: Databento GLBX.MDP3 statistics (stat_type 3, settlements; the last publication for each contract and trading
day) and definitions, for {root}.n.0, n.1, n.2. Definitions are pulled one root at a time and kept; statistics one root
and four years at a time, reduced on
arrival to the settlement rows (data/databento/cmeterm/settle_<ROOT>.csv) and the raw file is deleted: the manifest
keeps its quote, size and sha256.

Paper research only: nothing here can place an order.

    python scripts/run_cmeterm.py cost     # quotes only (free)
    python scripts/run_cmeterm.py fetch    # PREREG must verify; capped
    python scripts/run_cmeterm.py run      # PREREG must verify
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
LANE = ROOT / "experiments" / "cmeterm_v1"
DATA = ROOT / "data" / "databento" / "cmeterm"

ROOTS = {"CL": "energy", "HO": "energy", "RB": "energy", "NG": "energy",
         "GC": "metals", "SI": "metals", "HG": "metals", "PL": "metals",
         "ZC": "grains", "ZS": "grains", "ZW": "grains",
         "LE": "livestock", "HE": "livestock"}
RANKS = (0, 1, 2)
FETCH_START, FETCH_END = "2010-06-06", "2026-11-01"
CHUNKS = (("2010-06-06", "2014-01-01"), ("2014-01-01", "2018-01-01"), ("2018-01-01", "2022-01-01"),
          ("2022-01-01", "2026-11-01"))
FIRST_MONTH, LAST_DAY = "2010-09", "2026-10-31"
CENTS = {"ZC", "ZS", "ZW", "LE", "HE"}   # quoted in cents per unit; the others in dollars
MIN_ROOTS = 9
MIN_DAYS_TO_EXPIRY = 40
VOL_N, VOL_MIN = 63, 40
FEE_USD = 3.00                     # per contract per side, all-in
SLIP_TICKS = 1.0                   # per side against the settlement
NW_LAG = 20
CAP_STATS_USD, CAP_DEF_USD, CAP_TOTAL_USD = 0.40, 0.05, 3.50


# ---------- data ----------

def day_of(x):
    s = str(x)
    return dt.date.fromisoformat(s[:10])


def settlements_from_rows(rows):
    """{(instrument_id, trading day): price} from statistics rows: settlement (stat_type 3), new (update_action 1),
    the last publication by receive time."""
    best = {}
    for r in rows:
        if int(r["stat_type"]) != 3 or int(r["update_action"]) != 1 or r["ts_ref"] in (None, ""):
            continue
        key = (int(r["instrument_id"]), day_of(r["ts_ref"]))
        recv = str(r["ts_recv"])
        if key not in best or recv > best[key][0]:
            best[key] = (recv, float(r["price"]))
    return {k: p for k, (_, p) in best.items()}


def ranks_from_definitions(rows):
    """{day: {root: {rank: (iid, expiry date, tick, dollars per price unit, raw symbol)}}} from definition rows: per
    UTC day and continuous symbol, the earliest record of that day. Dollars per price unit = the contract's unit of
    measure quantity, divided by 100 for roots quoted in cents; notional = price x it, tick value = tick x it."""
    first = {}
    for r in rows:
        sym = str(r["symbol"])
        parts = sym.split(".")
        if len(parts) != 3 or parts[0] not in ROOTS or parts[1] != "n":
            continue
        day, recv = day_of(r["ts_recv"]), str(r["ts_recv"])
        key = (day, parts[0], int(parts[2]))
        if key not in first or recv < first[key][0]:
            mult = float(r["unit_of_measure_qty"]) * (0.01 if parts[0] in CENTS else 1.0)
            first[key] = (recv, (int(r["instrument_id"]), day_of(r["expiration"]), float(r["min_price_increment"]),
                                 mult, str(r["raw_symbol"])))
    out = defaultdict(lambda: defaultdict(dict))
    for (day, root, rank), (_, info) in first.items():
        out[day][root][rank] = info
    return {d: dict(v) for d, v in out.items()}


def _reader(path, cols):
    import pyarrow as pa
    import pyarrow.csv as pc
    types = {"ts_recv": pa.string(), "ts_ref": pa.string(), "symbol": pa.string(), "expiration": pa.string(),
             "raw_symbol": pa.string(), "instrument_id": pa.int64(), "price": pa.float64(), "stat_type": pa.int64(),
             "update_action": pa.int64(), "stat_flags": pa.int64(), "min_price_increment": pa.float64(),
             "unit_of_measure_qty": pa.float64()}
    opts = pc.ConvertOptions(include_columns=cols, column_types={c: types[c] for c in cols if c in types})
    return pc.open_csv(pa.input_stream(str(path), compression="zstd"), convert_options=opts)


STAT_COLS = ["ts_recv", "instrument_id", "ts_ref", "price", "stat_type", "update_action", "stat_flags", "symbol"]
DEF_COLS = ["ts_recv", "instrument_id", "raw_symbol", "expiration", "min_price_increment", "unit_of_measure_qty",
            "symbol"]


def reduce_stats(raw, out_csv):
    """Keep only settlement rows of a raw statistics file; append them to out_csv. Returns rows kept."""
    import pyarrow.compute as pcm
    kept = 0
    new = not out_csv.exists()
    with out_csv.open("a", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        if new:
            w.writerow(STAT_COLS)
        for batch in _reader(raw, STAT_COLS):
            b = batch.filter(pcm.and_(pcm.equal(batch["stat_type"], 3), pcm.equal(batch["update_action"], 1)))
            for r in b.to_pylist():
                w.writerow([r[c] for c in STAT_COLS])
                kept += 1
    return kept


def load():
    """(calendar, settle, ranks) from the reduced settlement files and the definitions file."""
    rows = []
    for root in ROOTS:
        with (DATA / f"settle_{root}.csv").open(newline="") as f:
            rows += list(csv.DictReader(f))
    settle = settlements_from_rows(rows)
    defs = []
    for path in sorted(DATA.glob("*_definition_*.csv.zst")):
        for batch in _reader(path, DEF_COLS):
            defs += batch.to_pylist()
    ranks = ranks_from_definitions(defs)
    return calendar(settle, ranks), settle, ranks


def calendar(settle, ranks):
    """Trading days (settlement days) with a settlement for at least 7 roots' ranked contracts (ranks carried
    forward as in rank_for)."""
    out = []
    for day in sorted({d for _, d in settle}):
        n = 0
        for root in ROOTS:
            rk = rank_for(ranks, day, root)
            if rk and any((info[0], day) in settle for info in rk.values()):
                n += 1
        if n >= 7:
            out.append(day)
    return out


# ---------- signal and book ----------

def carry_of(n0, n1, settle, day):
    """(carry %/yr as a fraction, far info) from the two top-open-interest contracts, or None."""
    if n0[0] == n1[0] or n0[1] == n1[1]:
        return None
    near, far = (n0, n1) if n0[1] < n1[1] else (n1, n0)
    a, b = settle.get((near[0], day)), settle.get((far[0], day))
    if not a or not b or a <= 0 or b <= 0:
        return None
    return math.log(a / b) * 365.25 / (far[1] - near[1]).days, far


def vol_series(cal, settle, ranks):
    """{root: [(day, same-contract daily return of the n.1 contract)]}."""
    out = defaultdict(list)
    last = {}
    for day in cal:
        for root in ROOTS:
            info = (rank_for(ranks, day, root) or {}).get(1)
            if not info:
                continue
            p = settle.get((info[0], day))
            if p is None:
                continue
            prev = last.get(root)
            if prev and prev[0] == info[0] and prev[1] > 0:
                out[root].append((day, p / prev[1] - 1.0))
            last[root] = (info[0], p)
    return out


def trailing_vol(series, day):
    xs = [r for d, r in series if d <= day][-VOL_N:]
    return statistics.stdev(xs) if len(xs) >= VOL_MIN else None


def rank_for(ranks, day, root):
    """The rank map on day, or the latest within the 31 days before (carried forward when a day has no
    definition record)."""
    for back in range(32):
        rk = ranks.get(day - dt.timedelta(days=back), {}).get(root)
        if rk:
            return rk
    return None


def decide(day, entry_day, settle, ranks, vols, k=None, weighting="ivol", signal="carry", carry_hist=None):
    """Target holdings {root: (weight, iid, cost rate per unit notional per side at 1x)} and diagnostics."""
    valid = {}
    skipped = Counter_()
    for root in ROOTS:
        rk = rank_for(ranks, day, root)
        if not rk or 0 not in rk or 1 not in rk:
            skipped["no_rank"] += 1
            continue
        c = carry_of(rk[0], rk[1], settle, day)
        if c is None:
            skipped["no_carry"] += 1
            continue
        carry, far = c
        if (far[1] - day).days < MIN_DAYS_TO_EXPIRY:
            skipped["near_expiry"] += 1
            continue
        px = settle.get((far[0], entry_day))
        if not px or px <= 0:
            skipped["no_entry_price"] += 1
            continue
        sd = trailing_vol(vols.get(root, []), day)
        if not sd:
            skipped["no_vol"] += 1
            continue
        sig = carry
        if carry_hist is not None:
            carry_hist[root].append(carry)
            if signal == "carry12":
                if len(carry_hist[root]) < 12:
                    skipped["short_hist"] += 1
                    continue
                sig = sum(carry_hist[root][-12:]) / 12
        notional = px * far[3]
        valid[root] = {"sig": sig, "carry": carry, "iid": far[0], "sd": sd, "notional": notional, "exp": far[1],
                       "rate": (FEE_USD + SLIP_TICKS * far[2] * far[3]) / notional, "raw": far[4]}
    if len(valid) < MIN_ROOTS:
        return {}, {"valid": len(valid), "skipped": dict(skipped), "book": False}
    kk = k or len(valid) // 3
    order = sorted(valid, key=lambda r: (-valid[r]["sig"], r))
    longs, shorts = order[:kk], order[-kk:]
    hold = {}
    for leg, sign in ((longs, 1.0), (shorts, -1.0)):
        inv = {r: (1.0 / valid[r]["sd"] if weighting == "ivol" else 1.0) for r in leg}
        tot = sum(inv.values())
        for r in leg:
            hold[r] = (sign * 0.5 * inv[r] / tot, valid[r]["iid"], valid[r]["rate"], valid[r]["notional"])
    spread = (sum(valid[r]["carry"] for r in longs) - sum(valid[r]["carry"] for r in shorts)) / kk
    return hold, {"valid": len(valid), "skipped": dict(skipped), "book": True, "longs": longs, "shorts": shorts,
                  "carry_spread": spread, "under_60d": sum((valid[r]["exp"] - day).days < 60 for r in hold),
                  "min_capital": max(h[3] / abs(h[0]) for h in hold.values())}


class Counter_(dict):
    def __missing__(self, key):
        return 0


def build(cal, settle, ranks, cost_k=1.0, k=None, weighting="ivol", lag=True, signal="carry", vols=None):
    """Daily rows {day, gross, cost, net, by root contributions} and monthly decisions."""
    vols = vols if vols is not None else vol_series(cal, settle, ranks)
    end = dt.date.fromisoformat(LAST_DAY)
    first = dt.date.fromisoformat(FIRST_MONTH + "-01")
    days = [d for d in cal if first - dt.timedelta(days=120) <= d <= end]
    months, seen = {}, set()
    for i, d in enumerate(days):
        ym = (d.year, d.month)
        if d >= first and ym not in seen:
            seen.add(ym)
            e = days[i + 1] if lag and i + 1 < len(days) else d
            if e <= end:
                months[e] = d
    carry_hist = defaultdict(list)
    held, last_px = {}, {}
    rows, decisions = [], []
    for d in days:
        if d < first:
            continue
        gross, contrib = 0.0, {}
        for root, (w, iid, rate, _) in held.items():
            p = settle.get((iid, d))
            if p is None or last_px[root] <= 0:
                continue
            r = p / last_px[root] - 1.0
            last_px[root] = p
            gross += w * r
            contrib[root] = w * r
        cost = 0.0
        is_last = d == days[-1] or d == end
        if d in months or is_last:
            if d in months and not is_last:
                new, info = decide(months[d], d, settle, ranks, vols, k=k, weighting=weighting, signal=signal,
                                   carry_hist=carry_hist)
                decisions.append(dict(info, decision=months[d].isoformat(), entry=d.isoformat()))
            else:
                new = {}
            for root in set(held) | set(new):
                wo, io, ro, _ = held.get(root, (0.0, None, 0.0, 0.0))
                wn, inn, rn, _ = new.get(root, (0.0, None, 0.0, 0.0))
                if io == inn:
                    cost += abs(wn - wo) * rn * cost_k
                else:
                    cost += (abs(wo) * ro + abs(wn) * rn) * cost_k
            held = new
            for root, (w, iid, rate, _) in held.items():
                last_px[root] = settle[(iid, d)]
        rows.append({"day": d.isoformat(), "gross": gross, "cost": cost, "net": gross - cost, "contrib": contrib})
        if is_last:
            break
    return rows, decisions


# ---------- statistics ----------

def summarize(rows):
    if len(rows) < 30:
        return {"days": len(rows)}
    from lab.stats import newey_west_t
    net = [r["net"] for r in rows]
    yrs = (day_of(rows[-1]["day"]) - day_of(rows[0]["day"])).days / 365.25
    ann = sum(net) / yrs
    vol = statistics.stdev(net) * math.sqrt(len(net) / yrs)
    eq, peak, mdd = 0.0, 0.0, 0.0
    for x in net:
        eq += x
        peak = max(peak, eq)
        mdd = min(mdd, eq - peak)
    return {"start": rows[0]["day"], "end": rows[-1]["day"], "days": len(rows), "years": round(yrs, 3),
            "ann_net_pct": round(ann * 100, 3), "ann_gross_pct": round(sum(r["gross"] for r in rows) / yrs * 100, 3),
            "ann_cost_pct": round(sum(r["cost"] for r in rows) / yrs * 100, 3),
            "ann_vol_pct": round(vol * 100, 3), "sharpe": round(ann / vol, 3) if vol > 0 else None,
            "nw_t": round(newey_west_t(net, NW_LAG)[2], 3), "max_drawdown_pct": round(mdd * 100, 3)}


def by_year(rows):
    out = defaultdict(list)
    for r in rows:
        out[r["day"][:4]].append(r)
    return {y: summarize(v) for y, v in sorted(out.items())}


def contributions(rows):
    if len(rows) < 2:
        return {}, {}
    yrs = (day_of(rows[-1]["day"]) - day_of(rows[0]["day"])).days / 365.25
    by_root, by_sector = defaultdict(float), defaultdict(float)
    for r in rows:
        for root, x in r["contrib"].items():
            by_root[root] += x
            by_sector[ROOTS[root]] += x
    return ({k: round(v / yrs * 100, 3) for k, v in sorted(by_root.items())},
            {k: round(v / yrs * 100, 3) for k, v in sorted(by_sector.items())})


def verdict_of(p1, p2):
    if p1.get("ann_net_pct", 0) > 0 and p1.get("nw_t", 0) >= 2.0 and p2.get("ann_net_pct", 0) > 0:
        return "CARRY_PASS"
    if p1.get("ann_net_pct", 0) > 0:
        return "CARRY_WEAK"
    return "CARRY_NULL"


# ---------- fetch ----------

def requests_plan():
    base = {"dataset": "GLBX.MDP3", "stype_in": "continuous"}
    plan = []
    for root in ROOTS:
        s = ",".join(f"{root}.n.{i}" for i in RANKS)
        plan.append(("definition", root, dict(base, symbols=s, schema="definition", start=FETCH_START,
                                              end=FETCH_END)))
        for a, b in CHUNKS:
            plan.append(("statistics", root, dict(base, symbols=s, schema="statistics", start=a, end=b)))
    return plan


def cost():
    from scripts import fetch_databento as fd
    key, tot = fd.read_key(), 0.0
    for kind, root, p in requests_plan():
        usd = fd.quote(p, key)
        tot += usd
        print(kind, root or "", p["start"], p["end"], f"${usd:.4f}")
    print(f"total ${tot:.4f}")
    return tot


def fetch():
    from lab.prereg import verify
    from scripts import fetch_databento as fd
    verify(LANE / "PREREG.md")
    check_inputs()
    key, spent = fd.read_key(), 0.0
    DATA.mkdir(parents=True, exist_ok=True)
    done = set()
    if (DATA / "reduced.csv").exists():
        with (DATA / "reduced.csv").open(newline="") as f:
            done = {r["request"] for r in csv.DictReader(f)}
    for kind, root, p in requests_plan():
        tag = f"{p['symbols']}|{p['schema']}|{p['start']}|{p['end']}"
        if tag in done:
            continue
        usd = fd.quote(p, key)
        if spent + usd > CAP_TOTAL_USD:
            raise SystemExit(f"stop: total cap ${CAP_TOTAL_USD} would be passed (spent ${spent:.4f})")
        path, usd = fd.fetch(p, key, DATA, CAP_DEF_USD if kind == "definition" else CAP_STATS_USD)
        spent += usd
        if kind == "statistics":
            kept = reduce_stats(path, DATA / f"settle_{root}.csv")
            path.unlink()
        else:
            kept = -1
        new = not (DATA / "reduced.csv").exists()
        with (DATA / "reduced.csv").open("a", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            if new:
                w.writerow(["request", "kept_rows", "raw_deleted"])
            w.writerow([tag, kept, kind == "statistics"])
        print(kind, root or "", p["start"], f"${usd:.4f}", kept, flush=True)
    print(f"spent ${spent:.4f}")


def check_inputs(prereg=None):
    import re
    text = Path(prereg or LANE / "PREREG.md").read_text(encoding="utf-8")
    pairs = re.findall(r"\|\s*`([^`]+)`\s*\|\s*([0-9a-f]{64})\s*\|", text)
    if not pairs:
        raise SystemExit("no input hashes in the PREREG")
    for path, digest in pairs:
        got = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        if got != digest:
            raise SystemExit(f"{path} changed since the freeze: {got} != {digest}")
    return pairs


# ---------- run ----------

def run():
    from lab.prereg import verify
    verify(LANE / "PREREG.md")
    check_inputs()
    cal, settle, ranks = load()
    vols = vol_series(cal, settle, ranks)
    res = LANE / "results"
    res.mkdir(parents=True, exist_ok=True)
    rep = {"rule": {"roots": ROOTS, "fee_usd": FEE_USD, "slip_ticks": SLIP_TICKS, "min_roots": MIN_ROOTS,
                    "min_days_to_expiry": MIN_DAYS_TO_EXPIRY, "vol_n": VOL_N, "nw_lag": NW_LAG},
           "calendar_days": len(cal), "settlements": len(settle)}
    prim, dec = build(cal, settle, ranks, vols=vols)
    rep["primary_1x"] = p1 = summarize(prim)
    rep["primary_2x"] = p2 = summarize(build(cal, settle, ranks, cost_k=2.0, vols=vols)[0])
    rep["primary_3x"] = summarize(build(cal, settle, ranks, cost_k=3.0, vols=vols)[0])
    rep["verdict"] = verdict_of(p1, p2)
    rep["by_year_1x"] = by_year(prim)
    rep["first_half_1x"] = summarize([r for r in prim if r["day"] < "2018-07-01"])
    rep["second_half_1x"] = summarize([r for r in prim if r["day"] >= "2018-07-01"])
    rep["since_2024_1x"] = summarize([r for r in prim if r["day"] >= "2024-01-01"])
    rep["by_root_gross_pct"], rep["by_sector_gross_pct"] = contributions(prim)
    books = [x for x in dec if x["book"]]

    def mean_(xs, f=statistics.mean, nd=2):
        xs = list(xs)
        return round(f(xs), nd) if xs else None

    rep["months"] = {"decisions": len(dec), "with_book": len(books),
                     "mean_valid_roots": mean_(x["valid"] for x in dec),
                     "skips": {k: sum(x["skipped"].get(k, 0) for x in dec) for k in
                               ("no_rank", "no_carry", "near_expiry", "no_entry_price", "no_vol")},
                     "mean_carry_spread_pct": mean_(x["carry_spread"] * 100 for x in books),
                     "holdings": sum(len(x["longs"]) + len(x["shorts"]) for x in books),
                     "holdings_under_60d_to_expiry": sum(x["under_60d"] for x in books),
                     "min_capital_usd_median": mean_((x["min_capital"] for x in books), statistics.median, 0),
                     "min_capital_usd_last": round(books[-1]["min_capital"]) if books else None,
                     "long_share": {r: mean_((r in x["longs"] for x in books), nd=3) for r in ROOTS},
                     "short_share": {r: mean_((r in x["shorts"] for x in books), nd=3) for r in ROOTS}}
    rep["equal_weight_1x"] = summarize(build(cal, settle, ranks, weighting="ew", vols=vols)[0])
    rep["k3_1x"] = summarize(build(cal, settle, ranks, k=3, vols=vols)[0])
    rep["no_lag_1x"] = summarize(build(cal, settle, ranks, lag=False, vols=vols)[0])
    rep["carry12_1x"] = summarize(build(cal, settle, ranks, signal="carry12", vols=vols)[0])
    with (res / "daily.csv").open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["day", "gross", "cost", "net"])
        for r in prim:
            w.writerow([r["day"], f"{r['gross']:.8f}", f"{r['cost']:.8f}", f"{r['net']:.8f}"])
    with (res / "months.csv").open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["decision", "entry", "valid", "book", "longs", "shorts", "carry_spread", "min_capital"])
        for x in dec:
            w.writerow([x["decision"], x["entry"], x["valid"], x["book"], " ".join(x.get("longs", [])),
                        " ".join(x.get("shorts", [])),
                        f"{x['carry_spread']:.5f}" if x["book"] else "", f"{x['min_capital']:.0f}" if x["book"] else ""])
    (res / "report.json").write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps({"verdict": rep["verdict"], "primary_1x": p1, "primary_2x": p2}, default=str))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("cost", "fetch", "run"))
    a = ap.parse_args(argv)
    return {"cost": cost, "fetch": fetch, "run": run}[a.cmd]()


if __name__ == "__main__":
    sys.exit(main() or 0)
