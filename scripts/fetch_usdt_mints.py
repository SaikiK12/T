"""Tether USDT mints (the token contract's Issue events) on Tron and Ethereum, from free public APIs, for R460.

Writes data/usdt_mints/events.csv (one row per Issue event: chain, block, ts_ms, amount_usdt, tx) and
data/usdt_mints/manifest.json (counts, window, sha256 of events.csv, the cross-checks below). data/ is gitignored;
record the folder with scripts/data_provenance.py afterwards.

Sources (no key, no account):
- Tron: TronGrid events API, contract TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t, event_name=Issue, only_confirmed=true,
  paged with the response's fingerprint.
- Ethereum: Blockscout's Etherscan-style logs API (eth.blockscout.com), contract
  0xdAC17F958D2ee523a2206206994597C13D831ec7, topic0 = keccak256("Issue(uint256)") =
  0xcb8241adb0c3fdb35b70c24ce35c5eb0c17af7431c99f827d44a445ca624176a, queried in block ranges so that no answer
  reaches Blockscout's 1,000-row cap.
- Cross-check: up to 6 Ethereum events are looked up again on a second provider (eth-mainnet.public.blastapi.io,
  eth_getLogs on the event's own block) and must match on transaction hash and amount; a mismatch stops the script.

Amounts are in USDT (6 decimals on both chains). block timestamps are the chain's, in UTC milliseconds. No market data
is read here.

usage: python scripts/fetch_usdt_mints.py [--start 2021-01-01] [--end 2026-11-11]
"""
import argparse
import csv
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "usdt_mints"
TRON_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
ETH_CONTRACT = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
ISSUE_TOPIC = "0xcb8241adb0c3fdb35b70c24ce35c5eb0c17af7431c99f827d44a445ca624176a"
TRONGRID = "https://api.trongrid.io/v1/contracts/{}/events"
BLOCKSCOUT = "https://eth.blockscout.com/api"
BLAST = "https://eth-mainnet.public.blastapi.io"
UA = {"User-Agent": "lab-research-fetch/1.0", "Accept": "application/json"}


def get_json(url, data=None, tries=5):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=dict(UA, **({"Content-Type": "application/json"}
                                                                               if data else {})))
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:  # network or rate limit: back off and retry
            if k == tries - 1:
                raise
            print(f"retry {k + 1} after {e!r}")
            time.sleep(2 ** (k + 1))


def ms(day):
    return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def tron_events(start_ms, end_ms):
    rows, fp, pages = [], None, 0
    while True:
        q = {"event_name": "Issue", "only_confirmed": "true", "limit": 200, "order_by": "block_timestamp,asc",
             "min_block_timestamp": start_ms, "max_block_timestamp": end_ms}
        if fp:
            q["fingerprint"] = fp
        d = get_json(TRONGRID.format(TRON_CONTRACT) + "?" + urllib.parse.urlencode(q))
        if not d.get("success", False):
            raise RuntimeError(f"TronGrid error: {str(d)[:300]}")
        pages += 1
        for e in d.get("data", []):
            if e.get("event_name") != "Issue" or e.get("contract_address") != TRON_CONTRACT:
                continue
            rows.append({"chain": "tron", "block": int(e["block_number"]), "ts_ms": int(e["block_timestamp"]),
                         "amount_usdt": int(e["result"]["amount"]) / 1e6, "tx": e["transaction_id"]})
        fp = (d.get("meta") or {}).get("fingerprint")
        if not fp or not d.get("data"):
            break
        time.sleep(0.4)
    print(f"tron: {len(rows)} events in {pages} pages")
    return rows


def eth_block_at(ts_s):
    d = get_json(f"{BLOCKSCOUT}?module=block&action=getblocknobytime&timestamp={ts_s}&closest=after")
    return int(d["result"]["blockNumber"])


def eth_events(start_ms, end_ms):
    b0, b1 = eth_block_at(start_ms // 1000), eth_block_at(end_ms // 1000)
    rows, step, lo = [], 500_000, b0
    while lo <= b1:
        hi = min(lo + step - 1, b1)
        q = {"module": "logs", "action": "getLogs", "fromBlock": lo, "toBlock": hi, "address": ETH_CONTRACT,
             "topic0": ISSUE_TOPIC}
        d = get_json(BLOCKSCOUT + "?" + urllib.parse.urlencode(q))
        res = d.get("result") or []
        if d.get("status") != "1" and res:
            raise RuntimeError(f"Blockscout error: {str(d)[:300]}")
        if len(res) >= 1000:
            raise RuntimeError(f"Blockscout cap reached for {lo}-{hi}; lower the step")
        for x in res:
            if x["address"].lower() != ETH_CONTRACT.lower() or x["topics"][0].lower() != ISSUE_TOPIC:
                continue
            rows.append({"chain": "ethereum", "block": int(x["blockNumber"], 16),
                         "ts_ms": int(x["timeStamp"], 16) * 1000, "amount_usdt": int(x["data"], 16) / 1e6,
                         "tx": x["transactionHash"]})
        lo = hi + 1
        time.sleep(0.3)
    print(f"ethereum: {len(rows)} events, blocks {b0}-{b1}")
    return rows


def eth_crosscheck(rows):
    """Look a few events up again on a second provider; return the checked tx hashes."""
    pick = rows[:3] + rows[-3:] if len(rows) > 6 else rows
    done = []
    for r in pick:
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_getLogs", "params": [{
            "address": ETH_CONTRACT, "topics": [ISSUE_TOPIC], "fromBlock": hex(r["block"]),
            "toBlock": hex(r["block"])}]}).encode()
        d = get_json(BLAST, data=body)
        got = {(x["transactionHash"], int(x["data"], 16) / 1e6) for x in d.get("result") or []}
        if (r["tx"], r["amount_usdt"]) not in got:
            raise RuntimeError(f"cross-check failed for {r['tx']} at block {r['block']}: {got}")
        done.append(r["tx"])
        time.sleep(0.5)
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2021-01-01")
    ap.add_argument("--end", default="2026-11-11")
    a = ap.parse_args()
    s, e = ms(a.start), ms(a.end) - 1
    tron = tron_events(s, e)
    eth = eth_events(s, e)
    checked = eth_crosscheck(eth)
    rows = sorted(tron + eth, key=lambda r: (r["ts_ms"], r["chain"], r["tx"]))
    seen = set()
    uniq = []
    for r in rows:
        k = (r["chain"], r["tx"], r["amount_usdt"])
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "events.csv"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["chain", "block", "ts_ms", "amount_usdt", "tx"])
        w.writeheader()
        for r in uniq:
            w.writerow(r)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    man = {"kind": "usdt_issue_events", "start": a.start, "end_exclusive": a.end,
           "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sources": {"tron": TRONGRID.format(TRON_CONTRACT) + "?event_name=Issue&only_confirmed=true",
                       "ethereum": BLOCKSCOUT + "?module=logs&action=getLogs&address=" + ETH_CONTRACT
                       + "&topic0=" + ISSUE_TOPIC},
           "rows": len(uniq), "by_chain": {c: sum(r["chain"] == c for r in uniq) for c in ("tron", "ethereum")},
           "duplicates_dropped": len(rows) - len(uniq), "eth_crosscheck_blastapi": checked,
           "events_sha256": digest}
    (OUT / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps({k: man[k] for k in ("rows", "by_chain", "duplicates_dropped", "events_sha256")}))


if __name__ == "__main__":
    main()
