"""R315 fixed fair-value snapshot diagnostic; no orders or strategy scoring.

Reuse frozen R314 bounded metadata/WS/depth/cost components. Dedicated fair
replies retain their own system timestamp and receipt, never an effective-price
or account-settlement attestation. One capture directory, no retry/reset.
"""
import argparse
import asyncio
from collections import Counter
import fcntl
import gzip
import hashlib
import json
import multiprocessing
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from lab.depth_replay import DepthReplay  # noqa:E402
from lab.funding_values import mexc_rest_fair, paired_values, streamed_value  # noqa:E402
from lab.stream_quotes import FrameClock, NS, SYMBOLS  # noqa:E402
from scripts import probe_depth_quotes as depth  # noqa:E402

LANE = ROOT/"experiments/funding_values_v1"
GRIDS = (10,20,30,40,50,60)
FAIR_BODY_BYTES, FAIR_REQUESTS, FAIR_TIMEOUT = 4096,36,3.
STOP_HTTP = (401,403,429,451,503)
sha,write = depth.sha,depth.write


def verify(lane=LANE):
    depth.verify(lane)


def fair_request(record,out,*,worker=depth.metadata_worker,seconds=FAIR_TIMEOUT):
    """One owned deadline-limited GET, fixed4096-byte reservation per slot."""
    if time.monotonic_ns() >= record.get("read_window_end_mono_ns",2**63):
        record["error"]="request_start_window_expired"
        return record
    record.update(attempted=True,started_utc_ns=time.time_ns(),started_mono_ns=time.monotonic_ns(),error=None)
    deadline = time.monotonic()+seconds
    ctx = multiprocessing.get_context("spawn")
    receiver,sender = ctx.Pipe(duplex=False)
    child = ctx.Process(target=worker,args=(record["url"],sender,FAIR_BODY_BYTES,seconds),daemon=True)
    chunks,total,complete = [],0,False
    received_clock=None
    try:
        child.start();sender.close()
        while time.monotonic() < deadline:
            if not receiver.poll(max(0,deadline-time.monotonic())):
                break
            try:kind,value = receiver.recv()
            except EOFError:break
            if kind == "status":record["http_status"] = value
            elif kind == "chunk":
                if not isinstance(value,bytes) or len(value) > FAIR_BODY_BYTES-total:
                    raise ValueError("fair worker exceeded declared body cap")
                chunks.append(value);total += len(value)
            elif kind == "done":
                complete=True
                received_clock=FrameClock(time.time_ns(),time.monotonic_ns())
                break
            elif kind == "error":raise ValueError(value)
            else:raise ValueError("unknown worker message")
        if not complete:raise TimeoutError("absolute fair request wall deadline or premature worker exit")
        if total == FAIR_BODY_BYTES or not 200 <= record.get("http_status",0) < 300:
            raise ValueError("failed or possibly truncated fair response")
        json.loads(b"".join(chunks))  # schema is checked only after sealing
    except Exception as exc:
        record["error"] = type(exc).__name__+": "+str(exc)
        if received_clock is None:received_clock=FrameClock(time.time_ns(),time.monotonic_ns())
    finally:
        if child.pid is not None:
            if child.is_alive():child.terminate()
            child.join(.2)
            if child.is_alive():child.kill();child.join(.2)
        receiver.close();sender.close()
    body = b"".join(chunks)
    record.update(received_utc_ns=received_clock.utc_ns,received_mono_ns=received_clock.mono_ns,
        worker_cleanup_finished_mono_ns=time.monotonic_ns(),bytes=len(body),
        body_read_upper_bound=len(body) if complete else FAIR_BODY_BYTES,sha256=hashlib.sha256(body).hexdigest())
    (out/record["body"]).write_bytes(gzip.compress(body,mtime=0))
    return record


class FairSchedule:
    def __init__(self,out,anchor):
        self.out,self.anchor = out,anchor
        self.records = [{"name":f"fair_{g}_{s}","body":f"fair_{g}_{s}.json.gz","symbol":s,"grid_second":g,
            "scheduled_mono_ns":anchor.mono_ns+(g-1)*NS,"attempted":False,"bytes":0,"body_read_upper_bound":0,
            "read_window_end_mono_ns":anchor.mono_ns+65*NS,
            "error":"slot_not_started","url":depth.old.MX_HTTP+"/fair_price/"+s+"_USDT"}
            for g in GRIDS for s in SYMBOLS]

    async def run(self):
        for g in GRIDS:
            await asyncio.sleep(max(0,(self.anchor.mono_ns+(g-1)*NS-time.monotonic_ns())/NS))
            if time.monotonic_ns() >= self.anchor.mono_ns+65*NS:
                break
            # Exactly six independent pre-reserved4KiB slots; no shared counter
            # can grant concurrent workers an extra request or unknown body tail.
            await asyncio.gather(*(asyncio.to_thread(fair_request,r,self.out) for r in self.records if r["grid_second"] == g))
            if any(r.get("http_status") in STOP_HTTP for r in self.records if r["attempted"]):
                for r in self.records:
                    if not r["attempted"]:r["error"]="skipped_after_server_backoff_or_access_denial"
                break  # no inferred Retry-After expiry; already dispatched slots may complete


