"""Bounded, durable M090 content capture; never qualifies a forecast clock.

OpenSSL supplies ASN.1/CMS/signature validation. A signed hash proves content
existence under an operator's key, not exchange truth, UTC or on-time trading.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import subprocess
import tempfile
import time

from scripts.m090_history_rule import parse_page_one

LIMIT = 1_000_000
ARCHIVE_LIMIT = 4_000_000
DISPLAY = "https://contract.mexc.com/api/v1/contract/funding_rate/BTC_USDT"
HISTORY = "https://contract.mexc.com/api/v1/contract/funding_rate/history?symbol=BTC_USDT&page_num=1&page_size=20"
PROTOCOL = "M090_CONTENT_V2"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()


def decode(raw):
    def pairs(items):
        out = {}
        for k,v in items:
            if k in out:
                raise ValueError("duplicate JSON key")
            out[k] = v
        return out
    def constant(_):
        raise ValueError("nonfinite JSON")
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)


def bounded(raw):
    if not isinstance(raw,bytes) or not 0 < len(raw) <= LIMIT:
        raise ValueError("missing/oversized evidence")
    return raw


def openssl(args):
    r = subprocess.run(["openssl",*map(str,args)],capture_output=True,timeout=20,
                       env=dict(os.environ,LC_ALL="C"))
    if r.returncode:
        raise ValueError("OpenSSL validation failed: "+r.stderr.decode(errors="replace")[-600:])
    return r.stdout


def query(payload,policy):
    with tempfile.TemporaryDirectory(prefix="m090_query_") as d:
        p = Path(d)
        (p/"data").write_bytes(bounded(payload))
        openssl(["ts","-query","-data",p/"data","-sha256","-cert","-tspolicy",policy,"-out",p/"query"])
        return (p/"query").read_bytes()


def field(text,name):
    values = re.findall(r"^"+re.escape(name)+r": (.*)$",text,re.M)
    if len(values) != 1:
        raise ValueError("missing/ambiguous OpenSSL field: "+name)
    return values[0].strip()


def verify_timestamp(payload,q,reply,trust):
    """Pinned signer, nonce, imprint, policy, chain/EKU and CRLs at genTime.

    Accuracy is reported as text only. This version supplies NO UTC interval,
    even if an authority reports Accuracy. No CPS or machine-clock fallback.
    """
    with tempfile.TemporaryDirectory(prefix="m090_verify_") as d:
        p = Path(d)
        for n,raw in dict(data=payload,query=q,reply=reply,root=trust["root"],
                          chain=trust["chain"],crls=trust["crls"]).items():
            (p/n).write_bytes(bounded(raw))
        text = openssl(["ts","-reply","-in",p/"reply","-text"]).decode("ascii")
        nonce = field(text,"Nonce")
        qtext = openssl(["ts","-query","-in",p/"query","-text"]).decode("ascii")
        if (not re.fullmatch(r"0x[0-9A-Fa-f]+",nonce) or int(nonce,16) <= 0
                or nonce != field(qtext,"Nonce") or field(text,"Policy OID") != trust["policy"]):
            raise ValueError("nonce or timestamp policy mismatch")
        stamp = field(text,"Time stamp")
        # Public provider is second resolution. Other formats fail closed.
        dt = datetime.strptime(stamp,"%b %d %H:%M:%S %Y GMT").replace(tzinfo=timezone.utc)
        at = str(int(dt.timestamp()))
        common = ["-CAfile",p/"root","-untrusted",p/"chain","-attime",at]
        openssl(["ts","-verify","-queryfile",p/"query","-in",p/"reply",*common])
        openssl(["ts","-verify","-data",p/"data","-in",p/"reply",*common])
        openssl(["ts","-reply","-in",p/"reply","-token_out","-out",p/"token"])
        openssl(["cms","-verify","-inform","DER","-in",p/"token","-CAfile",p/"root",
                 "-certfile",p/"chain","-purpose","timestampsign","-attime",at,
                 "-no-CApath","-no-CAstore","-signer",p/"signer","-out",p/"content"])
        signer = sha(openssl(["x509","-in",p/"signer","-outform","DER"]))
        if signer != trust["signer_sha256"]:
            raise ValueError("timestamp signer pin mismatch")
        openssl(["verify","-purpose","timestampsign",*common,"-CRLfile",p/"crls","-crl_check_all",
                 "-no-CApath","-no-CAstore",p/"signer"])
    return dict(payload_sha256=sha(payload),query_sha256=sha(q),reply_sha256=sha(reply),
                signer_sha256=signer,policy=trust["policy"],nonce=nonce,reported_gen_time=stamp,
                reported_accuracy=field(text,"Accuracy"),revocation_checked_at_signed_time=True,
                utc_interval=None,forecast_eligible=False)


def parse_inputs(display,history):
    d = decode(bounded(display))
    if not isinstance(d,dict) or d.get("success") is not True or not isinstance(d.get("data"),dict):
        raise ValueError("invalid displayed funding response")
    d = d["data"]
    target,rate = d["nextSettleTime"],d["fundingRate"]
    if d.get("symbol") != "BTC_USDT" or type(target) is not int or target <= 0 or isinstance(rate,bool):
        raise ValueError("invalid display identity/type")
    rate = float(rate)
    if not math.isfinite(rate) or abs(rate)>1:
        raise ValueError("invalid rate")
    page = parse_page_one(history,"BTC_USDT")
    if not page.settlements or page.settlements[0].settlement_ms >= target:
        raise ValueError("no exact reported event preceding target")
    previous = page.settlements[0]
    return dict(symbol="BTC_USDT",target_ms=target,previous_ms=previous.settlement_ms,
                displayed_rate=rate,previous_rate=previous.rate,units="fraction per reported settlement",
                previous_event_completeness_verified=False)


def fsync_dir(path):
    fd = os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def durable(path,raw):
    with path.open("xb") as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())
    fsync_dir(path.parent)


@contextmanager
def writer(root):
    root.mkdir(parents=True,exist_ok=True)
    if any(p.is_symlink() for p in [root,*root.parents]):
        raise ValueError("symlink archive")
    for p in [root,*root.parents]:
        fsync_dir(p)
    lock = root/".writer.lock"
    with lock.open("x"):
        pass
    try:
        yield
    finally:
        lock.unlink()


def inventory(root):
    result,total = {},0
    for p in root.iterdir():
        if p.name == ".writer.lock":
            continue
        if p.is_symlink() or not p.is_file():
            raise ValueError("nonregular archive file")
        total += p.stat().st_size
        if total > ARCHIVE_LIMIT or p.stat().st_size > LIMIT:
            raise ValueError("archive size cap")
        result[p.name] = sha(p.read_bytes())
    return result


PRECOMMIT = {"display.json","history.json","crl_0.raw","crl_1.raw","crls.pem"}
FILES = PRECOMMIT|{"manifest.json","journal.jsonl","checkpoint.json","query.tsq","reply.tsr","complete.json"}


def audit(root,trust,policy_sha,expected_head=None):
    files = inventory(root)
    if set(files) != FILES:
        raise ValueError("incomplete/orphan archive retained; no automatic recovery")
    complete = decode((root/"complete.json").read_bytes())
    if complete != {k:v for k,v in files.items() if k!="complete.json"}:
        raise ValueError("archive byte drift")
    manifest_raw = (root/"manifest.json").read_bytes()
    m = decode(manifest_raw)
    if m["protocol"] != PROTOCOL or m["policy_sha256"] != policy_sha or m["files"] != {k:files[k] for k in PRECOMMIT}:
        raise ValueError("manifest/policy drift")
    line = (root/"journal.jsonl").read_bytes()
    entry = dict(sequence=1,previous_commit_sha256="0"*64,manifest_sha256=sha(manifest_raw))
    if line != encode(entry):
        raise ValueError("journal order/bytes differ")
    head = sha(line)
    if expected_head is not None and head != expected_head:
        raise ValueError("externally retained head differs")
    checkpoint = encode(dict(protocol=PROTOCOL,journal_sha256=head,entry_sha256=head))
    if (root/"checkpoint.json").read_bytes() != checkpoint:
        raise ValueError("checkpoint differs")
    receipt = verify_timestamp(checkpoint,(root/"query.tsq").read_bytes(),(root/"reply.tsr").read_bytes(),
                               dict(trust,crls=(root/"crls.pem").read_bytes()))
    try:
        inputs,error = parse_inputs((root/"display.json").read_bytes(),(root/"history.json").read_bytes()),None
    except (KeyError,TypeError,ValueError,OverflowError) as exc:
        inputs,error = None,type(exc).__name__
    if (inputs,error) != (m["inputs"],m["input_error"]):
        raise ValueError("parsed inputs differ")
    return dict(protocol=PROTOCOL,journal_head_sha256=head,files=files,inputs=inputs,input_error=error,
                timestamp=receipt,prospective_events=0,strategy_trials=0,scoring_enabled=False,
                forecast_eligible=False,gate_eligible=False)


def capture(root,trust,policy_sha,exchange):
    """One source packet; a completed restart audits without refetching."""
    with writer(root):
        if inventory(root):
            return audit(root,trust,policy_sha)
        total = 0
        def get(url,data=None):
            nonlocal total
            raw = bounded(exchange(url,data)); total += len(raw)
            if total > LIMIT:
                raise ValueError("aggregate response budget")
            return raw
        crls = []
        for n,url in enumerate(trust["crl_urls"]):
            raw = get(url); durable(root/f"crl_{n}.raw",raw)
            with tempfile.TemporaryDirectory(prefix="m090_crl_") as d:
                p = Path(d)/"raw"; p.write_bytes(raw)
                crls.append(openssl(["crl","-inform","PEM" if raw.startswith(b"-----BEGIN") else "DER",
                                     "-in",p,"-outform","PEM"]))
        durable(root/"crls.pem",b"".join(crls))
        requests = {}
        for name,url in (("display",DISPLAY),("history",HISTORY)):
            a,b = time.time_ns(),time.monotonic_ns()
            raw = get(url)
            c,d = time.time_ns(),time.monotonic_ns()
            durable(root/(name+".json"),raw)
            requests[name] = dict(url=url,start_wall_ns=a,end_wall_ns=c,start_monotonic_ns=b,
                                  end_monotonic_ns=d,utc_verified=False)
        try:
            inputs,error = parse_inputs((root/"display.json").read_bytes(),(root/"history.json").read_bytes()),None
        except (KeyError,TypeError,ValueError,OverflowError) as exc:
            inputs,error = None,type(exc).__name__
        manifest = encode(dict(protocol=PROTOCOL,nonce=secrets.token_hex(32),policy_sha256=policy_sha,
                               files=inventory(root),requests=requests,inputs=inputs,input_error=error))
        durable(root/"manifest.json",manifest)
        line = encode(dict(sequence=1,previous_commit_sha256="0"*64,manifest_sha256=sha(manifest)))
        durable(root/"journal.jsonl",line)
        checkpoint = encode(dict(protocol=PROTOCOL,journal_sha256=sha(line),entry_sha256=sha(line)))
        durable(root/"checkpoint.json",checkpoint)
        q = query(checkpoint,trust["policy"]); durable(root/"query.tsq",q)
        reply = get(trust["url"],q); durable(root/"reply.tsr",reply)
        verify_timestamp(checkpoint,q,reply,dict(trust,crls=b"".join(crls)))
        durable(root/"complete.json",encode(inventory(root)))
        return audit(root,trust,policy_sha)
