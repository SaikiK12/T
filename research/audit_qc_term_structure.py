"""Execute one fingerprinted tutorial roll-ranking snippet on invented contracts.

python -m research.audit_qc_term_structure /tmp/qc_term_02.html

Receive the pinned Method HTML separately. No network IO, LEAN installation,
History, scheduling, orders or full algorithm executes. No publisher code is
vendored. The logarithmic comparison is the separately referenced Method's
formula, not a silent correction to the joint source.
"""

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
from types import SimpleNamespace


COMMIT = "4a341890296f7e79e095508f06170c72ccaa629c"
URL = (f"https://raw.githubusercontent.com/QuantConnect/Tutorials/{COMMIT}/"
       "04%20Strategy%20Library/30%20Momentum%20Effect%20Combined%20with%20Term%20"
       "Structure%20in%20Commodities/02%20Method.html")
SHA256 = "c59a9992c1e9abb2ffb4e66712d72cda89d7b25538b28bd217041fb05bc556b9"
BLOCK_SHA256 = "b25a189c2d7c3037203582fe04f3248a6e95858942f813991cbc7c7af6be0cf9"


class PythonBlocks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.blocks, self.inside = [], False

    def handle_starttag(self, tag, attrs):
        if tag == "pre" and dict(attrs).get("class") == "python":
            self.inside = True
            self.blocks.append("")

    def handle_data(self, text):
        if self.inside:
            self.blocks[-1] += text

    def handle_endtag(self, tag):
        if tag == "pre":
            self.inside = False


def definition(raw):
    if hashlib.sha256(raw).hexdigest() != SHA256:
        raise ValueError("Source version mismatch; nothing compiled")
    parser = PythonBlocks()
    parser.feed(raw.decode("utf-8"))
    if len(parser.blocks) != 3:
        raise ValueError("Expected exactly three Python snippets")
    block = parser.blocks[0].strip()
    if hashlib.sha256(block.encode()).hexdigest() != BLOCK_SHA256:
        raise ValueError("Selected block version mismatch; nothing compiled")
    return compile(block, URL + "#roll-snippet", "exec")


@dataclass(frozen=True)
class Contract:
    name: str
    Expiry: datetime
    LastPrice: float
    BidPrice: float = 0.0
    AskPrice: float = 0.0


def chain(root, prices, *, scale=1.0):
    start = datetime(2024, 1, 1)
    return [Contract(f"{root}{i}", start + timedelta(days=30*i), p*scale)
            for i, p in enumerate(prices)]


def execute(code, chains):
    state = {"self": SimpleNamespace(chains=chains), "floor": math.floor}
    exec(code, state)
    return state


def audit(raw):
    code = definition(raw)
    checks = []

    def summary(state):
        return dict(scores={c.name: v for c, v in state["roll_return"].items()},
                    rank=[c.name for c in state["sorted_by_roll_return"]],
                    high=[c.name for c in state["high"]],
                    low=[c.name for c in state["low"]])

    first = summary(execute(code, {"A": chain("A", [100, 99]),
                                   "B": chain("B", [1000, 995])}))
    scaled = summary(execute(code, {"A": chain("A", [100, 99]),
                                    "B": chain("B", [1000, 995], scale=.01)}))
    assert first["rank"] == ["B1", "A1"] and scaled["rank"] == ["A1", "B1"]
    log_scores = {"A1": (math.log(100)-math.log(99))*365/30,
                  "B1": (math.log(1000)-math.log(995))*365/30}
    assert log_scores["A1"] > log_scores["B1"]
    assert math.isclose(log_scores["B1"], (math.log(10)-math.log(9.95))*365/30)
    checks.append(dict(case="quote_units_change_joint_rank", prices={"A":[100,99],"B":[1000,995]},
                       original=first, B_quote_scale=.01, scaled=scaled,
                       referenced_log_formula_scores=log_scores))

    strip = summary(execute(code, {"A": chain("A", [100, 99, 98]),
                                   "B": chain("B", [200, 199])}))
    assert set(strip["scores"]) == {"A1", "A2", "B1"}
    checks.append(dict(case="deferred_contracts_are_separate_candidates", result=strip))

    missing = chain("A", [0, 0])
    missing[0] = Contract("A0", missing[0].Expiry, 0, 99, 101)
    state = summary(execute(code, {"A": missing}))
    assert math.isclose(state["scores"]["A1"], 100*365/30)
    checks.append(dict(case="near_midpoint_fallback_but_deferred_zero_used",
                       near_last=0, near_bid=99, near_ask=101, deferred_last=0, result=state))

    for name, chains, expected in (
            ("empty_chain", {"A": []}, IndexError),
            ("equal_expiry", {"A": [Contract("A0", datetime(2024,1,1),100),
                                      Contract("A1", datetime(2024,1,1),99)]}, ZeroDivisionError)):
        try:
            execute(code, chains)
        except expected as exc:
            checks.append(dict(case=name, exception=type(exc).__name__))
        else:
            raise AssertionError("Expected source boundary exception: " + name)

    one = summary(execute(code, {"A": chain("A", [100,99])}))
    assert one["high"] == [] and one["low"] == ["A1"]
    checks.append(dict(case="zero_tertile_negative_zero_slice", candidates=1, result=one))

    a, b = chain("A", [100,99]), chain("B", [200,199])
    forward = summary(execute(code, {"A": a,"B": b}))["rank"]
    reverse = summary(execute(code, {"B": b,"A": a}))["rank"]
    assert forward == ["A1","B1"] and reverse == ["B1","A1"]
    checks.append(dict(case="ties_inherit_input_order", forward=forward, reverse=reverse))

    return dict(schema_version=1, source_url=URL, source_commit=COMMIT,
                source_sha256=SHA256, selected_block_sha256=BLOCK_SHA256,
                execution_scope="Only the first joint Method Python block; all contracts invented.",
                checks=checks, checks_passed=len(checks), market_trials=0,
                cost_sensitivity="Not applicable to price-unit/ranking checks; no PnL or fills. "
                                 "Future strategy tests require complete 1x/2x/3x costs.",
                limits=["Not the embedded algorithm, other snippets, LEAN or MEXC runtime.",
                        "The log formula is a labelled comparison, not a repaired strategy.",
                        "No historical prices, market trials, execution evidence or alpha result."])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    print(json.dumps(audit(parser.parse_args().source.read_bytes()), indent=2, allow_nan=False))
