"""Invented-world formula discovery and chart information-loss demonstration.

No market loader/network, optimizer on market returns, strategy score or orders.
Optional --output writes a new JSON receipt exclusively; never overwrites.
"""
import argparse
from fractions import Fraction as F
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from lab import formula_space as fs  # noqa: E402


def demonstrate():
    x,z=fs.variable("x",fs.PRICE),fs.variable("z")
    # The factory sees primitives and budgets, never the planted target.
    family=fs.enumerate_family((x,z,fs.constant(1)),max_nodes=5,max_attempts=2000)
    xa,za=next(iter(x.inputs)),next(iter(z.inputs))
    train=[(F(a),F(b)) for a in (1,2,4) for b in (0,1,2)]
    held=[(F(a),b) for a in (3,7,11) for b in (F(1,2),F(3),F(5))]
    fits=[]
    for expr in family.forms:
        if expr.unit!=fs.PRICE:
            continue
        predictions=[expr.evaluate({xa:a,za:b}) for a,b in train]
        if any(p is None for p in predictions):
            continue
        error=sum(abs(p-a/(1+b)) for p,(a,b) in zip(predictions,train))
        fits.append((error,expr.nodes,expr.text,expr))
    _,_,_,winner=min(fits,key=lambda r:r[:3])
    planted=x/(1+z)
    assert fs.equivalent(winner,planted)
    assert all(winner.evaluate({xa:a,za:b})==a/(1+b) for a,b in held)

    high,low,close=(fs.variable(n,fs.PRICE) for n in ("high","low","close"))
    location=(close-low)/(high-low)
    clv=(2*close-high-low)/(high-low)
    redundant=((close-low)-(high-close))/(high-low)
    assert fs.equivalent(clv,redundant)
    assert fs.predicate_equivalent(location,F(4,5),clv,F(3,5))

    paths=([100,110,90,105],[100,90,110,105])
    def candle(p):
        return dict(open=p[0],high=max(p),low=min(p),close=p[-1],volume=4)
    assert candle(paths[0])==candle(paths[1])
    return dict(
        scope="invented-world engineering only; no market statistic or strategy result",
        family=dict(attempts=family.attempts,retained_forms=len(family.forms),
                    proven_duplicate_attempts=family.duplicates,invalid_attempts=family.invalid,
                    budget_exhausted=family.budget_exhausted),
        synthetic_recovery=dict(planted="x / (1 + z)",recovered=winner.text,
                                exact_algebraic_identity=True,training_points=len(train),
                                heldout_invented_points=len(held),heldout_exact=True),
        redundancy=dict(clv_identity_proved=True,location_080_vs_clv_060_same_predicate=True,
                        zero_range="undefined, never silently zero-filled"),
        compressed_paths=[dict(path=p,candle=candle(p),
                               total_variation=sum(abs(b-a) for a,b in zip(p,p[1:]))) for p in paths],
        ordered_response=dict(flow_first_area=str(fs.signed_area([0,0,1],[0,1,1])),
                              price_first_area=str(fs.signed_area([0,1,1],[0,0,1])),
                              same_endpoints=True,predictive_skill_tested=False),
        strategy_trials=0,market_fit=False,prospective_events=0,gate_eligible=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output")
    args=p.parse_args()
    payload=(json.dumps(demonstrate(),sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
    if args.output:
        output=Path(args.output)
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open("xb") as f:
            f.write(payload)
    print(payload.decode(),end="")


if __name__=="__main__":
    main()
