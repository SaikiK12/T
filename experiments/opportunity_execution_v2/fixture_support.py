"""Reuse R338's exact invented input contract with the R339 caller adapter."""
from pathlib import Path

from experiments.opportunity_execution_v1.fixture_support import Fixture, A
from lab.opportunity_execution_v2 import OpportunityExecutionV2
from lab.paper_account import PaperAccount
from lab.paper_controls import RiskPolicy
from decimal import Decimal


class FixtureV2(Fixture):
    def __init__(self, root, balances=None, policy=None):
        self.root = Path(root)
        self.balances = balances or {('mexc', 'USDT'): 1000}
        self.account = PaperAccount(self.balances, A, journal_path=self.root/'account.jsonl')
        self.policy = policy or RiskPolicy('R338-invented', max_symbol_gross_fraction=Decimal(1))
        self.risk = self.new_risk()
        self.execution = OpportunityExecutionV2(self.account, self.risk, account_id='R339-invented')
        self.counter = 0

    def reopen(self):
        self.execution.close()
        self.account = PaperAccount(self.balances, A, journal_path=self.root/'account.jsonl')
        self.risk = self.new_risk()
        self.execution = OpportunityExecutionV2(self.account, self.risk, account_id='R339-invented')
