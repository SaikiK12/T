"""R314 finite public depth probe: capture, seal, then report fixed cost controls.

No orders, accounts, history, retries, reconnects, scheduled job or activation.
Transport/receipt helpers from frozen R313 are reused; larger depth-frame caps
are declared here instead of changing any historical code/specification.
"""
import argparse
import asyncio
from collections import Counter
import fcntl
import gzip
import json
import multiprocessing
from pathlib import Path
import ssl
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab.depth_replay import DepthReplay  # noqa: E402
from lab.stream_quotes import FrameClock, NS, SYMBOLS, entry_cash_drift  # noqa: E402
from scripts import probe_stream_quotes as old  # noqa: E402

LANE = ROOT / "experiments/depth_quotes_v1"
REST_BYTES = old.REST_BYTES
STREAM_BYTES, FRAME_BYTES, MAX_MESSAGES = 8*1024**2, 256*1024, 20_000
STREAM_SECONDS, TOTAL_SECONDS = 65, 120
sha, write = old.sha, old.write


def verify(lane=LANE):
    old.verify(lane)  # generic manifest/runtime/symbol checks, explicit new lane
    if json.loads((lane/"code_inputs.json").read_text())["python_version"] != list(sys.version_info[:3]):
        raise ValueError("Python runtime version drift")


def metadata_worker(url, connection, limit, timeout):
    """One public GET in an owned, wall-time-bounded worker; no redirect/retry."""
    try:
        opener = urllib.request.build_opener(old.NoHTTPRedirect()).open
        req = urllib.request.Request(url, headers={"User-Agent":"quant-lab-R314-public/1", "Accept-Encoding":"identity"})
        try:
            response = opener(req, timeout=timeout)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            connection.send(("status",response.status))
            remaining = limit
            while remaining:
                chunk = response.read1(min(65536,remaining))
                if not chunk:
                    break
                connection.send(("chunk",chunk))
                remaining -= len(chunk)
        connection.send(("done",None))
    except Exception as exc:
        connection.send(("error",type(exc).__name__+": "+str(exc)))
    finally:
        connection.close()


class Metadata(old.Metadata):
    """Preserve partial receipts; bound absolute request time despite trickle reads."""
    def __init__(self,out,*,worker=metadata_worker,request_seconds=3.):
        super().__init__(out)
        self.worker, self.request_seconds = worker, request_seconds
        self.read_upper_bound = 0

    def get(self,name,url):
        if len(self.records) >= 7 or self.read_upper_bound >= REST_BYTES or time.monotonic()-self.start >= 20:
            raise old.BudgetStop("metadata request/byte/time budget")
        record = {"name":name,"url":url,"started_utc_ns":time.time_ns(),"started_mono_ns":time.monotonic_ns(),"error":None}
        self.records.append(record)  # failed or timed-out attempts consume allowance
        limit = min(1024**2,REST_BYTES-self.read_upper_bound)
        allowance = min(self.request_seconds,20-(time.monotonic()-self.start))
        deadline = time.monotonic()+allowance
        ctx = multiprocessing.get_context("spawn")
        receiver,sender = ctx.Pipe(duplex=False)
        process = ctx.Process(target=self.worker,args=(url,sender,limit,allowance),daemon=True)
        chunks,total,complete = [],0,False
        value = None
        try:
            process.start();sender.close()
            while time.monotonic() < deadline:
                if not receiver.poll(max(0,deadline-time.monotonic())):
                    break
                try:
                    kind,payload = receiver.recv()
                except EOFError:
                    break
                if kind == "status":
                    record["http_status"] = payload
                elif kind == "chunk":
                    if not isinstance(payload,bytes) or len(payload) > limit-total:
                        raise ValueError("worker exceeded declared body-read cap")
                    chunks.append(payload);total += len(payload)
                elif kind == "done":
                    complete = True
                    break
                elif kind == "error":
                    raise ValueError(payload)
                else:
                    raise ValueError("unknown metadata worker message")
            if not complete:
                raise TimeoutError("absolute metadata wall deadline or premature worker exit")
            if total == limit or not 200 <= record.get("http_status",0) < 300:
                raise ValueError("truncated or failed metadata response")
            value = json.loads(b"".join(chunks))
        except Exception as exc:
            record["error"] = type(exc).__name__+": "+str(exc)
        finally:
            if process.pid is not None:
                if process.is_alive():process.terminate()
                process.join(.2)
                if process.is_alive():process.kill();process.join(.2)
            receiver.close();sender.close()
        body = b"".join(chunks)
        import hashlib
        record.update(received_utc_ns=time.time_ns(),received_mono_ns=time.monotonic_ns(),bytes=len(body),
                      sha256=hashlib.sha256(body).hexdigest(),body=name+".json.gz")
        self.total += len(body)
        # A killed worker may have read a chunk still in transit. Reserve the
        # entire uncertain request tail instead of renewing those bytes later.
        record["body_read_upper_bound"] = len(body) if complete else limit
        self.read_upper_bound += record["body_read_upper_bound"]
        (self.out/record["body"]).write_bytes(gzip.compress(body,mtime=0))
        return value


