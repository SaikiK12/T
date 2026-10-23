"""Small free daily series for regime and context work: crypto sentiment, US rates and liquidity, stablecoin supply and
DeFi activity. Each source response is kept as fetched in data/macro/raw/ and parsed to data/macro/<name>.parquet with
columns t (ms, 00:00 UTC of the observation date) and value.

| name | source | note |
|---|---|---|
| fng | alternative.me Fear & Greed index | daily since 2018-02 |
| ust_3m ... breakeven_10y | FRED graph CSV (no key) | market series; weekly ones (fed_assets, tga) are dated by their week, published days later |
| stable_total, stable_usdt, stable_usdc | DefiLlama stablecoins | circulating USD |
| defi_tvl, dex_volume, defi_fees, options_volume | DefiLlama | revised as DefiLlama adds or reclassifies protocols |
| krw_usd, cny_usd, sp500, nasdaq, wti, ust_real_10y, nfci, stl_fsi, m2 | FRED graph CSV | KRW per USD prices the Korean premium; nfci, stl_fsi and m2 are weekly |
| btc_hashrate, btc_tx, btc_addresses, btc_miner_rev, btc_fees_usd, btc_mempool | blockchain.com charts API | Bitcoin on-chain, daily, the day's value known after it ends |

Plus one table, `cot_crypto.parquet`: the CFTC Traders in Financial Futures report (futures only, public Socrata API)
for every crypto contract (CME Bitcoin, Micro Bitcoin, Ether, Micro Ether, Micro SOL and XRP, Coinbase perp-style
contracts), one row per market and Tuesday report date, with dealer, asset-manager, leveraged-fund, other and
non-reportable longs and shorts. The report is released on the Friday after its Tuesday (`available_t` = report date
+ 4 days, 00:00 UTC); US government shutdowns delayed releases by weeks (late 2018-19, late 2025), which that column
does not know.

Not point-in-time: FRED and DefiLlama serve their latest vintage. A lane that uses a weekly or revised series lags it
by its publication delay and says so in its PREREG.

usage: python scripts/fetch_macro.py
"""
import csv
import hashlib
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

OUT = data.ROOT / "macro"
FRED = {"ust_3m": "DGS3MO", "ust_2y": "DGS2", "ust_10y": "DGS10", "curve_10y2y": "T10Y2Y", "fed_funds": "DFF",
        "vix": "VIXCLS", "hy_spread": "BAMLH0A0HYM2", "usd_broad": "DTWEXBGS", "breakeven_10y": "T10YIE",
        "fed_assets": "WALCL", "rrp": "RRPONTSYD", "tga": "WTREGEN", "krw_usd": "DEXKOUS", "cny_usd": "DEXCHUS",
        "sp500": "SP500", "nasdaq": "NASDAQCOM", "wti": "DCOILWTICO", "ust_real_10y": "DFII10", "nfci": "NFCI",
        "stl_fsi": "STLFSI4", "m2": "WM2NS"}
BLOCKCHAIN = {"btc_hashrate": "hash-rate", "btc_tx": "n-transactions", "btc_addresses": "n-unique-addresses",
              "btc_miner_rev": "miners-revenue", "btc_fees_usd": "transaction-fees-usd", "btc_mempool": "mempool-size"}
COT_URL = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
COT_WHERE = ("market_and_exchange_names like '%BITCOIN%' OR market_and_exchange_names like '%ETHER%' OR "
             "market_and_exchange_names like '% SOL %' OR market_and_exchange_names like '%MICRO SOL%' OR "
             "market_and_exchange_names like '%XRP%'")
