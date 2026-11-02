"""TradFi event stamper: public schedules and halt feeds that move stock, index and rates perps, each key stamped with the
time this recorder first saw it and every later revision. Schedules are revised in place and feeds roll over, so the
as-of-then view exists only if recorded (docs/LEADS.md, "events with public timestamps and no recorder").

Sources (public GET, no key, no login; User-Agent `lab/1`, no contact data):
  nasdaq_halts      every 5 min  nasdaqtrader.com RSS "tradehalts": symbol, halt time (ET), reason code (LUDP/LUDS
                    limit-up-down, T1 news pending, ...), resumption quote/trade times once set. A change row appears
                    when a halt gets its resumption times. Rolls over daily, so `gone` is not tracked.
  nasdaq_earnings   every 6 h    api.nasdaq.com earnings calendar for each weekday of today (ET) + 6 days: report date and
                    the pre-market / after-hours / not-supplied slot, fiscal quarter, consensus EPS and estimate count.
                    One request per date, 1.5 s apart (at most 5 per pass). Stamps when a date was first announced and
                    when it moves; the actual report time and EPS are not recorded here.
  fed_calendar      every 6 h    federalreserve.gov/json/calendar.json for the current month on: FOMC, speeches, testimony,
                    Beige Book, statistical releases (time as published, ET).
  treasury_auctions every 6 h    treasurydirect.gov upcoming auctions: announcement, close times (ET), offering amount.
Not available without a login or a contact address: SEC EDGAR (its fair-access policy asks for a contact in the
User-Agent; owner decision, not used), BLS release schedule and CME holiday calendar (HTTP 403), NYSE calendar page (404).

Journal: data/events/tradfi_calendar/events.csv and polls_<YYYYMM>.csv, the shared engine of scripts/event_journal.py
(columns and the baseline / new / gone / back / change events are described there). `event_time_raw` is the source's own
date and slot as published; `event_time_utc` is derived (ET -> UTC) only when the source gives a clock time.

usage: python scripts/record_tradfi_calendar.py [ensure|run [--once] [--force] [--only a,b]|status]
"""
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import event_journal as ej  # noqa: E402

OUT = ROOT / "data" / "events" / "tradfi_calendar"
NY = ZoneInfo("America/New_York")
URL = {
    "nasdaq_halts": "https://www.nasdaqtrader.com/rss.aspx?feed=tradehalts",
    "nasdaq_earnings": "https://api.nasdaq.com/api/calendar/earnings?date={date}",
    "fed_calendar": "https://www.federalreserve.gov/json/calendar.json",
    "treasury_auctions": "https://www.treasurydirect.gov/TA_WS/securities/upcoming?format=json",
}
EARN_DAYS = 7
MAP = {
    "nasdaq_halts": {"name": "ndaq:IssueName", "market": "ndaq:Market", "reason": "ndaq:ReasonCode",
                     "pause_price": "ndaq:PauseThresholdPrice", "resume_date": "ndaq:ResumptionDate",
                     "resume_quote": "ndaq:ResumptionQuoteTime", "resume_trade": "ndaq:ResumptionTradeTime",
                     "pub": "pubDate"},
    "nasdaq_earnings": {"date": "(request date)", "name": "name", "time": "time", "fiscal_qtr": "fiscalQuarterEnding",
                        "eps_forecast": "epsForecast", "n_est": "noOfEsts", "last_year_date": "lastYearRptDt"},
    "fed_calendar": {"type": "type", "month": "month", "days": "days", "time": "time", "location": "location",
                     "description": "description"},
    "treasury_auctions": {"type": "securityType", "term": "securityTerm", "description": "securityDescription",
                          "announcement_date": "announcementDate", "comp_close_date": "competitiveAuctionCloseDate",
                          "comp_close_time": "competitiveAuctionCloseTime",
                          "noncomp_close_date": "noncompetitiveAuctionCloseDate",
                          "noncomp_close_time": "noncompetitiveAuctionCloseTime", "issue_date": "issueDate",
                          "maturity_date": "maturityDate", "offering_amount": "offeringAmount",
                          "reopening": "reopening", "updated": "updatedTimestamp"},
}


