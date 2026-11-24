"""The lab's outside view: how often a registered test in each family passed, from every experiment's FINDINGS, and the
prior chance that the next one passes (Ioannidis 2005, "Why most published research findings are false").

- **Classification.** The first line of a FINDINGS that names a verdict (or the title) is read for keywords:
  - pass: PASS, SURVIVE(S), REPLICATES, CONFIRMED;
  - fail: FAIL, NULL, REJECT, DOES NOT;
  - other: everything else (PARTIAL, a measurement, PENDING, INCONCLUSIVE, no verdict line).
  A line naming both a pass and a fail word counts as "other".
- **Family:** `registry/lane_families.csv`.
- **Ioannidis.** With prior odds R that the tested relationship is real, power 1 - beta and size alpha:
  P(pass) = ((1 - beta) R + alpha) / (R + 1);
  PPV = (1 - beta) R / (R - beta R + alpha), the chance that a pass is real.
  The family's historical pass rate is an upper bound on P(pass) for a new test: many past passes were in-sample and
  failed their confirmations, and no strategy has yet passed forward paper.

usage: python scripts/base_rates.py              (the table by family)
       python scripts/base_rates.py --family carry --power 0.5 --alpha 0.0026
"""
import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PASS = re.compile(r"\b(PASS(ES|ED)?|SURVIVES?|REPLICATES|CONFIRMED)\b", re.I)
FAIL = re.compile(r"\b(FAIL(S|ED)?|NULL|REJECT(ED)?|DOES NOT)\b", re.I)


def classify(text):
    """'pass', 'fail' or 'other' from a FINDINGS text."""
    lines = text.splitlines()
    head = [ln for ln in lines if re.match(r"\s*\**\s*verdict", ln, re.I)]
    line = head[0] if head else (lines[0] if lines else "")
    p, f = bool(PASS.search(line)), bool(FAIL.search(line))
    if p and not f:
        return "pass"
    if f and not p:
        return "fail"
    if not head and lines:                      # no verdict line: the title alone, if it is clear
        return "other"
    return "other"


def families(path=ROOT / "registry" / "lane_families.csv"):
    with open(path, newline="") as f:
        return {r["lane"]: r["family"] for r in csv.DictReader(f)}


def table(root=ROOT):
    fam = families(root / "registry" / "lane_families.csv")
    out = defaultdict(Counter)
    for p in sorted((root / "experiments").glob("*/FINDINGS.md")):
        lane = p.parent.name
        out[fam.get(lane, "unmapped")][classify(p.read_text(encoding="utf-8", errors="replace"))] += 1
    return out


def p_pass(pi, power, alpha):
    """Chance a new test passes, with prior probability pi that the effect is real."""
    return pi * power + (1 - pi) * alpha


def ppv(pi, power, alpha):
    """Chance a pass is real (Ioannidis's PPV, written with pi = R / (R + 1))."""
    num = pi * power
    return num / (num + (1 - pi) * alpha) if num + (1 - pi) * alpha > 0 else 0.0


def implied_prior(pass_rate, power, alpha):
    """The prior pi that makes p_pass equal an observed pass rate (clipped to [0, 1])."""
    if power <= alpha:
        return 0.0
    return min(1.0, max(0.0, (pass_rate - alpha) / (power - alpha)))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--family")
    ap.add_argument("--power", type=float, default=0.5)
    ap.add_argument("--alpha", type=float, default=0.0026, help="the rule's size (t >= 2.8 one-sided: 0.0026)")
    a = ap.parse_args(argv)
    t = table()
    rows = []
    for f, c in sorted(t.items(), key=lambda kv: -sum(kv[1].values())):
        decided = c["pass"] + c["fail"]
        rows.append((f, c["pass"], c["fail"], c["other"], c["pass"] / decided if decided else None))
    print("| Family | Pass | Fail or null | Other | Pass share of decided |\n|---|---|---|---|---|")
    for f, p, n, o, r in rows:
        print(f"| {f} | {p} | {n} | {o} | {'' if r is None else f'{r:.0%}'} |")
    tot = Counter()
    for c in t.values():
        tot.update(c)
    print(f"| all | {tot['pass']} | {tot['fail']} | {tot['other']} | {tot['pass'] / (tot['pass'] + tot['fail']):.0%} |")
    if a.family:
        c = t.get(a.family, Counter())
        decided = c["pass"] + c["fail"]
        rate = (c["pass"] + 1) / (decided + 2)                     # Laplace: no family reads as 0 or 1
        pi = implied_prior(rate, a.power, a.alpha)
        print(f"\n{a.family}: pass rate {rate:.2f} (Laplace, {decided} decided) -> implied prior {pi:.2f}; "
              f"at power {a.power:g} and size {a.alpha:g}: P(pass) {p_pass(pi, a.power, a.alpha):.2f}, "
              f"PPV {ppv(pi, a.power, a.alpha):.2f}")
    return rows


if __name__ == "__main__":
    main(sys.argv[1:])