async def stream(venue, subscriptions, out, anchor, status, *, connector=None):
    connector = connector or old.no_redirect_connector()
    url = {"mexc": old.MX_WS, "lighter": old.LIGHTER_WS}[venue]
    status.update(url=url, handshake_attempts=1, opened_mono_ns=None, closed_mono_ns=None,
                  messages=0, payload_bytes=0, unusable_mono_ns=None, reason="not_started")
    deadline = anchor.mono_ns + STREAM_SECONDS*NS
    try:
        async with connector(url, ssl=ssl.create_default_context(), open_timeout=5, close_timeout=1,
                             max_size=FRAME_BYTES, max_queue=1, compression=None, ping_interval=None) as ws:
            try:
                status["opened_mono_ns"] = time.monotonic_ns()
                for subscription in subscriptions:
                    await asyncio.wait_for(ws.send(json.dumps(subscription)), timeout=2)
                last_ping = time.monotonic()
                with gzip.GzipFile(filename=str(out/(venue+".jsonl.gz")), mode="wb", mtime=0) as journal:
                    while time.monotonic_ns() < deadline:
                        if status["payload_bytes"]+FRAME_BYTES > STREAM_BYTES or status["messages"] >= MAX_MESSAGES:
                            status["reason"] = "payload_or_message_cap"
                            break
                        if time.monotonic()-last_ping >= 15:
                            await asyncio.wait_for(ws.send(json.dumps({"method":"ping"} if venue == "mexc" else {"type":"ping"})), 2)
                            last_ping = time.monotonic()
                        remaining = (deadline-time.monotonic_ns())/NS
                        if remaining <= 0:
                            status["reason"] = "duration_complete"
                            break
                        try:
                            raw = await asyncio.wait_for(ws.recv(), min(1., remaining))
                        except asyncio.TimeoutError:
                            continue
                        utc, mono = time.time_ns(), time.monotonic_ns()
                        if isinstance(raw, bytes):
                            raw = raw.decode("utf-8")
                        size = len(raw.encode())
                        if size > FRAME_BYTES:
                            raise ValueError("transport violated declared maximum frame")
                        status["messages"] += 1
                        status["payload_bytes"] += size
                        frame = {"venue":venue, "number":status["messages"], "utc_ns":utc, "mono_ns":mono, "raw":raw}
                        journal.write((json.dumps(frame, sort_keys=True, separators=(",", ":"))+"\n").encode())
                        try:
                            control = json.loads(raw)
                        except (ValueError, TypeError):
                            control = None  # retain malformed frames for fail-closed replay
                        if venue == "lighter" and isinstance(control, dict) and control.get("type") == "ping":
                            await asyncio.wait_for(ws.send('{"type":"pong"}'), 2)
                    else:
                        status["reason"] = "duration_complete"
            finally:
                # Invalidate BEFORE context cleanup/close can delay the boundary.
                status["unusable_mono_ns"] = time.monotonic_ns()
    except asyncio.CancelledError:
        status["reason"] = "total_duration_cap"
        raise
    except Exception as exc:
        status["reason"] = type(exc).__name__+": "+str(exc)
    finally:
        status["closed_mono_ns"] = time.monotonic_ns()
        if status["unusable_mono_ns"] is None:
            status["unusable_mono_ns"] = status["closed_mono_ns"]
    return status


