"""Perp contract-list watcher: the public contract list of eight venues diffed every few minutes, so the moment a contract
appears, disappears or changes status, funding interval, tick, lot size, leverage or fee is stamped. Nobody publishes
those histories (a venue lists today's contracts, with a listing time at best), so first-seen times exist only if
recorded (docs/LEADS.md, "events with public timestamps and no recorder": new-instrument openings on Hyperliquid and
Lighter, TradFi perp launches, delistings). scripts/record_notices.py covers Binance announcements; Binance's own
fapi list is HTTP 451 from this box and is not worked around. data/mexc/contracts holds one MEXC dump a day; this
is the minute-resolution diff of the same list plus seven more venues.

Venues (one public GET each per poll, gzip, no key): mexc (contract/detail), lighter (orderBookDetails, perps),
hyperliquid (allPerpMetas: the main dex and every HIP-3 dex, e.g. xyz stocks), kucoin (contracts/active), gate (usdt
futures contracts), dydx (indexer perpetualMarkets), okx (SWAP instruments), bitget (usdt-futures contracts).

Journal (append-only): data/events/listings/events.csv, one row per event (shared engine: scripts/event_journal.py,
columns and event types in its docstring); polls_<YYYYMM>.csv, one row per attempt. `baseline` rows are the first sight
of the whole list and carry no first-seen information. The exchange's own listing time goes in event_time_raw (field
named in event_time_field; Gate and others give epoch seconds, MEXC/KuCoin/OKX/Lighter/Bitget milliseconds); the UTC
column is derived from it. Hyperliquid and dYdX publish none. Compared fields are the raw values named in the
`FIELDS` tables below, never prices, volumes or open interest.

usage: python scripts/record_listings.py [ensure|run [--once] [--force] [--only mexc,gate]|status]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import event_journal as ej  # noqa: E402

OUT = ROOT / "data" / "events" / "listings"
URL = {
    "mexc": "https://contract.mexc.com/api/v1/contract/detail",
    "lighter": "https://mainnet.zklighter.elliot.ai/api/v1/orderBookDetails?filter=perp",
    "hyperliquid": "https://api.hyperliquid.xyz/info",
    "kucoin": "https://api-futures.kucoin.com/api/v1/contracts/active",
    "gate": "https://api.gateio.ws/api/v4/futures/usdt/contracts",
    "dydx": "https://indexer.dydx.trade/v4/perpetualMarkets",
    "okx": "https://www.okx.com/api/v5/public/instruments?instType=SWAP",
    "bitget": "https://api.bitget.com/api/v2/mix/market/contracts?productType=usdt-futures",
}
# field name -> the venue's own key (dotted: nested). Raw values are stored as the venue sent them.
FIELDS = {
    "mexc": {"status": "state", "kind": "type", "tick": "priceUnit", "lot": "volUnit", "contract_size": "contractSize",
             "min_lev": "minLeverage", "max_lev": "maxLeverage", "taker_fee": "takerFeeRate",
             "maker_fee": "makerFeeRate", "opening_time": "openingTime", "hidden": "isHidden",
             "pre_market": "preMarket", "api_allowed": "apiAllowed", "appraisal": "appraisal"},
    "lighter": {"market_id": "market_id", "status": "status", "kind": "market_type", "taker_fee": "taker_fee",
                "maker_fee": "maker_fee", "min_base": "min_base_amount", "min_quote": "min_quote_amount",
                "price_dec": "price_decimals", "size_dec": "size_decimals",
                "imf_default": "default_initial_margin_fraction", "imf_min": "min_initial_margin_fraction",
                "mmf": "maintenance_margin_fraction", "frozen": "is_frozen", "hidden": "market_config.hidden",
                "trading_hours": "market_config.trading_hours", "deployer": "market_deployer",
                "start_ts": "start_timestamp", "end_ts": "end_timestamp"},
    "hyperliquid": {"is_delisted": "isDelisted", "lot": "szDecimals", "max_lev": "maxLeverage",
                    "only_isolated": "onlyIsolated", "margin_mode": "marginMode", "growth_mode": "growthMode",
                    "margin_table": "marginTableId", "fee_scale": "deployerFeeScale", "dex": "dex",
                    "asset_pos": "universe_position"},
    "kucoin": {"status": "status", "kind": "type", "settle": "settleCurrency", "tick": "tickSize", "lot": "lotSize",
               "max_lev": "maxLeverage", "funding_interval": "fundingRateGranularity", "expire": "expireDate",
               "is_inverse": "isInverse", "multiplier": "multiplier"},
    "gate": {"status": "status", "in_delisting": "in_delisting", "kind": "type", "contract_type": "contract_type",
             "tick": "order_price_round", "lot": "order_size_min", "min_lev": "leverage_min", "max_lev": "leverage_max",
             "funding_interval": "funding_interval", "taker_fee": "taker_fee_rate", "maker_fee": "maker_fee_rate",
             "pre_market": "is_pre_market", "multiplier": "quanto_multiplier",
             "circuit_breaker": "enable_circuit_breaker", "config_change_time": "config_change_time"},
    "dydx": {"status": "status", "kind": "marketType", "tick": "tickSize", "lot": "stepSize",
             "imf": "initialMarginFraction", "mmf": "maintenanceMarginFraction", "oi_lower_cap": "openInterestLowerCap",
             "oi_upper_cap": "openInterestUpperCap", "clob_pair": "clobPairId"},
    "okx": {"status": "state", "kind": "instCategory", "rule": "ruleType", "tick": "tickSz", "lot": "lotSz",
            "min_sz": "minSz", "max_lev": "lever", "cont_val": "ctVal", "open_type": "openType",
            "cont_td_sw": "contTdSwTime", "pre_mkt_sw": "preMktSwTime", "exp": "expTime", "auction_end": "auctionEndTime",
            "upcoming": "upcChg"},
    "bitget": {"status": "symbolStatus", "kind": "symbolType", "rwa": "isRwa", "price_place": "pricePlace",
               "price_step": "priceEndStep", "vol_place": "volumePlace", "min_trade": "minTradeNum",
               "size_mult": "sizeMultiplier", "min_lev": "minLever", "max_lev": "maxLever",
               "fund_interval": "fundInterval", "maker_fee": "makerFeeRate", "taker_fee": "takerFeeRate",
               "off_time": "offTime", "limit_open": "limitOpenTime", "maintain": "maintainTime",
               "delivery": "deliveryTime"},
}
KEY_FIELD = {"mexc": "symbol", "lighter": "symbol", "hyperliquid": "name", "kucoin": "symbol", "gate": "name",
             "dydx": "ticker", "okx": "instId", "bitget": "symbol"}
INTERVAL_S = {"mexc": 300, "lighter": 300, "hyperliquid": 300, "dydx": 300, "kucoin": 600, "okx": 600, "bitget": 600,
              "gate": 900}


def dig(d, path):
    for p in path.split("."):
        d = d.get(p) if isinstance(d, dict) else None
    return d


def build(venue, rec, key, etime):
    f = {n: ej.text(dig(rec, k)) for n, k in FIELDS[venue].items()}
    return key, {"fields": f, "etime": etime}


def listing_time(field, raw, unit_ms=True):
    return (field, ej.text(raw), ej.epoch_utc(raw, unit_ms)) if field else ("", "", "")


def parse_mexc(raw):
    d = json.loads(raw)
    if not d.get("success") or not isinstance(d.get("data"), list):
        raise ValueError(f"mexc: success={d.get('success')} code={d.get('code')}")
    return dict(build("mexc", r, r["symbol"], listing_time("createTime", r.get("createTime")))
                for r in d["data"] if r.get("symbol"))


def parse_lighter(raw):
    d = json.loads(raw)
    if d.get("code") != 200 or not isinstance(d.get("order_book_details"), list):
        raise ValueError(f"lighter: code={d.get('code')}")
    return dict(build("lighter", r, r["symbol"], listing_time("created_at", r.get("created_at")))
                for r in d["order_book_details"] if r.get("symbol") and r.get("market_type", "perp") == "perp")


def parse_hyperliquid(raw):
    metas = json.loads(raw)
    if not isinstance(metas, list) or not metas or "universe" not in metas[0]:
        raise ValueError("hyperliquid: unexpected allPerpMetas shape")
    out = {}
    for i, m in enumerate(metas):
        for pos, u in enumerate(m.get("universe", [])):
            if not u.get("name"):
                continue
            dex = "main" if ":" not in u["name"] else u["name"].split(":", 1)[0]
            out.setdefault(u["name"], build("hyperliquid", {**u, "dex": dex, "universe_position": pos}, u["name"],
                                            ("", "", ""))[1])
    return out


def parse_kucoin(raw):
    d = json.loads(raw)
    if str(d.get("code")) != "200000" or not isinstance(d.get("data"), list):
        raise ValueError(f"kucoin: code={d.get('code')}")
    return dict(build("kucoin", r, r["symbol"], listing_time("firstOpenDate", r.get("firstOpenDate")))
                for r in d["data"] if r.get("symbol"))


def parse_gate(raw):
    d = json.loads(raw)
    if not isinstance(d, list):
        raise ValueError("gate: expected a list")
    out = {}
    for r in d:
        if not r.get("name"):
            continue
        fld = "launch_time" if r.get("launch_time") else "create_time"
        out.update([build("gate", r, r["name"], listing_time(fld, r.get(fld), unit_ms=False))])
    return out


def parse_dydx(raw):
    d = json.loads(raw)
    if not isinstance(d.get("markets"), dict):
        raise ValueError("dydx: no markets")
    return dict(build("dydx", r, r.get("ticker") or k, ("", "", "")) for k, r in d["markets"].items())


def parse_okx(raw):
    d = json.loads(raw)
    if d.get("code") != "0" or not isinstance(d.get("data"), list):
        raise ValueError(f"okx: code={d.get('code')}")
    return dict(build("okx", r, r["instId"], listing_time("listTime", r.get("listTime")))
                for r in d["data"] if r.get("instId"))


def parse_bitget(raw):
    d = json.loads(raw)
    if d.get("code") != "00000" or not isinstance(d.get("data"), list):
        raise ValueError(f"bitget: code={d.get('code')}")
    out = {}
    for r in d["data"]:
        if not r.get("symbol"):
            continue
        fld = "launchTime" if r.get("launchTime") else "openTime"
        out.update([build("bitget", r, r["symbol"], listing_time(fld, r.get(fld) or None))])
    return out


PARSE = {"mexc": parse_mexc, "lighter": parse_lighter, "hyperliquid": parse_hyperliquid, "kucoin": parse_kucoin,
         "gate": parse_gate, "dydx": parse_dydx, "okx": parse_okx, "bitget": parse_bitget}


def fetcher(venue):
    def fetch(now_s):
        body = {"type": "allPerpMetas"} if venue == "hyperliquid" else None
        return PARSE[venue](ej.http_get(URL[venue], body)), None
    return fetch


SOURCES = [ej.Source(v, INTERVAL_S[v], fetcher(v), KEY_FIELD[v], FIELDS[v]) for v in URL]


def main(argv=None):
    return ej.cli("listings", OUT, SOURCES, __file__, argv)


if __name__ == "__main__":
    sys.exit(main())
