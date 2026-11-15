"""Run independent reasoning workers on different models over one shared evidence pack.

Each worker gets the same facts and a distinct role, on a distinct model, so disagreement is
informative rather than an echo. Answers are saved verbatim; the coordinator verifies every
factual claim against the repo before acting on any of it. No worker writes to the repo.

usage: python scripts/ai_workers.py --pack /tmp/pack.md --out /tmp/workers
Requires QWEN_API_KEY and QWEN_BASE in the environment.
"""
import argparse
import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROLES = {
    "value": (
        "qwen3.7-max",
        "You are a quant portfolio strategist. Given ONLY the evidence pack, rank the candidate "
        "work items by expected value to the owner, whose goal is a reproducible positive NET "
        "return at executable costs. The owner has ~50 recorded nulls and one edge confirmed out "
        "of sample at ~1%/yr. Be blunt about which work is theatre. For each of your top 3, state "
        "the binding constraint it removes, the cheapest decisive test, and what would falsify it. "
        "Do not invent numbers; cite the pack. Max 500 words.",
    ),
    "referee": (
        "deepseek-v4-pro",
        "You are a hostile statistical referee. Given ONLY the evidence pack, find the ways the "
        "proposed next work could produce a false positive. Focus on: post-hoc conditioning, "
        "selection on the same sample, tail risk masquerading as edge, and multiplicity. The pack "
        "notes a dose filter (unlock/ADV < 0.82) was observed AFTER the run on the six worst "
        "losses. Say exactly how that must be handled to be admissible. Max 450 words.",
    ),
    "risk": (
        "qwen3.7-plus",
        "You are a risk engineer for a small crypto book. Given ONLY the evidence pack, design the "
        "sizing and squeeze-protection model that the strongest per-event edge is explicitly "
        "blocked on. Per-event sd is 16.7%, worst short squeeze -132% gross plus -45% funding. "
        "Give concrete, pre-registerable rules (position cap, notional vs ADV, hard exit, funding "
        "veto) and the arithmetic that shows a repeat of the worst event cannot ruin the book. "
        "State which rules need data the pack does not contain. Max 500 words.",
    ),
    "prop": (
        "qwen3.7-plus",
        "You are a prop-firm evaluation specialist. Given ONLY the evidence pack, assess whether "
        "any listed edge can pass a funded-account challenge (typical: 10% profit target, 5% daily "
        "loss, 10% max drawdown, min trading days). Carry is ~1%/yr with 0.07% max DD; the event "
        "edge is +3.24% per event with a -132% tail. Say plainly which constraints bind and whether "
        "a rules-compliant variant is conceivable. Do not assume the pack's numbers are tradable at "
        "size. Max 450 words.",
    ),
}


def ask(base, key, model, system, pack, timeout=180):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": pack}],
        "temperature": 0.4,
        "max_tokens": 6000,
    }).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode())
    msg = d["choices"][0]["message"]
    # reasoning models may put the answer in reasoning_content and leave content empty
    text = msg.get("content") or ""
    if not text.strip():
        text = msg.get("reasoning_content") or ""
    return text, d.get("usage", {})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--roles", default=",".join(ROLES))
    a = ap.parse_args()
    key, base = os.environ["QWEN_API_KEY"], os.environ["QWEN_BASE"]
    pack = Path(a.pack).read_text()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    roles = [r for r in a.roles.split(",") if r in ROLES]

    def run(role):
        model, system = ROLES[role]
        t0 = time.time()
        for attempt in range(3):
            try:
                text, usage = ask(base, key, model, system, pack)
                (out / f"{role}.md").write_text(f"# {role} ({model})\n\n{text}\n")
                return role, model, len(text), round(time.time() - t0, 1), usage.get("total_tokens")
            except Exception as e:
                if attempt == 2:
                    (out / f"{role}.error").write_text(f"{type(e).__name__}: {e}\n")
                    return role, model, 0, round(time.time() - t0, 1), str(e)[:80]
                time.sleep(3 * (attempt + 1))

    with ThreadPoolExecutor(len(roles)) as ex:
        for role, model, n, secs, tok in ex.map(run, roles):
            print(f"{role:8s} {model:18s} chars={n:5d} {secs:6.1f}s tokens={tok}", flush=True)


if __name__ == "__main__":
    main()
