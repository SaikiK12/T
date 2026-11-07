"""Invented FIFO worlds with identical public depth/trades and different own fills.

Run `python -m research.queue_identifiability`. This is an information-content
counterexample, not HftBacktest execution, a venue calibration or a backtest.
"""

from dataclasses import dataclass
import json


@dataclass(frozen=True)
class Order:
    identity: str
    quantity: int

    def __post_init__(self):
        if not isinstance(self.identity, str) or not self.identity:
            raise ValueError("Order identity must be nonempty text")
        _quantity(self.quantity)


def _quantity(value):
    if type(value) is not int or value <= 0:
        raise ValueError("Quantity must be a positive integer")


def cancel(queue, identity, quantity):
    _quantity(quantity)
    matches = [order for order in queue if order.identity == identity]
    if len(matches) != 1 or matches[0].quantity < quantity:
        raise ValueError("Cancellation must name one order with sufficient quantity")
    return tuple(Order(order.identity, order.quantity - quantity)
                 if order.identity == identity else order for order in queue
                 if order.identity != identity or order.quantity > quantity)


def consume(queue, quantity):
    """Execute a single sell print against a one-level FIFO bid queue."""
    _quantity(quantity)
    if sum(order.quantity for order in queue) < quantity:
        raise ValueError("Print exceeds this invented level's quantity")
    remaining, after, fills = quantity, [], []
    for order in queue:
        take = min(order.quantity, remaining)
        if take:
            fills.append(Order(order.identity, take))
            remaining -= take
        if order.quantity > take:
            after.append(Order(order.identity, order.quantity - take))
    assert remaining == 0
    return tuple(after), tuple(fills)


def world(cancel_identity):
    # Segmentation makes even the individual match sizes identical in both worlds.
    # Our accepted ten-unit bid is behind ten ten-unit A orders, before B arrives.
    queue = tuple(Order(f"A{i}",10) for i in range(1,11)) + (Order("ours",10),)
    public = [{"step": 0, "event": "bid_depth", "quantity": 110}]
    if cancel_identity not in {"A","B"}:
        raise ValueError("Unknown invented history")
    for i in range(1,6):
        queue += (Order(f"B{i}",10),)
        public.append({"step":i,"event":"bid_depth","quantity":110+10*i})
    cancelled = [f"{cancel_identity}{i}" for i in range(1,6)]
    for i,identity in enumerate(cancelled,6):
        queue = cancel(queue,identity,10)
        public.append({"step":i,"event":"bid_depth",
                       "quantity":sum(order.quantity for order in queue)})
    fills = []
    for step,quantity in enumerate([10]*7+[5],11):
        queue,match = consume(queue,quantity)
        assert len(match)==1  # Individual public match sizes need no aggregation.
        fills.extend(match)
        public.extend([
            {"step":step,"event":"sell_trade","quantity":quantity},
            {"step":step,"event":"bid_depth",
             "quantity":sum(order.quantity for order in queue)},
        ])
    return public, dict(
        cancelled_orders=cancelled, cancelled_quantity=50,
        fills=[dict(order=order.identity, quantity=order.quantity) for order in fills],
        our_filled=sum(order.quantity for order in fills if order.identity == "ours"),
        remaining=[dict(order=order.identity, quantity=order.quantity) for order in queue])


def demonstrate():
    first, ahead = world("A")
    second, behind = world("B")
    assert first == second
    assert (ahead["our_filled"], behind["our_filled"]) == (10, 0)
    return dict(
        schema_version=1,
        assumptions=["One invented bid price level; strict FIFO, displayed positive integer quantities.",
                     "Our accepted order is present in displayed depth in BOTH worlds; this is "
                     "not counterfactual insertion into an unchanged historical tape.",
                     "Identical initial acceptance/queue, individual ten-unit adds/cancels, "
                     "per-match print sizes and every intervening depth; only hidden order "
                     "identities differ. No trade aggregation is needed.",
                     "No latency, hidden liquidity, pro-rata, price changes, fees or market data."],
        initial_queue="Ten distinct A orders of 10 units, then our accepted 10-unit order.",
        public_trace=first, hidden_histories=[ahead,behind],
        conclusion="The same aggregate depth and trades can imply a full own fill or no own "
                   "fill. Any deterministic estimator using only these public observations "
                   "must give the same answer in both worlds and cannot identify both exactly.",
        limits=["Not a test of an installed HftBacktest model or MEXC matching rules.",
                "Private execution receipts or sufficiently detailed order-identified events "
                "would distinguish the worlds. Probabilistic/conservative queue models "
                "remain testable assumptions, not observed queue truth.",
                "No strategy selection, trading edge, real fill rate or PnL measured."],
        market_trials=0,
        cost_sensitivity="Not applicable to this fill-identifiability example; future strategy "
                         "evidence still needs complete 1x/2x/3x costs and prospective paper days.")


if __name__ == "__main__":
    print(json.dumps(demonstrate(), indent=2, allow_nan=False))
