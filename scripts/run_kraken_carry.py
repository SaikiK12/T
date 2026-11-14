"""R418: sole offline Kraken EEA funding/capital/cost screen, with public-source gaps explicit."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab import prereg, registry  # noqa: E402
from lab.carry_execution import Book, number, sweep  # noqa: E402
from lab.kraken_carry import fixed_quantity, funding_intervals, replay  # noqa: E402

LANE = ROOT / "experiments/kraken_carry_v1"
SOURCE = ROOT / "research/intake/funding_notional_20261103/kraken_eea_20261106"
D = Decimal


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify_inputs():
    sha = prereg.verify(LANE / "PREREG.md")
    p = LANE / "inputs.json"
    rel = p.relative_to(ROOT).as_posix()
    if f"{digest(p)}  {rel}" not in (LANE / "PREREG.md").read_text():
        raise ValueError("manifest is not the frozen manifest")
    inputs = json.loads(p.read_text())["sha256"]
    for name, wanted in inputs.items():
        path = ROOT / name
        if not path.resolve().is_relative_to(ROOT) or digest(path) != wanted:
            raise ValueError("input hash mismatch: " + name)
    for name in [*inputs, rel, "experiments/kraken_carry_v1/PREREG.md", "experiments/kraken_carry_v1/PREREG.sha256"]:
        committed = subprocess.run(["git", "show", "HEAD:"+name], cwd=ROOT, check=True, capture_output=True).stdout
        if committed != (ROOT / name).read_bytes():
            raise ValueError("uncommitted input: " + name)
    return sha


def read_bodies():
    bodies, receipts = {}, {}
    for filename in ["acquisition.json", "gap_acquisition.json"]:
        for r in json.loads((SOURCE / filename).read_text())["requests"]:
            if r.get("status") != 200 or r.get("error") or not r.get("body"):
                raise ValueError("unsuccessful raw input")
            p = SOURCE / r["body"]
            if p.parent != SOURCE:
                raise ValueError("unexpected raw input path")
            raw = gzip.decompress(p.read_bytes())
            if hashlib.sha256(raw).hexdigest() != r["sha256"]:
                raise ValueError("raw response hash mismatch")
            if r["name"] in bodies:
                raise ValueError("duplicate input name")
            bodies[r["name"]] = json.loads(raw, parse_float=D)
            receipts[r["name"]] = r
    return bodies, receipts


def epoch(iso):
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def unique(rows, field, scale=1):
    result = {}
    for r in rows:
        t = int(r[field]) // scale
        if t in result:
            raise ValueError("duplicate source timestamp")
        result[t] = r
    return result


def book(payload, *, spot_pair=None):
    if spot_pair:
        if payload.get("error") != []:
            raise ValueError("spot envelope")
        payload = payload["result"][spot_pair]
    else:
        if payload.get("result") != "success":
            raise ValueError("derivative envelope")
        payload = payload["orderBook"]
    sides = {}
    for side in ["bids", "asks"]:
        levels = {}
        for row in payload[side]:
            p, q = number(row[0], positive=True), number(row[1], positive=True)
            levels[p] = levels.get(p, D(0)) + q
        sides[side] = sorted(levels.items(), reverse=side == "bids")
    return Book(**sides)


def qualify(key, cfg, bodies, spec):
    sym, pair = cfg["perp"], cfg["spot"]
    metadata = bodies["kraken_instruments"]
    if metadata.get("result") != "success":
        raise ValueError("instrument envelope")
    instrument, = [i for i in metadata["instruments"] if i["symbol"] == sym]
    if (instrument["type"], instrument["base"], instrument["quote"], instrument["contractSize"]) != (
            "flexible_futures", cfg["base"], "USD", 1) or not instrument["tradeable"]:
        raise ValueError("linear USD contract identity")
    a = instrument["marginSchedules"]["europa"]["retail"]
    if a != instrument["marginSchedules"]["europa_crypto"]["retail"] or a[0]["numNonContractUnits"] != 0:
        raise ValueError("EEA retail schedule ambiguity")
    lot = D(10) ** -instrument["contractValueTradePrecision"]
    pairs = bodies["kraken_spot_pairs"]
    if pairs.get("error") != []:
        raise ValueError("spot metadata envelope")
    spot_meta = pairs["result"][pair]
    if spot_meta["quote"] != "ZUSD" or spot_meta["status"] != "online" or spot_meta["lot_multiplier"] != 1:
        raise ValueError("USD spot identity/status")
    lot = max(lot, D(10) ** -spot_meta["lot_decimals"])
    bars = bodies[f"kraken_{key}_spot"]
    if bars.get("error") != []:
        raise ValueError("spot OHLC envelope")
    spot = {}
    for r in bars["result"][pair]:
        if int(r[0]) in spot:
            raise ValueError("duplicate spot day")
        spot[int(r[0])] = number(r[1], positive=True)
    traded = bodies[f"kraken_{key}_trade"]
    if traded["more_candles"]:
        raise ValueError("unfinished daily trade pagination")
    trade = {t:number(r["open"], positive=True) for t,r in unique(traded["candles"], "time", 1000).items()}
    mark_rows = bodies[f"kraken_{key}_mark"]["candles"] + bodies[f"kraken_{key}_mark_tail"]["candles"]
    if bodies[f"kraken_{key}_mark_tail"]["more_candles"]:
        raise ValueError("unfinished mark pagination")
    marks = unique(mark_rows, "time", 1000)
    rates = bodies[f"kraken_{key}_funding"]
    if rates.get("result") != "success":
        raise ValueError("funding envelope")
    observed = {}
    for r in rates["rates"]:
        t = epoch(r["timestamp"])
        if t in observed:
            raise ValueError("duplicate funding hour")
        observed[t] = number(r["fundingRate"])
    start, end = epoch(spec["start"]), epoch(spec["end"])
    envelopes = {}
    for t in set(range(start, end, 3600)) - observed.keys():
        patch = bodies[f"kraken_{key}_funding_gap_index_{t}"]
        indexed = unique(patch["candles"], "time", 1000)
        if patch["more_candles"] or set(indexed) != {t-3600,t,t+3600}:
            raise ValueError("missing index envelope for funding cap scenario")
        envelopes[t] = max(number(r["high"], positive=True) for r in indexed.values())
    funding = funding_intervals(start, end, observed, envelopes, instrument["maxRelativeFundingRate"])
    return dict(start=start, end=end, lot=lot, spot=spot, trade=trade, marks=marks, funding=funding,
                initial_margin=a[0]["initialMargin"], maintenance_margin=a[0]["maintenanceMargin"],
                tier_ceiling=a[1]["numNonContractUnits"]), spot_meta


def measure(spec):
    bodies, receipts = read_bodies()
    results, quotes = [], []
    for key, cfg in spec["instruments"].items():
        inputs, spot_meta = qualify(key, cfg, bodies, spec)
        for capital in spec["capitals"]:
            for multiple in (1,2,3):
                row = replay(**inputs, capital=capital, spot_fee=spec["spot_taker"], perp_fee=spec["perp_taker"],
                             slip=spec["historical_slip_per_side"], multiple=multiple)
                if row["quantity"] < number(spot_meta["ordermin"], positive=True):
                    raise ValueError("spot minimum quantity")
                results.append(dict(instrument=key, **row))
        sb = book(bodies[f"kraken_{key}_spot_depth"], spot_pair=cfg["spot"])
        pb = book(bodies[f"kraken_{key}_perp_depth"])
        skew = abs(receipts[f"kraken_{key}_spot_depth"]["received_mono_ns"] -
                   receipts[f"kraken_{key}_perp_depth"]["received_mono_ns"])/1e6
        for capital in spec["capitals"]:
            q = fixed_quantity(capital, sb.mid, inputs["lot"], spec["spot_taker"], spec["historical_slip_per_side"])
            for m in (1,2,3):
                buy, sell = sweep(sb, "buy", q, fee_rate=spec["spot_taker"], multiple=m), sweep(pb, "sell", q, fee_rate=spec["perp_taker"], multiple=m)
                complete = buy["complete"] and sell["complete"]
                if buy["quote"] < number(spot_meta["costmin"], positive=True):
                    raise ValueError("spot quote minimum")
                spot_cash = D(capital)/2-buy["quote"]-buy["fee"]
                short_buffer = D(capital)/2-sell["fee"]-sell["book_cost"]-q*pb.mid*number(inputs["initial_margin"], positive=True)
                quotes.append(dict(instrument=key, capital=capital, cost_multiple=m, quantity=q,
                                   spot_buy=buy, perp_sell=sell, receive_skew_ms=skew,
                                   complete=complete, unmatched=buy["filled"]-sell["filled"],
                                   spot_cash_after_entry=spot_cash, short_initial_margin_buffer_at_mid=short_buffer,
                                   funded_at_mid=complete and spot_cash>=0 and short_buffer>=0,
                                   entry_friction=None if not complete else buy["book_cost"]+sell["book_cost"]+buy["fee"]+sell["fee"],
                                   future_exit_known=False, capacity_now=None))
    candidates = []
    for key in spec["instruments"]:
        for capital in spec["capitals"]:
            rows = [r for r in results if r["instrument"]==key and str(r["capital"])==capital]
            one, three = [next(r for r in rows if r["cost_multiple"]==m) for m in [1,3]]
            passes = (all(r["margin_screen_clear"] for r in rows) and
                      one["annual_return_on_total_capital_lower"] > D(spec["annual_hurdle_assumption"]) and
                      three["annual_return_on_total_capital_lower"] > 0)
            candidates.append(dict(instrument=key, capital=capital,
                                   verdict="MODEL_CANDIDATE_EXECUTION_UNPROVEN" if passes else "DOES_NOT_CLEAR_FROZEN_SCREEN"))
    return dict(round="R418", predictive_trials=2, program_trials=registry.program_trials(ROOT/"registry/rounds.csv"),
                gate=0, source="latest-vintage public archives, exploratory; no unseen-sample claim",
                executable_net=None, owner_access_confirmed=False, prospective_days=0,
                historical_replays=results, conditional_entry_snapshots=quotes, screen=candidates)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    frozen=verify_inputs()
    out=LANE/"results"
    out.mkdir(exist_ok=False)
    started=datetime.now(timezone.utc).isoformat()
    result=measure(json.loads((LANE/"cases.json").read_text()))
    verify_inputs()
    result.update(prereg_sha256=frozen, started_utc=started, completed_utc=datetime.now(timezone.utc).isoformat())
    (out/"report.json").write_text(json.dumps(result,default=str,indent=2)+"\n")
    print(json.dumps(dict(round="R418",start=started,completed=result["completed_utc"],replays=len(result["historical_replays"]),quotes=len(result["conditional_entry_snapshots"]))))


if __name__=="__main__":
    main()