def capture(lane=LANE):
    verify(lane)
    out = lane/"evidence"
    out.mkdir()  # refuses reset/retry even after a failed attempt
    begin = time.monotonic()
    meta, mapping, errors, connections = {}, {}, [], {}
    network = Metadata(out)
    old.LT_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with old.LT_LOCK.open("a") as lock:
        locked = False
        try:
            while time.monotonic()-begin < 10:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                    break
                except BlockingIOError:
                    time.sleep(.05)
            if not locked:
                raise old.BudgetStop("existing public API writer held lock")
            network.start = time.monotonic()
            listing = network.get("lighter_metadata", old.LT_HTTP+"/orderBookDetails?filter=perp")
            for symbol in SYMBOLS:
                try:
                    m = network.get(symbol+"_mexc_metadata", old.MX_HTTP+"/detail?symbol="+symbol+"_USDT")
                    if not m or m.get("success") is not True or not listing or listing.get("code") != 200:
                        raise ValueError("metadata_failed")
                    mm = m["data"]
                    if isinstance(mm, list):
                        mm, = [x for x in mm if x["symbol"] == symbol+"_USDT"]
                    lm, = [x for x in listing["order_book_details"] if x["symbol"] == symbol and x["market_type"] == "perp"]
                    if mm["symbol"] != symbol+"_USDT":
                        raise ValueError("MEXC metadata identity mismatch")
                    meta[symbol] = {"mexc":mm, "lighter":lm}
                    mapping[int(lm["market_id"])] = symbol
                except (KeyError, ValueError, TypeError, old.BudgetStop) as exc:
                    errors.append(symbol+":"+type(exc).__name__+":"+str(exc))
                    if isinstance(exc, old.BudgetStop):
                        break
            write(out/"metadata.json", {"symbols":list(SYMBOLS), "metadata":meta, "names":mapping, "errors":errors})
            anchor = FrameClock(time.time_ns(), time.monotonic_ns())
            write(out/"anchor.json", vars(anchor))
            mx = [{"method":kind,"param":{"symbol":s+"_USDT", **({"limit":5} if kind == "sub.depth.full" else {})}}
                  for s in SYMBOLS if s in meta for kind in ("sub.depth.full","sub.fair.price")]
            lt = [{"type":"subscribe","channel":f"{kind}/{m}"}
                  for m in sorted(mapping) for kind in ("order_book","market_stats")]
            connections = {v:{} for v in ("mexc","lighter")}
            async def both():
                await asyncio.wait_for(asyncio.gather(stream("mexc",mx,out,anchor,connections["mexc"]),
                    stream("lighter",lt,out,anchor,connections["lighter"])),
                    timeout=min(75., max(.001, TOTAL_SECONDS-(time.monotonic()-begin))))
            asyncio.run(both())
        except Exception as exc:
            errors.append(type(exc).__name__+": "+str(exc))
        finally:
            write(out/"connections.json", connections)
            write(out/"receipts.json", {"records":network.records, "requests":len(network.records),
                "response_bytes":network.total, "response_body_read_upper_bound":network.read_upper_bound,
                "duration_seconds":time.monotonic()-begin, "errors":errors})
            if locked:
                fcntl.flock(lock, fcntl.LOCK_UN)
    return out


def seal(lane=LANE):
    return old.seal(lane)


