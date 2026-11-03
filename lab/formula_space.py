"""Bounded rational formula discovery with units and definition domains.

Engineering only: no market loader, target fit, PnL, significance or UTC
qualification. Lag/clock metadata are caller declarations, not source proof.
Equivalence is exact real arithmetic and preserves required inputs and guards;
it is deliberately incomplete, and is not IEEE floating-point bit equivalence.
"""
from dataclasses import dataclass
from fractions import Fraction
import math
import operator
import re

MAX_TERMS = 64
MAX_NODES = 63
MAX_PATH_POINTS = 10000


class BudgetError(ValueError):
    pass


@dataclass(frozen=True, order=True)
class Unit:
    price: int = 0
    volume: int = 0
    time: int = 0

    def __post_init__(self):
        if any(type(x) is not int for x in (self.price,self.volume,self.time)):
            raise ValueError("integer unit exponents required")

    def combine(self, other, sign=1):
        return Unit(self.price+sign*other.price,self.volume+sign*other.volume,self.time+sign*other.time)


ONE, PRICE, VOLUME, TIME = Unit(), Unit(price=1), Unit(volume=1), Unit(time=1)


@dataclass(frozen=True, order=True)
class Atom:
    name: str
    unit: Unit
    lag: int = 0
    clock: str = "decision"

    def __post_init__(self):
        if not isinstance(self.name,str) or not re.fullmatch(r"[a-z][a-z0-9_]*",self.name) or not isinstance(self.unit,Unit):
            raise ValueError("invalid symbol/unit")
        if type(self.lag) is not int or self.lag<0:
            raise ValueError("future/invalid lag")
        if not isinstance(self.clock,str) or not re.fullmatch(r"[a-z][a-z0-9_]*",self.clock):
            raise ValueError("invalid clock declaration")


def _fraction(value):
    if isinstance(value,bool):
        raise ValueError("boolean is not a numeric measurement")
    if isinstance(value,float):
        if not math.isfinite(value):
            raise ValueError("nonfinite value")
        return Fraction(str(value))
    if not isinstance(value,(int,Fraction)):
        raise ValueError("expected finite rational measurement")
    return Fraction(value)


def _poly(items):
    out = {}
    for monomial,coefficient in items:
        monomial=tuple(sorted(monomial))
        out[monomial]=out.get(monomial,Fraction(0))+coefficient
    out={k:v for k,v in out.items() if v}
    if len(out)>MAX_TERMS:
        raise BudgetError("polynomial term budget")
    return tuple(sorted(out.items()))


PONE = (((),Fraction(1)),)


def _add(a,b,sign=1):
    return _poly([*a,*((m,sign*c) for m,c in b)])


def _mul(a,b):
    return _poly((ma+mb,ca*cb) for ma,ca in a for mb,cb in b)


def _guard(poly):
    if not poly:
        raise ValueError("identically zero divisor")
    if len(poly)==1 and not poly[0][0]:
        return frozenset()  # A nonzero constant never restricts the domain.
    scale=poly[0][1]
    return frozenset({tuple((m,c/scale) for m,c in poly)})


def _pvalue(poly,values):
    total=Fraction(0)
    for monomial,coefficient in poly:
        product=coefficient
        for atom in monomial:
            product*=values[atom]
        total+=product
    return total


@dataclass(frozen=True)
class Expr:
    numerator: tuple
    denominator: tuple
    unit: Unit
    inputs: frozenset
    guards: frozenset
    nodes: int
    text: str

    def _binary(self,other,op):
        other=other if isinstance(other,Expr) else constant(other)
        if self.nodes+other.nodes+1>MAX_NODES:
            raise BudgetError("expression tree budget")
        inputs=self.inputs|other.inputs
        declarations={}
        for atom in inputs:
            key=(atom.name,atom.lag,atom.clock)
            if key in declarations and declarations[key]!=atom.unit:
                raise ValueError("conflicting units for one input")
            declarations[key]=atom.unit
        if len({a.clock for a in inputs})>1:
            raise ValueError("join different clocks explicitly before combining")
        guards=self.guards|other.guards
        if op in ("+","-"):
            if self.unit!=other.unit:
                raise ValueError("cannot add unlike units")
            unit=self.unit
            num=_add(_mul(self.numerator,other.denominator),_mul(other.numerator,self.denominator),1 if op=="+" else -1)
            den=_mul(self.denominator,other.denominator)
        elif op=="*":
            unit=self.unit.combine(other.unit)
            num,den=_mul(self.numerator,other.numerator),_mul(self.denominator,other.denominator)
        elif op=="/":
            unit=self.unit.combine(other.unit,-1)
            guards|=_guard(other.numerator)
            num,den=_mul(self.numerator,other.denominator),_mul(self.denominator,other.numerator)
        else:
            raise ValueError("unknown operator")
        return Expr(num,den,unit,inputs,guards,self.nodes+other.nodes+1,f"({self.text} {op} {other.text})")

    def __add__(self,other): return self._binary(other,"+")
    def __sub__(self,other): return self._binary(other,"-")
    def __mul__(self,other): return self._binary(other,"*")
    def __truediv__(self,other): return self._binary(other,"/")
    def __radd__(self,other): return constant(other)+self
    def __rsub__(self,other): return constant(other)-self
    def __rmul__(self,other): return constant(other)*self
    def __rtruediv__(self,other): return constant(other)/self
    def __neg__(self): return constant(-1)*self

    def evaluate(self,measurements):
        """Exact scalar result, or None for missing/nonfinite/undefined inputs.

        Every original input is required even after algebraic cancellation.
        This is a small engineering evaluator, not a production array adapter.
        """
        try:
            values={a:_fraction(measurements[a]) for a in self.inputs}
        except (KeyError,ValueError):
            return None
        if any(_pvalue(g,values)==0 for g in self.guards):
            return None
        den=_pvalue(self.denominator,values)
        return _pvalue(self.numerator,values)/den if den else None


