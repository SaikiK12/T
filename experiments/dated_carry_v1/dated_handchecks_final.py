"""Independent literal adapter checks on invented books only, zero network."""
from pathlib import Path
from fractions import Fraction as F
from copy import deepcopy
import hashlib,importlib.util,sys,json
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
CODE=ROOT/'lab/dated_carry.py'
EXPECTED='ce0daa930a4f821f9eec13bbd0f10597ac4b67c9b2eee405f285b47ee64e94bb'
assert hashlib.sha256(CODE.read_bytes()).hexdigest()==EXPECTED
spec=importlib.util.spec_from_file_location('reviewed_dated_carry',CODE);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
U=1793000000*10**9;NS=10**9;EX=U+100*NS
checks=[]
def checked(n):checks.append(n)
def inputs():
 meta={'result':{'instrument_name':'BTC-TEST','kind':'future','instrument_type':'reversed','base_currency':'BTC','settlement_currency':'BTC','quote_currency':'USD','counter_currency':'USD','settlement_period':'month','expiration_timestamp':EX//10**6,'is_active':True,'min_trade_amount':'10','contract_size':'100','tick_size':'5','taker_commission':'0.00035'}}
 sm={'symbols':[{'symbol':'BTCUSDT','baseAsset':'BTC','quoteAsset':'USDT','baseAssetPrecision':2,'status':'1','isSpotTradingAllowed':True,'tradeSideType':1,'orderTypes':['MARKET'],'baseSizePrecision':'0','quoteAmountPrecisionMarket':'1','maxQuoteAmountMarket':'1000000','takerCommission':'0.0005'}]}
 s={'lastUpdateId':123,'bids':[['90','10']],'asks':[['100','10']]}
 d={'result':{'instrument_name':'BTC-TEST','timestamp':U//10**6,'state':'open','bids':[['110','100'],['100','150']],'asks':[['120','250']]}}
 r=m.Receipt(U,U+NS//10,0,NS//10)
 return meta,sm,s,d,r

def get_plan(v=None,profile='full'):
 meta,sm,s,d,r=v or inputs();return m.entry_plan(s,sm,r,d,m.rules(meta,'BTC-TEST','BTC',EX,'constructed-review'),r,profile=profile)
p=get_plan()
# Literal3xprices100/70, face100/150:hedge22/7; reserve1.00105; roundUPto.01=3.15.
assert p['initial_coin']==F(315,100);assert p['hedge_coin']==F(53,22);assert p['face_usd']==250
assert p['future_harmonic_entry_usd']==F(5500,53);assert p['spot_principal_usdt']==315;checked('fixed_face_harmonic_hedge_and_three_cost_coin_reserve')
# Contractsize100USDdoesnotforce100USDsteps: face250allowedatstep10.
assert m.rules(inputs()[0],'BTC-TEST','BTC',EX,'review').contract.face_step_usd==10
assert p['face_usd']/m.rules(inputs()[0],'BTC-TEST','BTC',EX,'review').contract_size_usd==F(5,2);checked('fractional_contracts_use_minimum_as_step_not_contract_size')
# Actual admitted/accountnet alwaysunknownforconditionaloutputs.
assert not p['executable_admission']and p['future_net_usdt']is None
assert not p['spot_base_unit_contract_verified']and not p['deribit_tick_size_steps_verified'];checked('source_grid_unit_admission_flags_withheld')
# Publicfee1/2/3literalprices110/100,105/85,100/70; sameqandface.
hedges={1:F(53,22),2:F(970,357),3:F(22,7)}
for k in (1,2,3):
 r=m.projected_result(p,cost_multiple=k,fee_control='public_standard',delivery_rate='0.00025',delivery_price=80,exit_ratio='0.98')
 h=hedges[k];ef=h*F(7,20000)*k;df=F(1,4000)*k;sf=F(1,2000)*k
 principal=F(315,100)*(95+5*k);initial=principal*(1+sf)
 coin=F(250,80)*(1-df)+(F(315,100)-ef-h)
 actual_sale=coin*F(392,5)*(1-sf) #exit78.4=80*.98
 assert r['stressed_hedge_coin']==h and r['entry_fee_coin']==ef
 assert r['initial_spend_usdt']==initial and r['conditional_net_usdt']==actual_sale-initial
 assert r['idle_cash_usdt']==10000-initial and r['conditional_net_on_total_capital']==(actual_sale-initial)/10000
 assert r['same_initial_coin_passive_net_usdt']==F(315,100)*F(392,5)*(1-sf)-initial
 assert r['actual_net_usdt']is None and not r['executable_admission']
 assert r['break_even_exit_ratio']==initial/(coin*80*(1-sf))
 assert r['residual_unhedged_coin']==F(315,100)-ef-h
checked('literal_all_three_cost_prices_fees_terminal_cash_passive_capital_hurdles')
# NofeecontrolkeepsSAMEqnotresizingtoidealhedge.
for k in (1,2,3):
 r=m.projected_result(p,cost_multiple=k,fee_control='zero_charge',delivery_rate='0.00025',delivery_price=80,exit_ratio='0.98')
 assert r['entry_fee_coin']==r['delivery_fee_rate']==r['spot_fee_rate']==0
 assert r['residual_unhedged_coin']==F(315,100)-hedges[k]
checked('zero_fee_control_same_quantity_and_reserve_delta')
# Topcapfailuredoesnotshrinkface250totop100.
try:get_plan(profile='top_only')
except ValueError as e:assert 'insufficient'in str(e)
else:raise AssertionError('topinsufficientsilentlyresized')
checked('top_capacity_failure_retains_fixed_face')
# Wherefulldepthandtopbothsupport, bothderiveqfromidenticalfullreference.
v=inputs();v[3]['result']['bids']=[['110','250']]
a=get_plan(v,'full');b=get_plan(v,'top_only');assert a['initial_coin']==b['initial_coin']==F(251,100);assert a['face_usd']==b['face_usd']==250;checked('supported_full_top_share_fixed_quantity')
# Haltedstateandlinearquantityrulescannotcomputeadmissibleplan.
v=inputs();v[3]['result']['state']='halted'
try:get_plan(v)
except ValueError as e:assert 'dated_not_open'in str(e)
else:raise AssertionError('haltedaccepted')
v=inputs();v[0]['result']['instrument_type']='linear'
try:get_plan(v)
except ValueError:pass
else:raise AssertionError('linearaccepted')
checked('visibility_not_tradability_and_inverse_identity')
# OffstepUSDshownquantitiesrejectratherthanbecomefractionaloffgridfills.
v=inputs();v[3]['result']['bids'][0][1]='99'
try:get_plan(v)
except ValueError as e:assert 'increment'in str(e)
else:raise AssertionError('offstepdepthaccepted')
checked('per_level_USD_amount_increment')
# Unknownterminalworldnevercreatesnetzero.
r=m.projected_result(p,cost_multiple=2,fee_control='public_standard',delivery_rate='0.00025');assert r['terminal']is None and r['conditional_net_usdt']is None;checked('unknown_future_exit_net_retained')
# Sameworldcostdoublecountfree: nofullpositionprincipalcredited,separatecoinsnotcountedtwice.
r=m.projected_result(p,cost_multiple=1,fee_control='zero_charge',delivery_rate=0,delivery_price=80,exit_ratio=1)
assert 10000+r['conditional_net_usdt']==r['idle_cash_usdt']+r['terminal']['usdt_proceeds'];checked('whole_capital_idle_plus_terminal_identity')
# Clockadversarialdiagnosticsare reported as findingsuntilrootfix.
s=m.Receipt(U,U+NS//10,0,NS//10)
d=m.Receipt(U+100*NS,U+100*NS+NS//10,NS//2,6*NS//10)
clock_flags=m.local_pair_flags(s,d,d.received_utc_ns)
assert 'cross_receipt_clock_step_over_50ms'in clock_flags
# Age is measured at common decision, not merely each response completion.
early=m.Receipt(U,U+19*NS//10,0,19*NS//10)
later=m.Receipt(U+27*NS//10,U+28*NS//10,27*NS//10,28*NS//10)
assert 'spot:decision_request_age_over_2s'in m.local_pair_flags(early,later,later.received_utc_ns)
# Fresh-looking own receipt publication is stale at later common decision.
dated=m.Receipt(U+18*NS//10,U+19*NS//10,18*NS//10,19*NS//10)
spot=m.Receipt(U+27*NS//10,U+28*NS//10,27*NS//10,28*NS//10)
assert any('dated_publication_age'in flag for flag in m.local_pair_flags(spot,dated,U))
# Negative source version and a book received after fixed expiry must reject.
v=inputs();v[2]['lastUpdateId']=-1
try:get_plan(v)
except ValueError:pass
else:raise AssertionError('negativeversionaccepted')
v=inputs();after=EX+NS;v[3]['result']['timestamp']=after//10**6
v=list(v);v[4]=m.Receipt(after,after+NS//10,101*NS,1011*NS//10)
try:get_plan(v)
except ValueError as e:assert 'opening_at_or_after_expiry'in str(e)
else:raise AssertionError('afterexpiryaccepted')

# Laterrootfix shouldmakeflagged; recordingallowsreviewofintermediatehashwithoutfabricatedpass.
out={'reviewed_code_sha256':EXPECTED,'scope':'constructed literal adapter cases; no marketdata/network; not wholecollector/bridge','passed_handchecks':len(checks),'checks':checks,'crossreceipt_clock_jump_flags':clock_flags,'known_clock_gap_fixed':bool(clock_flags),'new_market_observations':0,'additional_guard_regressions':['crossreceipt_clockstep','commondecision_request_age','commondecision_publication_age','negative_version','opening_after_expiry']}
Path(__file__).with_name('dated_handchecks_final.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
