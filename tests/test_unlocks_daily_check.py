import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

import numpy as np
import pandas as pd
from scripts import unlocks_daily_check as u


class UnlockDailyTests(unittest.TestCase):
    def bars(self):
        return {s:{d:(d,100.,110.,90.,1.,1000.) for d in range(u.START,u.START+100*u.DAY,u.DAY)}
                for s in ['TESTUSDT','BTCUSDT','OTHERUSDT','THIRDUSDT']}

    def test_exact_daily_times_cost_sign_and_intrahold_high(self):
        b=self.bars();d=u.START+50*u.DAY
        b['TESTUSDT'][d]=(d,232.,240.,90.,1.,1000.)
        p=u.price(b,'TESTUSDT',d)
        self.assertAlmostEqual(p['gross'],-1.32)
        self.assertAlmostEqual(p['max_adverse_high'],1.4)
        self.assertTrue(p['complete_hold_path'])
        b['TESTUSDT'][d-7*u.DAY]=(d-7*u.DAY,100.,999.,90.,1.,1000.)
        self.assertAlmostEqual(u.price(b,'TESTUSDT',d)['max_adverse_high'],1.4)

    def test_no_stale_substitution_zero_fill_or_reserved_dates(self):
        b=self.bars();d=u.START+50*u.DAY
        del b['TESTUSDT'][d]
        self.assertIsNone(u.price(b,'TESTUSDT',d))
        self.assertIsNone(u.price(b,'TESTUSDT',u.START-10*u.DAY))
        b=self.bars();b['TESTUSDT'][d]=(d,100.,110.,90.,0.,0.)
        self.assertIsNone(u.price(b,'TESTUSDT',d))
        b=self.bars();del b['TESTUSDT'][d-u.DAY]
        self.assertFalse(u.price(b,'TESTUSDT',d)['complete_hold_path'])
        self.assertIsNone(u.price(b,'TESTUSDT',d)['max_adverse_high'])

    def test_parser_requires_ms_daily_calendar_finite_consistent_ohlc(self):
        def blob(row):
            s=io.BytesIO()
            with zipfile.ZipFile(s,'w') as z:z.writestr('TESTUSDT-1d-2021-01.csv','open_time,open,high,low,close,volume,close_time,qv,count,tbv,tbq,ignore\n'+','.join(map(str,row))+'\n')
            return s.getvalue()
        row=[u.START,100,110,90,105,1,u.START+u.DAY-1,1000,3,.5,50,0]
        self.assertEqual(u.parse(blob(row),'TESTUSDT-1d-2021-01.zip')[0][1],105)
        for idx,value in [(0,u.START-u.DAY),(0,u.START*1000),(4,999),(5,-1),(7,float('nan'))]:
            bad=row.copy();bad[idx]=value
            with self.assertRaises(ValueError):u.parse(blob(bad),'TESTUSDT-1d-2021-01.zip')

    def test_cluster_se_independent_formula(self):
        days=np.array([u.START+3*u.DAY,u.START+4*u.DAY,u.START+10*u.DAY,u.START+17*u.DAY])
        x=np.array([.02,-.01,.04,-.02]);z=x-x.mean()
        se=np.sqrt(3/2*((z[0]+z[1])**2+z[2]**2+z[3]**2))/4
        self.assertAlmostEqual(u.summary(x,days)['cluster_t'],x.mean()/se)
        self.assertIsNone(u.summary([.1],days[:1])['cluster_t'])
        self.assertEqual(u.summary([],[])['n'],0)

    def test_seeded_matched_null_and_exclusion_band(self):
        bars=self.bars();d=u.START+50*u.DAY
        events=pd.DataFrame([{'perp':'TESTUSDT','day_ms':d}])
        scored=[{'perp':'TESTUSDT','gross':0}]
        a=u.null_test(bars,events,scored,10)
        self.assertEqual(a,u.null_test(bars,events,scored,10));self.assertEqual(a['p'],1.)
        # D=37..99 inclusive (63), excluding D=36..64 inclusive: 28 from this range.
        self.assertEqual(a['admissible_counts']['TESTUSDT'],35)

    def test_full_synthetic_decision_and_two_leg_costs(self):
        bars=self.bars();events=pd.DataFrame([{'day':pd.Timestamp(d,unit='ms',tz='UTC').strftime('%Y-%m-%d'),
            'day_ms':d,'perp':s,'venue':'binance','window':'archive','check':'verified'} for s,d in
            [('TESTUSDT',u.START+50*u.DAY),('OTHERUSDT',u.START+60*u.DAY),('THIRDUSDT',u.START+70*u.DAY),('BTCUSDT',u.START+80*u.DAY)]])
        with mock.patch.object(u,'null_test',return_value={'p':1.}):a,e,rows,v=u.evaluate(bars,events)
        self.assertEqual(v['verdict'],'NULL');self.assertEqual(v['priced_events'],4);self.assertEqual(e,[])
        np.testing.assert_allclose([r['mean'] for r in rows if r['label']=='primary'],[-.002,-.004,-.006])
        np.testing.assert_allclose([r['mean'] for r in rows if r['label']=='btc_hedged_two_leg_cost'],[-.004,-.008,-.012])
        self.assertEqual(v['trials'],2)

    def test_budget_refuses_before_network_and_no_overwrite(self):
        budget=u.Budget(u.MAX_TOTAL)
        with mock.patch.object(u.urllib.request,'urlopen') as opener:
            with self.assertRaises(ValueError):budget.get('https://example.com',100)
            opener.assert_not_called()
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileExistsError):u.run(Path(d)/'raw',Path(d))

    def test_changed_manifest_rejected_before_market_parse(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(u,'verify',return_value=('frozen',[])), mock.patch.object(u,'LANE',Path(d)), mock.patch.object(u,'parse') as parse:
            Path(d,'DATA.sha256').write_text('0'*64)
            Path(d,'manifest.json').write_text('{}')
            with self.assertRaises(ValueError):u.load(d)
            parse.assert_not_called()
