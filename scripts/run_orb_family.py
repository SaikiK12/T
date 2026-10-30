"""Run one frozen four-arm ORB pilot with exact code/data byte verification.

Use --lane experiments/orb_index_v1 --run-id <unused-name>. The runner has no
network client, optimizer or order endpoint. A completed diagnostic is not alpha.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg, registry  # noqa: E402
from lab.orb_family import Bar, Contract, Funding, Session, run_family  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe(root, name):
    rel = PurePosixPath(name)
    if rel.is_absolute() or ".." in rel.parts or "\\" in name:
        raise ValueError("unsafe input path")
    p = root / name
    if any((root / Path(*rel.parts[:i])).is_symlink() for i in range(1, len(rel.parts) + 1)):
        raise ValueError("symlink input")
    p.resolve().relative_to(root.resolve())
    return p


def verified_inputs(root, lane):
    sha = prereg.verify(lane / "PREREG.md")
    text = (lane / "PREREG.md").read_text()
    expected = re.search(r"^- \*\*Inputs manifest SHA-256:\*\* ([0-9a-f]{64})$", text, re.M)
    if not expected or digest(lane / "inputs.json") != expected[1]:
        raise ValueError("inputs manifest is not bound by frozen PREREG")
    inputs = json.loads((lane / "inputs.json").read_text())
    for name, want in inputs["code_and_policy"].items():
        if digest(safe(root, name)) != want:
            raise ValueError("frozen input drift: " + name)
    for required in ("lab/orb_family.py", "scripts/run_orb_family.py", "scripts/fetch_orb_pilot.py",
                     inputs["calendar"], inputs["data_manifest"]):
        if required not in inputs["code_and_policy"]:
            raise ValueError("required direct input is not frozen: " + required)
    spec_id = re.search(r"^- \*\*Registry id:\*\* (R[0-9]+)$", text, re.M)
    rows = registry.rows(root / "registry/rounds.csv")
    row = next((r for r in rows if spec_id and r["id"] == spec_id[1]), None)
    if row is None or row["prereg_sha"] != sha or int(row["trials"]) != 12:
        raise ValueError("registered identity/hash/trial count mismatch")
    manifest = json.loads(safe(root, inputs["data_manifest"]).read_text())
    folder = safe(root, manifest["folder"])
    expected_files = {r["path"]: r for r in manifest["file_hashes"]}
    if len(expected_files) != len(manifest["file_hashes"]):
        raise ValueError("duplicate data path")
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
    if actual != set(expected_files):
        raise ValueError("data file set differs from sealed manifest")
    for name, rec in expected_files.items():
        p = safe(folder, name)
        if p.stat().st_size != rec["bytes"] or digest(p) != rec["sha256"]:
            raise ValueError("data byte drift: " + name)
    return inputs, manifest, folder


def parse_bars(body):
    if body.get("success") is not True or not isinstance(body.get("data"), dict):
        raise ValueError("unsuccessful/malformed bar response")
    d = body["data"]
    keys = ("time", "open", "high", "low", "close", "vol")
    if any(not isinstance(d.get(k), list) for k in keys) or len({len(d[k]) for k in keys}) != 1:
        raise ValueError("bar response arrays differ or are absent")
    bars = []
    for t, o, h, l, c, v in zip(*(d[k] for k in keys)):
        if type(t) is not int or any(isinstance(x, bool) for x in (o, h, l, c, v)):
            raise ValueError("invalid raw bar type")
        bars.append(Bar(t * 1000, float(o), float(h), float(l), float(c), float(v)))
    if any(a.t >= b.t for a, b in zip(bars, bars[1:])):
        raise ValueError("unordered/duplicate provider bars")
    return bars


def load_data(folder, calendar, symbol):
    last, fair = [], []
    for s in calendar["sessions"]:
        for kind, target in (("last", last), ("fair", fair)):
            bars = parse_bars(json.loads((folder / f'{s["day"]}_{kind}.json').read_text()))
            if any(not s["open_ms"] <= b.t <= s["close_ms"] + 60_000 for b in bars):
                raise ValueError("bar outside exact request window")
            target.extend(bars)
    funding = []
    previous = None
    for page, p in enumerate(sorted(folder.glob("funding_*.json")), 1):
        body = json.loads(p.read_text())
        d = body.get("data", {})
        if body.get("success") is not True or d.get("currentPage") != page:
            raise ValueError("funding response/page identity")
        for row in d["resultList"]:
            t = row["settleTime"]
            if row.get("symbol") != symbol or type(t) is not int or isinstance(row["fundingRate"], bool):
                raise ValueError("funding identity/unit field invalid")
            if previous is not None and t >= previous:
                raise ValueError("funding ordering/duplicate failure")
            previous = t
            funding.append(Funding(t, float(row["fundingRate"])))
    if not funding or funding[-1].t >= calendar["sessions"][0]["open_ms"]:
        raise ValueError("funding history does not reach before requested window")
    if funding[0].t <= calendar["sessions"][-1]["close_ms"] + 60_000:
        raise ValueError("funding history does not bracket end")
    detail = json.loads((folder / "contract.json").read_text())["data"]
    if isinstance(detail, list):
        detail = next(d for d in detail if d["symbol"] == symbol)
    if detail["symbol"] != symbol or detail.get("type") != 2:
        raise ValueError("wrong contract")
    if any(isinstance(detail[k], bool) for k in ("contractSize", "volUnit", "minVol", "maxVol", "priceUnit")):
        raise ValueError("invalid raw contract units")
    contract = Contract(*(float(detail[k]) for k in ("contractSize", "volUnit", "minVol", "maxVol", "priceUnit")))
    return last, fair, sorted(funding, key=lambda f: f.t), contract


def summarize(result):
    summary = {}
    for key, equity in result["equity"].items():
        records = [d["accounts"][key] for d in result["days"]]
        trades = [r for r in records if r["status"] == "trade"]
        turnover = sum(r["raw_turnover"] for r in trades)
        summary[key] = dict(known_days=sum(r["pnl"] is not None for r in records),
                            trades=sum(r["status"] == "trade" for r in records),
                            pnl=None if equity is None else equity - result["initial_equity_each"],
                            mean_bp_calendar_day=None if equity is None else
                            (equity / result["initial_equity_each"] - 1) * 10000 / len(records),
                            break_even_total_cost_bp_per_side=None if equity is None or turnover == 0 else
                            sum(r["gross_before_costs"] - r["funding"] for r in trades) / turnover * 10000)
    pairs = (("vwap", "parent"), ("volume", "parent"), ("joint", "parent"),
             ("joint", "vwap"), ("joint", "volume"))
    comparisons = {}
    for a, b in pairs:
        x, y = result["equity"][a + "_2x"], result["equity"][b + "_2x"]
        comparisons[a + "_minus_" + b] = None if not result["complete"] else x - y
    return dict(accounts=summary, paired_2x_dollars=comparisons, gate_eligible=False,
                inference="Descriptive pilot only; no p-value, winner selection or program-wide error control.")


@contextmanager
def lane_lock(lane):
    p = lane / ".orb_run.lock"
    with p.open("x"):
        pass
    try:
        yield
    finally:
        p.unlink()


def run(root, lane, run_id):
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", run_id):
        raise ValueError("invalid run id")
    with lane_lock(lane):
        inputs, manifest, folder = verified_inputs(root, lane)
        output = lane / "runs" / run_id
        if output.exists():
            raise ValueError("run destination exists; outcomes are never overwritten")
        calendar = json.loads(safe(root, inputs["calendar"]).read_text())
        bars, fair, funding, contract = load_data(folder, calendar, manifest["symbol"])
        result = run_family(bars, fair, funding, [Session(**s) for s in calendar["sessions"]],
                            calendar["calendar"], contract, closed_days=calendar["closed_days"])
        payload = dict(status="COMPLETE_DIAGNOSTIC" if result["complete"] else "BLOCKED_INCOMPLETE_ACCOUNT",
                       result=result, summary=summarize(result),
                       prereg_sha256=prereg.verify(lane / "PREREG.md"),
                       input_manifest_sha256=digest(lane / "inputs.json"),
                       program_trials=registry.program_trials(root / "registry/rounds.csv"))
        verified_inputs(root, lane)  # data/code/policy unchanged before publishing outcomes
        output.mkdir(parents=True, exist_ok=False)
        with (output / "result.json").open("x") as f:
            json.dump(payload, f, indent=2, allow_nan=False)
            f.write("\n")
        print(json.dumps(dict(status=payload["status"], summary=payload["summary"]), indent=2, allow_nan=False))
        return payload


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lane", required=True)
    ap.add_argument("--run-id", required=True)
    a = ap.parse_args()
    run(ROOT, safe(ROOT, a.lane), a.run_id)


if __name__ == "__main__":
    main()
