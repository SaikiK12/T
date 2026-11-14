"""R424 sole offline fixed CDE/Kraken net proxy screen; no native journal or HTTP."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab import prereg, registry  # noqa: E402
from lab.cde_carry_screen import friction, replay, text  # noqa: E402

LANE = ROOT / "experiments/cde_carry_screen_v1"
SOURCE = ROOT / "research/intake/funding_notional_20261103"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    frozen = prereg.verify(LANE / "PREREG.md")
    manifest = LANE / "inputs.json"
    if sha(manifest) + "  experiments/cde_carry_screen_v1/inputs.json" not in (LANE / "PREREG.md").read_text():
        raise ValueError("unfrozen economic manifest")
    files = json.loads(manifest.read_text())["sha256"]
    for path, wanted in files.items():
        if not (ROOT / path).resolve().is_relative_to(ROOT) or sha(ROOT / path) != wanted:
            raise ValueError("frozen input drift: " + path)
    for path in [*files, "experiments/cde_carry_screen_v1/inputs.json",
                 "experiments/cde_carry_screen_v1/PREREG.md", "experiments/cde_carry_screen_v1/PREREG.sha256"]:
        if subprocess.check_output(["git", "show", "HEAD:" + path], cwd=ROOT) != (ROOT / path).read_bytes():
            raise ValueError("economic input not committed: " + path)
    return frozen


def body(folder, receipt):
    raw = gzip.decompress((folder / receipt["body"]).read_bytes())
    if receipt["status"] != 200 or receipt.get("error") or not receipt.get("response_complete", True):
        raise ValueError("failed input receipt")
    if len(raw) != receipt.get("bytes_read", receipt.get("bytes")) or hashlib.sha256(raw).hexdigest() != receipt["sha256"]:
        raise ValueError("raw receipt body hash changed")
    return json.loads(raw, parse_float=str)


def epoch(value):
    d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if d.tzinfo is None or d.timestamp() % 3600:
        raise ValueError("nonhour or naive source timestamp")
    return int(d.timestamp())


def unique(rows, field, *, scale=1, iso=False):
    out = {}
    for row in rows:
        t = epoch(row[field]) if iso else int(row[field]) // scale
        if t in out:
            raise ValueError("duplicate source timestamp")
        out[t] = row
    return out


def load_sources(cfg):
    inputs = {coin: {"cde_bars": {}} for coin in cfg["instruments"]}
    for folder in ("cde_carry_bars_20261107", "cde_bar_edges_20261107"):
        base = SOURCE / folder
        for receipt in json.loads((base / "acquisition.json").read_text())["requests"]:
            if not receipt["response_complete"] or len(gzip.decompress((base / receipt["body"]).read_bytes())) != receipt["bytes_read"]:
                raise ValueError("incomplete candle source")
            coin = receipt["body"][:3]
            instrument = cfg["instruments"][coin]["cde"]
            wanted = f"https://api.coinbase.com/api/v3/brokerage/market/products/{instrument}/candles?start={receipt['requested_start']}&end={receipt['requested_end']}&granularity=ONE_HOUR&limit=350"
            if receipt["url"] != wanted:
                raise ValueError("wrong CDE candle identity")
            bars = unique(body(base, receipt)["candles"], "start")
            if bars.keys() & inputs[coin]["cde_bars"].keys():
                raise ValueError("overlapping candle pages")
            inputs[coin]["cde_bars"].update(bars)
    base = SOURCE / "kraken_eea_20261106"
    receipts = {r["name"]: r for r in json.loads((base / "acquisition.json").read_text())["requests"]}
    for coin, instrument in cfg["instruments"].items():
        historical = SOURCE / "coinbase_public_history_20261107"
        receipt = json.loads((historical / (coin + ".receipt.json")).read_text())
        wanted = f"https://www.coinbase.com/api/mda/v1/instruments/CDE/{instrument['mda']}/funding?result_limit=2160"
        if receipt["url"] != wanted:
            raise ValueError("wrong MDA source identity")
        receipt = dict(receipt, body=coin + ".body.gz", sha256=receipt["body_sha256"])
        rows = body(historical, receipt)["results"]
        if any(r["symbol"] != instrument["mda"] for r in rows):
            raise ValueError("MDA instrument drift")
        inputs[coin]["cde_rates"] = {t: row["funding_rate"] for t, row in unique(rows, "event_time", iso=True).items()}
        key = instrument["kraken_key"]
        receipt = receipts[f"kraken_{key}_funding"]
        if receipt["url"] != "https://futures.kraken.com/derivatives/api/v3/historical-funding-rates?symbol=" + instrument["kraken"]:
            raise ValueError("wrong Kraken funding identity")
        obj = body(base, receipt)
        if obj["result"] != "success":
            raise ValueError("Kraken funding failure")
        inputs[coin]["kraken_rates"] = {t: row["fundingRate"] for t, row in unique(obj["rates"], "timestamp", iso=True).items()}
        mark_rows = []
        for suffix in ("mark", "mark_tail"):
            receipt = receipts[f"kraken_{key}_{suffix}"]
            if not receipt["url"].startswith("https://futures.kraken.com/api/charts/v1/mark/" + instrument["kraken"] + "/1h?"):
                raise ValueError("wrong Kraken mark identity")
            mark_rows.extend(body(base, receipt)["candles"])
        inputs[coin]["kraken_marks"] = unique(mark_rows, "time", scale=1000)
    return inputs


def main():
    frozen = verify()
    out = LANE / "results"
    out.mkdir(exist_ok=True)
    with (out / "RUN_STARTED.json").open("x") as f:
        f.write(json.dumps(dict(prereg_sha256=frozen, started_utc=datetime.now(timezone.utc).isoformat(),
                               commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip())) + "\n")
    try:
        cfg = json.loads((LANE / "cases.json").read_text())
        sources = load_sources(cfg)
        parent = json.loads((ROOT / "experiments/eea_execution_v1/results/report.json").read_text())
        scenarios, used_slips = [], {}
        for coin, instrument in cfg["instruments"].items():
            slips = friction(parent, coin)
            used_slips[coin] = {v: {k: text(x) for k, x in row.items()} for v, row in slips.items()}
            for direction in (1, -1):
                for multiple in (1, 2, 3):
                    row = replay(**sources[coin], start=epoch(cfg["start"]), end=epoch(cfg["end"]),
                                 allowed_missing_cde_bars=[epoch(x) for x in cfg["allowed_missing_cde_bars"]],
                                 capital=cfg["capital"], lot=instrument["lot"], slips=slips,
                                 fees=cfg["fees"], multiple=multiple, direction=direction)
                    scenarios.append(dict(coin=coin, **row))
        result = dict(round="R424", prereg_sha256=frozen, predictive_trials=4,
                      program_trials=registry.program_trials(ROOT / "registry/rounds.csv"), scenarios=scenarios,
                      start=cfg["start"], end=cfg["end"], measured_book_friction_fractions=used_slips,
                      verdict="PARTIAL_PROXY_ECONOMICS_ONLY", out_of_sample=False,
                      prospective_days=0, executable_capacity_admitted=False,
                      cash_mark_bounds_certified=False, historical_fees_or_books_certified=False,
                      owner_access_verified=False, real_orders=False,
                      meaning="Every case retained; conditional historic-price net scenario, not broker cash or a proven strategy")
        verify()
        with (out / "report.json").open("x") as f:
            f.write(json.dumps(result, indent=2) + "\n")
        print(json.dumps(dict(verdict=result["verdict"], scenarios=len(scenarios),
                              outputs=[{k: r[k] for k in ("coin", "direction", "multiple", "state", "terminal_net")} for r in scenarios],
                              report_sha256=sha(out / "report.json"))))
    except BaseException as exc:
        with (out / "ERROR.json").open("x") as f:
            f.write(json.dumps(dict(error=type(exc).__name__ + ": " + str(exc))) + "\n")
        raise


if __name__ == "__main__":
    main()