def constant(value,unit=ONE):
    if not isinstance(unit,Unit):
        raise ValueError("invalid constant unit")
    value=_fraction(value)
    return Expr((((),value),) if value else (),PONE,unit,frozenset(),frozenset(),1,str(value))


def variable(name,unit=ONE,lag=0,clock="decision"):
    a=Atom(name,unit,lag,clock)
    text=name+(f"[lag={lag}]" if lag else "")
    return Expr((((a,),Fraction(1)),),PONE,unit,frozenset({a}),frozenset(),1,text)


def _same_domain(a,b):
    return a.unit==b.unit and a.inputs==b.inputs and a.guards==b.guards


def equivalent(a,b):
    """Only prove identities on matching input/guard domains; no data correlation."""
    if not _same_domain(a,b):
        return False
    try:
        return _mul(a.numerator,b.denominator)==_mul(b.numerator,a.denominator)
    except BudgetError:
        return False  # Failure to prove is not proof of equality.


def predicate_equivalent(a,threshold_a,b,threshold_b,comparison="gt"):
    """Prove same-direction threshold aliases with identical definition domains.

    Threshold numbers inherit the feature's declared unit. Strict/non-strict
    comparisons must be audited separately; this function uses one common op.
    """
    if comparison not in ("gt","ge","lt","le"):
        raise ValueError("unsupported comparison")
    x,y=a-constant(threshold_a,a.unit),b-constant(threshold_b,b.unit)
    if not _same_domain(x,y):
        return False
    try:
        left,right=_mul(x.numerator,y.denominator),_mul(y.numerator,x.denominator)
    except BudgetError:
        return False
    if not left or not right:
        return not left and not right
    if tuple(m for m,_ in left)!=tuple(m for m,_ in right):
        return False
    scale=left[0][1]/right[0][1]
    return scale>0 and all(lc==scale*rc for (_,lc),(_,rc) in zip(left,right))


@dataclass(frozen=True)
class Family:
    forms: tuple
    attempts: int
    duplicates: int
    invalid: int
    budget_exhausted: bool


def enumerate_family(leaves,max_nodes=5,max_attempts=2000):
    """Deterministic, bounded +,-,*,/ factory with data-independent pruning.

    Attempts include leaf admissions and rejected/duplicate operator trials.
    These are engineering counts, never a reason to erase prior alpha trials.
    No loss function, price history, target or winner is accepted here.
    """
    if type(max_nodes) is not int or not 1<=max_nodes<=9 or max_nodes%2!=1:
        raise ValueError("odd max_nodes in 1..9 required")
    if type(max_attempts) is not int or not len(leaves)<=max_attempts<=10000 or not 1<=len(leaves)<=16:
        raise ValueError("invalid attempt budget/leaves")
    if any(not isinstance(x,Expr) or x.nodes!=1 for x in leaves):
        raise ValueError("primitive leaves required")
    forms,levels=[],{}
    attempts=duplicates=invalid=0
    def admit(x):
        nonlocal duplicates
        if any(equivalent(x,other) for other in forms):
            duplicates+=1
        else:
            forms.append(x);levels.setdefault(x.nodes,[]).append(x)
    for x in leaves:
        attempts+=1;admit(x)
    for size in range(3,max_nodes+1,2):
        for left_size in range(1,size-1,2):
            right_size=size-left_size-1
            for left in tuple(levels.get(left_size,())):
                for right in tuple(levels.get(right_size,())):
                    for op in (operator.add,operator.sub,operator.mul,operator.truediv):
                        if attempts>=max_attempts:
                            return Family(tuple(forms),attempts,duplicates,invalid,True)
                        attempts+=1
                        try:
                            x=op(left,right)
                        except ValueError:
                            invalid+=1;continue
                        admit(x)
    return Family(tuple(forms),attempts,duplicates,invalid,False)


def signed_area(xs,ys):
    """Oriented area of a polygonal path closed back to its start.

    Pure representation: ordered, dimensionless paths must be supplied by a
    causal adapter. This does not authenticate arrival order, feed freshness,
    a clock, a source, or predict a future return. Missing values stay unknown.
    """
    if len(xs)>MAX_PATH_POINTS or len(ys)>MAX_PATH_POINTS:
        raise BudgetError("exact path evaluator point budget")
    if len(xs)!=len(ys) or len(xs)<2:
        raise ValueError("aligned paths with at least two points required")
    try:
        x,y=list(map(_fraction,xs)),list(map(_fraction,ys))
    except ValueError:
        return None
    x=[v-x[0] for v in x];y=[v-y[0] for v in y]
    return sum((a*d-b*c for a,b,c,d in zip(x,y,x[1:],y[1:])),Fraction(0))/2
