"""R426 sole registered partial-fill/inventory diagnostic on fixed archived Lighter fragments."""
from datetime import datetime, timezone
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab import prereg, registry  # noqa: E402
from lab.maker_pilot import num, replay  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

LANE = ROOT / "experiments/maker_pilot_v1"
SOURCE = ROOT / "research/intake/maker_pilot_20261107"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify():
    frozen = prereg.verify(LANE / "PREREG.md")
    manifest = LANE / "inputs.json"
    if sha(manifest) + "  experiments/maker_pilot_v1/inputs.json" not in (LANE / "PREREG.md").read_text():
        raise ValueError("manifest not frozen")
    files = json.loads(manifest.read_text())["sha256"]
    for path, wanted in files.items():
        if not (ROOT / path).resolve().is_relative_to(ROOT) or sha(ROOT / path) != wanted:
            raise ValueError("frozen input drift: " + path)
    for path in [*files, "experiments/maker_pilot_v1/inputs.json", "experiments/maker_pilot_v1/PREREG.md", "experiments/maker_pilot_v1/PREREG.sha256"]:
        if subprocess.check_output(["git", "show", "HEAD:" + path], cwd=ROOT) != (ROOT / path).read_bytes():
            raise ValueError("uncommitted input: " + path)
    return frozen


def epoch_us(s):
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()) * 1_000_000


def load_market(symbol, cfg):
    p = SOURCE / "metadata"
    receipt = json.loads((p / (symbol + ".receipt.json")).read_text())
    raw = gzip.decompress((p / receipt["body"]).read_bytes())
    if (receipt["status"] != 200 or receipt["error"] or not receipt["response_complete"]
            or len(raw) != receipt["bytes_read"] or hashlib.sha256(raw).hexdigest() != receipt["sha256"]):
        raise ValueError("metadata raw receipt failed")
    m, = json.loads(raw, parse_float=str)["order_book_details"]
    if m["symbol"] != symbol or m["market_id"] != cfg["market_id"] or m["status"] != "active":
        raise ValueError("metadata identity failed")
    if receipt["url"] != f"https://mainnet.zklighter.elliot.ai/api/v1/orderBookDetails?market_id={cfg['market_id']}":
        raise ValueError("metadata URL identity failed")
    root = SOURCE / "source/data/lighter_trades"
    q = pq.read_table(root / cfg["quote_file"]).to_pylist()
    quotes = [{**r, **{k: num(str(r[k])) for k in ("bid", "ask", "bq", "aq")}} for r in q]
    trades = None
    if cfg["trade_file"] is not None:
        t = pq.read_table(root / cfg["trade_file"]).to_pylist()
        trades = [{**r, "px": num(str(r["px"])), "sz": num(str(r["sz"]))} for r in t]
    return quotes, trades, dict(lot=str(Decimal(10) ** -m["supported_size_decimals"]),
                               tick=str(Decimal(10) ** -m["supported_price_decimals"]),
                               min_base=m["min_base_amount"], min_quote=m["min_quote_amount"])


def main():
    frozen = verify()
    out = LANE / "results"
    out.mkdir(exist_ok=True)
    with (out / "RUN_STARTED.json").open("x") as f:
        f.write(json.dumps(dict(prereg_sha256=frozen, started_utc=datetime.now(timezone.utc).isoformat(),
                               commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip())) + "\n")
    try:
        cfg = json.loads((LANE / "cases.json").read_text())
        rows = []
        for symbol, case in cfg["markets"].items():
            quotes, trades, meta = load_market(symbol, case)
            for usd in cfg["quote_usd"]:
                for profile, fees in cfg["fee_profiles"].items():
                    for multiple in (1, 2, 3):
                        r = replay(quotes, trades, **meta, start=epoch_us(cfg["start"]), end=epoch_us(cfg["end"]),
                                   quote_usd=usd, maker_fee=fees["maker"], taker_fee=fees["taker"], multiple=multiple,
                                   capital=cfg["capital"], assets=3, **cfg["timing"])
                        rows.append(dict(symbol=symbol, fee_profile=profile, **r))
        result = dict(round="R426", prereg_sha256=frozen, strategy_arms=12,
                      program_trials=registry.program_trials(ROOT / "registry/rounds.csv"), cases=rows,
                      start=cfg["start"], end=cfg["end"],
                      verdict="PARTIAL_EXECUTION_DIAGNOSTIC_ONLY", out_of_sample=False,
                      prospective_days=0, real_orders=False, deployed=False,
                      portfolio_return=None, recurring_income_rate=None, confidence_of_profit=None,
                      statement="Source fragment, assumed ack/clock/fee/minimum conditions and unmeasured funding; no certified economic net or successful strategy")
        verify()
        with (out / "report.json").open("x") as f:
            f.write(json.dumps(result, indent=2) + "\n")
        print(json.dumps(dict(verdict=result["verdict"], cases=len(rows),
                              summary=[dict(symbol=r["symbol"], profile=r["fee_profile"], quote_usd=r.get("quote_usd"), cost=r.get("multiple"), state=r["state"], fills=len(r.get("fills", [])), before_funding_pnl=r["pnl"]) for r in rows],
                              report_sha256=sha(out / "report.json"))))
    except BaseException as exc:
        with (out / "ERROR.json").open("x") as f:
            f.write(json.dumps(dict(error=type(exc).__name__ + ": " + str(exc))) + "\n")
        raise


if __name__ == "__main__":
    main()
