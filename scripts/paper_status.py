"""Read-only paper/account view over registered evidence; no runner is started."""
import hashlib
import json
from pathlib import Path

from lab.paper_admission import legacy_projection


def read_report(root, relative, *, limit=8*1024**2):
    root=Path(root).resolve();p=root/relative
    p.resolve().relative_to(root)
    if any(x.is_symlink() for x in (p,*p.parents)) or not p.is_file() or p.stat().st_size>limit:
        raise ValueError('bounded regular registered report required')
    raw=p.read_bytes()
    if len(raw)>limit:raise ValueError('report grew beyond bound')
    return json.loads(raw),hashlib.sha256(raw).hexdigest()


def datasets(root, legacy_days=()):
    """One central view; model account amounts never become observed money.

    Source time is inherited, never replaced by an export clock. No currency
    conversion or cross-venue cash netting is performed. Missing output stays
    unavailable, rather than showing a zero PnL or implying an active process.
    """
    root=Path(root).resolve()
    result={'paper_accounts':[], 'paper_controls':[], 'paper_requirements':[],
            'paper_admission':legacy_projection(legacy_days)}
    rel='experiments/owner_acceptance_v1/results.json'
    try:
        report,digest=read_report(root,rel)
        if report.get('registry_id')!='R320' or report.get('simulation_only') is not True or report.get('activation_allowed') is not False:
            raise ValueError('paper-only registered report required')
        snapshot=report['paper_snapshot']
        if snapshot.get('activation_allowed') is not False:raise ValueError('unexpected account permission')
        for a in snapshot['accounts']:
            row={k:a.get(k) for k in ('venue','asset','initial_cash','cash','realized_price_pnl','funding_pnl',
                'fees_paid','realized_net_pnl','unrealized_liquidation_pnl','estimated_future_exit_fees',
                'nav','nav_state','locked_capital','available_capital','capital_basis')}
            row.update(key=a['venue']+'|'+a['asset'], observed_net_pnl=None,
                evidence_mode='invented_validation', first_seen_market_utc=None,
                model_asof_mono_ns=snapshot['asof_mono_ns'], report_sha256=digest,
                source_report=rel, source_input_sha256=report['data_identity_sha256'],
                source_code_sha256=report['code_identity_sha256'],
                period_label='Cas fixe de12secondes inventées ; aucune séance de marché observée.',
                explanation='Compte de test avec montants inventés ; PnL observé inconnu.',
                market_validated=False, actual_order_allowed=False)
            result['paper_accounts'].append(row)
        for k in (1,2,3):
            t=report['entry_thresholds'][str(k)]
            result['paper_controls'].append({'key':'cost'+str(k),'cost_multiple':k,
                'expected_gross_quote':None,'calibrated_error_quote':None,
                'all_in_cost_quote':None,
                'expected_net_lower_quote':t['expected_net_lower_quote'], 'state':t['state'],
                'risk_state':report['risk_summary']['historical_state'],
                'missing_input':'Prévision de gain net calibrée, carnets synchronisés, frais, sessions et prix de financement liés aux événements.',
                'code_state':'codé et testé sur cas inventés','market_state':'inconnu',
                'new_prospective_days':0, 'actual_order_allowed':False,
                'reproduce':'python -m lab account --controls --out /tmp/R320-reproduction',
                'source_report':rel,'report_sha256':digest})
    except (OSError,ValueError,KeyError,TypeError):
        result['paper_accounts']=[]
        result['paper_controls']=[{'key':'unavailable','state':'UNAVAILABLE','risk_state':'UNKNOWN',
            'missing_input':'Rapport R320 complet et lisible absent ou invalide.',
            'expected_gross_quote':None,'expected_net_lower_quote':None,'calibrated_error_quote':None,
            'actual_order_allowed':False,'new_prospective_days':0}]
    try:
        coverage,_=read_report(root,'experiments/owner_acceptance_v1/requirements_coverage.json')
        result['paper_requirements']=coverage['items']
    except (OSError,ValueError,KeyError,TypeError):pass
    return result