def load_capture(lane):
    """Verify all sealed raw observations before any cost calculation."""
    verify(lane)
    identity = json.loads((lane/"evidence_inputs.json").read_text())
    actual = {str(p.relative_to(lane)) for p in (lane/"evidence").iterdir() if p.is_file()}
    if actual != set(identity["sha256"]) or identity["code_manifest_sha256"] != sha(lane/"code_inputs.json"):
        raise ValueError("evidence/code inventory drift")
    for name, digest in identity["sha256"].items():
        if sha(lane/name) != digest:
            raise ValueError("sealed evidence drift")
    read = lambda name: json.loads((lane/"evidence"/name).read_text())
    receipts = read("receipts.json")
    if not (0 <= receipts["requests"] <= 7 and 0 <= receipts["response_bytes"] <= REST_BYTES
            and 0 <= receipts["duration_seconds"] <= TOTAL_SECONDS):
        raise ValueError("collection cap exceeded")
    records = receipts["records"]
    if len(records) != receipts["requests"] or sum(r["bytes"] for r in records) != receipts["response_bytes"]:
        raise ValueError("metadata receipt counters disagree")
    if (sum(r["body_read_upper_bound"] for r in records) != receipts["response_body_read_upper_bound"]
            or not receipts["response_bytes"] <= receipts["response_body_read_upper_bound"] <= REST_BYTES):
        raise ValueError("metadata uncertain read budget disagrees")
    bodies = {}
    import hashlib
    for record in records:
        raw = gzip.decompress((lane/"evidence"/record["body"]).read_bytes())
        if len(raw) != record["bytes"] or hashlib.sha256(raw).hexdigest() != record["sha256"]:
            raise ValueError("metadata raw body disagrees with receipt")
        if not len(raw) <= record["body_read_upper_bound"] <= 1024**2 or record["received_mono_ns"] < record["started_mono_ns"]:
            raise ValueError("metadata body/clock cap")
        if not record["error"]:
            bodies[record["name"]] = json.loads(raw)
    connections, frames = read("connections.json"), []
    if set(connections)-{"mexc","lighter"}:
        raise ValueError("unknown connection")
    for venue, status in connections.items():
        if not (status["handshake_attempts"] == 1 and 0 <= status["payload_bytes"] <= STREAM_BYTES
                and 0 <= status["messages"] <= MAX_MESSAGES):
            raise ValueError("stream cap exceeded")
        if not 0 <= status["unusable_mono_ns"] <= status["closed_mono_ns"]:
            raise ValueError("invalid stop/transport-close boundary")
        path = lane/"evidence"/(venue+".jsonl.gz")
        with gzip.open(path, "rt") if path.exists() else open_empty() as f:
            observed = [json.loads(line) for line in f]
        if len(observed) != status["messages"] or sum(len(f["raw"].encode()) for f in observed) != status["payload_bytes"]:
            raise ValueError("stream receipt counters disagree")
        for i, frame in enumerate(observed, 1):
            if frame["venue"] != venue or frame["number"] != i or len(frame["raw"].encode()) > FRAME_BYTES:
                raise ValueError("stream identity/order/size mismatch")
            if not status["opened_mono_ns"] <= frame["mono_ns"] <= status["unusable_mono_ns"]:
                raise ValueError("frame outside its connection")
            if i > 1 and frame["mono_ns"] < observed[i-2]["mono_ns"]:
                raise ValueError("receive monotonic clock regressed")
        frames.extend(observed)
    anchor = FrameClock(**read("anchor.json")) if (lane/"evidence/anchor.json").exists() else FrameClock(0,0)
    if any(r["received_mono_ns"] > anchor.mono_ns for r in records) and anchor.mono_ns:
        raise ValueError("metadata received after anchor")
    mapping = read("metadata.json") if (lane/"evidence/metadata.json").exists() else {"metadata":{},"names":{}}
    for symbol, pair in mapping["metadata"].items():
        if symbol not in SYMBOLS:
            raise ValueError("unexpected symbol")
        mx = bodies[symbol+"_mexc_metadata"]["data"]
        if isinstance(mx,list):
            mx, = [m for m in mx if m["symbol"] == symbol+"_USDT"]
        lt, = [m for m in bodies["lighter_metadata"]["order_book_details"] if m["symbol"] == symbol and m["market_type"] == "perp"]
        if pair != {"mexc":mx,"lighter":lt}:
            raise ValueError("parsed metadata disagrees with raw inputs")
    if mapping["names"] != {str(p["lighter"]["market_id"]):s for s,p in mapping["metadata"].items()}:
        raise ValueError("market mapping disagrees with metadata")
    return frames, mapping, anchor, connections


def open_empty():
    from io import StringIO
    return StringIO("")


def eligible(row):
    return bool(row["cost"] and row["cost"]["displayed_fillable"] and not row["book_flags"])


