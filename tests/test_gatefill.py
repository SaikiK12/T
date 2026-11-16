"""scripts/forward_gatefill.py (R498): R390's open book, placement, queue-aware fills, Binance paging, pair costs, the
frozen verdict and a full place-then-settle tick against a fake API."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import forward_gatefill as gf  # noqa: E402

T0 = 1_794_000_000.0


def tape(rows):
    return pd.DataFrame(rows, columns=["id", "t", "size", "price"])


def gbook(bid, ask, bid_size=10, ask_size=10, t=T0, levels=5, step=0.1):
    return {"current": t, "bids": [{"p": f"{bid - i * step:.4f}", "s": bid_size if i == 0 else 1000} for i in range(levels)],
            "asks": [{"p": f"{ask + i * step:.4f}", "s": ask_size if i == 0 else 1000} for i in range(levels)]}


def bbook(bid, ask, levels=5, step=0.01):
    return {"bids": [[f"{bid - i * step:.4f}", "1000"] for i in range(levels)],
            "asks": [[f"{ask + i * step:.4f}", "1000"] for i in range(levels)]}


GCON = {"name": "X_USDT", "quanto_multiplier": "1", "order_price_round": "0.1", "maker_fee_rate": "-0.0001"}


class Inputs(unittest.TestCase):
    def test_open_book(self):
        rows = [{"book": "A", "action": "enter", "coin": "AUSDT", "long": "gate", "short": "binance"},
                {"book": "A", "action": "enter", "coin": "BUSDT", "long": "binance", "short": "gate"},
                {"book": "A", "action": "enter", "coin": "CUSDT", "long": "binance", "short": "gate"},
                {"book": "A", "action": "exit", "coin": "CUSDT", "long": "binance", "short": "gate"},
                {"book": "B", "action": "enter", "coin": "DUSDT", "long": "gate", "short": "binance"}]
        self.assertEqual(gf.open_book(rows), {"AUSDT": 1, "BUSDT": -1})

    def test_walk(self):
        self.assertAlmostEqual(gf.walk_bp([(100.1, 100)], 1000, 100.0), 10.0, places=6)
        self.assertTrue(np.isnan(gf.walk_bp([(100.1, 1)], 1000, 100.0)))


class Place(unittest.TestCase):
    def test_inside_when_room(self):
        rows = gf.place("tk", "XUSDT", "X_USDT", "XUSDT", 1, gbook(99.9, 100.4), GCON, bbook(99.99, 100.01))
        self.assertEqual(len(rows), 2 * 2 * 2)                        # sides x sizes x placements
        ins = [r for r in rows if r["placement"] == "inside"]
        self.assertTrue(all(r["primary"] for r in ins))
        self.assertFalse(any(r["primary"] for r in rows if r["placement"] == "touch"))
        bid_in = [r for r in ins if r["side"] == 1][0]
        self.assertAlmostEqual(bid_in["price"], 100.0)
        self.assertEqual(bid_in["queue_ahead"], 0.0)
        bid_touch = [r for r in rows if r["side"] == 1 and r["placement"] == "touch"][0]
        self.assertEqual(bid_touch["queue_ahead"], 10.0)
        self.assertEqual(bid_touch["spread_ticks"], 5)
        self.assertAlmostEqual(bid_touch["maker_fee_listed_bp"], -1.0)

    def test_touch_only_when_one_tick(self):
        rows = gf.place("tk", "XUSDT", "X_USDT", "XUSDT", 1, gbook(99.9, 100.0), GCON, bbook(99.99, 100.01))
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r["primary"] and r["placement"] == "touch" for r in rows))

    def test_crossed_or_empty(self):
        self.assertEqual(gf.place("tk", "X", "X_USDT", "X", 1, gbook(100.0, 100.0), GCON, bbook(1, 2)), [])
        self.assertEqual(gf.place("tk", "X", "X_USDT", "X", 1, {"current": T0, "bids": [], "asks": []}, GCON,
                                  bbook(1, 2)), [])


class Fills(unittest.TestCase):
    def test_queue_then_fill_then_through(self):
        x = tape([(1, T0 - 5, -50, 100.0),          # before placement: ignored
                  (2, T0 + 10, -8, 100.0),          # consumes 8 of the 10 ahead
                  (3, T0 + 15, 4, 100.1),           # a taker buy: not for a resting bid
                  (4, T0 + 20, -4, 100.0),          # 2 more ahead, then 2 fill
                  (5, T0 + 30, -1, 99.9)])          # trade-through: the remaining 3 fill
        f = gf.fills(x, T0, 1, 100.0, 10, 5, 3600, 0.1)
        self.assertEqual([(t - T0, q, th) for t, q, th in f], [(20, 2.0, False), (30, 3.0, True)])

    def test_horizon_and_ask_side(self):
        x = tape([(1, T0 + 10, 3, 100.2), (2, T0 + 1000, 9, 100.3)])
        self.assertEqual(gf.fills(x, T0, -1, 100.2, 0, 5, 900, 0.1), [(T0 + 10, 3.0, False)])
        self.assertEqual(len(gf.fills(x, T0, -1, 100.2, 0, 5, 3600, 0.1)), 2)


def flat_mid(v):
    return lambda at: np.full(len(at), float(v))


class Settle(unittest.TestCase):
    def order(self, **kw):
        o = {"id": "o", "t0": T0, "side": 1, "price": 99.9, "tick_size": 0.1, "queue_ahead": 0.0, "qty": 5.0,
             "mid_g0": 100.0, "mid_b0": 100.0, "gate_taker_bp": 10.0, "bn_taker_bp": 2.0, "maker_fee_listed_bp": -1.0}
        o.update(kw)
        return o

    def test_filled_at_once(self):
        x = tape([(1, T0 + 10, -9, 99.8)])
        r = gf.settle_order(self.order(), x, flat_mid(100), flat_mid(100), 3600, True, True, "now")
        self.assertTrue(r["valid"])
        self.assertAlmostEqual(r["fill_frac"], 1.0)
        self.assertAlmostEqual(r["gate_part_bp"], -10.0)
        self.assertAlmostEqual(r["taker_pair_bp"], 24.5)              # 10 + 7.5 + 2 + 5
        self.assertAlmostEqual(r["maker_pair_bp"], -1.0)              # -10 + 0 + 0 + 2 + 5 + 2 fee
        self.assertAlmostEqual(r["saving_bp"], 25.5)
        self.assertAlmostEqual(r["saving_listed_bp"], 28.5)

    def test_unfilled_common_move_cancels(self):
        r = gf.settle_order(self.order(), tape([]), flat_mid(101), flat_mid(101), 3600, True, True, "now")
        self.assertAlmostEqual(r["fill_frac"], 0.0)
        self.assertAlmostEqual(r["chase_part_bp"], 100 + 10 + 7.5 - 100)
        self.assertAlmostEqual(r["saving_bp"], 0.0)

    def test_adverse_selection_shows_in_the_hedge(self):
        x = tape([(1, T0 + 10, -9, 99.8)])                           # filled, then Binance falls 0.5%
        r = gf.settle_order(self.order(), x, flat_mid(99.5), flat_mid(99.5), 3600, True, True, "now")
        self.assertAlmostEqual(r["hedge_part_bp"], 50.0)
        self.assertAlmostEqual(r["saving_bp"], 25.5 - 50.0)

    def test_invalid_flags(self):
        r = gf.settle_order(self.order(), tape([]), flat_mid(np.nan), flat_mid(100), 3600, False, True, "now")
        self.assertFalse(r["valid"])
        self.assertIn("gate_tape_incomplete", r["reason"])
        self.assertIn("chase_mid_missing", r["reason"])


class BinancePaging(unittest.TestCase):
    def test_pages_forward_and_trims(self):
        trades = [{"a": i, "T": int((T0 - 400 + i * 2) * 1000), "p": "1.0", "m": bool(i % 2)} for i in range(3000)]

        def get(url):
            q = dict(kv.split("=") for kv in url.split("?")[1].split("&"))
            if "fromId" in q:
                out = [t for t in trades if t["a"] >= int(q["fromId"])]
            else:
                out = [t for t in trades if int(q["startTime"]) <= t["T"] <= int(q["endTime"])]
            return out[:int(q["limit"])]
        f, complete = gf.bn_tape(get, "X", T0 - 300, T0 + 3606, sleep=lambda s: None)
        self.assertTrue(complete)
        self.assertGreaterEqual(f.t.min(), T0 - 300)
        self.assertLessEqual(f.t.max(), T0 + 3606)
        self.assertEqual(len(f), len([t for t in trades if (T0 - 300) * 1000 <= t["T"] <= (T0 + 3606) * 1000]))
        self.assertEqual(set(f.d), {1, -1})


def fake_settled(n, saving, days=12, contracts=6):
    orders, settled = [], []
    for i in range(n):
        t0 = T0 + (i % (days * 12)) * 7200
        oid = f"o{i}"
        orders.append({"id": oid, "tick": f"tick{i % (days * 12)}", "t0": t0, "contract": f"C{i % contracts}",
                       "usd": 5000, "primary": True})
        s = saving(i)
        settled.append({"id": oid, "horizon_s": 3600, "valid": True, "saving_bp": s, "saving_high_bp": s - 2,
                        "saving_listed_bp": s + 3, "maker_pair_bp": 20 - s, "taker_pair_bp": 20, "fill_frac": 0.5})
    return orders, settled


class Verdict(unittest.TestCase):
    def test_rules(self):
        rng = np.random.default_rng(1)
        o, s = fake_settled(400, lambda i: 10 + rng.normal(0, 5))
        self.assertEqual(gf.decide(o, s)["verdict"], "MAKER_ROUTE")
        o, s = fake_settled(400, lambda i: -3 + rng.normal(0, 5))
        self.assertEqual(gf.decide(o, s)["verdict"], "NO_GAIN")
        o, s = fake_settled(100, lambda i: 10.0)
        self.assertEqual(gf.decide(o, s)["verdict"], "INSUFFICIENT_DATA")
        o, s = fake_settled(400, lambda i: 10.0, days=5)
        self.assertEqual(gf.decide(o, s)["verdict"], "INSUFFICIENT_DATA")

    def test_two_contracts_cannot_carry_it(self):
        o, s = fake_settled(400, lambda i: 60.0 if i % 6 in (0, 1) else -5.0)
        d = gf.decide(o, s)
        self.assertGreater(d["mean_saving_bp"], 0)
        self.assertEqual(d["verdict"], "NO_GAIN")


class Tick(unittest.TestCase):
    def test_place_then_settle(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            with open(d / "tickets.csv", "w", newline="") as f:
                w = csv.DictWriter(f, ["book", "action", "coin", "long", "short"])
                w.writeheader()
                w.writerow({"book": "A", "action": "enter", "coin": "XUSDT", "long": "gate", "short": "binance"})
            (d / "symbols.csv").write_text("key,binance,gate\nXUSDT,XUSDT,X_USDT\n")
            t_place = T0
            gtrades = [{"id": 1, "create_time_ms": t_place + 30, "size": -500, "price": "99.8"},
                       {"id": 2, "create_time_ms": t_place + 40, "size": 500, "price": "100.5"}]
            btrades = [{"a": i, "T": int((t_place - 200 + i * 10) * 1000), "p": "100.0" if i % 2 else "100.02",
                        "m": bool(i % 2)} for i in range(500)]

            def get(url):
                if url.endswith("/contracts"):
                    return [GCON]
                if "/order_book?" in url:
                    return gbook(99.9, 100.4, t=t_place)
                if "/depth?" in url:
                    return bbook(99.99, 100.01)
                if "/trades?" in url:
                    q = dict(kv.split("=") for kv in url.split("?")[1].split("&"))
                    return sorted([t for t in gtrades if int(q["from"]) <= t["create_time_ms"] <= int(q["to"])],
                                  key=lambda t: -t["id"])[:int(q["limit"])]
                if "/aggTrades?" in url:
                    q = dict(kv.split("=") for kv in url.split("?")[1].split("&"))
                    if "fromId" in q:
                        out = [t for t in btrades if t["a"] >= int(q["fromId"])]
                    else:
                        out = [t for t in btrades if int(q["startTime"]) <= t["T"] <= int(q["endTime"])]
                    return out[:int(q["limit"])]
                raise AssertionError(url)
            j = d / "journal"
            kw = dict(get=get, sleep=lambda s: None, journal=j, tickets=d / "tickets.csv", symbols=d / "symbols.csv")
            s1 = gf.tick(now=t_place, **kw)
            self.assertEqual(s1["placed_now"], 8)
            first = (j / "orders.csv").read_text()
            s2 = gf.tick(now=t_place + gf.SETTLE_AFTER_S + 1, **kw)
            self.assertEqual(s2["settled_now"], 8 * len(gf.HORIZONS_S))
            self.assertTrue((j / "orders.csv").read_text().startswith(first))    # append-only
            with open(j / "settled.csv", newline="") as f:
                st = list(csv.DictReader(f))
            bid_inside = [r for r in st if "|+1|5000|inside" in r["id"] and r["horizon_s"] == "3600"][0]
            self.assertEqual(bid_inside["valid"], "True")
            self.assertAlmostEqual(float(bid_inside["fill_frac"]), 1.0)
            self.assertEqual(bid_inside["through"], "True")
            s3 = gf.tick(now=gf.END.timestamp() + 10, **kw)
            self.assertEqual(s3["placed_now"], 0)


if __name__ == "__main__":
    unittest.main()
