"""Invented quotes only: no touch fills, no old-trade fills and losses before recovery."""
from fractions import Fraction as F
import unittest

from lab.maker_pilot import num, replay

S = 1_000_000


def fixtures(end=30):
    quotes = [dict(t=t*S,bid=F(101),ask=F(103),bq=F(100),aq=F(100)) for t in range(end+1)]
    args = dict(start=0,end=end*S,quote_usd="102",lot="1",tick="1",min_base="1",min_quote="10",
                maker_fee="0",taker_fee="0",multiple=1)
    return quotes,args


def trade(i,tx,recv,price,size="1",maker_ask=0,liq=0):
    return dict(trade_id=i,tx_us=int(tx*S),t=int(recv*S),px=F(str(price)),sz=F(size),maker_ask=maker_ask,liq=liq)


class MakerPilotTests(unittest.TestCase):
    def test_touch_never_fills_and_contra_side_required(self):
        q,a=fixtures()
        ts=[trade(1,5,5.2,101),trade(2,6,6.2,100,maker_ask=1),trade(3,7,7.2,104,maker_ask=0)]
        r=replay(q,ts,**a)
        self.assertEqual(r['fills'],[])
        self.assertEqual(r['pnl'],'0.000000000000')

    def test_two_sided_ledger_fees_and_cost_stress(self):
        q,a=fixtures();ts=[trade(1,5,5.2,100),trade(2,20,20.2,104,maker_ask=1)]
        self.assertEqual(replay(q,ts,**a)['pnl'],'2.000000000000')
        a['maker_fee']='0.01'
        self.assertEqual([replay(q,ts,**dict(a,multiple=m))['pnl'] for m in (1,2,3)],['-0.040000000000','-2.080000000000','-4.120000000000'])

    def test_partial_fills_never_exceed_print_and_terminal_spread_costs(self):
        q,a=fixtures();a['lot']='0.1';a['min_base']='0.1'
        ts=[trade(1,5,5.2,100,size='0.5')]
        rs=[replay(q,ts,**dict(a,multiple=m)) for m in (1,2,3)]
        self.assertEqual(rs[0]['fills'][0]['quantity'],'0.500000000000')
        self.assertEqual([r['pnl']for r in rs],['0.000000000000','-0.500000000000','-1.000000000000'])

    def test_bootstrap_trade_cannot_fill_after_arrival(self):
        q,a=fixtures();ts=[trade(1,0.5,5,100)]
        self.assertEqual(replay(q,ts,**a)['fills'],[])

    def test_cancel_flight_keeps_old_order_exposed(self):
        q,a=fixtures();ts=[trade(1,15.5,15.7,100)]
        r=replay(q,ts,**a)
        self.assertEqual(len(r['fills']),1)
        self.assertEqual(r['fills'][0]['order'],0)

    def test_late_receive_can_report_a_pre_cancel_fill(self):
        q,a=fixtures();ts=[trade(1,15.5,17,100)]
        r=replay(q,ts,**a)
        self.assertTrue(r['fills'][0]['receive_after_effective_cancel'])

    def test_liquidation_and_execution_at_end_are_not_regular_fills(self):
        q,a=fixtures();ts=[trade(1,5,5.2,100,liq=1),trade(2,30,30.1,100)]
        self.assertEqual(replay(q,ts,**a)['fills'],[])

    def test_postonly_rejection_uses_arrival_state(self):
        q,a=fixtures()
        q[1].update(bid=F(99),ask=F(100))
        r=replay(q,[trade(1,5,5.2,100)],**a)
        self.assertEqual(r['fills'],[])
        self.assertLess(r['accepted_in_model'],r['hypothetical_orders'])

    def test_unpriced_exit_has_no_liquidatable_pnl(self):
        q,a=fixtures();q[-1]['bq']=F('0.5')
        r=replay(q,[trade(1,5,5.2,100)],**a)
        self.assertEqual(r['state'],'EXIT_DEPTH_UNQUALIFIED')
        self.assertIsNone(r['pnl'])

    def test_missing_trades_is_unknown_not_zero(self):
        q,a=fixtures();r=replay(q,None,**a)
        self.assertEqual(r['state'],'NO_TRADE_FILE')
        self.assertIsNone(r['pnl'])

    def test_delayed_inventory_ack_breach_suppresses_recovery(self):
        q,a=fixtures(60)
        ts=[trade(1,5,45.1,100),trade(2,20,45.2,100),trade(3,35,45.3,100),trade(4,50,50.1,104,size='3',maker_ask=1)]
        r=replay(q,ts,**a)
        self.assertEqual(r['state'],'INVENTORY_OR_CAPITAL_GUARD_BREACH')
        self.assertIsNone(r['pnl'])
        self.assertFalse(r['recovery_counted'])
        self.assertEqual(len(r['fills']),3)

    def test_current_tick_drift_and_nonfinite_or_duplicate_inputs_fail(self):
        q,a=fixtures();a['tick']='2'
        with self.assertRaises(ValueError):replay(q,[],**a)
        for x in [True,0.1,'NaN','Infinity']:
            with self.assertRaises(ValueError):num(x)
        q,a=fixtures()
        with self.assertRaises(ValueError):replay(q,[trade(1,5,5.2,100),trade(1,6,6.2,100)],**a)


if __name__=='__main__':
    unittest.main()