def et_to_utc(date_s, clock_s, fmts):
    """Eastern wall clock as the source wrote it -> UTC string; '' when it does not parse."""
    for fmt in fmts:
        try:
            d = datetime.strptime(f"{date_s} {clock_s}".strip(), fmt).replace(tzinfo=NY)
            return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
    return ""


# ---- Nasdaq trade halts ---------------------------------------------------------------------------------------------
def parse_halts(raw):
    root = ET.fromstring(raw.lstrip(b"\xef\xbb\xbf"))
    out = {}
    for it in root.iter("item"):
        f = {c.tag.rsplit("}", 1)[-1]: (c.text or "").strip() for c in it}
        sym, d, t = f.get("IssueSymbol", ""), f.get("HaltDate", ""), f.get("HaltTime", "")
        if not (sym and d and t):
            continue
        fields = {"name": f.get("IssueName", ""), "market": f.get("Market", ""), "reason": f.get("ReasonCode", ""),
                  "pause_price": f.get("PauseThresholdPrice", ""), "resume_date": f.get("ResumptionDate", ""),
                  "resume_quote": f.get("ResumptionQuoteTime", ""), "resume_trade": f.get("ResumptionTradeTime", ""),
                  "pub": f.get("pubDate", "")}
        out[f"{sym}|{d}|{t}"] = {"fields": fields, "etime": (
            "ndaq:HaltDate+ndaq:HaltTime", f"{d} {t}", et_to_utc(d, t, ("%m/%d/%Y %H:%M:%S.%f", "%m/%d/%Y %H:%M:%S")))}
    return out


def fetch_halts(now_s):
    return parse_halts(ej.http_get(URL["nasdaq_halts"], headers={"Accept": "application/rss+xml, */*"})), None


# ---- Nasdaq earnings calendar ---------------------------------------------------------------------------------------
def earn_dates(now_s, n=EARN_DAYS):
    d0 = datetime.fromtimestamp(now_s, timezone.utc).astimezone(NY).date()
    return [d.isoformat() for d in (d0 + timedelta(days=i) for i in range(n)) if d.weekday() < 5]


def parse_earnings(raw, date):
    """Rows of one validated date; a mismatched/invalid partition fails the whole source poll.

    Returning an empty partition on error would falsely mark its old rows gone.
    A valid asOf with rows=[]/null remains a genuine empty result.
    """
    d = json.loads(raw)
    if not isinstance(d, dict) or not isinstance(d.get("data"), dict):
        raise ValueError("nasdaq earnings: missing data object")
    status = d.get("status")
    if status is not None and (not isinstance(status, dict) or str(status.get("rCode")) != "200"):
        raise ValueError("nasdaq earnings: unsuccessful status")
    data = d["data"]
    try:
        as_of = datetime.strptime(data.get("asOf", ""), "%a, %b %d, %Y").date().isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError("nasdaq earnings: invalid asOf") from exc
    if as_of != date:
        raise ValueError(f"nasdaq earnings: asOf {as_of} differs from requested {date}")
    if "rows" not in data:
        raise ValueError("nasdaq earnings: missing rows field")
    rows = data["rows"]
    if rows is None:
        rows = []
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise ValueError("nasdaq earnings: invalid rows")
    out = {}
    for r in rows:
        if not r.get("symbol"):
            continue
        fields = {"date": date, "name": ej.text(r.get("name")), "time": ej.text(r.get("time")),
                  "fiscal_qtr": ej.text(r.get("fiscalQuarterEnding")), "eps_forecast": ej.text(r.get("epsForecast")),
                  "n_est": ej.text(r.get("noOfEsts")), "last_year_date": ej.text(r.get("lastYearRptDt"))}
        out[f"{date}|{r['symbol']}"] = {"fields": fields, "etime": ("date+time", f"{date} {fields['time']}", "")}
    return out


