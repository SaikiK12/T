"""Independent literal inverse-cash examples, no market data/outcomes."""
from pathlib import Path
from fractions import Fraction as F
import hashlib,importlib.util,sys,json,tempfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
CODE=ROOT/'lab/inverse_cash.py'
EXPECTED='18d57d37737288a4655efdeaef8e15693a3565ba8f6d7c1a4a1c5bf0f589348f'
assert hashlib.sha256(CODE.read_bytes()).hexdigest()==EXPECTED
spec=importlib.util.spec_from_file_location('reviewed_inverse_cash',CODE);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
NS=10**9;anchor=m.FrameClock(1700000000*NS,NS)
contract=m.InverseContract('BTC-TEST','BTC','1','1',anchor.utc_ns+10*NS,'constructed-review')
checks=[]
def checked(name):checks.append(name)
def event(i,kind,p,q='0',fee='0',ident=None,at=None):
 t=anchor.utc_ns+i*NS
 return m.InverseEvent(ident or f'case-{i}',kind,contract.instrument,t,m.FrameClock(t,anchor.mono_ns+i*NS),'constructed-review',str(p),str(q),fee)
def post(a,i,kind,p,q='0',fee='0',ident=None):
 return a.post(event(i,kind,p,q,fee,ident),anchor.mono_ns+i*NS)