def capture(lane=LANE):
    verify(lane);out=lane/"evidence";out.mkdir()
    begin=time.monotonic();network=depth.Metadata(out)
    meta,names,errors,connections = {},{},[],{}
    schedule=None
    depth.old.LT_LOCK.parent.mkdir(parents=True,exist_ok=True)
    with depth.old.LT_LOCK.open("a") as lock:
        locked=False
        try:
            while time.monotonic()-begin < 10:
                try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);locked=True;break
                except BlockingIOError:time.sleep(.05)
            if not locked:raise depth.old.BudgetStop("existing public API writer held lock")
            network.start=time.monotonic()
            listing=network.get("lighter_metadata",depth.old.LT_HTTP+"/orderBookDetails?filter=perp")
            if network.records[-1].get("http_status") in STOP_HTTP:
                raise depth.old.BudgetStop("metadata server backoff/access stop; no further GETs")
            for s in SYMBOLS:
                try:
                    m=network.get(s+"_mexc_metadata",depth.old.MX_HTTP+"/detail?symbol="+s+"_USDT")
                    if network.records[-1].get("http_status") in STOP_HTTP:
                        raise depth.old.BudgetStop("metadata server backoff/access stop; no further GETs")
                    if not m or m.get("success") is not True or not listing or listing.get("code") != 200:
                        raise ValueError("metadata_failed")
                    mm=m["data"]
                    if isinstance(mm,list):mm,=[x for x in mm if x["symbol"] == s+"_USDT"]
                    lm,=[x for x in listing["order_book_details"] if x["symbol"] == s and x["market_type"] == "perp"]
                    if mm["symbol"] != s+"_USDT":raise ValueError("MEXC identity mismatch")
                    meta[s]={"mexc":mm,"lighter":lm};names[int(lm["market_id"])]=s
                except (ValueError,KeyError,TypeError,depth.old.BudgetStop) as exc:
                    errors.append(s+":"+type(exc).__name__+":"+str(exc))
                    if isinstance(exc,depth.old.BudgetStop):raise
            write(out/"metadata.json",{"symbols":list(SYMBOLS),"metadata":meta,"names":names,"errors":errors})
            anchor=FrameClock(time.time_ns(),time.monotonic_ns());write(out/"anchor.json",vars(anchor))
            schedule=FairSchedule(out,anchor)
            mx=[{"method":k,"param":{"symbol":s+"_USDT",**({"limit":5} if k == "sub.depth.full" else {})}}
                for s in SYMBOLS if s in meta for k in ("sub.depth.full","sub.fair.price")]
            lt=[{"type":"subscribe","channel":f"{k}/{m}"} for m in sorted(names) for k in ("order_book","market_stats")]
            connections={v:{} for v in ("mexc","lighter")}
            async def both():
                await asyncio.wait_for(asyncio.gather(depth.stream("mexc",mx,out,anchor,connections["mexc"]),
                    depth.stream("lighter",lt,out,anchor,connections["lighter"]),schedule.run()),
                    timeout=min(75.,max(.001,120-(time.monotonic()-begin))))
            asyncio.run(both())
        except Exception as exc:errors.append(type(exc).__name__+": "+str(exc))
        finally:
            write(out/"connections.json",connections)
            write(out/"fair_receipts.json",{"records":schedule.records if schedule else []})
            write(out/"receipts.json",{"records":network.records,"requests":len(network.records),
                "response_bytes":network.total,"response_body_read_upper_bound":network.read_upper_bound,
                "duration_seconds":time.monotonic()-begin,"errors":errors})
            if locked:fcntl.flock(lock,fcntl.LOCK_UN)
    return out


def seal(lane=LANE):
    return depth.seal(lane)