def fetch_earnings(now_s):
    dates = earn_dates(now_s)
    items = {}
    for i, d in enumerate(dates):
        if i:
            time.sleep(ej.PACE_S)
        items.update(parse_earnings(ej.http_get(URL["nasdaq_earnings"].format(date=d), headers={"Accept": "application/json"}), d))
    return items, (lambda fields: fields.get("date") in dates)


# ---- Federal Reserve calendar ---------------------------------------------------------------------------------------
def fed_clock(days, clock):
    """'12:15 p.m.' on a single day of the month -> ('HH:MM' 24 h) or ''."""
    m = re.match(r"^\s*(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m\.?\s*$", clock or "", re.I)
    if not m or not str(days).strip().isdigit():
        return ""
    h = int(m.group(1)) % 12 + (12 if m.group(3).lower() == "p" else 0)
    return f"{h:02d}:{int(m.group(2) or 0):02d}:00"


def parse_fed(raw, month_from):
    d = json.loads(raw.lstrip(b"\xef\xbb\xbf"))
    ev = d.get("events")
    if not isinstance(ev, list):
        raise ValueError("fed: no events")
    out, seen = {}, {}
    for e in ev:
        month = e.get("month") or ""
        if not month or month < month_from:
            continue
        base = f"{e.get('type', '')}|{month}|{e.get('days', '')}|{e.get('title', '')}"
        n = seen[base] = seen.get(base, 0) + 1
        fields = {k: ej.text(e.get(k)) for k in ("type", "month", "days", "time", "location", "description")}
        clock = fed_clock(fields["days"], fields["time"])
        when = et_to_utc(f"{month}-{int(fields['days']):02d}", clock, ("%Y-%m-%d %H:%M:%S",)) if clock else ""
        out[f"{base}|{n}"] = {"fields": fields, "etime": ("month+days+time",
                                                          f"{month}|{fields['days']}|{fields['time']}", when)}
    return out


def fetch_fed(now_s):
    month_from = time.strftime("%Y-%m", time.gmtime(now_s))
    return parse_fed(ej.http_get(URL["fed_calendar"]), month_from), (lambda fields: fields.get("month", "") >= month_from)


# ---- Treasury auctions ----------------------------------------------------------------------------------------------
def parse_treasury(raw):
    d = json.loads(raw)
    if not isinstance(d, list):
        raise ValueError("treasury: expected a list")
    out = {}
    for r in d:
        key = r.get("cusip") or f"{r.get('securityTerm', '')}|{r.get('competitiveAuctionCloseDate', '')}"
        if not key.strip("|"):
            continue
        fields = {n: ej.text(r.get(k)) for n, k in MAP["treasury_auctions"].items()}
        day = fields["comp_close_date"][:10]
        out[key] = {"fields": fields, "etime": (
            "competitiveAuctionCloseDate+competitiveAuctionCloseTime", f"{fields['comp_close_date']} {fields['comp_close_time']}",
            et_to_utc(day, fields["comp_close_time"], ("%Y-%m-%d %I:%M %p",)))}
    return out


def fetch_treasury(now_s):
    return parse_treasury(ej.http_get(URL["treasury_auctions"])), None


SOURCES = [
    ej.Source("nasdaq_halts", 300, fetch_halts, "ndaq:IssueSymbol+HaltDate+HaltTime", MAP["nasdaq_halts"],
              track_gone=False, guard=False),
    ej.Source("nasdaq_earnings", 21600, fetch_earnings, "symbol", MAP["nasdaq_earnings"]),
    ej.Source("fed_calendar", 21600, fetch_fed, "type+month+days+title", MAP["fed_calendar"]),
    ej.Source("treasury_auctions", 21600, fetch_treasury, "cusip", MAP["treasury_auctions"], guard=False),
]


def main(argv=None):
    return ej.cli("tradfi_calendar", OUT, SOURCES, __file__, argv)


if __name__ == "__main__":
    sys.exit(main())