def account(coin,journal=None):return m.InverseCashAccount(contract,str(coin),anchor,journal_path=journal)
# Short200USD fills at100and200: hedge1+.5=1.5coins; no arithmeticVWAP.
a=account('1.5');assert post(a,1,'open',100,-100)['status']=='applied';assert post(a,2,'open',200,-100)['status']=='applied';assert a.entry_reciprocal==F(3,400)
assert post(a,3,'daily',80)['status']=='applied';assert a.coin==F(5,2);assert a.price_pnl==1
assert post(a,10,'delivery',500)['status']=='applied';assert a.coin==F(2,5);assert a.price_pnl==F(-11,10);assert a.coin*500==200;checked('two_price_short_daily_and_delivery_literal_coin')
# Long sign is inverse to short; positiveprice addscoin.
a=account(1);post(a,1,'open',100,100);post(a,2,'daily',200);assert a.coin==F(3,2);post(a,10,'delivery',50);assert a.coin==0;checked('long_sign_daily_positive_final_negative')
# Short:1coin+1coinfirstgain-1.5secondloss+.75finalgain=1.25.
a=account(1);post(a,1,'open',100,-100);post(a,2,'daily',50);assert a.coin==2;post(a,3,'daily',200);assert a.coin==F(1,2);post(a,10,'delivery',80);assert a.coin==F(5,4);assert a.coin*80==100;checked('multiple_daily_settlements_telescope_once')
# No daily settlements gives sameexact terminalcoin.
b=account(1);post(b,1,'open',100,-100);post(b,10,'delivery',80);assert a.snapshot()==b.snapshot();checked('direct_vs_daily_endpoint_identity')
# Addshort afterdaily:initial2coins,hedge1+.25=1.25, residual.75; final200/500+.75=1.15.
a=account(2);post(a,1,'open',100,-100);post(a,2,'daily',200);assert a.coin==F(3,2);assert post(a,3,'open',400,-100)['status']=='applied';post(a,10,'delivery',500);assert a.coin==F(23,20);checked('opening_after_daily_uses_reset_reciprocal')
# Oldshortlossmakesnew100USDshortinadmissible:cash1butmarkequity.5<newnotional1.
a=account(1);post(a,1,'open',100,-100);r=post(a,2,'open',200,-100);assert r['status']=='rejected' and 'full_coin_collateral_unavailable'in r['reasons'];assert a.face==-100;checked('opening_guard_includes_old_unrealized_loss')
# Oldlongprofitmakesnew200USDlongadmissible:equity1.5=currenttotalnotional1.5.
a=account(1);post(a,1,'open',100,100);assert post(a,2,'open',200,200)['status']=='applied';assert a.face==300;checked('opening_guard_includes_old_unrealized_gain')
# Unknownopeningfeeisnotzeroandblocksnewrisk.
a=account(2);r=post(a,1,'open',100,-100,None);assert r['entry_collateral_assessment']=='unknown_fee';assert a.snapshot()['coin_cash']is None;assert post(a,2,'open',200,-100)['status']=='rejected';checked('unknown_fee_withholds_cash_and_new_open')
# Duplicateclockdoesnotduplicatepayment; changedpayloadconflicts/withholdsnet.
a=account(2);post(a,1,'open',100,-100);post(a,2,'daily',50,ident='same-day');coin=a.coin
r=a.post(event(2,'daily',50,ident='same-day'),anchor.mono_ns+3*NS);assert r['status']=='duplicate'and a.coin==coin
r=a.post(event(2,'daily',60,ident='same-day'),anchor.mono_ns+3*NS);assert r['status']=='conflicting_revision'and a.coin==coin and a.snapshot()['coin_cash']is None;checked('duplicate_no_doublepost_conflict_withholds')
# Knownentrycoinfee0.001anddeliveryfee0.0025subtractonce.
a=account('1.501');post(a,1,'open',100,-100,'0.001');post(a,2,'open',200,-100);post(a,10,'delivery',80,fee='0.0025');assert a.coin==F(999,400);assert a.fees==F(7,2000);checked('entry_delivery_coin_fees_once')
# Explicit0isdistinctfromunknownsettlementfee.
a=account(1);post(a,1,'open',100,-100);post(a,10,'delivery',100,fee=None);assert a.snapshot()['coin_cash']is None and a.snapshot()['delivered'];checked('unknown_delivery_fee_preserved')
# Clockandexpiresneveroverridepositionorcreatecash.
a=account(2);post(a,1,'open',100,-100);assert 'delivery_before_expiry'in post(a,2,'delivery',100)['reasons'];assert 'opposite_fill_requires_separate_close_protocol'in post(a,3,'open',100,100)['reasons'];assert 'opening_at_or_after_expiry'in post(a,10,'open',100,-100)['reasons'];checked('premature_delivery_expired_open_and_opposite_rejected')
# Showninversebookwalkisreciprocalnotarithmetic.
fills,hedge=m.walk([['200','100'],['100','100']],'200',side='sell',unit='USD_face');assert hedge==F(3,2)and hedge!=F(4,3)
fills,proceeds=m.walk([['100','1'],['200','1']],'1.5',side='buy',unit='base');assert proceeds==200;checked('finite_depth_units_harmonic_vs_spot_cash')
try:m.walk([['200','100']],'200',side='sell',unit='USD_face')
except ValueError:pass
else:raise AssertionError('insufficientdepthnotrejected')
checked('no_depth_extrapolation')
# Exactcoin-afterfeeandactualspot/TWAPratio,notguaranteedface.
r=m.terminal_conversion('200','1.5','1.500525','0.000525','0.00025','80','0.875','0.0005')
assert r['residual_coin_delta']==0 and r['coin_after_delivery']==F(3999,1600)
assert r['usdt_proceeds']==F(175)*F(3999,4000)*F(1999,2000);assert r['usdt_proceeds']<175;checked('terminal_actual_exit_ratio_and_fees')
assert m.terminal_conversion(200,'1.5','1.5',0,0,None,1,0)is None
assert m.terminal_conversion(200,'1.5','1.5',0,0,80,None,0)is None;checked('unknown_delivery_or_exit_not_zero')
r=m.terminal_conversion(200,'1.5','1.6',0,0,80,1,0);assert r['residual_coin_delta']==F(1,10)and r['usdt_proceeds']==208;checked('excess_coin_reserve_retains_price_delta')
# Durablecashpathreplaymatchesanddedupattemptdoesnotdoublepost.
with tempfile.TemporaryDirectory()as td:
 p=Path(td)/'journal.jsonl';a=account(1,p);post(a,1,'open',100,-100);post(a,2,'daily',50);post(a,10,'delivery',80)
 b=account(1,p);assert a.snapshot()==b.snapshot();assert len(p.read_text().splitlines())==4
 checked('journal_reopen_literal_coin_balances')
# Largeexp/bool/floatrejectedbeforematerializingenormousFraction.
for v in ('1e-100000000000',True,1.0):
 try:m.rational(v)
 except ValueError:pass
 else:raise AssertionError('unsafeinputaccepted')
checked('exact_bounded_rational_input_guard')
out={'reviewed_code_sha256':EXPECTED,'scope':'conditional inverse component literal handchecks only; no market data/outcome/feeattestation','passed':len(checks),'checks':checks,'source_formula_corrobation':'oldformalURL404;fullreciprocalprimaryformulaunreceived','independent_market_observations':0}
Path(__file__).with_name('math_handchecks_final.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
