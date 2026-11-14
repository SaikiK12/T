#!/usr/bin/env python3
"""Compile one fingerprinted public signal function on invented quotes only.

Save the public article HTML (or its exact first code block) locally, then run:
    python -m research.audit_fh_hft /tmp/hacking-hft-systems.html

No network, market history, Zorro runtime, order framework or fill simulator.
Each scenario starts a fresh process, resetting the source's static variables.
"""

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile


URL = "https://financial-hacker.com/hacking-hft-systems/"
SIGNAL_SHA256 = "e01e7b2905eb64662cec737ad9fc7a6202035b28341511ad8044ab80c6170ff0"


class CodeBlocks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.current = []
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        if tag == "pre":
            self.inside = True
            self.current = []

    def handle_endtag(self, tag):
        if tag == "pre" and self.inside:
            self.blocks.append("".join(self.current).encode())
            self.inside = False

    def handle_data(self, text):
        if self.inside:
            self.current.append(text)


def checked_signal(raw):
    """Fingerprint before compiling; never compile other article snippets."""
    if hashlib.sha256(raw).hexdigest() == SIGNAL_SHA256:
        return raw
    parser = CodeBlocks()
    parser.feed(raw.decode("utf-8"))
    matches = [block for block in parser.blocks
               if hashlib.sha256(block).hexdigest() == SIGNAL_SHA256]
    if len(matches) != 1:
        raise ValueError("Exactly one fingerprinted signal block is required")
    return matches[0]


def audit(raw):
    signal = checked_signal(raw)
    compiler = shutil.which("g++")
    if compiler is None:
        raise RuntimeError("g++ is required; no source function executed")
    compiler_version = subprocess.run(
        [compiler, "--version"], check=True, capture_output=True, text=True,
        timeout=10).stdout.splitlines()[0]
    # Only the verified function is compiled. Static initialization is valid C++.
    harness = (b"\n#include <iostream>\nint main() { double a,b,c,d; "
               b"while(std::cin >> a >> b >> c >> d) "
               b"std::cout << tradeHFT(a,b,c,d) << '\\n'; return 0; }\n")
    cases = []
    with tempfile.TemporaryDirectory(prefix="fh-hft-audit-") as folder:
        source = Path(folder) / "signal.cpp"
        binary = Path(folder) / "signal"
        source.write_bytes(signal + harness)
        subprocess.run([compiler, "-std=c++17", "-O2", str(source), "-o", str(binary)],
                       check=True, capture_output=True, timeout=30)

        def run(quotes):
            assert all(a >= b > 0 and c >= d > 0 for a, b, c, d in quotes)
            text = "".join(" ".join(map(str, row)) + "\n" for row in quotes)
            completed = subprocess.run([str(binary)], input=text, text=True,
                                       capture_output=True, check=True, timeout=5)
            codes = list(map(int, completed.stdout.splitlines()))
            assert len(codes) == len(quotes)
            return codes

        # Common level is arbitrary; changes are <0.2% of these invented prices.
        # The article's Outlier wrapper is still outside this function audit.
        normal = (2500.01, 2499.99, 2500.125, 2499.875)
        codes = run([normal, normal])
        assert codes == [-1, -1]
        cases.append(dict(case="unchanged_startup", quotes=[normal, normal],
                          codes=codes, kind="control"))

        for name, quotes, expected, edge in [
            ("buy_es_sell_spy_with_negative_crossed_edge",
             [(2500.01,2499.99,2502.,2498.), (2502.01,2501.99,2502.,2498.)], 1, -.01),
            ("buy_spy_sell_es_with_negative_crossed_edge",
             [(2502.,2498.,2500.01,2499.99), (2502.,2498.,2502.01,2501.99)], 2, -.01),
        ]:
            codes = run(quotes)
            assert codes == [-1, expected]
            a, b, c, d = quotes[-1]
            crossed_edge = b - c if expected == 1 else d - a
            assert abs(crossed_edge - edge) < 1e-12
            cases.append(dict(
                case=name, quotes=quotes, codes=codes,
                kind="incomplete_spread_guard", normalized_instantaneous_sell_bid_minus_buy_ask=crossed_edge,
                interpretation="Signal can open when the instantaneous normalized two-leg "
                               "crossed-price gap is negative. This is not a complete "
                               "two-leg spread/fee guard and not proof of risk-free arbitrage; "
                               "it does not prove the statistical trade must lose."))

        jump = (2501.01,2500.99,2500.125,2499.875)
        unique, repeated = run([normal,jump]), run([normal,jump,jump])
        assert unique == [-1,-1] and repeated == [-1,-1,1]
        cases.append(dict(
            case="unchanged_duplicate_can_trigger", kind="event_clock_identity",
            unique_quotes=[normal,jump], unique_codes=unique,
            repeated_quotes=[normal,jump,jump], repeated_codes=repeated,
            interpretation="Filters advance per call, not per elapsed time. One repeated "
                           "snapshot can trigger an entry without a new price. This is an "
                           "algorithm choice; deduplication and feed cadence need a frozen policy."))

        lifecycle = [normal, (2502.01,2501.99,2500.125,2499.875),
                     (2498.01,2497.99,2500.125,2499.875),
                     (2498.01,2497.99,2500.125,2499.875)]
        codes = run(lifecycle)
        assert codes == [-1,1,-1,0]
        cases.append(dict(
            case="command_state_without_fill_receipts", kind="execution_boundary",
            quotes=lifecycle, codes=codes,
            interpretation="The function changes its internal target state immediately "
                           "on commands; it receives no fill acknowledgments. Pending, rejected, "
                           "partial and one-leg outcomes must be managed outside this signal. "
                           "This check does not simulate any fill or failed order."))

    return dict(
        schema_version=1, source_url=URL, signal_sha256=SIGNAL_SHA256,
        signal_bytes=len(signal), input_sha256=hashlib.sha256(raw).hexdigest(),
        runtime=dict(python=platform.python_version(), compiler=compiler_version,
                     flags=["-std=c++17","-O2"]),
        quote_order=["AskSPY","BidSPY","AskES","BidES"],
        units="Invented, already-normalized common price units; no real contract notionals or prices.",
        source_code_meaning={"-1":"no action", "0":"close target", "1":"long ES/short SPY target", "2":"short ES/long SPY target"},
        checks=cases, checks_passed=len(cases), market_trials=0,
        cost_sensitivity="Not applicable: no fills, portfolio PnL or market-cost results. A future "
                         "registered study needs complete1x/2x/3x costs.",
        limits=["Only the displayed fingerprinted tradeHFT function compiled as C++; "
                "Zorro/lite-C and the replay/data-conversion snippets were not executed.",
                "No historical data, asset-list parameters, lot conversion, fees, borrow, "
                "funding, margin, depth or partial-fill behavior received or validated.",
                "No timestamps enter the function: quote age, receive/exchange time and "
                "latency constraints must be implemented in the surrounding framework.",
                "The source Outlier=1.002 price-validation wrapper was not executed; "
                "no claim that the original replay admits every invented event.",
                "The article's profit/latency figures were not reproduced or adopted.",
                "Mutable webpage: a changed signal fails validation; the original local "
                "received bytes may be needed for later reproduction."])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Locally received HTML or exact signal block")
    args = parser.parse_args()
    print(json.dumps(audit(args.source.read_bytes()), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
