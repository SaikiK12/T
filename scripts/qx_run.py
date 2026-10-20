"""Run a family lane on the qx engine, end to end: verify, check inputs, run, summarise, register.

A lane is a folder experiments/<lane>/ with:
- PREREG.md, frozen with lab.prereg.freeze(). It names its registry id ("Registry id: R###") and lists every input in
  a fenced block:

      ```inputs
      engine/specs/x.toml  <sha256>        # or a path inside the lane
      experiments/x/legs.csv  <sha256>
      rebuild: python scripts/x_events.py --out {tmp}   # optional; must reproduce legs.csv byte for byte
      ```
- spec.toml, the qx spec (its hash is one of the inputs).

Steps: prereg.verify -> input hashes -> optional byte-for-byte rebuild -> `qx events spec.toml` (or `qx spread` when the
spec has venue `sets`) -> results/report.json and the tables -> results/SUMMARY.md (1x/2x/3x, reality check, null,
survivors) -> with --register, the registry row (trials = the family's strategy count, verdict PARTIAL if any strategy
passes gate 0, else NULL).

usage: python scripts/qx_run.py experiments/<lane> [--register]
"""
import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg, registry  # noqa: E402

QX = ROOT / "engine" / "target" / "release" / "qx"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def inputs(text):
    m = re.search(r"```inputs\n(.*?)```", text, re.S)
    if not m:
        raise SystemExit("PREREG has no ```inputs block")
    files, rebuild = {}, None
    for line in m.group(1).splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        if line.startswith("rebuild:"):
            rebuild = line[len("rebuild:"):].strip()
        else:
            path, h = line.split()
            files[path] = h
    return files, rebuild


def check(lane, text):
    files, rebuild = inputs(text)
    for path, h in files.items():
        if sha(ROOT / path) != h:
            raise SystemExit(f"input {path} changed: {sha(ROOT / path)} != frozen {h}")
    if rebuild:
        with tempfile.TemporaryDirectory() as d:
            cmd = [sys.executable if c == "python" else c for c in shlex.split(rebuild.format(tmp=d))]
            subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True)
            for path in files:
                built = Path(d) / Path(path).name
                if (ROOT / path).parent.resolve() != Path(lane).resolve():
                    continue                        # the rebuild writes the lane's own files; others are hashed only
                if built.exists() and built.read_bytes() != (ROOT / path).read_bytes():
                    raise SystemExit(f"rebuilt {Path(path).name} differs from the frozen file")
    log(f"{len(files)} inputs match the frozen hashes" + ("; rebuild is byte-identical" if rebuild else ""))


def fmt(x, nd=2, sign=True):
    return "n/a" if x is None or x != x else (f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}")