def fixed_rows(replay):
    rows = []
    for second in range(5,61,5):
        immediate = {}
        for symbol in SYMBOLS:
            row, books = replay.observe(symbol, replay.anchor.mono_ns+second*NS)
            row.update(grid_second=second, access_delay_ms=0, entry_quote_cash_drift=None)
            immediate[symbol] = row, books
            rows.append(row)
            top, _ = replay.observe(symbol, replay.anchor.mono_ns+second*NS, row["quantity_base"],
                                    allow_new_quantity=False, profile="top_only")
            top.update(grid_second=second, access_delay_ms=0, entry_quote_cash_drift=None)
            rows.append(top)
        for symbol in SYMBOLS:
            before, before_books = immediate[symbol]
            q = before["quantity_base"]
            row, books = replay.observe(symbol, replay.anchor.mono_ns+second*NS+300_000_000, q,
                                        allow_new_quantity=False)
            row.update(grid_second=second, access_delay_ms=300, entry_quote_cash_drift=None)
            if eligible(before) and eligible(row):
                row["entry_quote_cash_drift"] = entry_cash_drift(before_books, books, q)
            rows.append(row)
            top, _ = replay.observe(symbol, replay.anchor.mono_ns+second*NS+300_000_000, q,
                                    allow_new_quantity=False, profile="top_only")
            top.update(grid_second=second, access_delay_ms=300, entry_quote_cash_drift=None)
            rows.append(top)
    return rows


def immutable(path, data):
    if path.exists() and path.read_bytes() != data:
        raise ValueError("refusing different output overwrite: "+str(path))
    if not path.exists():
        path.write_bytes(data)


def report(lane=LANE, out=None):
    frames, mapping, anchor, connections = load_capture(lane)
    replay = DepthReplay(frames,mapping["metadata"],{int(k):v for k,v in mapping["names"].items()},anchor,connections)
    rows = fixed_rows(replay)
    out = Path(out) if out is not None else lane
    out.mkdir(exist_ok=True)
    encoded = "".join(json.dumps(r,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n" for r in rows).encode()
    immutable(out/"observations.jsonl.gz", gzip.compress(encoded,mtime=0))
    summary = {"registry_id":"R314", "evidence_manifest_sha256":sha(lane/"evidence_inputs.json"),
        "observations_sha256":sha(out/"observations.jsonl.gz"), "rows":len(rows), "predictive_trials":0,
        "scope":"conditional depth/access costs only; no fills, inference, expected return or paper scoring",
        "charge_reserve_bp":[10,4], "capital_usd":10000, "capital_per_venue_usd":5000,
        "access_delay_ms":[0,300], "depth_profiles":["full","top_only"],
        "parser_errors_through_grid":dict(replay.errors),
        "assembly_events_through_grid":[{"symbol":s,"status":a,"reason":r,"n":n}
            for (s,a,r),n in sorted(replay.assembly_events.items())], "pairs":[]}
    for symbol in SYMBOLS:
        for delay in (0,300):
            for profile in ("full","top_only"):
                subset = [r for r in rows if r["symbol"] == symbol and r["access_delay_ms"] == delay and r["depth_profile"] == profile]
                valid = [r for r in subset if eligible(r)]
                tiers = [{"multiple":k,"n":len(valid),"round_trip_cost_usd_range":[min(v),max(v)] if v else None,
                          "break_even_leg_bp_range":[min(b),max(b)] if b else None}
                    for k in (1,2,3)
                    for v,b in [([r["cost"]["scenarios"][k-1]["round_trip_cost_usd"] for r in valid],
                                 [r["cost"]["scenarios"][k-1]["break_even_leg_bp"] for r in valid])]]
                summary["pairs"].append({"symbol":symbol,"delay_ms":delay,"profile":profile,"grids":len(subset),
                    "valid_cost_grids":len(valid),"book_flags":dict(Counter(f for r in subset for f in r["book_flags"])),
                    "cost_tiers":tiers,"fresh_fair_index_grids":sum(all(not x["flags"] for x in r["references"]) for r in subset)})
    immutable(out/"results.json", (json.dumps(summary,sort_keys=True,indent=2,allow_nan=False)+"\n").encode())
    return out/"results.json"


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("capture","seal","report"))
    p.add_argument("--out", type=Path, help="fresh report reproduction folder only")
    a = p.parse_args()
    if a.out is not None and a.command != "report":
        p.error("--out is report-only; acquisition cannot be retried at another path")
    print(report(out=a.out) if a.command == "report" else {"capture":capture,"seal":seal}[a.command]())
