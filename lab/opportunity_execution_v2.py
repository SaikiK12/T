"""R339 canonical-mark adapter for the unchanged R338 paper coordinator.

R338's durable request normalizes Decimal spelling; feed it that same spelling
BEFORE its first financial snapshot. Keep its strict state hash, clocks, cash,
costs, reservations and risk gates unchanged. Use a distinct bound account id.
"""
from lab.opportunity_execution import OpportunityExecution, plain
from lab.paper_account import CloseMark, text

CONTRACT = '|canonical-marks-v1'


def canonical_marks(marks):
    result = []
    for mark in marks:
        if not isinstance(mark, CloseMark):
            raise ValueError('typed liquidation marks required')
        fields = plain(mark)
        fields['clock'] = mark.clock
        result.append(CloseMark(**fields))
    return tuple(result)


class OpportunityExecutionV2(OpportunityExecution):
    """Fresh dedicated account; cannot silently adopt an old R338 journal."""
    def __init__(self, account, risk, *, account_id):
        super().__init__(account, risk, account_id=text(account_id)+CONTRACT)

    def admit(self, *args, marks=(), **kwargs):
        return super().admit(*args, marks=canonical_marks(marks), **kwargs)
