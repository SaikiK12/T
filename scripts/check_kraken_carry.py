"""Independently check saved R418 cash, funding ranges and displayed depth with rational arithmetic."""
from datetime import datetime
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
LANE=ROOT/"experiments/kraken_carry_v1"
SOURCE=ROOT/"research/intake/funding_notional_20261103/kraken_eea_20261106"


def read(path):
    return json.loads(path.read_text(),parse_float=str)


def epoch(s):
    return int(datetime.fromisoformat(s.replace("Z","+00:00")).timestamp())


def main():
    # No import of the Decimal implementation, loader or measurement runner.
    manifest=read(LANE/"inputs.json")["sha256"]
    for name,wanted in manifest.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=wanted:
            raise ValueError("input hash mismatch")
    frozen=hashlib.sha256((LANE/"PREREG.md").read_bytes()).hexdigest()
    if (LANE/"PREREG.sha256").read_text().strip()!=frozen:
        raise ValueError("PREREG changed")
    result=read(LANE/"results/report.json")
    if result["prereg_sha256"]!=frozen:
        raise ValueError("report belongs to another freeze")
    spec=read(LANE/"cases.json");bodies={}
    for filename in ["acquisition.json","gap_acquisition.json"]:
        for r in read(SOURCE/filename)["requests"]:
            body=gzip.decompress((SOURCE/r["body"]).read_bytes())
            if hashlib.sha256(body).hexdigest()!=r["sha256"]:
                raise ValueError("raw source hash mismatch")
            bodies[r["name"]]=json.loads(body,parse_float=str)
    count=0
    def equal(actual,expected):
        nonlocal count
        if abs(F(actual)-expected)>F(1,10**12):
            raise ValueError("saved result differs from independent rational ledger")
        count+=1
    start,end=epoch(spec["start"]),epoch(spec["end"])
    sf,pf,b=map(F,[spec["spot_taker"],spec["perp_taker"],spec["historical_slip_per_side"]])
    for r in result["historical_replays"]:
        key=r["instrument"];cfg=spec["instruments"][key];c=F(r["capital"]);m=r["cost_multiple"]
        instrument=next(i for i in bodies["kraken_instruments"]["instruments"] if i["symbol"]==cfg["perp"])
        lot=F(1,10**int(instrument["contractValueTradePrecision"]))
        spots={int(x[0]):F(x[1]) for x in bodies[f"kraken_{key}_spot"]["result"][cfg["spot"]]}
        trades={x["time"]//1000:F(x["open"]) for x in bodies[f"kraken_{key}_trade"]["candles"]}
        marks={x["time"]//1000:x for page in ["mark","mark_tail"] for x in bodies[f"kraken_{key}_{page}"]["candles"]}
        funds={epoch(x["timestamp"]):F(x["fundingRate"]) for x in bodies[f"kraken_{key}_funding"]["rates"]}
        q=(c/2/(spots[start]*(1+3*b)*(1+3*sf))/lot).__floor__()*lot
        equal(r["quantity"],q)
        sb,ss=spots[start]*(1+m*b),spots[end]*(1-m*b)
        fs,fb=trades[start]*(1-m*b),trades[end]*(1+m*b)
        cash_spot=c/2-q*sb*(1+sf*m);cash_perp=c/2-q*fs*pf*m
        fl,fu=F(0),F(0);minimum=None;cash_min=cash_perp;first=None;cash_first=None
        navs={x["t"]:x for x in r["daily_nav_interval"] if x["label"]=="daily open mark"}
        for t in range(start,end,3600):
            if t in funds:lo=hi=funds[t]
            else:
                envelope=bodies[f"kraken_{key}_funding_gap_index_{t}"]["candles"]
                hi=F(instrument["maxRelativeFundingRate"])*max(F(x["high"]) for x in envelope);lo=-hi
            usd=cash_perp+fl+min(0,q*lo)
            buffer=usd+q*(fs-F(marks[t]["high"]))-q*F(marks[t]["high"])*F(instrument["marginSchedules"]["europa"]["retail"][0]["maintenanceMargin"])
            minimum=buffer if minimum is None else min(minimum,buffer)
            cash_min=min(cash_min,usd)
            if buffer<=0 and first is None:first=t
            if usd<0 and cash_first is None:cash_first=t
            if t in navs:
                base=cash_spot+q*spots[t]+cash_perp+q*(fs-F(marks[t]["open"]))
                equal(navs[t]["lower"],base+fl);equal(navs[t]["upper"],base+fu)
            fl+=q*lo;fu+=q*hi
        fees=q*m*(sf*(sb+ss)+pf*(fs+fb))
        slip=q*m*b*(spots[start]+spots[end]+trades[start]+trades[end])
        basis=q*(spots[end]-spots[start]+trades[start]-trades[end])
        base=cash_spot+q*ss*(1-sf*m)+cash_perp+q*(fs-fb)-q*fb*pf*m-c
        for name,value in [("funding_lower",fl),("funding_upper",fu),("fees",fees),("slippage_assumption",slip),
                           ("basis_pnl",basis),("counterfactual_net_lower",base+fl),("counterfactual_net_upper",base+fu),
                           ("min_short_wallet_maintenance_buffer",minimum),("min_short_usd_cash_lower",cash_min),
                           ("annual_return_on_total_capital_lower",(base+fl)/c*F(365*86400,end-start)),
                           ("annual_return_on_total_capital_upper",(base+fu)/c*F(365*86400,end-start))]:equal(r[name],value)
        equal(base,basis-fees-slip)
        if first!=(r["possible_maintenance_breach"] or {}).get("t") or cash_first!=(r["possible_usd_cash_deficit"] or {}).get("t"):
            raise ValueError("margin/cash breach clock disagrees")
        count+=2
    def reference_sweep(book,side,q,m,fee):
        bids,asks=book["bids"],book["asks"]
        mid=(max(F(x[0]) for x in bids)+min(F(x[0]) for x in asks))/2
        levels={}
        for row in asks if side=="buy" else bids:
            p,size=F(row[0]),F(row[1]);levels[p]=levels.get(p,F(0))+size
        left=q;quote=F(0)
        for p,size in sorted(levels.items(),reverse=side=="sell"):
            take=min(left,size);quote+=take*(mid+m*(p-mid));left-=take
            if not left:break
        filled=q-left;drag=quote-filled*mid if side=="buy" else filled*mid-quote
        return filled,quote,quote*fee*m,drag
    for r in result["conditional_entry_snapshots"]:
        key=r["instrument"];cfg=spec["instruments"][key];q=F(r["quantity"]);m=r["cost_multiple"]
        spot=bodies[f"kraken_{key}_spot_depth"]["result"][cfg["spot"]]
        perp=bodies[f"kraken_{key}_perp_depth"]["orderBook"]
        instrument=next(i for i in bodies["kraken_instruments"]["instruments"] if i["symbol"]==cfg["perp"])
        lot=F(1,10**int(instrument["contractValueTradePrecision"]))
        mid=(max(F(x[0]) for x in spot["bids"])+min(F(x[0]) for x in spot["asks"]))/2
        equal(q,(F(r["capital"])/2/(mid*(1+3*b)*(1+3*sf))/lot).__floor__()*lot)
        drags=[]
        for name,book,side,fee in [("spot_buy",spot,"buy",sf),("perp_sell",perp,"sell",pf)]:
            filled,quote,charged,drag=reference_sweep(book,side,q,m,fee)
            for field,value in [("filled",filled),("quote",quote),("fee",charged),("book_cost",drag)]:equal(r[name][field],value)
            drags.append(drag+charged)
        if r["complete"]:equal(r["entry_friction"],sum(drags))
    check=dict(round="R418",checker="independent Fraction ledger, no Decimal kernel import",equalities=count,
               tolerance_usd="1e-12",verdict="PASS",report_sha256=hashlib.sha256((LANE/"results/report.json").read_bytes()).hexdigest())
    path=LANE/"results/check.json"
    with path.open("x") as handle:handle.write(json.dumps(check,indent=2)+"\n")
    print(json.dumps(check))


if __name__=="__main__":
    main()
