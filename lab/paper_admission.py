"""Conservative projection of legacy reports, without rewriting their journals.

Legacy 'ontime' and 'net' labels retain their original meanings. They cannot
certify executable, on-time, fully costed account evidence. This projection is
an input audit, never an activation gate or a way to turn unknown cash into0.
"""
from collections import defaultdict


REQUIRED = ('first_seen_quote_depth', 'complete_session_availability',
            'event_bound_fair_index_notional', 'source_bound_fees',
            'complete_fill_and_capital_accounting', 'on_time_frozen_protocol')


def legacy_projection(rows):
    """Preserve every row and its native figures, with a separate strict scope.

    Old exporters carry none of the six evidence identities. An arbitrary
    Boolean flag is deliberately insufficient to upgrade a historical report.
    A future supported adapter needs its own frozen source contract and audit.
    """
    grouped = defaultdict(list)
    for row in rows:
        if not isinstance(row, dict) or not row.get('series'):
            raise ValueError('explicit legacy series required')
        grouped[row['series']].append(row)
    return [{'series': series, 'round': records[0].get('round'),
             'reported_rows': len(records),
             'native_ontime_labels': sum(r.get('kind') == 'ontime' for r in records),
             'native_missing_money_rows': sum(any(r.get(k) is None for k in ('net', 'net_2x', 'net_3x')) for r in records),
             'strict_executable_scored_days': 0, 'strict_net_return': None,
             'state': 'INCOMPLETE', 'missing_inputs': list(REQUIRED),
             'native_report_preserved': True, 'activation_allowed': False,
             'scope': 'Conservative legacy adapter; native net/on-time figures remain in their original datasets. No inferred source completeness.'}
            for series, records in sorted(grouped.items())]
