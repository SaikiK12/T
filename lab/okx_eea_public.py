"""Bounded public EEA capability probe. No accounts, orders or host fallback.

This is unactivated plumbing, not a forward recorder or a paper lane. Funding
values are retained as received, but the probe reports schemas/counts/time
bounds only. A strategy measurement needs its own frozen protocol.
"""
import hashlib
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

HOST = "https://eea.okx.com"
ALLOWED = frozenset(("/api/v5/public/instruments", "/api/v5/public/funding-rate-history",
                     "/api/v5/public/funding-rate",
                     "/api/v5/public/position-tiers", "/api/v5/market/books",
                     "/api/v5/market/history-candles"))


class ProbeStopped(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProbeStopped("redirect refused; no regional or host substitution")


class PublicProbe:
    def __init__(self, output, *, opener=None, max_requests=12, max_bytes=6 * 1024 * 1024):
        if not 0 < max_requests <= 12 or not 0 < max_bytes <= 6 * 1024 * 1024:
            raise ValueError("probe budget exceeds the bounded handoff")
        self.output = Path(output)
        self.output.mkdir(exist_ok=False, parents=True)
        self.opener = opener or urllib.request.build_opener(NoRedirect()).open
        self.max_requests, self.max_bytes = max_requests, max_bytes
        self.requests, self.bytes, self.stopped = 0, 0, False

    def get(self, path, **params):
        if self.stopped:
            raise ProbeStopped("probe already stopped; no retry")
        if path not in ALLOWED or any(k.lower().startswith(("key", "auth", "pass", "secret")) for k in params):
            raise ValueError("public allowlisted endpoints only")
        if self.requests >= self.max_requests or self.bytes >= self.max_bytes:
            self.stopped = True
            raise ProbeStopped("finite request/byte budget exhausted")
        url = HOST + path + "?" + urllib.parse.urlencode(params)
        self.requests += 1
        name = f"response_{self.requests:02d}"
        receipt = dict(url=url, started_utc_ns=time.time_ns(), http_status=None, bytes=0,
                       user_agent_override=False, account_or_trading_access_verified=False)
        body = b""
        try:
            # Deliberately no browser User-Agent, authentication header, retry,
            # alternative domain or direct-network route.
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with self.opener(req, timeout=20) as response:
                receipt["http_status"] = response.status
                cap = min(2 * 1024 * 1024, self.max_bytes - self.bytes)
                body = response.read(cap)
                if len(body) >= cap:
                    raise ProbeStopped("response reached byte cap; truncated body is not data")
            data = json.loads(body)
            if data.get("code") != "0" or not isinstance(data.get("data"), list):
                raise ProbeStopped("non-success or nonstandard public response")
            return data
        except Exception as exc:
            self.stopped = True
            if isinstance(exc, urllib.error.HTTPError):
                receipt["http_status"] = exc.code
            receipt["error"] = str(exc)
            raise ProbeStopped(str(exc)) from exc
        finally:
            self.bytes += len(body)
            receipt.update(received_utc_ns=time.time_ns(), bytes=len(body),
                           sha256=hashlib.sha256(body).hexdigest(), stopped=self.stopped)
            (self.output / (name + ".body")).write_bytes(body)
            (self.output / (name + ".receipt.json")).write_text(json.dumps(receipt, indent=2) + "\n")


def xperp_candidates(payload):
    """Strict provisional binding to the official BTC/ETH USD_UM product names.

    Native metadata remains unverified until captured. Reject SWAP, inverse,
    normal short-expiry futures and an ambiguous duplicate rather than guessing
    a tradable instrument id from the display name in the contract PDF.
    """
    out = {}
    for row in payload["data"]:
        family = row.get("instFamily", "")
        base = family.split("-")[0]
        if base not in ("BTC", "ETH") or family != base + "-USD_UM":
            continue
        try:
            term = (int(row["expTime"]) - int(row["listTime"])) / (365.25 * 86400000)
            valid = (row["instType"] == "FUTURES" and row["ctType"] == "linear"
                     and row["ctValCcy"] == base and row["settleCcy"] == "USD"
                     and row["state"] == "live" and 4.5 <= term <= 5.5)
        except (KeyError, ValueError, TypeError):
            valid = False
        if not valid or base in out or not row.get("instId") or "SWAP" in row["instId"]:
            raise ProbeStopped("unqualified or ambiguous EEA X-Perp metadata")
        out[base] = row
    if set(out) != {"BTC", "ETH"}:
        raise ProbeStopped("BTC/ETH EEA X-Perp identities not both established")
    return out


def capabilities(probe):
    rows = xperp_candidates(probe.get("/api/v5/public/instruments", instType="FUTURES"))
    result = {}
    for base, row in sorted(rows.items()):
        inst = row["instId"]
        requests = [
            ("funding_history", "/api/v5/public/funding-rate-history", dict(instId=inst, limit=400)),
            ("funding_current", "/api/v5/public/funding-rate", dict(instId=inst)),
            ("books", "/api/v5/market/books", dict(instId=inst, sz=400)),
            ("tiers", "/api/v5/public/position-tiers", dict(instType="FUTURES", instFamily=row["instFamily"], tdMode="cross")),
            ("candles_head", "/api/v5/market/history-candles", dict(instId=inst, bar="1H", limit=300)),
        ]
        result[base] = {"instrument_id": inst}
        for label, endpoint, params in requests:
            payload = probe.get(endpoint, **params)["data"]
            record = dict(rows=len(payload), keys=sorted(payload[0]) if payload and isinstance(payload[0], dict) else [])
            if label == "funding_history" and payload:
                if any(x.get("instId") != inst or x.get("instType") != "FUTURES" for x in payload):
                    raise ProbeStopped("history instrument/type mismatch")
                stamps = [int(x["fundingTime"]) for x in payload]
                record.update(first_ms=min(stamps), last_ms=max(stamps))
            result[base][label] = record
    return dict(scope="counts/schema/time bounds only; no rate, return or fill statistic", instruments=result,
                premium_history_endpoint=None, paper_lane_ready=False)