LLAMA = "https://api.llama.fi/overview/{}?excludeTotalDataChart=false&excludeTotalDataChartBreakdown=true&dataType={}"
SOURCES = {
    "fng": ("https://api.alternative.me/fng/?limit=0&format=json", "fng"),
    **{k: (f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={v}", "fred") for k, v in FRED.items()},
    "stable_total": ("https://stablecoins.llama.fi/stablecoincharts/all", "stable"),
    "stable_usdt": ("https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=1", "stable"),
    "stable_usdc": ("https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=2", "stable"),
    "defi_tvl": ("https://api.llama.fi/v2/historicalChainTvl", "tvl"),
    "dex_volume": (LLAMA.format("dexs", "dailyVolume"), "chart"),
    "defi_fees": (LLAMA.format("fees", "dailyFees"), "chart"),
    "options_volume": (LLAMA.format("options", "dailyNotionalVolume"), "chart"),
    **{k: (f"https://api.blockchain.info/charts/{v}?timespan=all&format=json&sampled=false", "bc")
       for k, v in BLOCKCHAIN.items()},
}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def day_ms(sec):
    return int(sec) // 86400 * 86_400_000


def parse(kind, raw):
    """(t ms, value) rows, sorted, one per day, missing values dropped."""
    rows = []
    if kind == "fng":
        rows = [(day_ms(d["timestamp"]), float(d["value"])) for d in json.loads(raw)["data"]]
    elif kind == "fred":
        r = csv.reader(io.StringIO(raw.decode()))
        next(r)
        for date, v in r:
            if v not in ("", "."):
                rows.append((int(pd.Timestamp(date, tz="UTC").value // 1_000_000), float(v)))
    elif kind == "stable":
        rows = [(day_ms(d["date"]), float(d["totalCirculatingUSD"].get("peggedUSD", 0.0))) for d in json.loads(raw)]
    elif kind == "tvl":
        rows = [(day_ms(d["date"]), float(d["tvl"])) for d in json.loads(raw)]
    elif kind == "chart":
        rows = [(day_ms(t), float(v)) for t, v in json.loads(raw)["totalDataChart"]]
    elif kind == "bc":
        rows = [(day_ms(d["x"]), float(d["y"])) for d in json.loads(raw)["values"]]
    df = pd.DataFrame(rows, columns=["t", "value"]).drop_duplicates("t", keep="last").sort_values("t")
    return df.reset_index(drop=True)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.5.0"})        # FRED drops other agents
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def parse_cot(raw):
    """One row per market and report date: identity columns, then every position count as a float."""
    df = pd.DataFrame(json.loads(raw))
    ident = ["market_and_exchange_names", "cftc_contract_market_code"]
    num = sorted(c for c in df.columns if c not in ident and (c.endswith("_all") or "positions" in c
                                                               or c.startswith("open_interest")))
    out = df[ident].copy()
    out.insert(0, "t", [int(pd.Timestamp(x[:10], tz="UTC").value // 1_000_000) for x in df.report_date_as_yyyy_mm_dd])
    out.insert(1, "available_t", out.t + 4 * 86_400_000)
    out[num] = df[num].apply(pd.to_numeric, errors="coerce")
    return out.sort_values(["cftc_contract_market_code", "t"], ignore_index=True)


def cot():
    q = urllib.parse.urlencode({"$where": COT_WHERE, "$limit": 50000, "$order": "report_date_as_yyyy_mm_dd"})
    raw = get(f"{COT_URL}?{q}")
    df = parse_cot(raw)
    (OUT / "raw" / "cot_crypto.json").write_bytes(raw)
    df.to_parquet(OUT / "cot_crypto.parquet", index=False)
    log(f"cot_crypto: {len(df)} rows, {df.cftc_contract_market_code.nunique()} markets")
    return {"url": COT_URL, "where": COT_WHERE, "rows": len(df), "markets": int(df.cftc_contract_market_code.nunique()),
            "raw_sha256": hashlib.sha256(raw).hexdigest()}


def main():
    (OUT / "raw").mkdir(parents=True, exist_ok=True)
    manifest = {}
    try:
        manifest["cot_crypto"] = cot()
    except Exception as e:                         # one source failing must not stop the others
        log(f"cot_crypto: FAILED {type(e).__name__}: {e}")
        manifest["cot_crypto"] = {"url": COT_URL, "error": f"{type(e).__name__}: {e}"}
    for name, (url, kind) in SOURCES.items():
        try:
            raw = get(url)
            df = parse(kind, raw)
        except Exception as e:                     # one source failing must not stop the others
            log(f"{name}: FAILED {type(e).__name__}: {e}")
            manifest[name] = {"url": url, "error": f"{type(e).__name__}: {e}"}
            continue
        (OUT / "raw" / f"{name}.{'csv' if kind == 'fred' else 'json'}").write_bytes(raw)
        df.to_parquet(OUT / f"{name}.parquet", index=False)
        first, last = (pd.Timestamp(df.t.iloc[i], unit="ms").date().isoformat() for i in (0, -1))
        manifest[name] = {"url": url, "rows": len(df), "first": first, "last": last,
                          "raw_sha256": hashlib.sha256(raw).hexdigest()}
        log(f"{name}: {len(df)} days {first} .. {last}")
        time.sleep(0.5)
    (OUT / "manifest.json").write_text(json.dumps({"fetched_utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()),
                                                   "series": manifest}, indent=1))


if __name__ == "__main__":
    main()
