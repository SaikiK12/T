"""Independent Fraction/array audit of R372's frozen historical proxy receipts.

Checks the same fixed tickets and trade arithmetic; creates no new strategy,
fit, look or changed input. It never edits a frozen file or original result.
"""
import argparse
from fractions import Fraction as F
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.run_orb_family import digest, safe, verified_inputs  # noqa: E402

MIN = 60_000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw_bars(path):
    d = json.loads(path.read_text())["data"]
    return {t * 1000: {k: F(str(d[k][i])) for k in ("open", "high", "low", "close", "vol")}
            for i, t in enumerate(d["time"])}


def audit(root, lane, result_path):
    inputs, manifest, folder = verified_inputs(root, lane)
    calendar = json.loads(safe(root, inputs["calendar"]).read_text())
    payload = json.loads(result_path.read_text())
    require(payload["status"] == "COMPLETE_DIAGNOSTIC", "audit requires complete original accounts")
    require(payload["prereg_sha256"] == (lane / "PREREG.sha256").read_text().strip(), "result/spec mismatch")
    require(payload["input_manifest_sha256"] == digest(lane / "inputs.json"), "result/input mismatch")
    raw = json.loads((folder / "contract.json").read_text())["data"]
    if isinstance(raw, list):
        raw = next(x for x in raw if x["symbol"] == manifest["symbol"])
    size, step, tick, min_lots, max_lots = [F(str(raw[k])) for k in
                                          ("contractSize", "volUnit", "priceUnit", "minVol", "maxVol")]
    funding = []
    for p in sorted(folder.glob("funding_*.json")):
        funding.extend((r["settleTime"], F(str(r["fundingRate"])))
                       for r in json.loads(p.read_text())["data"]["resultList"])
    days = payload["result"]["days"]
    require([d["day"] for d in days] == calendar["calendar"], "calendar deletion/reordering")
    sessions = {s["day"]: s for s in calendar["sessions"]}
    equity = {k: F(2000) for k in payload["result"]["equity"]}
    trade_checks = ticket_checks = 0
    for day in days:
        s = sessions.get(day["day"])
        ticket = None
        if s:
            bars = raw_bars(folder / f'{s["day"]}_last.json')
            fair = raw_bars(folder / f'{s["day"]}_fair.json')
            a = s["open_ms"]
            opening = [bars[t] for t in range(a, a + 30 * MIN, MIN)]
            hi, lo = max(b["high"] for b in opening), min(b["low"] for b in opening)
            scan = np.arange(a + 30 * MIN, a + 119 * MIN, MIN, dtype=np.int64)
            fired = np.flatnonzero([bars[int(t)]["close"] > hi for t in scan])
            if len(fired):
                t = int(scan[fired[0]])
                prefix = [bars[k] for k in range(a, t + MIN, MIN)]
                v = sum(b["vol"] for b in prefix)
                vw = sum((b["high"] + b["low"] + b["close"]) * b["vol"] / 3 for b in prefix) / v
                mean_v = sum(b["vol"] for b in opening) / 30
                vwap_ok = bars[t]["close"] > vw
                vol_ok = bars[t]["vol"] >= F(3, 2) * mean_v
                ticket = dict(entry=t + 2 * MIN, stop=lo,
                              accept=dict(parent=True, vwap=vwap_ok, volume=vol_ok, joint=vwap_ok and vol_ok))
                d = day["decision"]
                require(d["status"] == "ticket" and d["decision_ms"] == t + MIN and d["entry_ms"] == ticket["entry"],
                        "first-parent/latency discrepancy")
                require(d["accept"] == ticket["accept"] and F(str(d["stop"])) == lo, "filter/stop discrepancy")
                ticket_checks += 1
            else:
                require(day["decision"]["status"] == "cash", "invented parent ticket")
        else:
            require(day["decision"]["reason"] == "calendar_closed", "weekend cash discrepancy")
        for key, record in day["accounts"].items():
            arm, scale_text = key.rsplit("_", 1)
            scale = int(scale_text[:-1])
            if ticket is None or not ticket["accept"][arm]:
                require(record["status"] == "cash" and record["pnl"] == 0, "rejected ticket not cash")
                continue
            start, end = ticket["entry"], s["close_ms"] + MIN
            if bars[start]["open"] <= ticket["stop"]:
                require(record["status"] == "cash" and record["pnl"] == 0, "entry-gap refusal discrepancy")
                continue
            times = np.arange(start, end, MIN, dtype=np.int64)
            hits = np.flatnonzero([bars[int(t)]["low"] <= ticket["stop"] for t in times])
            raw_exit = bars[end]["open"]
            if len(hits):
                end = int(times[hits[0]]) + MIN
                raw_exit = min(ticket["stop"], bars[end]["open"])
            slip, fee = F(scale, 5000), F(scale, 1250)
            e = ((bars[start]["open"] * (1 + slip)) / tick).__ceil__() * tick
            x = ((raw_exit * (1 - slip)) / tick).__floor__() * tick
            budget = min(F(1000), equity[key] / (1 + 2 * fee))
            lots = min((budget / (e * size) / step).__floor__() * step,
                       (max_lots / step).__floor__() * step)
            if lots < min_lots:
                require(record["status"] == "cash" and record["pnl"] == 0, "lot refusal discrepancy")
                continue
            q = lots * size
            require(not any(t in (start, end) for t, r in funding), "ambiguous funding boundary")
            paid = sum(q * fair[t]["open"] * rate for t, rate in funding if start < t < end)
            pnl = q * (x - e) - q * (x + e) * fee - paid
            require(record["status"] == "trade", "selected trade status discrepancy")
            for label, expected in [("lots", lots), ("entry", e), ("exit", x), ("funding", paid), ("pnl", pnl)]:
                require(abs(float(expected) - record[label]) < 1e-8, f"rational {label} discrepancy {day['day']} {key}")
            equity[key] += pnl
            require(abs(float(equity[key]) - record["equity_after"]) < 1e-8, "capital continuity discrepancy")
            trade_checks += 1
    for key, value in equity.items():
        require(abs(float(value) - payload["result"]["equity"][key]) < 1e-8, "terminal cash discrepancy")
    verified_inputs(root, lane)
    return dict(status="PASS", result_sha256=digest(result_path), ticket_checks=ticket_checks,
                trade_account_checks=trade_checks, exact_rational_terminal_equity={k:str(v) for k,v in equity.items()},
                scope="same frozen conditional model only; no market authenticity, fills, inference or new trials")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lane", required=True)
    ap.add_argument("--result", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    report = audit(ROOT, safe(ROOT, a.lane), safe(ROOT, a.result))
    with safe(ROOT, a.out).open("x") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
