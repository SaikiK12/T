"""Fail-closed public HTTP limits for the owner's operational takeover, without changing source bodies."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import gzip
import json
from pathlib import Path
import time
from urllib import error, request, parse


class TransportStop(BaseException):
    """Escape legacy retry/skip handlers: a denied source is never silently retried."""


def append(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row, sort_keys=True)+"\n")
        f.flush()
        import os
        os.fsync(f.fileno())


class Budget:
    def __init__(self, folder, policy):
        self.folder, self.policy = Path(folder), policy
        self.folder.mkdir(parents=True, exist_ok=True)
        self.events = self.folder/"requests.jsonl"

    @contextmanager
    def lock(self):
        with (self.folder/"budget.lock").open("a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            yield

    def records(self):
        return [json.loads(x) for x in self.events.read_text().splitlines()] if self.events.exists() else []

    def usage(self):
        starts, ends = {}, {}
        for r in self.records():
            if r["event"] == "START":
                if r["id"] in starts:
                    raise TransportStop("duplicate network reservation")
                starts[r["id"]] = r
            elif r["event"] == "END":
                if r["id"] not in starts or r["id"] in ends:
                    raise TransportStop("unmatched network receipt")
                ends[r["id"]] = r
        return len(starts), sum(ends[i]["charged_bytes"] if i in ends else s["reserved_bytes"]
                                for i, s in starts.items())

    def reserve(self, req):
        url = req.full_url if isinstance(req, request.Request) else req
        u = parse.urlsplit(url)
        key = u.netloc+u.path
        with self.lock():
            if "start" in self.policy:
                now = datetime.now(timezone.utc).isoformat()
                if not self.policy["start"] <= now < self.policy["end"]:
                    raise TransportStop("source dispatch outside frozen campaign window")
            blocked = [r for r in self.records() if r["event"] == "BLOCK"]
            if any(r["key"] in (u.netloc, key) for r in blocked):
                raise TransportStop("source blocked pending review: "+key)
            if u.scheme != "https" or u.username or u.password or not any(url.startswith(p) for p in self.policy["prefixes"]):
                raise TransportStop("URL outside registered public source scope: "+key)
            if isinstance(req, request.Request):
                headers = {k.lower(): v for k, v in req.header_items()}
                if any(k in headers for k in ("authorization", "cookie", "x-api-key")):
                    raise TransportStop("authenticated request refused")
                if any(x in headers.get("user-agent", "").lower() for x in ("mozilla", "chrome/", "firefox/")):
                    raise TransportStop("browser User-Agent spoof refused")
            n, used = self.usage()
            cap = self.policy["response_cap"]
            if n >= self.policy["max_requests"] or used+cap+1 > self.policy["max_body_bytes"]:
                raise TransportStop("accumulated campaign network budget exhausted")
            rid = str(n)
            append(self.events, dict(event="START", id=rid, url=url, utc_ns=time.time_ns(), reserved_bytes=cap+1))
            return rid, cap, u.netloc, key

    def finish(self, rid, size, *, complete, status=None, body_sha256=None):
        with self.lock():
            append(self.events, dict(event="END", id=rid, utc_ns=time.time_ns(), status=status,
                                     charged_bytes=size if complete else self.policy["response_cap"]+1,
                                     body_sha256=body_sha256))

    def block(self, key, reason):
        with self.lock():
            append(self.events, dict(event="BLOCK", key=key, reason=reason, utc_ns=time.time_ns()))


class BoundedResponse:
    def __init__(self, response, budget, reservation):
        self.response, self.budget = response, budget
        self.rid, self.cap, self.host, self.key = reservation
        self.read_bytes, self.finished, self.uncertain = 0, False, False
        self.body_hash = hashlib.sha256()

    def __getattr__(self, name):
        return getattr(self.response, name)

    def read(self, n=-1):
        limit = self.cap-self.read_bytes+1
        try:
            raw = self.response.read(limit if n is None or n < 0 else min(n, limit))
        except BaseException:
            self.uncertain = True
            raise
        self.read_bytes += len(raw)
        self.body_hash.update(raw)
        if self.read_bytes > self.cap:
            self.uncertain = True
            self.budget.block(self.key, "response cap exceeded")
            self.close()
            raise TransportStop("response cap exceeded: "+self.key)
        return raw

    def close(self):
        if not self.finished:
            self.finished = True
            self.budget.finish(self.rid, self.read_bytes, complete=not self.uncertain,
                               status=getattr(self.response, "code", None), body_sha256=self.body_hash.hexdigest())
            self.response.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


@contextmanager
def fence(folder, policy):
    """No headers/rates/prices are changed. Denials and budget exhaustion stop the child."""
    budget = Budget(folder, policy)
    original = request.OpenerDirector.open
    redirect = request.HTTPRedirectHandler.redirect_request

    def no_redirect(self, req, fp, code, msg, headers, newurl):
        raise TransportStop("redirect refused; no target request sent")

    def opened(self, fullurl, *args, **kwargs):
        reservation = budget.reserve(fullurl)
        try:
            response = original(self, fullurl, *args, **kwargs)
        except error.HTTPError as exc:
            rid, cap, host, key = reservation
            raw = exc.read(cap+1)
            denial = budget.folder/"denials"/(rid+".body.gz")
            denial.parent.mkdir(parents=True, exist_ok=True)
            with denial.open("xb") as f:
                f.write(gzip.compress(raw, mtime=0))
            append(budget.folder/"denials.jsonl", dict(url=exc.url, status=exc.code,
                   bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), body=denial.name, utc_ns=time.time_ns()))
            budget.finish(rid, len(raw), complete=len(raw) <= cap, status=exc.code)
            if exc.code in (401, 403, 404, 429, 451) or 300 <= exc.code < 400:
                budget.block(host if exc.code in (403, 451) else key, "HTTP "+str(exc.code))
            raise TransportStop("HTTP "+str(exc.code)+": "+key) from None
        except TransportStop:
            budget.block(reservation[3], "redirect refused")
            budget.finish(reservation[0], 0, complete=False)
            raise
        except BaseException:
            budget.finish(reservation[0], 0, complete=False)
            raise TransportStop("network/redirect failure; reservation retained") from None
        if "html" in response.headers.get("Content-Type", "").lower():
            budget.block(reservation[3], "HTML/bot response")
            response.close()
            budget.finish(reservation[0], 0, complete=False)
            raise TransportStop("HTML/bot response refused")
        return BoundedResponse(response, budget, reservation)

    request.OpenerDirector.open, request.HTTPRedirectHandler.redirect_request = opened, no_redirect
    try:
        yield budget
    finally:
        request.OpenerDirector.open, request.HTTPRedirectHandler.redirect_request = original, redirect