def read_fairs(lane,anchor):
    path=lane/"evidence/fair_receipts.json"
    records=json.loads(path.read_text())["records"] if path.exists() else []
    if records and {(r["symbol"],r["grid_second"]) for r in records} != {(s,g) for s in SYMBOLS for g in GRIDS}:
        raise ValueError("fair schedule inventory mismatch")
    if len(records) not in (0,FAIR_REQUESTS):raise ValueError("unexpected fair request slots")
    if sum(r["attempted"] for r in records) > FAIR_REQUESTS or sum(r["body_read_upper_bound"] for r in records) > FAIR_REQUESTS*FAIR_BODY_BYTES:
        raise ValueError("fair request/body-read cap exceeded")
    out=[]
    for r in records:
        if not r["attempted"]:
            if r["bytes"] or r["body_read_upper_bound"]:raise ValueError("unattempted fair slot charged bytes")
            continue
        if r["scheduled_mono_ns"] != anchor.mono_ns+(r["grid_second"]-1)*NS:
            raise ValueError("changed fair schedule")
        if not r["scheduled_mono_ns"] <= r["started_mono_ns"] <= r["received_mono_ns"]:
            raise ValueError("fair request receipt clocks")
        if not r["started_mono_ns"] < anchor.mono_ns+65*NS or r["received_mono_ns"] > r["worker_cleanup_finished_mono_ns"]:
            raise ValueError("fair start/cleanup boundary")
        raw=gzip.decompress((lane/"evidence"/r["body"]).read_bytes())
        if len(raw) != r["bytes"] or hashlib.sha256(raw).hexdigest() != r["sha256"] or not len(raw) <= r["body_read_upper_bound"] <= FAIR_BODY_BYTES:
            raise ValueError("fair raw receipt/budget drift")
        clock=FrameClock(r["received_utc_ns"],r["received_mono_ns"])
        try:
            if r["error"]:raise ValueError(r["error"])
            packet=mexc_rest_fair(json.loads(raw),r["symbol"],clock,r["body"])
            if packet.source_time_ns > clock.utc_ns+100_000_000:raise ValueError("fair system clock ahead of receipt")
        except (ValueError,KeyError,TypeError,AttributeError) as exc:
            packet=None;r={**r,"decode_error":str(exc)}
        out.append((r,packet))
    return out


def rows_for(replay,fairs):
    rows=[]
    for g in GRIDS:
        quantities={}
        for delay in (0,300):
            for s in SYMBOLS:
                target=replay.anchor.mono_ns+g*NS+delay*1_000_000
                row,books=replay.observe(s,target,quantities.get(s),allow_new_quantity=(delay == 0))
                if delay == 0:quantities[s]=row["quantity_base"]
                for profile in ("WS_change","REST_system"):
                    mx=streamed_value(replay.latest.get(("mexc","reference",s)))
                    lt=streamed_value(replay.latest.get(("lighter","reference",s)))
                    selected=None
                    if profile == "REST_system":
                        selected=next(((r,p) for r,p in sorted(fairs,key=lambda x:x[0]["received_mono_ns"],reverse=True)
                            if r["symbol"] == s and r["received_mono_ns"] <= target),None)
                        mx=selected[1] if selected else None
                    values=paired_values((mx,lt),row["quantity_base"],books,target,replay.anchor)
                    if row["book_flags"]:values["products"]=None
                    rows.append({**row,"grid_second":g,"access_delay_ms":delay,"value_profile":profile,
                        "value_evidence":values,"rest_source_receipt":selected[0]["body"] if selected else None,
                        "cash_ledger_status":"unscored: no funding-event-bound value, units, asset or exposure evidence"})
    return rows


def report(lane=LANE,out=None):
    frames,mapping,anchor,connections=depth.load_capture(lane)
    fairs=read_fairs(lane,anchor)
    replay=DepthReplay(frames,mapping["metadata"],{int(k):v for k,v in mapping["names"].items()},anchor,connections)
    rows=rows_for(replay,fairs)
    out=Path(out) if out is not None else lane;out.mkdir(exist_ok=True)
    encoded="".join(json.dumps(r,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n" for r in rows).encode()
    depth.immutable(out/"observations.jsonl.gz",gzip.compress(encoded,mtime=0))
    summary={"registry_id":"R315","rows":len(rows),"predictive_trials":0,"cash_confirmed":0,"paper_days":0,
        "evidence_manifest_sha256":sha(lane/"evidence_inputs.json"),"observations_sha256":sha(out/"observations.jsonl.gz"),
        "scope":"source-publication/quote-cost availability and conditional one-bp sensitivities; no settled cash or return inference",
        "capital_usd":10000,"capital_per_venue_usd":5000,"charge_reserve_bp":[10,4],"pairs":[]}
    for s in SYMBOLS:
        for delay in (0,300):
            for profile in ("WS_change","REST_system"):
                subset=[r for r in rows if r["symbol"] == s and r["access_delay_ms"] == delay and r["value_profile"] == profile]
                cost=[r for r in subset if depth.eligible(r)]
                joint=[r for r in cost if not r["value_evidence"]["flags"]]
                summary["pairs"].append({"symbol":s,"delay_ms":delay,"profile":profile,"grids":len(subset),
                    "cost_rows":len(cost),"joint_publication_rows":len(joint),
                    "value_flags":dict(Counter(f for r in subset for f in r["value_evidence"]["flags"])),
                    "cost_tiers":[{"multiple":k,"n":len(joint),"round_trip_usd_range":[min(v),max(v)] if v else None}
                        for k in (1,2,3) for v in [[r["cost"]["scenarios"][k-1]["round_trip_cost_usd"] for r in joint]]]})
    depth.immutable(out/"results.json",(json.dumps(summary,sort_keys=True,indent=2,allow_nan=False)+"\n").encode())
    return out/"results.json"


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("command",choices=("capture","seal","report"));parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    if args.out is not None and args.command != "report":parser.error("--out is report-only; acquisition cannot reset")
    print(report(out=args.out) if args.command == "report" else {"capture":capture,"seal":seal}[args.command]())