def summary(rep, rid, psha):
    S = rep["strategies"]
    lines = [f"# {rep['name']} ({rid}): {rep['verdict']}", "",
             f"- **Family:** {rep['trials']} strategies; {rep['events_in']} event legs, {rep['priced_legs']} priced, "
             f"{rep['no_market']} with no traded instrument at the event hour.",
             f"- **Clusters by type:** " + ", ".join(f"{k} {v}" for k, v in rep["clusters"].items()) + ".",
             f"- **Legs by venue:** " + ", ".join(f"{k} {v}" for k, v in rep["legs_by_venue"].items()) + ".",
             f"- **Reality check:** the family's max-t null has its 95th percentile at {rep['rc_null_p95']:.2f}.",
             f"- **Survivors (all gates):** {', '.join(rep['survivors']) or 'none'}.",
             f"- **Prereg sha:** {psha[:12]}. Costs {', '.join(f'{c * 1e4:.0f}' for c in rep['spec']['costs'])} bp "
             f"round trip at 1x/2x/3x.", "",
             "## Top 15 by t (1x)", "",
             "| Strategy | n | 1x mean | Median | Hit | t | RC p | Halves | 2025+ (n) | 2x | 3x | Null p | Pass |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in S[:15]:
        s, s2, s3 = r["stats"][0], r["stats"][1], r["stats"][2]
        nl = r.get("null") or {}
        lines.append(f"| {r['label']} | {s['n']} | {fmt(s['mean_pct'])}% | {fmt(s['median_pct'])}% | {s['hit']:.0%} | "
                     f"{fmt(s['t'], 2, False)} | {r['p_rc']:.4f} | {fmt(s['half1_pct'])} / {fmt(s['half2_pct'])} | "
                     f"{fmt(s['y2025_pct'])}% ({s['y2025_n']}) | {fmt(s2['mean_pct'])}% | {fmt(s3['mean_pct'])}% | "
                     f"{nl.get('p', float('nan')):.4f} | {'**yes**' if r['pass'] else 'no'} |")
    lines += ["", "## Bottom 5 by t (1x)", ""]
    for r in S[-5:]:
        s = r["stats"][0]
        lines.append(f"- {r['label']}: n {s['n']}, {fmt(s['mean_pct'])}%, t {fmt(s['t'])}")
    rc = [r for r in S if r["gates"].get("RC")]
    if rc:
        lines += ["", "## Strategies that clear the reality check", ""]
        for r in rc:
            ro = r.get("robustness") or {}
            yr = ", ".join(f"{y} {v['mean_pct']:+.2f}% ({v['n']})" for y, v in (ro.get("per_year") or {}).items())
            lines.append(f"- **{r['label']}**: gates {r['gates']}; null {json.dumps(r.get('null'))}")
            lines.append(f"  - per year: {yr}")
            if ro:
                lines.append(f"  - without the top 3 legs: {fmt(ro['drop_top3_legs']['mean_pct'])}% (t "
                             f"{fmt(ro['drop_top3_legs']['t'])}); premove in direction {fmt(ro['premove_in_direction']['mean_pct'])}%; "
                             f"by venue " + ", ".join(f"{v} {fmt(x['mean_pct'])}% (n {x['n']})" for v, x in ro['by_venue'].items()))
    return "\n".join(lines) + "\n"


def spread_summary(rep, rid, psha):
    S = rep["strategies"]
    c = rep["spec"]["costs"]
    lines = [f"# {rep['name']} ({rid}): {rep['verdict']}", "",
             f"- **Family:** {rep['trials']} books; {rep['coins']} coins on 2+ venues ("
             + ", ".join(f"{k} {v}" for k, v in rep["coins_by_venue"].items()) + ").",
             f"- **Reality check:** the family's max-t null (blocks of {rep['spec']['block_days']} days) has its 95th "
             f"percentile at {rep['rc_null_p95']:.2f}.",
             f"- **Survivors (all gates):** {', '.join(rep['survivors']) or 'none'}.",
             f"- **Prereg sha:** {psha[:12]}. Costs {', '.join(f'{x * 1e4:.0f}' for x in c)} bp per leg per side at "
             f"1x/2x/3x; hurdle {rep['spec']['hurdle_ann_pct']}%/yr.", "",
             "## Venue sets", "", "| Set | Lookback | From | Coins ever eligible | Mean coins per day at or above threshold |",
             "|---|---|---|---|---|"]
    for x in rep["sets"]:
        lines.append(f"| {x['set']} | {x['lookback']} d | {x['window_from']} | {x['coins_ever']} | "
                     + ", ".join(f">={float(k) * 100:.0f}%: {v:.1f}" for k, v in x["mean_candidates"].items()) + " |")
    lines += ["", "## Top 15 by t (1x)", "",
              "| Book | From | 1x %/yr | 2x | 3x | Sharpe | t | NW t | RC p | Halves bp/day | 2025+ bp/day | Trimmed | Max DD | "
              "Funding share | Held | Trades | Pass |", "|" + "---|" * 17]
    for r in S[:15]:
        s = r["stats"]
        lines.append(f"| {r['label']} | {r['window_from']} | {fmt(s[0]['ann_pct'])} | {fmt(s[1]['ann_pct'])} | "
                     f"{fmt(s[2]['ann_pct'])} | {fmt(s[0]['sharpe'])} | {fmt(s[0]['t'])} | {fmt(s[0]['t_nw'])} | "
                     f"{r['p_rc']:.4f} | {fmt(s[0]['half1_bp'])} / {fmt(s[0]['half2_bp'])} | {fmt(s[0]['recent_bp'])} | "
                     f"{fmt(s[0]['trimmed_bp'])} | {fmt(s[0]['max_dd_pct'], 1)}% | {fmt(r['funding_share'], 2, False)} | "
                     f"{fmt(r['avg_held'], 1, False)} | {r['trades']} | {'**yes**' if r['pass'] else 'no'} |")
    lines += ["", "## Bottom 5 by t (1x)", ""]
    for r in S[-5:]:
        s = r["stats"][0]
        lines.append(f"- {r['label']}: {fmt(s['ann_pct'])}%/yr, t {fmt(s['t'])}")
    near = [r for r in S if r["gates"].get("RC")]
    if near:
        lines += ["", "## Books that clear the reality check", ""]
        lines += [f"- **{r['label']}**: gates {r['gates']}" for r in near]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lane")
    ap.add_argument("--register", action="store_true")
    a = ap.parse_args()
    lane = (ROOT / a.lane).resolve()
    pre = lane / "PREREG.md"
    psha = prereg.verify(pre)
    text = pre.read_text()
    log("prereg sha", psha[:12])
    check(lane, text)
    if not QX.exists():
        subprocess.run(["cargo", "build", "--release", "--manifest-path", str(ROOT / "engine" / "Cargo.toml")], check=True)
    out = lane / "results"
    out.mkdir(exist_ok=True)
    kind = "spread" if "sets" in tomllib.loads((lane / "spec.toml").read_text()) else "events"
    with open(lane / "run.log", "a") as f:
        subprocess.run([str(QX), kind, str(lane / "spec.toml")], cwd=ROOT, check=True, stderr=f,
                       env={**os.environ, "QX_DATA": str(ROOT / "data")})
    rep = json.loads((out / "report.json").read_text())
    rid = re.search(r"Registry id:\*?\*?\s*(R\d+)", text).group(1)
    (out / "SUMMARY.md").write_text((spread_summary if kind == "spread" else summary)(rep, rid, psha))
    log(f"{rid} {rep['verdict']}; survivors {rep['survivors']}; summary in {out / 'SUMMARY.md'}")
    if a.register:
        verdict = "PARTIAL" if rep["survivors"] else "NULL"
        best = rep["strategies"][0]
        if kind == "spread":
            b = best["stats"]
            note = (f"qx spread family; survivors {rep['survivors'] or 'none'}; best {best['label']} "
                    f"{b[0]['ann_pct']:+.2f}%/yr t {b[0]['t']:.2f} NW {b[0]['t_nw']:.2f} RC p {best['p_rc']:.3f}; "
                    f"1x/2x/3x {b[0]['ann_pct']:+.2f}/{b[1]['ann_pct']:+.2f}/{b[2]['ann_pct']:+.2f}%/yr")
        else:
            note = (f"qx family; survivors {rep['survivors'] or 'none'}; best {best['label']} "
                    f"{best['stats'][0]['mean_pct']:+.2f}% t {best['stats'][0]['t']:.2f} RC p {best['p_rc']:.3f}")
        registry.append(str(ROOT / "registry" / "rounds.csv"), id=rid, date=time.strftime("%Y-%m-%d"),
                        lane=lane.name, title=re.search(r"^# PREREG: \S+ \(R\d+\)\. (.+)$", text, re.M).group(1),
                        status="DONE", verdict=verdict, trials=rep["trials"], prereg_sha=psha,
                        path=str(lane.relative_to(ROOT)),
                        notes=note)
        log(f"registered {rid} {verdict}, {rep['trials']} trials; program {registry.program_trials(str(ROOT / 'registry' / 'rounds.csv')):,}")


if __name__ == "__main__":
    main()
