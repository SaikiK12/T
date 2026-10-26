"""Independently reconstruct every venue/day from tickets and source settlements.

This verifies the historical proxy arithmetic. It cannot resolve unknown funding,
prove fair-price cash, fill availability, margin or prospective performance.
"""
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from lab.equations import COSTS, HOUR  # noqa: E402
from lab.equation_data import load_panel  # noqa: E402
from scripts.run_equations import verify_inputs, sha  # noqa: E402


def reconstruct(panel, tickets, origins, start):
    """Cash from signed fills + current position value + strictly prior inventory funding."""
    dq = np.zeros_like(panel.prices)
    fill_cash = np.zeros((len(panel.times), 2))
    fees = np.zeros_like(fill_cash)
    running = np.zeros((len(panel.keys), 2))
    lookup = {key: i for i, key in enumerate(panel.keys)}
    for z in tickets.to_dict("records"):
        h = (int(z["time_ms"])-int(panel.times[0]))//HOUR
        i = lookup[z["coin"]]
        assert panel.times[h] == z["time_ms"]
        old = np.array([z["old_mexc"], z["old_lighter"]])
        target = np.array([z["new_mexc"], z["new_lighter"]])
        np.testing.assert_allclose(running[i], old, rtol=0, atol=1e-12)
        px = panel.prices[h, i]
        np.testing.assert_array_equal(px, [z["mexc_price_proxy"], z["lighter_price_proxy"]])
        delta = target-old
        dq[h, i] += delta
        fill_cash[h] -= delta*px
        fees[h] += abs(delta)*px*COSTS
        running[i] = target
    after = np.cumsum(dq, axis=0)
    before = after-dq  # entry at an event clock does not earn that clock's settlement
    last = np.stack([pd.DataFrame(panel.prices[:, :, v]).ffill().to_numpy() for v in range(2)], axis=2)
    known_rate = np.where(panel.funding_ok, panel.rates, 0.)
    pay = -np.sum(np.nan_to_num(before*last*known_rate), axis=1)
    position_value = np.sum(np.nan_to_num(after*last), axis=1)
    cum_cash, cum_fees = np.cumsum(fill_cash+pay, axis=0), np.cumsum(fees, axis=0)
    ix = ((np.asarray(origins, np.int64)+24*HOUR-int(panel.times[0]))//HOUR).astype(int)
    assert int(panel.times[ix[0]]) == start+24*HOUR
    return np.stack([5000.+cum_cash[ix]+position_value[ix]-m*cum_fees[ix] for m in (1, 2, 3)], axis=1)


def main():
    _, inputs = verify_inputs()
    lane = Path(__file__).resolve().parent
    out = lane/"results"
    manifest = json.loads((out/"manifest.json").read_text())
    for name, expected in manifest["outputs"].items():
        assert sha(out/name) == expected, name
    settings = json.loads((lane/"settings.json").read_text())
    parse = lambda s: int(pd.Timestamp(s, tz="UTC").timestamp()*1000)
    panel, _ = load_panel(ROOT/inputs["data_root"], ROOT/inputs["symbols"],
                          parse(settings["start"]), parse(settings["end_exclusive"]))
    daily = pd.read_csv(out/"daily.csv.gz", float_precision="round_trip")
    tickets = pd.read_csv(out/"tickets.csv.gz", float_precision="round_trip")
    maximum, count = 0., 0
    for (split, label), rows in daily.groupby(["split", "label"], sort=True):
        trades = tickets[(tickets.split == split) & (tickets.label == label)]
        rows = rows.sort_values("origin_ms")
        recovered = reconstruct(panel, trades, rows.origin_ms, int(rows.origin_ms.iloc[0]))
        expected = np.stack([rows[[f"mexc_equity_{m}x", f"lighter_equity_{m}x"]].to_numpy()
                             for m in (1, 2, 3)], axis=1)
        error = float(np.max(abs(recovered-expected)))
        np.testing.assert_allclose(recovered, expected, rtol=0, atol=1e-6)
        maximum = max(maximum, error)
        count += len(rows)*6
    verify_inputs()
    print(json.dumps({"venue_day_tier_balances_checked": count, "max_abs_dollar_error": maximum,
                      "proxy_arithmetic_only": True, "unknown_intervals_remain_unscored": True}))


if __name__ == "__main__":
    main()
