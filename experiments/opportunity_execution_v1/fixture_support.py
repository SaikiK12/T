"""Frozen toy inputs shared by R338 regression tests and diagnostic runner.

No market data, measured forecasts, account permissions or network operations.
"""
from dataclasses import replace
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
from pathlib import Path

from lab.microstructure import DepthLevel, DepthSnapshot
from lab.opportunity_execution import OpportunityExecution, ExecutionReceipt, plain
from lab.opportunity_value import Opportunity, Outcome
from lab.paper_account import PaperAccount, PaperEvent, CloseMark
from lab.paper_controls import PaperRisk, RiskPolicy
from lab.stream_quotes import FrameClock, StreamBook, NS

A = FrameClock(1790000000*NS, 10*NS)


def clock(t=0):
    return FrameClock(A.utc_ns+NS+t, A.mono_ns+NS+t)


class Fixture:
    def __init__(self, root, balances=None, policy=None):
        self.root = Path(root)
        self.balances = balances or {('mexc', 'USDT'): 1000}
        self.account = PaperAccount(self.balances, A, journal_path=self.root/'account.jsonl')
        # This declared fixture limit is unlevered; it changes no market policy.
        self.policy = policy or RiskPolicy('R338-invented', max_symbol_gross_fraction=D(1))
        self.risk = self.new_risk()
        self.execution = OpportunityExecution(self.account, self.risk, account_id='R338-invented')
        self.counter = 0

    def new_risk(self, name='risk.jsonl'):
        return PaperRisk(self.root/name, self.policy, A,
            contract_version='R338-invented', initial_balances=self.balances)

    def reopen(self):
        self.execution.close()
        self.account = PaperAccount(self.balances, A, journal_path=self.root/'account.jsonl')
        self.risk = self.new_risk()
        self.execution = OpportunityExecution(self.account, self.risk, account_id='R338-invented')

    def request(self, name='one', *, q='1', t=0, venue='mexc', asset='USDT', symbol='ETH',
                bid=99.5, ask=100.5, reserve='.5', outcomes=None):
        c = clock(t)
        o = Opportunity(name, 'model-'+name, venue, asset, symbol, D(q), c, c.utc_ns+12*3600*NS,
            outcomes or (Outcome('.9', '100', '0'), Outcome('.1', '-100', '0')),
            D(2), 'invented-not-calibrated-market-evidence', D(reserve))
        b = StreamBook(venue, symbol, c, DepthSnapshot(symbol, c.utc_ns, c.mono_ns,
            (DepthLevel(bid, 20),), (DepthLevel(ask, 20),)), 1, 'invented-book')
        market = {'state': 'pass', 'asof_mono_ns': c.mono_ns, 'venue': venue, 'asset': asset,
            'symbol': symbol, 'quantity_base': str(abs(o.quantity)), 'contract_model': 'linear_base',
            'quote_asset': asset, 'instrument_type': 'perpetual', 'step_base': '.1', 'min_base': '.1', 'max_base': '20',
            'valid_from_utc_ns': c.utc_ns, 'valid_until_utc_ns': c.utc_ns+NS,
            **{k: 'invented-not-authenticated' for k in ('source_identity', 'fee_source_identity',
                'lot_source_identity', 'session_source_identity', 'settlement_source_identity')}}
        return dict(opportunities=(o,), books={name: b}, fees_bp={name: '10'}, asof=c.mono_ns,
            risk_inputs=dict(clock=c, complete=True, session_open=True, fee_inputs_known=True,
                contract_version='R338-invented', expected_contract_version='R338-invented', mode='fixture'),
            market_reports={name: market})

    def admit(self, name='one', **kwargs):
        return self.execution.admit('batch-'+name, **self.request(name, **kwargs))

    def receipt(self, ident, order, kind, *, purpose='open', q=None, price=None, fee='0',
                total=None, trade=None, t=None, occurred=None, receipt_id=None):
        self.counter += 1
        t = self.counter*10 if t is None else t
        r = ExecutionReceipt(ident, receipt_id or 'receipt-'+str(self.counter), order, kind,
            clock(t).utc_ns if occurred is None else occurred, clock(t), 'invented-receipt',
            purpose, None if q is None else D(q), trade, None if price is None else D(price),
            None if kind != 'fill' or fee is None else D(fee), None if total is None else D(total))
        return r, clock(t).mono_ns

    def post(self, *args, **kwargs):
        r, t = self.receipt(*args, **kwargs)
        return self.execution.post(r, t)

    def marks(self, t=1000, prices=None):
        prices = prices or {}
        result = []
        with localcontext() as context:
            context.prec = 80
            for (v, a, s), (q, entry) in self.account.positions.items():
                if q:
                    result.append(CloseMark(v, a, s, q, abs(q)*D(prices.get(s, entry)), D(0),
                        clock(t), clock(t).utc_ns, 'invented-mark'))
        return result

    def view(self, t=1000, prices=None):
        return self.execution.snapshot(clock(t).mono_ns, self.marks(t, prices))

    def release(self, ident, t=1000):
        return self.execution.release(ident, release_id='release-'+ident, clock=clock(t),
            source_identity='invented-terminal-confirmation', asof=clock(t).mono_ns)


